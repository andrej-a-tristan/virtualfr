import { useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import {
  getBillingStatus,
  subscribeToPlan,
  cancelSubscription,
} from "@/lib/api/endpoints"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import {
  Check,
  Crown,
  Heart,
  Sparkles,
  ArrowUpCircle,
  XCircle,
} from "lucide-react"
import AddCardModal from "@/components/billing/AddCardModal"

const PLANS = [
  {
    id: "free",
    name: "Free",
    price: "€0.00",
    period: "/month",
    icon: Heart,
    color: "text-muted-foreground",
    badgeClass: "",
    features: [
      "Reveal her photo",
      "50 messages / month",
    ],
  },
  {
    id: "plus",
    name: "Plus",
    price: "€14.99",
    period: "/month",
    icon: Sparkles,
    color: "text-primary",
    badgeClass: "bg-primary/20 text-primary border-primary/30",
    badge: "Most Popular",
    features: [
      "Everything in Free",
      "Voice messages",
      "Receive photos – 30 / month",
      "Unlock nude photos",
    ],
  },
  {
    id: "premium",
    name: "Premium",
    price: "€29.99",
    period: "/month",
    icon: Crown,
    color: "text-amber-400",
    badgeClass: "bg-amber-500/20 text-amber-300 border-amber-500/30",
    features: [
      "Everything in Plus",
      "Receive photos – 80 / month",
      "More intimate moments",
      "More nude photos",
    ],
  },
] as const

export default function Billing() {
  const queryClient = useQueryClient()
  const {
    data: billing,
    isLoading,
  } = useQuery({ queryKey: ["billingStatus"], queryFn: getBillingStatus })

  const [changingTo, setChangingTo] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showCardModal, setShowCardModal] = useState(false)
  const [pendingPlan, setPendingPlan] = useState<string | null>(null)
  const [showCancelConfirm, setShowCancelConfirm] = useState(false)
  const [showUpgradeConfirm, setShowUpgradeConfirm] = useState(false)
  const [upgradePlanId, setUpgradePlanId] = useState<string | null>(null)

  const currentPlan = billing?.plan ?? "free"
  const hasCard = billing?.has_card_on_file ?? false
  const currentPlanMeta = PLANS.find((p) => p.id === currentPlan) ?? PLANS[0]
  const CurrentIcon = currentPlanMeta.icon

  const planIndex = (id: string) => PLANS.findIndex((p) => p.id === id)
  const upgradePlanMeta = upgradePlanId ? PLANS.find((p) => p.id === upgradePlanId) : null

  // ── Change plan ──────────────────────────────────────────────────────
  const handleUpgradeClick = (planId: string) => {
    if (planId === currentPlan || planIndex(planId) <= planIndex(currentPlan)) return
    setError(null)

    // No card? Open card modal first
    if (!hasCard) {
      setPendingPlan(planId)
      setShowCardModal(true)
      return
    }

    // Card on file — show confirmation with price
    setUpgradePlanId(planId)
    setShowUpgradeConfirm(true)
  }

  const confirmUpgrade = async () => {
    if (!upgradePlanId) return
    setShowUpgradeConfirm(false)
    setChangingTo(upgradePlanId)
    setLoading(true)
    setError(null)
    try {
      await subscribeToPlan(upgradePlanId)
      await queryClient.invalidateQueries({ queryKey: ["billingStatus"] })
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to upgrade plan")
    } finally {
      setLoading(false)
      setChangingTo(null)
      setUpgradePlanId(null)
    }
  }

  const handleCardSaved = async () => {
    setShowCardModal(false)
    await queryClient.invalidateQueries({ queryKey: ["billingStatus"] })
    // Card saved — now show upgrade confirmation
    if (pendingPlan) {
      setUpgradePlanId(pendingPlan)
      setPendingPlan(null)
      setShowUpgradeConfirm(true)
    }
  }

  // ── Cancel subscription ──────────────────────────────────────────────
  const handleCancel = async () => {
    setShowCancelConfirm(false)
    setLoading(true)
    setError(null)
    try {
      await cancelSubscription()
      await queryClient.invalidateQueries({ queryKey: ["billingStatus"] })
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to cancel subscription")
    } finally {
      setLoading(false)
    }
  }

  // ── Loading ──────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">Billing</h1>
        <Skeleton className="h-40 w-full rounded-2xl" />
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold tracking-tight">Billing</h1>

      {/* ── Current plan card ──────────────────────────────────────────── */}
      <Card className="rounded-2xl border-white/10">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div
                className={cn(
                  "flex h-11 w-11 items-center justify-center rounded-xl",
                  currentPlan === "premium"
                    ? "bg-amber-500/15"
                    : currentPlan === "plus"
                      ? "bg-primary/15"
                      : "bg-white/10"
                )}
              >
                <CurrentIcon
                  className={cn("h-5 w-5", currentPlanMeta.color)}
                />
              </div>
              <div>
                <CardTitle className="text-lg">Current plan</CardTitle>
                <p className="text-sm text-muted-foreground">
                  {currentPlanMeta.price}
                  {currentPlanMeta.period}
                </p>
              </div>
            </div>
            <Badge
              className={cn(
                "capitalize text-sm px-3 py-1",
                currentPlanMeta.badgeClass
              )}
            >
              {currentPlanMeta.name}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <ul className="space-y-2">
            {currentPlanMeta.features.map((f) => (
              <li key={f} className="flex items-center gap-2 text-sm">
                <Check
                  className={cn(
                    "h-4 w-4 shrink-0",
                    currentPlanMeta.color
                  )}
                />
                <span className="text-muted-foreground">{f}</span>
              </li>
            ))}
          </ul>

          {currentPlan !== "free" && (
            <Button
              variant="outline"
              size="sm"
              className="gap-2 text-destructive border-destructive/30 hover:bg-destructive/10 hover:text-destructive"
              onClick={() => setShowCancelConfirm(true)}
              disabled={loading}
            >
              <XCircle className="h-4 w-4" />
              Cancel subscription
            </Button>
          )}
        </CardContent>
      </Card>

      {/* ── Upgrade options (only show higher tiers) ──────────────────── */}
      {currentPlan !== "premium" && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Upgrade your plan</h2>

          <div className={cn(
            "grid gap-4",
            PLANS.filter((p) => planIndex(p.id) > planIndex(currentPlan)).length === 1
              ? "md:grid-cols-1 max-w-md"
              : "md:grid-cols-2"
          )}>
            {PLANS.filter((p) => planIndex(p.id) > planIndex(currentPlan)).map((plan) => {
              const Icon = plan.icon
              const isProcessing = changingTo === plan.id && loading

              return (
                <div
                  key={plan.id}
                  className="relative flex flex-col rounded-2xl border-2 border-white/10 hover:border-white/20 p-5 transition-all"
                >
                  {"badge" in plan && plan.badge && (
                    <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground">
                      {plan.badge}
                    </span>
                  )}

                  <div className="flex items-center gap-3 mb-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/10">
                      <Icon className={cn("h-4 w-4", plan.color)} />
                    </div>
                    <div>
                      <h3 className="font-bold">{plan.name}</h3>
                      <p className="text-xs text-muted-foreground">
                        {plan.price}
                        {plan.period}
                      </p>
                    </div>
                  </div>

                  <ul className="space-y-2 mb-5 flex-1">
                    {plan.features.map((f) => (
                      <li
                        key={f}
                        className="flex items-start gap-2 text-xs"
                      >
                        <Check className="h-3.5 w-3.5 mt-0.5 shrink-0 text-white/40" />
                        <span className="text-muted-foreground">{f}</span>
                      </li>
                    ))}
                  </ul>

                  <Button
                    size="sm"
                    className="w-full rounded-xl gap-2"
                    disabled={loading}
                    onClick={() => handleUpgradeClick(plan.id)}
                  >
                    {isProcessing ? (
                      "Processing…"
                    ) : (
                      <>
                        <ArrowUpCircle className="h-4 w-4" />
                        Upgrade to {plan.name} – {plan.price}{plan.period}
                      </>
                    )}
                  </Button>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <p className="text-sm text-destructive text-center">{error}</p>
      )}

      {/* ── Card modal (when switching to paid without card) ─────────── */}
      <AddCardModal
        open={showCardModal}
        onClose={() => {
          setShowCardModal(false)
          setPendingPlan(null)
        }}
        onSaved={handleCardSaved}
        plan={pendingPlan ?? undefined}
      />

      {/* ── Upgrade confirmation modal ─────────────────────────────────── */}
      {showUpgradeConfirm && upgradePlanMeta && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
          <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-card p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200 space-y-5">
            <div className="text-center space-y-2">
              <div className={cn(
                "mx-auto flex h-12 w-12 items-center justify-center rounded-full",
                upgradePlanMeta.id === "premium" ? "bg-amber-500/15" : "bg-primary/15"
              )}>
                <upgradePlanMeta.icon className={cn("h-6 w-6", upgradePlanMeta.color)} />
              </div>
              <h2 className="text-xl font-semibold">Upgrade to {upgradePlanMeta.name}</h2>
              <p className="text-muted-foreground text-sm">
                You&apos;ll be charged{" "}
                <span className="font-semibold text-foreground">
                  {upgradePlanMeta.price}{upgradePlanMeta.period}
                </span>{" "}
                starting now. You can cancel anytime from this page.
              </p>
            </div>
            <div className="flex gap-3">
              <Button
                variant="outline"
                className="flex-1 rounded-xl"
                onClick={() => { setShowUpgradeConfirm(false); setUpgradePlanId(null) }}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button
                className="flex-1 rounded-xl gap-2"
                onClick={confirmUpgrade}
                disabled={loading}
              >
                {loading ? "Processing…" : `Confirm & pay ${upgradePlanMeta.price}`}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ── Cancel confirmation modal ──────────────────────────────────── */}
      {showCancelConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
          <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-card p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200 space-y-5">
            <div className="text-center space-y-2">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-destructive/15">
                <XCircle className="h-6 w-6 text-destructive" />
              </div>
              <h2 className="text-xl font-semibold">Cancel subscription?</h2>
              <p className="text-muted-foreground text-sm">
                You&apos;ll lose access to{" "}
                <span className="font-semibold text-foreground">
                  {currentPlanMeta.name}
                </span>{" "}
                features and be moved to the Free plan. This takes effect
                immediately.
              </p>
            </div>
            <div className="flex gap-3">
              <Button
                variant="outline"
                className="flex-1 rounded-xl"
                onClick={() => setShowCancelConfirm(false)}
                disabled={loading}
              >
                Keep plan
              </Button>
              <Button
                variant="destructive"
                className="flex-1 rounded-xl"
                onClick={handleCancel}
                disabled={loading}
              >
                {loading ? "Cancelling…" : "Cancel subscription"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
