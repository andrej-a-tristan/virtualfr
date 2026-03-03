import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { getOnboardingPromptImages } from "@/lib/api/endpoints"
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
  const [selected, setSelected] = useState<VibeOption | "">(appearance?.vibe ?? "")

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
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-background to-background/95 px-4 py-8">
      <OnboardingSignIn />
      <div className="w-full max-w-3xl space-y-10">
        {/* Big hero title */}
        <div className="text-center space-y-3">
          <h1 className="text-4xl font-bold tracking-tight text-foreground md:text-5xl lg:text-6xl">
            Create your beloved girl
          </h1>
          <p className="text-lg text-muted-foreground">
            Start by choosing her overall vibe
          </p>
        </div>

        {/* Vibe selection grid */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {VIBE_OPTIONS.map((value) => {
            const optionImageUrl = promptImages?.[`appearance_vibe_${value}`]
            return (
              <button
                key={value}
                type="button"
                className={cn(
                  "flex flex-col overflow-hidden rounded-2xl border-2 text-left transition-all",
                  selected === value
                    ? "border-primary bg-primary/10 scale-[1.02] shadow-lg shadow-primary/20"
                    : "border-white/10 hover:border-white/20 hover:scale-[1.01]"
                )}
                onClick={() => setSelected(value)}
              >
                <div className="aspect-[4/5] w-full overflow-hidden bg-muted">
                  {optionImageUrl ? (
                    <img
                      src={optionImageUrl}
                      alt={value}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center text-xs text-muted-foreground">
                      Image
                    </div>
                  )}
                </div>
                <span className="px-4 py-3 text-base font-semibold capitalize">
                  {value.replace(/-/g, " ")}
                </span>
              </button>
            )
          })}
        </div>

        {/* Continue button */}
        <div className="flex justify-center">
          <Button
            size="lg"
            className="min-w-[200px] rounded-xl text-base"
            disabled={!selected}
            onClick={handleContinue}
          >
            Continue
          </Button>
        </div>
      </div>
    </div>
  )
}
