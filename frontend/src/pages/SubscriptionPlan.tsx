import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useAppStore } from "@/lib/store/useAppStore"
import { getBillingStatus } from "@/lib/api/endpoints"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { Check, Crown, Heart, Sparkles, CreditCard } from "lucide-react"
import AddCardModal from "@/components/billing/AddCardModal"

const PLANS = [
  {
    id: "free",
    name: "Free",
    price: "€0.00",
    period: "/month",
    icon: Heart,
    highlight: false,
    tagline: (name: string) => `Meet ${name} and chat to her`,
    features: [
      "Reveal her photo",
      "Unlimited messaging",
    ],
  },
  {
    id: "plus",
    name: "Plus",
    price: "€14.99",
    period: "/month",
    icon: Sparkles,
    highlight: true,
    badge: "Most Popular",
    tagline: () => "Your sweetheart",
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
    highlight: false,
    tagline: () => "Exclusive relationship",
    features: [
      "Everything in Plus",
      "Receive photos – 80 / month",
      "More intimate moments",
      "More nude photos",
    ],
  },
] as const

export default function SubscriptionPlan() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const girlfriend = useAppStore((s) => s.girlfriend)
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [showCardModal, setShowCardModal] = useState(false)

  const { data: billing } = useQuery({
    queryKey: ["billingStatus"],
    queryFn: getBillingStatus,
    retry: false,
    staleTime: 10_000,
  })

  const hasCard = billing?.has_card_on_file ?? false

  const girlfriendName =
    girlfriend?.display_name || girlfriend?.name || "Your Girl"
  const avatarUrl = girlfriend?.avatar_url || "/assets/companion-avatar.png"

  const handleSubscribe = async () => {
    if (!selectedPlan) return

    // Every plan requires a card on file
    if (!hasCard) {
      setShowCardModal(true)
      return
    }

    // Card already saved — proceed
    await finishSubscription()
  }

  const finishSubscription = async () => {
    setLoading(true)
    // Simulate subscription processing
    await new Promise((r) => setTimeout(r, 800))
    setLoading(false)
    navigate("/app/chat", { replace: true })
  }

  const handleCardSaved = async () => {
    setShowCardModal(false)
    // Refetch billing status to confirm card is on file
    await queryClient.invalidateQueries({ queryKey: ["billingStatus"] })
    // Card saved — now finish the subscription
    await finishSubscription()
  }

  return (
    <div className="flex min-h-screen flex-col items-center bg-gradient-to-b from-background to-background/95 px-4 py-8">
      <div className="w-full max-w-4xl space-y-8">
        {/* Blurred photo + title */}
        <div className="flex flex-col items-center gap-6">
          <div className="relative w-40 overflow-hidden rounded-2xl border-2 border-white/10 shadow-xl shadow-primary/10">
            <div className="aspect-[3/4] w-full overflow-hidden bg-muted">
              <img
                src={avatarUrl}
                alt={girlfriendName}
                className="h-full w-full object-cover blur-lg scale-110"
              />
            </div>
            <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent" />
            <div className="absolute bottom-0 left-0 right-0 p-3 text-center">
              <p className="text-sm font-semibold text-white">{girlfriendName}</p>
            </div>
          </div>

          <div className="text-center space-y-2">
            <h1 className="text-3xl font-bold tracking-tight md:text-4xl">
              Choose a plan
            </h1>
            <p className="text-muted-foreground max-w-md">
              Reveal {girlfriendName}&apos;s photo and unlock your full experience
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
                    "mt-5 rounded-xl border-2 py-2.5 text-center text-sm font-semibold transition-colors",
                    isSelected
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-white/10 text-muted-foreground"
                  )}
                >
                  {isSelected ? "Selected" : "Select plan"}
                </div>
              </button>
            )
          })}
        </div>

        {/* Subscribe button */}
        <div className="flex flex-col items-center gap-3 pt-2">
          <Button
            size="lg"
            className="w-full max-w-sm rounded-xl text-base gap-2"
            disabled={!selectedPlan || loading}
            onClick={handleSubscribe}
          >
            {loading ? (
              "Processing…"
            ) : hasCard ? (
              selectedPlan === "free" ? "Continue for free" : "Subscribe & reveal"
            ) : (
              <>
                <CreditCard className="h-4 w-4" />
                {selectedPlan === "free" ? "Add card & continue" : "Add card & subscribe"}
              </>
            )}
          </Button>
          <p className="text-xs text-muted-foreground text-center max-w-sm">
            {selectedPlan === "free"
              ? "You won\u2019t be charged unless you upgrade. You can cancel anytime from settings."
              : "You can cancel anytime from settings."}
          </p>
        </div>
      </div>

      {/* Stripe card modal */}
      <AddCardModal
        open={showCardModal}
        onClose={() => setShowCardModal(false)}
        onSaved={handleCardSaved}
        plan={selectedPlan ?? undefined}
      />
    </div>
  )
}
