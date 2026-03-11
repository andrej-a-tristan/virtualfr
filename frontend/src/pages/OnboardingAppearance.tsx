import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { getOnboardingPromptImages, guestSession } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import OnboardingSignIn from "@/components/onboarding/OnboardingSignIn"

const VIBE_OPTIONS = ["cute", "elegant", "sporty", "goth", "girl-next-door", "model"] as const
type VibeOption = (typeof VIBE_OPTIONS)[number]

export default function OnboardingAppearance() {
  const navigate = useNavigate()
  const appearance = useAppStore((s) => s.onboardingAppearance)
  const setOnboardingAppearance = useAppStore((s) => s.setOnboardingAppearance)
  const user = useAppStore((s) => s.user)
  const setUser = useAppStore((s) => s.setUser)
  const [selected, setSelected] = useState<VibeOption | "">(appearance?.vibe ?? "")

  // Ensure we have a guest session when landing on this page
  useEffect(() => {
    if (!user) {
      guestSession()
        .then(({ user }) => setUser(user))
        .catch(() => {
          // Backend might be down - continue anyway, store state locally
        })
    }
  }, [user, setUser])

  const { data: promptImages } = useQuery({
    queryKey: ["onboardingPromptImages"],
    queryFn: getOnboardingPromptImages,
  })

  const handleContinue = () => {
    if (!selected) return
    setOnboardingAppearance({ ...appearance, vibe: selected as VibeOption })
    navigate("/onboarding/appearance/age", { replace: true })
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-8">
      <OnboardingSignIn />
      <div className="w-full max-w-3xl space-y-10">
        {/* Premium hero title */}
        <div className="text-center space-y-4">
          <p className="text-primary text-sm font-medium tracking-[0.2em] uppercase">
            Step 1 of 5
          </p>
          <h1 className="text-4xl font-serif font-medium text-foreground md:text-5xl lg:text-6xl">
            Choose her <span className="text-primary">vibe</span>.
          </h1>
          <p className="text-lg text-muted-foreground max-w-md mx-auto">
            This sets the foundation for her look and personality.
          </p>
        </div>

        {/* Vibe selection grid */}
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {VIBE_OPTIONS.map((value) => {
            const optionImageUrl = promptImages?.[`appearance_vibe_${value}`]
            const isSelected = selected === value
            return (
              <button
                key={value}
                type="button"
                className={cn(
                  "group relative flex flex-col overflow-hidden rounded-2xl border text-left transition-all duration-300",
                  isSelected
                    ? "border-primary ring-2 ring-primary/30 scale-[1.02]"
                    : "border-border/50 hover:border-primary/50 hover:scale-[1.01]"
                )}
                onClick={() => setSelected(value)}
              >
                <div className="aspect-[4/5] w-full overflow-hidden bg-muted relative">
                  {optionImageUrl ? (
                    <img
                      src={optionImageUrl}
                      alt={value}
                      className={cn(
                        "h-full w-full object-cover transition-transform duration-500",
                        "group-hover:scale-105"
                      )}
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center text-xs text-muted-foreground">
                      Image
                    </div>
                  )}
                  {/* Gradient overlay */}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                  {/* Selected check */}
                  {isSelected && (
                    <div className="absolute top-3 right-3 w-6 h-6 rounded-full bg-primary flex items-center justify-center">
                      <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  )}
                </div>
                <div className="px-4 py-3 bg-card/80">
                  <span className="text-base font-medium capitalize">
                    {value.replace(/-/g, " ")}
                  </span>
                </div>
              </button>
            )
          })}
        </div>

        {/* Continue button */}
        <div className="flex justify-center pt-4">
          <Button
            size="lg"
            className="min-w-[200px] rounded-lg text-base bg-primary hover:bg-primary/90 px-8 py-6"
            disabled={!selected}
            onClick={handleContinue}
          >
            Continue
          </Button>
        </div>
        
        {/* Progress hint */}
        <p className="text-center text-sm text-muted-foreground">
          Your companion is just a few steps away.
        </p>
      </div>
    </div>
  )
}
