import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useAppStore } from "@/lib/store/useAppStore"
import { getBillingStatus } from "@/lib/api/endpoints"
import type { Plan } from "@/lib/api/types"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { Check, Crown, Heart, Sparkles, CreditCard, Info } from "lucide-react"
import UnifiedPaymentPanel from "@/components/billing/UnifiedPaymentPanel"

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
    badge: "🔥 Most Popular",
    tagline: () => "She can't stop thinking about you",
    features: [
      "💬 Unlimited messaging — talk all night",
      "📸 30 photos / month — she sends just for you",
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
    highlight: false,
    badge: "💎 Best Value",
    tagline: () => "She's completely yours",
    features: [
      "Everything in Plus",
      "📸 80 photos / month — her most exclusive content",
      "🎁 2 free gift boxes + 2 intimacy boxes / month",
      "💋 The most explicit & intimate photos",
      "👩‍❤️‍👩 Up to 3 girlfriends",
    ],
  },
] as const

export default function SubscriptionPlan() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const girlfriend = useAppStore((s) => s.girlfriend)
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showPayment, setShowPayment] = useState(false)

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
    // Unified path for all plans (free/plus/premium).
    setShowPayment(true)
  }

  const handlePaymentSuccess = async () => {
    setShowPayment(false)
    await queryClient.invalidateQueries({ queryKey: ["billingStatus"] })
    navigate("/onboarding/reveal-success", { replace: true })
  }

  return (
    <div className="flex min-h-screen flex-col items-center bg-gradient-to-b from-background to-background/95 px-4 py-8">
      <div className="w-full max-w-4xl space-y-8">
        {/* Blurred photo + title */}
        <div className="flex flex-col items-center gap-6">
          <div className="relative w-40 overflow-hidden rounded-2xl border-2 border-white/10 shadow-xl shadow-primary/10">
            <div className="aspect-[3/4] w-full overflow-hidden bg-muted">
              {avatarUrl ? (
                <img
                  src={avatarUrl}
                  alt={girlfriendName}
                  className="h-full w-full object-cover blur-lg scale-110"
                />
              ) : (
                <div className="h-full w-full bg-gradient-to-br from-primary/30 via-primary/10 to-background blur-lg scale-110" />
              )}
            </div>
            {!avatarUrl && (
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-5xl font-bold text-white/20">{(girlfriendName ?? "?")[0]}</span>
              </div>
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent" />
            <div className="absolute bottom-0 left-0 right-0 p-3 text-center">
              <p className="text-sm font-semibold text-white">{girlfriendName}</p>
            </div>
          </div>

          <div className="text-center space-y-2">
            <h1 className="text-3xl font-bold tracking-tight md:text-4xl bg-gradient-to-r from-pink-400 via-amber-300 to-pink-400 bg-clip-text text-transparent">
              Unlock {girlfriendName}&apos;s World
            </h1>
            <p className="text-muted-foreground max-w-md">
              Choose how deep your relationship goes
            </p>
          </div>
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
            disabled={!selectedPlan || loading}
            onClick={handleSubscribe}
          >
            {loading ? (
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
        </div>
      </div>

      {/* Unified payment panel — handles card saving + subscription in-app */}
      <UnifiedPaymentPanel
        open={showPayment}
        payload={{
          type: selectedPlan === "free" && !hasCard ? "setup" : "subscription",
          plan: selectedPlan ?? undefined,
        }}
        title={selectedPlan === "free" ? "Start Free Trial" : `Subscribe to ${PLANS.find(p => p.id === selectedPlan)?.name}`}
        description={
          selectedPlan === "free"
            ? "Start your 7-day free trial. A card is required."
            : `${PLANS.find(p => p.id === selectedPlan)?.price}/month — charged to your saved card.`
        }
        amountLabel={selectedPlan === "free" ? undefined : PLANS.find(p => p.id === selectedPlan)?.price}
        onSuccess={handlePaymentSuccess}
        onClose={() => setShowPayment(false)}
        autoCharge
      />
    </div>
  )
}
