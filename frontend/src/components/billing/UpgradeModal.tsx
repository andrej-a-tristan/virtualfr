import { useState, useEffect, useCallback } from "react"
import { useQueryClient } from "@tanstack/react-query"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Crown, Sparkles, Users, Check, CreditCard, Info, ArrowUpCircle } from "lucide-react"
import { previewPlanChange, changePlan } from "@/lib/api/endpoints"
import type { Plan, PreviewPlanChangeResponse } from "@/lib/api/types"
import AddCardModal from "./AddCardModal"

/** Format cents → display string like "€14.99" */
function formatCents(cents: number, currency = "eur"): string {
  const abs = Math.abs(cents)
  const symbol = currency === "eur" ? "€" : currency === "usd" ? "$" : currency.toUpperCase() + " "
  const str = `${symbol}${(abs / 100).toFixed(2)}`
  return cents < 0 ? `-${str}` : str
}

/** Format ISO date → readable string like "Mar 15, 2026" */
function formatDate(iso: string): string {
  if (!iso) return "your next billing date"
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    })
  } catch {
    return iso
  }
}

const PLAN_META: Record<string, { name: string; price: string; icon: typeof Crown; color: string; features: string[] }> = {
  plus: {
    name: "Plus",
    price: "€14.99/month",
    icon: Sparkles,
    color: "text-primary",
    features: [
      "Voice messages",
      "Receive photos – 30/month",
      "Unlock nude photos",
    ],
  },
  premium: {
    name: "Premium",
    price: "€29.99/month",
    icon: Crown,
    color: "text-amber-400",
    features: [
      "Up to 5 girls",
      "Receive photos – 80/month",
      "More intimate moments",
      "Unlimited messages & images",
    ],
  },
}

interface UpgradeModalProps {
  open: boolean
  onClose: () => void
  /** Target plan to upgrade to. Defaults to "premium" */
  targetPlan?: Plan
  /** Called after successful plan change */
  onSuccess?: () => void
}

export default function UpgradeModal({
  open,
  onClose,
  targetPlan = "premium",
  onSuccess,
}: UpgradeModalProps) {
  const queryClient = useQueryClient()
  const [loading, setLoading] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState(false)
  const [showCardModal, setShowCardModal] = useState(false)
  const [preview, setPreview] = useState<PreviewPlanChangeResponse | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  const plan = targetPlan === "free" ? "premium" : targetPlan
  const meta = PLAN_META[plan] ?? PLAN_META.premium
  const PlanIcon = meta.icon

  // ── Load proration preview when modal opens ─────────────────────────
  const loadPreview = useCallback(async () => {
    setPreviewLoading(true)
    try {
      const data = await previewPlanChange(plan)
      setPreview(data)
    } catch {
      // Preview failed — still allow upgrade, just without proration info
      setPreview(null)
    } finally {
      setPreviewLoading(false)
    }
  }, [plan])

  useEffect(() => {
    if (open) {
      setError("")
      setSuccess(false)
      setPreview(null)
      loadPreview()
    }
  }, [open, loadPreview])

  // ── Confirm upgrade ─────────────────────────────────────────────────
  const handleConfirm = async () => {
    setConfirming(true)
    setError("")
    try {
      const res = await changePlan(plan)
      if (res.ok) {
        setSuccess(true)
        queryClient.invalidateQueries({ queryKey: ["billingStatus"] })
        queryClient.invalidateQueries({ queryKey: ["girlfriendsList"] })
        onSuccess?.()
        setTimeout(() => {
          setSuccess(false)
          onClose()
        }, 1500)
      } else {
        setError("Plan change failed. Please try again.")
      }
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || ""
      if (msg === "NO_PAYMENT_METHOD" || msg.includes("card") || msg.includes("payment method") || msg.includes("No Stripe customer")) {
        setShowCardModal(true)
        setError("")
      } else {
        setError(msg || "Failed to change plan")
      }
    } finally {
      setConfirming(false)
    }
  }

  // ── Card saved → retry upgrade ──────────────────────────────────────
  const handleCardSaved = async () => {
    setShowCardModal(false)
    await queryClient.invalidateQueries({ queryKey: ["billingStatus"] })
    await handleConfirm()
  }

  // ── Reset on close ──────────────────────────────────────────────────
  const handleClose = () => {
    if (confirming) return
    setError("")
    setSuccess(false)
    setPreview(null)
    onClose()
  }

  return (
    <>
      <Dialog open={open && !showCardModal} onOpenChange={(v) => !v && handleClose()}>
        <DialogContent className="max-w-md border-white/10 bg-card">
          <DialogHeader className="text-center">
            <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-amber-400 to-pink-500 shadow-lg">
              {success ? (
                <Check className="h-7 w-7 text-white" />
              ) : (
                <PlanIcon className="h-7 w-7 text-white" />
              )}
            </div>
            <DialogTitle className="text-xl font-bold">
              {success ? `You're on ${meta.name}!` : `Upgrade to ${meta.name}`}
            </DialogTitle>
            <DialogDescription className="text-muted-foreground">
              {success
                ? plan === "premium"
                  ? "You can now create up to 5 girls"
                  : "Enjoy your upgraded experience"
                : "Unlock the full experience"}
            </DialogDescription>
          </DialogHeader>

          {!success && (
            <div className="space-y-4 py-4">
              {/* Features */}
              <div className="space-y-3">
                {meta.features.map((f) => (
                  <div key={f} className="flex items-start gap-3 rounded-lg bg-white/5 p-3">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                    <p className="text-sm">{f}</p>
                  </div>
                ))}
              </div>

              {/* Proration preview */}
              <div className="rounded-lg bg-white/5 p-4 space-y-2">
                {previewLoading ? (
                  <div className="flex items-center justify-center gap-2 py-2">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                    <span className="text-sm text-muted-foreground">Calculating price...</span>
                  </div>
                ) : preview ? (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Due today (prorated)</span>
                      <span className="text-lg font-bold">
                        {formatCents(preview.amount_due_now, preview.currency)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Then monthly</span>
                      <span className="text-sm font-semibold">
                        {formatCents(preview.next_recurring_amount, preview.currency)}/mo
                      </span>
                    </div>
                    {preview.next_renewal_date && (
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Next renewal</span>
                        <span className="text-sm">{formatDate(preview.next_renewal_date)}</span>
                      </div>
                    )}
                    {preview.proration_line_items.length > 0 && (
                      <div className="mt-2 border-t border-white/10 pt-2 space-y-1">
                        {preview.proration_line_items.map((item, i) => (
                          <div key={i} className="flex items-center justify-between text-xs text-muted-foreground">
                            <span className="truncate max-w-[70%]">{item.description}</span>
                            <span>{formatCents(item.amount, item.currency)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-center">
                    <p className="text-lg font-bold">{meta.price}</p>
                    <p className="text-xs text-muted-foreground">Cancel anytime from settings</p>
                  </div>
                )}
              </div>

              {/* Proration explanation */}
              <div className="flex items-start gap-2 rounded-lg bg-blue-500/5 border border-blue-500/10 p-3">
                <Info className="h-4 w-4 mt-0.5 shrink-0 text-blue-400" />
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Upgrades are prorated: unused time on your current plan is credited.
                  You can cancel anytime from settings.
                </p>
              </div>

              {error && (
                <p className="text-center text-sm text-red-400">{error}</p>
              )}
            </div>
          )}

          {!success && (
            <div className="flex gap-3">
              <Button
                variant="ghost"
                className="flex-1"
                onClick={handleClose}
                disabled={confirming}
              >
                Not now
              </Button>
              <Button
                className="flex-1 bg-gradient-to-r from-amber-500 to-pink-500 font-semibold text-white shadow-lg hover:from-amber-600 hover:to-pink-600"
                onClick={handleConfirm}
                disabled={confirming || previewLoading}
              >
                {confirming ? (
                  <span className="flex items-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    Processing...
                  </span>
                ) : preview ? (
                  <span className="flex items-center gap-2">
                    <ArrowUpCircle className="h-4 w-4" />
                    Confirm & pay {formatCents(preview.amount_due_now, preview.currency)}
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <ArrowUpCircle className="h-4 w-4" />
                    Subscribe & Pay
                  </span>
                )}
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Card modal — shown when user has no card saved */}
      <AddCardModal
        open={showCardModal}
        onClose={() => setShowCardModal(false)}
        onSaved={handleCardSaved}
        plan={plan}
      />
    </>
  )
}
