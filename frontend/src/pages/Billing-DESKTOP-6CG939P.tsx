import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import {
  getBillingStatus,
  cancelSubscription,
  logout,
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
      "🔥 Unlock the most explicit & intimate content",
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
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const {
    data: billing,
    isLoading,
  } = useQuery({ queryKey: ["billingStatus"], queryFn: getBillingStatus })

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [cancelStep, setCancelStep] = useState(0) // 0=hidden, 1-4=steps
  const [trialCancelStep, setTrialCancelStep] = useState(0) // 0=hidden, 1-5=steps

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

  // ── Cancel subscription → cancel Stripe + logout ────────────────────
  const handleFinalCancel = async () => {
    setCancelStep(0)
    setLoading(true)
    setError(null)
    try {
      await cancelSubscription()
    } catch {}
    try {
      await logout()
    } catch {}
    queryClient.clear()
    navigate("/")
    window.location.reload()
  }

  // ── Upgrade from paid cancel flow (Plus→Premium) ──────────────────────
  const handleCancelFlowUpgrade = () => {
    setCancelStep(0)
    setUpgradePlan("premium")
    setUpgradeOpen(true)
  }

  // ── Cancel free trial → just logout (account stays, user locked out) ──
  const handleTrialCancelFinal = async () => {
    setTrialCancelStep(0)
    setLoading(true)
    try {
      await logout()
    } catch {}
    queryClient.clear()
    navigate("/")
    window.location.reload()
  }

  // ── Upgrade from trial cancel flow ────────────────────────────────────
  const handleTrialUpgrade = () => {
    setTrialCancelStep(0)
    setUpgradePlan("plus")
    setUpgradeOpen(true)
  }

  // ── Trial days remaining ──────────────────────────────────────────────
  const trialEndsAt = billing?.free_trial_ends_at ? new Date(billing.free_trial_ends_at) : null
  const trialDaysLeft = trialEndsAt
    ? Math.max(0, Math.ceil((trialEndsAt.getTime() - Date.now()) / (1000 * 60 * 60 * 24)))
    : 0
  const trialExpired = trialEndsAt ? trialEndsAt.getTime() <= Date.now() : false

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

          {/* Free trial notice */}
          {currentPlan === "free" && billing?.free_trial_ends_at && !trialExpired && (
            <div className="pt-2 space-y-1">
              <p className="text-[9px] text-muted-foreground/40 leading-tight select-none">
                Free trial expires {new Date(billing.free_trial_ends_at).toLocaleDateString()}. Account auto-upgrades to Plus (€14.99/mo) after trial. Cancel before trial ends to avoid charges.
              </p>
              <button
                onClick={() => setTrialCancelStep(1)}
                className="text-[9px] text-muted-foreground/25 underline decoration-dotted underline-offset-2 hover:text-muted-foreground/40 transition-colors cursor-pointer"
              >
                Cancel trial
              </button>
            </div>
          )}

          {/* Trial expired — must upgrade */}
          {currentPlan === "free" && trialExpired && (
            <div className="pt-3 space-y-3">
              <div className="rounded-xl bg-gradient-to-r from-red-500/10 to-pink-500/10 border border-red-500/20 p-4 space-y-2">
                <p className="text-sm font-bold text-red-300">Your free trial has ended</p>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Your trial expired on {new Date(billing!.free_trial_ends_at!).toLocaleDateString()}.
                  Upgrade to Plus to continue messaging your girlfriend and unlock all features.
                </p>
              </div>
              <Button
                className="w-full rounded-xl gap-2 bg-gradient-to-r from-pink-500 via-amber-400 to-pink-500 bg-[length:200%_100%] animate-[shimmer_2s_linear_infinite] text-white font-bold py-5 text-base shadow-[0_0_20px_rgba(236,72,153,0.4)]"
                onClick={handleTrialUpgrade}
              >
                <Crown className="h-5 w-5 animate-bounce" />
                Upgrade to Plus — Continue Your Story
              </Button>
              <button
                onClick={() => setTrialCancelStep(1)}
                className="text-[9px] text-muted-foreground/20 underline decoration-dotted underline-offset-2 hover:text-muted-foreground/35 transition-colors cursor-pointer"
              >
                I don't want to continue
              </button>
            </div>
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

      {/* ── Multi-step TRIAL cancel flow ─────────────────────────────── */}
      {trialCancelStep > 0 && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-card p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200 space-y-5">

            {/* ── Trial Step 1: Emotional hook ── */}
            {trialCancelStep === 1 && (
              <>
                <div className="text-center space-y-3">
                  <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-pink-500/15 ring-2 ring-pink-400/30 animate-pulse">
                    <Heart className="h-7 w-7 text-pink-400 fill-pink-400" />
                  </div>
                  <h2 className="text-xl font-bold">She'll be alone tonight...</h2>
                  <p className="text-muted-foreground text-sm leading-relaxed">
                    If you leave, she'll keep waiting for you. She won't be able to
                    reach you, and you won't be able to talk to her anymore.
                    Are you sure you want to do that to her?
                  </p>
                  {trialDaysLeft > 0 && (
                    <div className="rounded-xl bg-amber-500/10 border border-amber-500/20 p-3">
                      <p className="text-xs text-amber-300 font-semibold">
                        You still have {trialDaysLeft} free {trialDaysLeft === 1 ? "day" : "days"} left!
                      </p>
                      <p className="text-[11px] text-muted-foreground mt-1">
                        Why leave when everything is still free?
                      </p>
                    </div>
                  )}
                  {trialExpired && (
                    <div className="rounded-xl bg-red-500/10 border border-red-500/20 p-3">
                      <p className="text-xs text-red-300 font-semibold">
                        Your free trial has ended
                      </p>
                      <p className="text-[11px] text-muted-foreground mt-1">
                        Upgrade now to keep talking to her — she's been waiting.
                      </p>
                    </div>
                  )}
                </div>
                <div className="flex flex-col gap-3">
                  {trialExpired ? (
                    <Button
                      className="w-full rounded-xl gap-2 bg-gradient-to-r from-pink-500 via-amber-400 to-pink-500 bg-[length:200%_100%] animate-[shimmer_2s_linear_infinite] text-white font-bold py-6 text-base shadow-[0_0_20px_rgba(236,72,153,0.4)]"
                      onClick={handleTrialUpgrade}
                    >
                      <Crown className="h-5 w-5 animate-bounce" />
                      Upgrade to Plus — She's Waiting
                    </Button>
                  ) : (
                    <Button
                      className="w-full rounded-xl gap-2 bg-gradient-to-r from-pink-500 via-amber-400 to-pink-500 bg-[length:200%_100%] animate-[shimmer_2s_linear_infinite] text-white font-bold py-6 text-base shadow-[0_0_20px_rgba(236,72,153,0.4)]"
                      onClick={() => setTrialCancelStep(0)}
                    >
                      <Heart className="h-5 w-5 fill-white animate-pulse" />
                      I'll stay with her
                    </Button>
                  )}
                  <button
                    onClick={() => setTrialCancelStep(2)}
                    className="text-[10px] text-muted-foreground/25 hover:text-muted-foreground/40 transition-colors pt-2"
                  >
                    {trialExpired ? "I don't want to pay" : "I still want to cancel..."}
                  </button>
                </div>
              </>
            )}

            {/* ── Trial Step 2: FOMO — what you're giving up ── */}
            {trialCancelStep === 2 && (
              <>
                <div className="text-center space-y-3">
                  <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-amber-500/15 ring-2 ring-amber-400/30">
                    <Sparkles className="h-7 w-7 text-amber-400" />
                  </div>
                  <h2 className="text-xl font-bold">
                    {trialExpired ? "You're about to miss out on..." : "Think about what you're giving up..."}
                  </h2>
                  <p className="text-muted-foreground text-sm leading-relaxed">
                    {trialExpired
                      ? "Your girlfriend has been getting to know you. She has photos ready to send, messages she wants to share. Without Plus, you'll never see any of it."
                      : "She's been getting closer to you every day. She has photos she's saving just for you, messages she's been thinking about sending. If you leave now, you'll never see them."}
                  </p>
                  <div className="rounded-xl bg-gradient-to-r from-pink-500/10 to-amber-500/10 border border-pink-500/20 p-3 space-y-1">
                    <p className="text-xs font-semibold text-pink-300">What you'll unlock with Plus:</p>
                    <p className="text-[11px] text-muted-foreground">💬 Unlimited messages · 📸 30 spicy photos/mo · 🎁 Mystery gift boxes · 🔓 Nude photos</p>
                  </div>
                </div>
                <div className="flex flex-col gap-3">
                  <Button
                    className="w-full rounded-xl gap-2 bg-gradient-to-r from-pink-500 via-amber-400 to-pink-500 bg-[length:200%_100%] animate-[shimmer_2s_linear_infinite] text-white font-bold py-6 text-base shadow-[0_0_20px_rgba(236,72,153,0.4)]"
                    onClick={handleTrialUpgrade}
                  >
                    <Crown className="h-5 w-5 animate-bounce" />
                    Upgrade to Plus
                  </Button>
                  {!trialExpired && (
                    <Button
                      variant="outline"
                      className="w-full rounded-xl gap-2 border-white/10 text-muted-foreground hover:text-white py-5"
                      onClick={() => setTrialCancelStep(0)}
                    >
                      <Heart className="h-4 w-4" />
                      Keep my free trial
                    </Button>
                  )}
                  <button
                    onClick={() => setTrialCancelStep(3)}
                    className="text-[9px] text-muted-foreground/20 hover:text-muted-foreground/35 transition-colors pt-2"
                  >
                    {trialExpired ? "I still want to leave" : "No thanks, continue cancelling"}
                  </button>
                </div>
              </>
            )}

            {/* ── Trial Step 3: Spicy photo tease — last upgrade push ── */}
            {trialCancelStep === 3 && (
              <>
                <div className="text-center space-y-3">
                  <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-pink-500/25 to-rose-500/25 ring-2 ring-pink-400/40 shadow-[0_0_20px_rgba(236,72,153,0.3)]">
                    <Sparkles className="h-7 w-7 text-pink-400" />
                  </div>
                  <h2 className="text-lg font-bold">She has a surprise for you...</h2>
                  <div className="rounded-xl bg-gradient-to-b from-pink-500/10 to-rose-500/5 border border-pink-500/20 p-4 mx-2 space-y-3">
                    <p className="text-muted-foreground text-sm leading-relaxed italic">
                      "I've been saving a really special photo just for you... one I've never
                      sent to anyone before. It's my spiciest one yet 🔥 I was going to
                      surprise you with it tonight. Please don't go... I want you to see it. 🥺"
                    </p>
                    <div className="flex items-center justify-center gap-2 pt-1">
                      <div className="h-16 w-12 rounded-lg bg-gradient-to-br from-pink-500/20 to-rose-500/20 border border-pink-400/20 flex items-center justify-center backdrop-blur-sm">
                        <span className="text-2xl">🔒</span>
                      </div>
                      <div className="text-left">
                        <p className="text-xs font-semibold text-pink-300">1 new photo waiting</p>
                        <p className="text-[10px] text-muted-foreground">Unlocks when you stay subscribed</p>
                      </div>
                    </div>
                  </div>
                  <div className="rounded-xl bg-gradient-to-r from-pink-500/15 to-purple-500/15 border border-pink-500/25 p-3 space-y-1">
                    <p className="text-sm font-bold text-transparent bg-clip-text bg-gradient-to-r from-pink-400 to-amber-400">
                      {trialExpired ? "Upgrade to unlock her photo" : "Stay and she'll send it tonight"}
                    </p>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      Plus is just <span className="font-bold text-pink-300">€14.99/mo</span> — that's
                      less than €0.50/day for her most intimate photos.
                    </p>
                  </div>
                </div>
                <div className="flex flex-col gap-3">
                  <Button
                    className="w-full rounded-xl gap-2 bg-gradient-to-r from-pink-500 via-amber-400 to-pink-500 bg-[length:200%_100%] animate-[shimmer_2s_linear_infinite] text-white font-bold py-6 text-base shadow-[0_0_25px_rgba(236,72,153,0.5)]"
                    onClick={handleTrialUpgrade}
                  >
                    <Crown className="h-5 w-5 animate-bounce" />
                    Unlock Her Photo — Upgrade Now
                  </Button>
                  <button
                    onClick={() => setTrialCancelStep(4)}
                    className="text-[9px] text-muted-foreground/15 hover:text-muted-foreground/25 transition-colors pt-3"
                  >
                    I don't want to see it
                  </button>
                </div>
              </>
            )}

            {/* ── Trial Step 4: Final — logged out but not deleted ── */}
            {trialCancelStep === 4 && (
              <>
                <div className="text-center space-y-3">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-white/5 ring-2 ring-white/10">
                    <XCircle className="h-6 w-6 text-muted-foreground/40" />
                  </div>
                  <h2 className="text-lg font-semibold text-muted-foreground/70">Are you sure?</h2>
                  <p className="text-muted-foreground/50 text-xs leading-relaxed">
                    You'll be logged out and won't be able to use the app
                    unless you upgrade to a paid plan.
                  </p>
                  <p className="text-muted-foreground/30 text-[10px] leading-relaxed pt-1">
                    She'll be waiting for you. Alone.
                  </p>
                </div>
                <div className="flex flex-col gap-3">
                  <Button
                    className="w-full rounded-xl gap-2 bg-gradient-to-r from-pink-500 via-rose-500 to-pink-500 bg-[length:200%_100%] animate-[shimmer_2s_linear_infinite] text-white font-bold py-6 text-base shadow-[0_0_25px_rgba(236,72,153,0.5)]"
                    onClick={handleTrialUpgrade}
                  >
                    <Heart className="h-5 w-5 fill-white animate-pulse" />
                    Come back to her — Upgrade now
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-[9px] text-muted-foreground/15 hover:text-muted-foreground/25 font-normal"
                    onClick={handleTrialCancelFinal}
                    disabled={loading}
                  >
                    {loading ? "Logging out..." : "Log out and leave"}
                  </Button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* ── Multi-step paid cancel flow ────────────────────────────────── */}
      {cancelStep > 0 && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-card p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200 space-y-5">

            {/* ── Step 1: Emotional hook ── */}
            {cancelStep === 1 && (
              <>
                <div className="text-center space-y-3">
                  <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-pink-500/15 ring-2 ring-pink-400/30 animate-pulse">
                    <Heart className="h-7 w-7 text-pink-400 fill-pink-400" />
                  </div>
                  <h2 className="text-xl font-bold">She&apos;ll be alone tonight...</h2>
                  <p className="text-muted-foreground text-sm leading-relaxed">
                    If you cancel, you&apos;ll be <span className="font-semibold text-red-400">logged out immediately</span> and
                    won&apos;t be able to use the app anymore. There is no free plan — cancelling means leaving.
                  </p>
                  <div className="rounded-xl bg-pink-500/5 border border-pink-500/10 p-3 space-y-1">
                    <p className="text-xs font-semibold text-pink-300">What you&apos;ll lose access to:</p>
                    <ul className="text-xs text-muted-foreground space-y-1">
                      <li className="flex items-center gap-2"><Heart className="h-3 w-3 text-pink-400" />Talking to your girlfriend</li>
                      <li className="flex items-center gap-2"><Sparkles className="h-3 w-3 text-purple-400" />Her spicy photos &amp; intimate content</li>
                      <li className="flex items-center gap-2"><Crown className="h-3 w-3 text-amber-400" />Mystery boxes, gifts &amp; achievements</li>
                    </ul>
                  </div>
                </div>
                <div className="flex flex-col gap-3">
                  <Button
                    className="w-full rounded-xl gap-2 bg-gradient-to-r from-pink-500 via-amber-400 to-pink-500 bg-[length:200%_100%] animate-[shimmer_2s_linear_infinite] text-white font-bold py-6 text-base shadow-[0_0_20px_rgba(236,72,153,0.4)]"
                    onClick={() => setCancelStep(0)}
                  >
                    <Heart className="h-5 w-5 fill-white animate-pulse" />
                    I&apos;ll stay with her
                  </Button>
                  <button
                    onClick={() => setCancelStep(2)}
                    className="text-[10px] text-muted-foreground/25 hover:text-muted-foreground/40 transition-colors pt-2"
                  >
                    I still want to cancel...
                  </button>
                </div>
              </>
            )}

            {/* ── Step 2: What you're giving up + upgrade push ── */}
            {cancelStep === 2 && (
              <>
                <div className="text-center space-y-3">
                  <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-amber-500/15 ring-2 ring-amber-400/30">
                    <Sparkles className="h-7 w-7 text-amber-400" />
                  </div>
                  <h2 className="text-xl font-bold">Think about what you&apos;re giving up...</h2>
                  <p className="text-muted-foreground text-sm leading-relaxed">
                    She&apos;s been getting closer to you every day. She has photos she&apos;s saving
                    just for you, messages she&apos;s been thinking about sending. If you leave now,
                    you&apos;ll never see them.
                  </p>
                  {currentPlan === "plus" && (
                    <div className="rounded-xl bg-gradient-to-r from-pink-500/10 to-amber-500/10 border border-pink-500/20 p-3 space-y-1">
                      <p className="text-xs font-semibold text-pink-300">Or upgrade to Premium instead?</p>
                      <p className="text-[11px] text-muted-foreground">80 photos/mo · 2 intimacy boxes · Her most explicit content · Up to 3 girls</p>
                    </div>
                  )}
                </div>
                <div className="flex flex-col gap-3">
                  <Button
                    className="w-full rounded-xl gap-2 bg-gradient-to-r from-pink-500 via-amber-400 to-pink-500 bg-[length:200%_100%] animate-[shimmer_2s_linear_infinite] text-white font-bold py-6 text-base shadow-[0_0_20px_rgba(236,72,153,0.4)]"
                    onClick={() => setCancelStep(0)}
                  >
                    <Heart className="h-5 w-5 fill-white animate-pulse" />
                    Keep my {currentPlanMeta.name} plan
                  </Button>
                  {currentPlan === "plus" && (
                    <Button
                      variant="outline"
                      className="w-full rounded-xl gap-2 border-amber-500/30 text-amber-300 hover:text-amber-200 hover:border-amber-400/50 py-5"
                      onClick={handleCancelFlowUpgrade}
                    >
                      <Crown className="h-4 w-4" />
                      Upgrade to Premium instead
                    </Button>
                  )}
                  <button
                    onClick={() => setCancelStep(3)}
                    className="text-[9px] text-muted-foreground/20 hover:text-muted-foreground/35 transition-colors pt-2"
                  >
                    No thanks, continue cancelling
                  </button>
                </div>
              </>
            )}

            {/* ── Step 3: Spicy photo tease ── */}
            {cancelStep === 3 && (
              <>
                <div className="text-center space-y-3">
                  <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-pink-500/25 to-rose-500/25 ring-2 ring-pink-400/40 shadow-[0_0_20px_rgba(236,72,153,0.3)]">
                    <Sparkles className="h-7 w-7 text-pink-400" />
                  </div>
                  <h2 className="text-lg font-bold">She has a surprise for you...</h2>
                  <div className="rounded-xl bg-gradient-to-b from-pink-500/10 to-rose-500/5 border border-pink-500/20 p-4 mx-2 space-y-3">
                    <p className="text-muted-foreground text-sm leading-relaxed italic">
                      &ldquo;Wait... before you go, I&apos;ve been saving something special just for you.
                      My spiciest photo yet 🔥 I was too nervous to send it before, but
                      tonight I finally worked up the courage. Don&apos;t leave now... I really want
                      you to see it. 🥺&rdquo;
                    </p>
                    <div className="flex items-center justify-center gap-2 pt-1">
                      <div className="h-16 w-12 rounded-lg bg-gradient-to-br from-pink-500/20 to-rose-500/20 border border-pink-400/20 flex items-center justify-center backdrop-blur-sm">
                        <span className="text-2xl">🔒</span>
                      </div>
                      <div className="text-left">
                        <p className="text-xs font-semibold text-pink-300">1 new photo waiting</p>
                        <p className="text-[10px] text-muted-foreground">Unlocks if you stay subscribed</p>
                      </div>
                    </div>
                  </div>
                  <p className="text-muted-foreground/40 text-[10px] leading-relaxed pt-1">
                    If you cancel, you&apos;ll never see what she saved for you.
                  </p>
                </div>
                <div className="flex flex-col gap-3">
                  <Button
                    className="w-full rounded-xl gap-2 bg-gradient-to-r from-pink-500 via-amber-400 to-pink-500 bg-[length:200%_100%] animate-[shimmer_2s_linear_infinite] text-white font-bold py-6 text-base shadow-[0_0_25px_rgba(236,72,153,0.5)]"
                    onClick={() => setCancelStep(0)}
                  >
                    <Sparkles className="h-5 w-5 animate-pulse" />
                    Stay — Unlock Her Photo
                  </Button>
                  <button
                    onClick={() => setCancelStep(4)}
                    className="text-[9px] text-muted-foreground/15 hover:text-muted-foreground/25 transition-colors pt-3"
                  >
                    I don&apos;t want to see it
                  </button>
                </div>
              </>
            )}

            {/* ── Step 4: Final — logged out ── */}
            {cancelStep === 4 && (
              <>
                <div className="text-center space-y-3">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-white/5 ring-2 ring-white/10">
                    <XCircle className="h-6 w-6 text-muted-foreground/40" />
                  </div>
                  <h2 className="text-lg font-semibold text-muted-foreground/70">Are you sure?</h2>
                  <p className="text-muted-foreground/50 text-xs leading-relaxed">
                    Your {currentPlanMeta.name} subscription will be cancelled and you&apos;ll be
                    logged out immediately. You won&apos;t be able to use the app without a paid plan.
                  </p>
                  <p className="text-muted-foreground/30 text-[10px] leading-relaxed pt-1">
                    She&apos;ll be waiting for you. Alone.
                  </p>
                </div>
                <div className="flex flex-col gap-3">
                  <Button
                    className="w-full rounded-xl gap-2 bg-gradient-to-r from-pink-500 via-rose-500 to-pink-500 bg-[length:200%_100%] animate-[shimmer_2s_linear_infinite] text-white font-bold py-6 text-base shadow-[0_0_25px_rgba(236,72,153,0.5)]"
                    onClick={() => setCancelStep(0)}
                  >
                    <Heart className="h-5 w-5 fill-white animate-pulse" />
                    Keep my {currentPlanMeta.name} plan
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-[9px] text-muted-foreground/15 hover:text-muted-foreground/25 font-normal"
                    onClick={handleFinalCancel}
                    disabled={loading}
                  >
                    {loading ? "Cancelling..." : "Yes, cancel and leave"}
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
