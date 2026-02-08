import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { getOnboardingPromptImages } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import OnboardingSignIn from "@/components/onboarding/OnboardingSignIn"

const SECTIONS = [
  {
    key: "body_type",
    label: "Body type",
    options: ["slim", "athletic", "curvy"],
    promptKey: "appearance_body_type",
  },
  {
    key: "breast_size",
    label: "Breast size",
    options: ["small", "medium", "large", "massive"],
    promptKey: "appearance_breast_size",
  },
  {
    key: "butt_size",
    label: "Butt size",
    options: ["small", "medium", "large", "massive"],
    promptKey: "appearance_butt_size",
  },
] as const

export default function AppearanceBodyDetails() {
  const navigate = useNavigate()
  const appearance = useAppStore((s) => s.onboardingAppearance)
  const setOnboardingAppearance = useAppStore((s) => s.setOnboardingAppearance)

  const [selections, setSelections] = useState<Record<string, string>>({
    body_type: (appearance as Record<string, string>)?.body_type ?? "",
    breast_size: (appearance as Record<string, string>)?.breast_size ?? "",
    butt_size: (appearance as Record<string, string>)?.butt_size ?? "",
  })

  const { data: promptImages } = useQuery({
    queryKey: ["onboardingPromptImages"],
    queryFn: getOnboardingPromptImages,
  })

  const isComplete = selections.body_type && selections.breast_size && selections.butt_size

  const handleSelect = (key: string, value: string) => {
    setSelections((prev) => ({ ...prev, [key]: value }))
  }

  const handleContinue = () => {
    if (!isComplete) return
    setOnboardingAppearance({ ...appearance, ...selections })
    navigate("/onboarding/appearance/hair-eyes", { replace: true })
  }

  const handleBack = () => {
    if (Object.values(selections).some(Boolean)) {
      setOnboardingAppearance({ ...appearance, ...selections })
    }
    navigate("/onboarding/appearance/ethnicity", { replace: true })
  }

  return (
    <div className="flex min-h-screen flex-col items-center bg-gradient-to-b from-background to-background/95 px-4 py-8">
      <OnboardingSignIn />
      <div className="w-full max-w-3xl space-y-8">
        {/* Progress */}
        <div className="flex items-center justify-center gap-1.5">
          {Array.from({ length: 5 }, (_, i) => (
            <div
              key={i}
              className={cn(
                "h-1.5 rounded-full transition-all",
                i < 3 ? "w-8 bg-primary" : i === 3 ? "w-8 bg-primary/60" : "w-8 bg-white/10"
              )}
            />
          ))}
        </div>

        {/* Title */}
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight md:text-4xl">Her body</h1>
          <p className="mt-2 text-muted-foreground">Choose her figure and proportions</p>
        </div>

        {/* Sections */}
        {SECTIONS.map((section) => (
          <div key={section.key} className="space-y-3">
            <h2 className="text-lg font-semibold">{section.label}</h2>
            <div className={cn(
              "grid gap-3",
              section.options.length === 3 ? "grid-cols-3" : "grid-cols-2 sm:grid-cols-4"
            )}>
              {section.options.map((value) => {
                const optionImageUrl = promptImages?.[`${section.promptKey}_${value}`]
                const isSelected = selections[section.key] === value
                return (
                  <button
                    key={value}
                    type="button"
                    className={cn(
                      "flex flex-col overflow-hidden rounded-2xl border-2 text-left transition-all",
                      isSelected
                        ? "border-primary bg-primary/10 scale-[1.02] shadow-lg shadow-primary/20"
                        : "border-white/10 hover:border-white/20 hover:scale-[1.01]"
                    )}
                    onClick={() => handleSelect(section.key, value)}
                  >
                    <div className="aspect-square w-full overflow-hidden bg-muted">
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
                    <span className="px-3 py-2 text-sm font-medium capitalize">
                      {value.replace(/-/g, " ")}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>
        ))}

        {/* Navigation */}
        <div className="flex justify-center gap-4 pt-2">
          <Button variant="outline" size="lg" className="rounded-xl" onClick={handleBack}>
            Back
          </Button>
          <Button size="lg" className="rounded-xl" disabled={!isComplete} onClick={handleContinue}>
            Continue
          </Button>
        </div>
      </div>
    </div>
  )
}
