import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { getOnboardingPromptImages } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import OnboardingSignIn from "@/components/onboarding/OnboardingSignIn"

interface AppearanceStepPageProps {
  title: string
  subtitle: string
  storeKey: string
  options: string[]
  promptKey: string
  nextRoute: string
  backRoute: string
  stepNumber: number
  totalSteps: number
  columns?: number
}

export default function AppearanceStepPage({
  title,
  subtitle,
  storeKey,
  options,
  promptKey,
  nextRoute,
  backRoute,
  stepNumber,
  totalSteps,
  columns,
}: AppearanceStepPageProps) {
  const navigate = useNavigate()
  const appearance = useAppStore((s) => s.onboardingAppearance)
  const setOnboardingAppearance = useAppStore((s) => s.setOnboardingAppearance)
  const [selected, setSelected] = useState<string>(
    (appearance as Record<string, string>)?.[storeKey] ?? ""
  )

  const { data: promptImages } = useQuery({
    queryKey: ["onboardingPromptImages"],
    queryFn: getOnboardingPromptImages,
  })

  const handleSelect = (value: string) => {
    setSelected(value)
  }

  const handleContinue = () => {
    if (!selected) return
    setOnboardingAppearance({ ...appearance, [storeKey]: selected })
    navigate(nextRoute, { replace: true })
  }

  const handleBack = () => {
    if (selected) {
      setOnboardingAppearance({ ...appearance, [storeKey]: selected })
    }
    navigate(backRoute, { replace: true })
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-background to-background/95 px-4 py-8">
      <OnboardingSignIn />
      <div className={cn("w-full space-y-8", columns && columns > 3 ? "max-w-4xl" : "max-w-2xl")}>
        {/* Progress */}
        <div className="flex items-center justify-center gap-1.5">
          {Array.from({ length: totalSteps }, (_, i) => (
            <div
              key={i}
              className={cn(
                "h-1.5 rounded-full transition-all",
                i < stepNumber ? "w-8 bg-primary" : i === stepNumber ? "w-8 bg-primary/60" : "w-8 bg-white/10"
              )}
            />
          ))}
        </div>

        {/* Title */}
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight md:text-4xl">{title}</h1>
          <p className="mt-2 text-muted-foreground">{subtitle}</p>
        </div>

        {/* Options grid */}
        <div className={cn(
          "grid gap-3",
          columns === 4 ? "grid-cols-2 sm:grid-cols-4" :
          columns === 7 ? "grid-cols-2 sm:grid-cols-4" :
          "sm:grid-cols-2 lg:grid-cols-3"
        )}>
          {options.map((value) => {
            const optionImageUrl = promptImages?.[`${promptKey}_${value}`]
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
                onClick={() => handleSelect(value)}
              >
                <div className="aspect-[3/4] w-full overflow-hidden bg-muted">
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
                <span className="px-4 py-3 text-sm font-medium capitalize">
                  {/^\d+[-–]\d+/.test(value) ? value.replace(/-/g, " – ") : value.replace(/-/g, " ")}
                </span>
              </button>
            )
          })}
        </div>

        {/* Navigation */}
        <div className="flex justify-center gap-4 pt-2">
          <Button variant="outline" size="lg" className="rounded-xl" onClick={handleBack}>
            Back
          </Button>
          <Button size="lg" className="rounded-xl" disabled={!selected} onClick={handleContinue}>
            Continue
          </Button>
        </div>
      </div>
    </div>
  )
}
