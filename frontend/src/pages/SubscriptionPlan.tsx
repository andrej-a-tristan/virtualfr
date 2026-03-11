import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useAppStore } from "@/lib/store/useAppStore"
import { getBillingStatus, changePlan, previewPlanChange } from "@/lib/api/endpoints"
import type { Plan, PreviewPlanChangeResponse } from "@/lib/api/types"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { Check, Crown, Heart, Sparkles, CreditCard, Info, ArrowUpCircle } from "lucide-react"
import AddCardModal from "@/components/billing/AddCardModal"

const PLANS = [
  {
    id: "free" as Plan,
    name: "Free",
    price: "€0.00",
    period: "/month",
    icon: Heart,
    highlight: false,
    tagline: (name: string) => `Say hi to ${name}`,
    features: [
      "7-day free trial",
      "20 messages per day",
      "See her profile photo",
    ],
  },
  {
    id: "plus" as Plan,
    name: "Plus",
    price: "€14.99",
    period: "/month",
    icon: Sparkles,
    highlight: true,
    badge: "Most Popular",
    tagline: () => "She can't stop thinking about you",
    features: [
      "Unlimited messaging — talk all night",
      "30 photos / month — she sends just for you",
      "Unlock spicy nude photos",
      "2 free Surprise Her mystery boxes",
      "Voice messages from her",
    ],
  },
  {
    id: "premium" as Plan,
    name: "Premium",
    price: "€29.99",
    period: "/month",
    icon: Crown,
    highlight: false,
    badge: "Best Value",
    tagline: () => "She's completely yours",
    features: [
      "Everything in Plus",
      "80 photos / month — her most exclusive content",
      "2 free gift boxes + 2 intimacy boxes / month",
      "The most explicit & intimate photos",
      "Up to 3 girlfriends",
    ],
  },
] as const

function formatCents(cents: number, currency = "eur"): string {
  const abs = Math.abs(cents)
  const symbol = currency === "eur" ? "€" : currency === "usd" ? "$" : currency.toUpperCase() + " "
  const str = `${symbol}${(abs / 100).toFixed(2)}`
  return cents < 0 ? `-${str}` : str
}

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

export default function SubscriptionPlan() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const girlfriend = useAppStore((s) => s.girlfriend)
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showCardModal, setShowCardModal] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [preview, setPreview] = useState<PreviewPlanChangeResponse | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  const { data: billing } = useQuery({
    queryKey: ["billingStatus"],
    queryFn: getBillingStatus,
    retry: false,
    staleTime: 10_000,
  })

  const hasCard = billing?.has_card_on_file ?? false

  const girlfriendName =
    girlfriend?.display_name || girlfriend?.name || "Your Girl"
  const avatarUrl = girlfriend?.avatar_url || null

  const handleSubscribe = async () => {
    if (!selectedPlan) return

    // Every plan requires a card on file
    if (!hasCard) {
      setShowCardModal(true)
      return
    }

    // Free plan — no payment needed
    if (selectedPlan === "free") {
      await finishSubscription()
      return
    }

    // Paid plan — load proration preview and show confirmation
    setPreviewLoading(true)
    try {
      const data = await previewPlanChange(selectedPlan)
      setPreview(data)
    } catch {
      setPreview(null)
    } finally {
      setPreviewLoading(false)
    }
    setShowConfirm(true)
  }

  const handleConfirmPurchase = async () => {
    setShowConfirm(false)
    await finishSubscription()
  }

  const finishSubscription = async () => {
    if (!selectedPlan) return
    setLoading(true)
    setError(null)
    try {
      if (selectedPlan !== "free") {
        await changePlan(selectedPlan)
      }
      await queryClient.invalidateQueries({ queryKey: ["billingStatus"] })
      navigate("/onboarding/reveal-success", { replace: true })
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || ""
      if (msg === "NO_PAYMENT_METHOD" || msg.includes("card") || msg.includes("payment method")) {
        setShowCardModal(true)
        setError(null)
      } else {
        setError(msg || "Subscription failed")
      }
    } finally {
      setLoading(false)
    }
  }

  const handleCardSaved = async () => {
    setShowCardModal(false)
    await queryClient.invalidateQueries({ queryKey: ["billingStatus"] })
    await finishSubscription()
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Progress bar */}
      <div className="fixed top-0 inset-x-0 z-50">
        <div className="h-1 bg-muted">
          <div className="h-full bg-primary w-[95%]" />
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center px-4 py-10">
        <div className="w-full max-w-4xl space-y-8">
          {/* Header */}
          <div className="text-center space-y-3">
            <h1 className="text-3xl md:text-4xl font-serif text-foreground">
              Choose your <span className="text-primary">experience</span>
            </h1>
            <p className="text-muted-foreground max-w-md mx-auto">
              Unlock everything {girlfriendName} has to offer
            </p>
          </div>

        {/* Plan cards */}
        <div className="grid gap-4 md:grid-cols-3">
          {PLANS.map((plan) => {
            const Icon = plan.icon
            const isSelected = selectedPlan === plan.id
            return (
              <button
                key={plan.id}
                type="button"
                onClick={() => setSelectedPlan(plan.id)}
                className={cn(
                  "relative flex flex-col rounded-2xl border-2 p-6 text-left transition-all",
                  plan.highlight && !isSelected
                    ? "border-primary/50 bg-primary/5"
                    : isSelected
                      ? "border-primary bg-primary/10 scale-[1.02] shadow-lg shadow-primary/20"
                      : "border-white/10 hover:border-white/20 hover:scale-[1.01]"
                )}
              >
                {plan.highlight && "badge" in plan && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground">
                    {plan.badge}
                  </span>
                )}

                <div className="flex items-center gap-3 mb-2">
                  <div
                    className={cn(
                      "flex h-10 w-10 items-center justify-center rounded-xl",
                      plan.highlight
                        ? "bg-primary/20 text-primary"
                        : "bg-white/10 text-white/70"
                    )}
                  >
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold">{plan.name}</h3>
                  </div>
                </div>

                <p className="text-sm text-muted-foreground mb-4 italic">
                  &ldquo;{plan.tagline(girlfriendName)}&rdquo;
                </p>

                <div className="mb-5">
                  <span className="text-3xl font-bold">{plan.price}</span>
                  <span className="text-muted-foreground text-sm">
                    {plan.period}
                  </span>
                </div>

                <ul className="space-y-2.5 flex-1">
                  {plan.features.map((feature) => (
                    <li
                      key={feature}
                      className="flex items-start gap-2 text-sm"
                    >
                      <Check
                        className={cn(
                          "h-4 w-4 mt-0.5 shrink-0",
                          plan.highlight ? "text-primary" : "text-white/50"
                        )}
                      />
                      <span className="text-muted-foreground">{feature}</span>
                    </li>
                  ))}
                </ul>

                {/* Selection indicator */}
                <div
                  className={cn(
                    "mt-5 rounded-xl border-2 py-2.5 text-center text-sm font-bold transition-all",
                    isSelected && plan.id !== "free"
                      ? "border-pink-400 bg-gradient-to-r from-pink-500 via-amber-400 to-pink-500 bg-[length:200%_100%] animate-[shimmer_2s_linear_infinite] text-white shadow-[0_0_15px_rgba(236,72,153,0.4)]"
                      : isSelected
                        ? "border-primary bg-primary text-primary-foreground"
                        : plan.id !== "free"
                          ? "border-pink-500/30 text-pink-300/80 hover:border-pink-400/50 hover:shadow-[0_0_10px_rgba(236,72,153,0.2)] transition-all"
                          : "border-white/10 text-muted-foreground"
                  )}
                >
                  {isSelected ? (plan.id === "free" ? "Selected" : "Selected") : (plan.id === "free" ? "Start 7-day trial" : "Unlock now")}
                </div>
              </button>
            )
          })}
        </div>

        {/* Proration notice */}
        {billing?.plan !== "free" && (
          <div className="flex items-start gap-2 rounded-lg bg-blue-500/5 border border-blue-500/10 p-3 max-w-sm mx-auto">
            <Info className="h-4 w-4 mt-0.5 shrink-0 text-blue-400" />
            <p className="text-xs text-muted-foreground leading-relaxed">
              Upgrades are prorated: unused time on your current plan is credited.
            </p>
          </div>
        )}

        {/* Error message */}
        {error && (
          <p className="text-sm text-destructive text-center">{error}</p>
        )}

        {/* Subscribe button */}
        <div className="flex flex-col items-center gap-3 pt-2">
          <Button
            size="lg"
            className={cn(
              "w-full max-w-sm rounded-xl text-base gap-2 font-bold transition-all",
              selectedPlan && selectedPlan !== "free"
                ? "bg-gradient-to-r from-pink-500 via-amber-400 to-pink-500 bg-[length:200%_100%] animate-[shimmer_2s_linear_infinite] text-white shadow-[0_0_25px_rgba(236,72,153,0.5)] hover:shadow-[0_0_40px_rgba(236,72,153,0.7)] ring-2 ring-pink-400/30"
                : ""
            )}
            disabled={!selectedPlan || loading || previewLoading}
            onClick={handleSubscribe}
          >
            {loading || previewLoading ? (
              "Processing…"
            ) : hasCard ? (
              selectedPlan === "free" ? "Start 7-day free trial" : (
                <>
                  <Crown className="h-5 w-5 animate-pulse" />
                  Unlock Her Now
                </>
              )
            ) : selectedPlan === "free" ? (
              <>
                <CreditCard className="h-4 w-4" />
                Add card & continue
              </>
            ) : (
              <>
                <Crown className="h-5 w-5 animate-pulse" />
                Unlock Her Now
              </>
            )}
          </Button>
          <p className="text-xs text-muted-foreground text-center max-w-sm">
            {selectedPlan === "free"
              ? "Try everything free for 7 days. Upgrade anytime from settings."
              : "Upgrades are prorated. You can cancel anytime from settings."}
          </p>
          {selectedPlan === "free" && (
            <p className="text-[9px] text-muted-foreground/40 text-center max-w-xs leading-tight mt-2">
              Free trial lasts 7 days. After the trial period, your account will be automatically upgraded to the Plus plan (€14.99/mo). A valid payment method is required to continue. You may cancel before the trial ends to avoid charges.
            </p>
          )}
          
          {/* Skip option */}
          <button
            type="button"
            className="text-sm text-muted-foreground/60 hover:text-muted-foreground transition-colors mt-4"
            onClick={() => navigate("/app/girl", { replace: true })}
          >
            Skip for now and start chatting
          </button>
        </div>
        </div>
      </div>

      {/* Stripe card modal */}
      <AddCardModal
        open={showCardModal}
        onClose={() => setShowCardModal(false)}
        onSaved={handleCardSaved}
        plan={selectedPlan ?? undefined}
      />

      {/* Confirm purchase modal (when card already on file) */}
      {showConfirm && selectedPlan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
          <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-card p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200 space-y-5">
            <div className="text-center space-y-2">
              <h2 className="text-xl font-semibold">Confirm subscription</h2>

              {preview ? (
                <div className="space-y-3 text-left">
                  <div className="rounded-lg bg-white/5 p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Due today</span>
                      <span className="font-bold">{formatCents(preview.amount_due_now, preview.currency)}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Then monthly</span>
                      <span className="text-sm font-semibold">{formatCents(preview.next_recurring_amount, preview.currency)}/mo</span>
                    </div>
                    {preview.next_renewal_date && (
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Next renewal</span>
                        <span className="text-sm">{formatDate(preview.next_renewal_date)}</span>
                      </div>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground text-center">
                    Using your card on file for the{" "}
                    <span className="font-semibold text-foreground">
                      {PLANS.find((p) => p.id === selectedPlan)?.name}
                    </span>{" "}
                    plan.
                  </p>
                </div>
              ) : (
                <p className="text-muted-foreground text-sm">
                  You&apos;ll be charged{" "}
                  <span className="font-semibold text-foreground">
                    {PLANS.find((p) => p.id === selectedPlan)?.price}
                    /month
                  </span>{" "}
                  for the{" "}
                  <span className="font-semibold text-foreground">
                    {PLANS.find((p) => p.id === selectedPlan)?.name}
                  </span>{" "}
                  plan using your card on file.
                </p>
              )}
            </div>
            <div className="flex gap-3">
              <Button
                variant="outline"
                className="flex-1 rounded-xl"
                onClick={() => { setShowConfirm(false); setPreview(null) }}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button
                className="flex-1 rounded-xl gap-2"
                onClick={handleConfirmPurchase}
                disabled={loading}
              >
                {loading ? "Processing…" : preview ? (
                  <>
                    <ArrowUpCircle className="h-4 w-4" />
                    Confirm & pay {formatCents(preview.amount_due_now, preview.currency)}
                  </>
                ) : "Confirm & pay"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
