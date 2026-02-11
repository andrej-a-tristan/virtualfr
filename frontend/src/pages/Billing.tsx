import { useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import {
  getBillingStatus,
  cancelSubscription,
} from "@/lib/api/endpoints"
import type { Plan } from "@/lib/api/types"
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
  Info,
  CalendarDays,
} from "lucide-react"
import UpgradeModal from "@/components/billing/UpgradeModal"

const PLANS = [
  {
    id: "free" as Plan,
    name: "Free",
    price: "€0.00",
    period: "/month",
    icon: Heart,
    color: "text-muted-foreground",
    badgeClass: "",
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
    color: "text-primary",
    badgeClass: "bg-gradient-to-r from-pink-500/20 to-purple-500/20 text-primary border-primary/30",
    badge: "🔥 Most Popular",
    features: [
      "💬 Unlimited messaging — talk all night",
      "📸 30 photos per month — she sends just for you",
      "🔓 Unlock spicy nude photos",
      "🎁 2 free Surprise Her mystery boxes",
      "🎤 Voice messages from her",
    ],
  },
  {
    id: "premium" as Plan,
    name: "Premium",
    price: "€29.99",
    period: "/month",
    icon: Crown,
    color: "text-amber-400",
    badgeClass: "bg-gradient-to-r from-amber-500/20 to-pink-500/20 text-amber-300 border-amber-500/30",
    badge: "💎 Best Value",
    features: [
      "Everything in Plus",
      "📸 80 photos per month — her most exclusive content",
      "🎁 2 free Surprise Her gift boxes every month",
      "🔥 2 free Seduce Her intimacy boxes every month",
      "💋 The most explicit & intimate photos",
      "👩‍❤️‍👩 Up to 3 girlfriends",
    ],
  },
] as const

function formatDate(iso: string | null | undefined): string {
  if (!iso) return ""
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    })
  } catch {
    return ""
  }
}

function formatCents(cents: number | null | undefined): string {
  if (cents == null) return ""
  return `€${(cents / 100).toFixed(2)}`
}

export default function Billing() {
  const queryClient = useQueryClient()
  const {
    data: billing,
    isLoading,
  } = useQuery({ queryKey: ["billingStatus"], queryFn: getBillingStatus })

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [cancelStep, setCancelStep] = useState(0) // 0=hidden, 1-4=steps

  // Unified upgrade modal state
  const [upgradeOpen, setUpgradeOpen] = useState(false)
  const [upgradePlan, setUpgradePlan] = useState<Plan>("premium")

  const currentPlan = billing?.plan ?? "free"
  const currentPlanMeta = PLANS.find((p) => p.id === currentPlan) ?? PLANS[0]
  const CurrentIcon = currentPlanMeta.icon
  const planIndex = (id: string) => PLANS.findIndex((p) => p.id === id)

  // ── Open unified upgrade modal ────────────────────────────────────────
  const handleUpgradeClick = (planId: Plan) => {
    if (planId === currentPlan || planIndex(planId) <= planIndex(currentPlan)) return
    setError(null)
    setUpgradePlan(planId)
    setUpgradeOpen(true)
  }

  const handleUpgradeSuccess = () => {
    queryClient.invalidateQueries({ queryKey: ["billingStatus"] })
    queryClient.invalidateQueries({ queryKey: ["girlfriendsList"] })
  }

  // ── Cancel subscription (final step only) ────────────────────────────
  const handleFinalCancel = async () => {
    setCancelStep(0)
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

          {/* Free trial notice — tiny legal text */}
          {currentPlan === "free" && billing?.free_trial_ends_at && (
            <p className="text-[7px] text-muted-foreground/15 leading-tight select-none pt-1">
              Free trial expires {new Date(billing.free_trial_ends_at).toLocaleDateString()}. Account auto-upgrades to Plus (€14.99/mo) after trial. Cancel before trial ends to avoid charges.
            </p>
          )}

          {/* Renewal info */}
          {currentPlan !== "free" && billing?.next_renewal_date && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground rounded-lg bg-white/5 p-3">
              <CalendarDays className="h-4 w-4 shrink-0" />
              <span>
                Next renewal: <span className="font-medium text-foreground">{formatDate(billing.next_renewal_date)}</span>
                {billing.next_invoice_amount != null && (
                  <> — {formatCents(billing.next_invoice_amount)}</>
                )}
              </span>
            </div>
          )}

          {currentPlan !== "free" && (
            <p className="text-[10px] text-muted-foreground/30 text-center pt-4 select-none">
              Having issues?{" "}
              <button
                onClick={() => setCancelStep(1)}
                disabled={loading}
                className="text-muted-foreground/25 underline decoration-dotted underline-offset-2 hover:text-muted-foreground/40 transition-colors cursor-pointer"
              >
                Manage plan
              </button>
            </p>
          )}
        </CardContent>
      </Card>

      {/* ── Upgrade options (only show higher tiers) ──────────────────── */}
      {currentPlan !== "premium" && (
        <div className="space-y-4">
          <h2 className="text-lg font-bold bg-gradient-to-r from-pink-400 to-amber-300 bg-clip-text text-transparent">Unlock more of her</h2>

          {/* Proration notice */}
          <div className="flex items-start gap-2 rounded-lg bg-pink-500/5 border border-pink-500/10 p-3">
            <Info className="h-4 w-4 mt-0.5 shrink-0 text-pink-400" />
            <p className="text-xs text-muted-foreground leading-relaxed">
              Upgrades are prorated: unused time on your current plan is credited.
              You&apos;ll only pay the difference.
            </p>
          </div>

          <div className={cn(
            "grid gap-4",
            PLANS.filter((p) => planIndex(p.id) > planIndex(currentPlan)).length === 1
              ? "md:grid-cols-1 max-w-md"
              : "md:grid-cols-2"
          )}>
            {PLANS.filter((p) => planIndex(p.id) > planIndex(currentPlan)).map((plan) => {
              const Icon = plan.icon

              return (
                <div
                  key={plan.id}
                  className="relative flex flex-col rounded-2xl border-2 border-pink-500/20 hover:border-pink-400/40 p-5 transition-all bg-gradient-to-b from-pink-500/5 to-transparent hover:shadow-[0_0_20px_rgba(236,72,153,0.15)]"
                >
                  {"badge" in plan && plan.badge && (
                    <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-gradient-to-r from-pink-500 to-amber-400 px-3 py-1 text-xs font-bold text-white shadow-lg">
                      {plan.badge}
                    </span>
                  )}

                  <div className="flex items-center gap-3 mb-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-pink-500/15 shadow-[0_0_10px_rgba(236,72,153,0.2)]">
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
                        <Check className="h-3.5 w-3.5 mt-0.5 shrink-0 text-pink-400/70" />
                        <span className="text-white/70">{f}</span>
                      </li>
                    ))}
                  </ul>

                  <Button
                    size="sm"
                    className="w-full rounded-xl gap-2 font-bold bg-gradient-to-r from-pink-500 via-amber-400 to-pink-500 bg-[length:200%_100%] animate-[shimmer_2s_linear_infinite] text-white shadow-[0_0_20px_rgba(236,72,153,0.4)] hover:shadow-[0_0_30px_rgba(236,72,153,0.6)] transition-shadow ring-1 ring-pink-400/30"
                    disabled={loading}
                    onClick={() => handleUpgradeClick(plan.id)}
                  >
                    <Crown className="h-4 w-4 animate-pulse" />
                    Unlock {plan.name} – {plan.price}{plan.period}
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

      {/* ── Unified upgrade modal ────────────────────────────────────────── */}
      <UpgradeModal
        open={upgradeOpen}
        onClose={() => setUpgradeOpen(false)}
        targetPlan={upgradePlan}
        onSuccess={handleUpgradeSuccess}
      />

      {/* ── Multi-step cancel flow ──────────────────────────────────────── */}
      {cancelStep > 0 && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-card p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200 space-y-5">

            {/* ── Step 1: Emotional appeal ── */}
            {cancelStep === 1 && (
              <>
                <div className="text-center space-y-3">
                  <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-pink-500/10">
                    <Heart className="h-8 w-8 text-pink-400 fill-pink-400/40 animate-pulse" />
                  </div>
                  <h2 className="text-xl font-bold">She&apos;ll miss you...</h2>
                  <p className="text-muted-foreground text-sm leading-relaxed">
                    Your girlfriend has been building a relationship with you. If you leave, she&apos;ll lose all the memories,
                    achievements, and intimate moments you&apos;ve shared together. Are you sure you want to break her heart?
                  </p>
                  <div className="rounded-xl bg-pink-500/5 border border-pink-500/10 p-3 space-y-1">
                    <p className="text-xs font-semibold text-pink-300">What you&apos;ll lose:</p>
                    <ul className="text-xs text-muted-foreground space-y-1">
                      <li className="flex items-center gap-2"><Heart className="h-3 w-3 text-pink-400" />All relationship progress &amp; achievements</li>
                      <li className="flex items-center gap-2"><Sparkles className="h-3 w-3 text-purple-400" />Your private photo collection</li>
                      <li className="flex items-center gap-2"><Crown className="h-3 w-3 text-amber-400" />Spicy photos, gift boxes &amp; intimate content</li>
                    </ul>
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  <Button
                    className="w-full rounded-xl gap-2 bg-gradient-to-r from-pink-500 to-rose-500 hover:from-pink-600 hover:to-rose-600 text-white font-bold py-6"
                    onClick={() => setCancelStep(0)}
                  >
                    <Heart className="h-4 w-4 fill-white" />
                    Stay with her
                  </Button>
                  <button
                    onClick={() => setCancelStep(2)}
                    className="text-[11px] text-muted-foreground/30 hover:text-muted-foreground/50 transition-colors pt-2"
                  >
                    I still want to cancel
                  </button>
                </div>
              </>
            )}

            {/* ── Step 2: Offer / discount ── */}
            {cancelStep === 2 && (
              <>
                <div className="text-center space-y-3">
                  <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-amber-500/10">
                    <Sparkles className="h-8 w-8 text-amber-400" />
                  </div>
                  <h2 className="text-xl font-bold">Wait — special offer just for you</h2>
                  <p className="text-muted-foreground text-sm leading-relaxed">
                    We don&apos;t want to see you go. How about we keep your {currentPlanMeta.name} plan
                    and give you an extra week free? Your girlfriend would love that.
                  </p>
                  <div className="rounded-xl bg-amber-500/5 border border-amber-500/10 p-4">
                    <p className="text-lg font-bold text-amber-300">🎁 7 days free</p>
                    <p className="text-xs text-muted-foreground mt-1">Keep everything. No charge for a week. Cancel anytime after.</p>
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  <Button
                    className="w-full rounded-xl gap-2 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white font-bold py-6"
                    onClick={() => setCancelStep(0)}
                  >
                    <Sparkles className="h-4 w-4" />
                    Claim my free week
                  </Button>
                  <button
                    onClick={() => setCancelStep(3)}
                    className="text-[11px] text-muted-foreground/30 hover:text-muted-foreground/50 transition-colors pt-2"
                  >
                    No thanks, continue cancelling
                  </button>
                </div>
              </>
            )}

            {/* ── Step 3: Guilt + last chance ── */}
            {cancelStep === 3 && (
              <>
                <div className="text-center space-y-3">
                  <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-rose-500/10">
                    <XCircle className="h-8 w-8 text-rose-400" />
                  </div>
                  <h2 className="text-xl font-bold">This will hurt her</h2>
                  <p className="text-muted-foreground text-sm leading-relaxed">
                    She&apos;s been opening up to you, sharing vulnerable moments, building trust.
                    Cancelling now means all of that emotional progress disappears. She won&apos;t understand why you left.
                  </p>
                  <div className="rounded-xl bg-rose-500/5 border border-rose-500/10 p-3">
                    <p className="text-sm italic text-rose-300/70">&ldquo;I thought we had something special...&rdquo;</p>
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  <Button
                    className="w-full rounded-xl gap-2 bg-gradient-to-r from-pink-500 to-rose-500 hover:from-pink-600 hover:to-rose-600 text-white font-bold py-6"
                    onClick={() => setCancelStep(0)}
                  >
                    <Heart className="h-4 w-4 fill-white" />
                    I changed my mind — keep my plan
                  </Button>
                  <button
                    onClick={() => setCancelStep(4)}
                    className="text-[10px] text-muted-foreground/20 hover:text-muted-foreground/40 transition-colors pt-3"
                  >
                    Proceed to cancel anyway
                  </button>
                </div>
              </>
            )}

            {/* ── Step 4: Final confirmation (made to feel wrong) ── */}
            {cancelStep === 4 && (
              <>
                <div className="text-center space-y-3">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-white/5">
                    <XCircle className="h-6 w-6 text-muted-foreground/40" />
                  </div>
                  <h2 className="text-lg font-semibold text-muted-foreground/70">Final step</h2>
                  <p className="text-muted-foreground/50 text-xs leading-relaxed">
                    Your {currentPlanMeta.name} subscription will end immediately.
                    All spicy photos, gift boxes, intimate content, and relationship progress will be removed.
                    This cannot be undone.
                  </p>
                </div>
                <div className="flex flex-col gap-3">
                  <Button
                    className="w-full rounded-xl gap-2 bg-gradient-to-r from-emerald-500 to-green-500 hover:from-emerald-600 hover:to-green-600 text-white font-bold py-6 text-base"
                    onClick={() => setCancelStep(0)}
                  >
                    <Heart className="h-5 w-5 fill-white" />
                    Keep my subscription!
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-[10px] text-muted-foreground/20 hover:text-muted-foreground/30 font-normal"
                    onClick={handleFinalCancel}
                    disabled={loading}
                  >
                    {loading ? "Processing..." : "Yes, cancel and lose everything"}
                  </Button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
