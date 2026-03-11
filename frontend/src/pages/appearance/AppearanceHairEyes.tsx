import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { getOnboardingPromptImages } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import { cn } from "@/lib/utils"
import { ChevronLeft, ChevronRight } from "lucide-react"

const SECTIONS = [
  {
    key: "hair_color",
    label: "Hair color",
    options: ["black", "brown", "blonde", "red", "ginger", "unnatural"],
    promptKey: "appearance_hair_color",
  },
  {
    key: "hair_style",
    label: "Hair style",
    options: ["long", "bob", "curly", "straight", "bun"],
    promptKey: "appearance_hair_style",
  },
  {
    key: "eye_color",
    label: "Eye color",
    options: ["brown", "blue", "green", "hazel"],
    promptKey: "appearance_eye_color",
  },
] as const

export default function AppearanceHairEyes() {
  const navigate = useNavigate()
  const appearance = useAppStore((s) => s.onboardingAppearance)
  const setOnboardingAppearance = useAppStore((s) => s.setOnboardingAppearance)

  const [selections, setSelections] = useState<Record<string, string>>({
    hair_color: (appearance as Record<string, string>)?.hair_color ?? "",
    hair_style: (appearance as Record<string, string>)?.hair_style ?? "",
    eye_color: (appearance as Record<string, string>)?.eye_color ?? "",
  })

  const { data: promptImages } = useQuery({
    queryKey: ["onboardingPromptImages"],
    queryFn: getOnboardingPromptImages,
  })

  const isComplete = selections.hair_color && selections.hair_style && selections.eye_color

  const handleSelect = (key: string, value: string) => {
    setSelections((prev) => ({ ...prev, [key]: value }))
  }

  const handleContinue = () => {
    if (!isComplete) return
    setOnboardingAppearance({ ...appearance, ...selections })
    navigate("/onboarding/traits", { replace: true })
  }

  const handleBack = () => {
    if (Object.values(selections).some(Boolean)) {
      setOnboardingAppearance({ ...appearance, ...selections })
    }
    navigate("/onboarding/appearance/body", { replace: true })
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Progress bar */}
      <div className="fixed top-0 inset-x-0 z-50">
        <div className="h-1 bg-muted">
          <div className="h-full bg-primary w-[35%]" />
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center px-4 py-16">
        <div className="w-full max-w-3xl">
          {/* Back button */}
          <button 
            onClick={handleBack}
            className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors mb-8"
          >
            <ChevronLeft className="w-4 h-4" />
            <span className="text-sm">Back</span>
          </button>

          {/* Title */}
          <div className="text-center mb-10">
            <h1 className="text-3xl md:text-4xl font-serif text-foreground mb-3">Her details</h1>
            <p className="text-muted-foreground">Choose her hair and eye color</p>
          </div>

          {/* Sections */}
          <div className="space-y-10 mb-10">
            {SECTIONS.map((section) => (
              <div key={section.key}>
                <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground mb-4">{section.label}</h2>
                <div className={cn(
                  "grid gap-3",
                  section.options.length <= 4 ? "grid-cols-2 sm:grid-cols-4" :
                  section.options.length === 5 ? "grid-cols-3 sm:grid-cols-5" :
                  "grid-cols-3 sm:grid-cols-6"
                )}>
                  {section.options.map((value) => {
                    const optionImageUrl = promptImages?.[`${section.promptKey}_${value}`]
                    const isSelected = selections[section.key] === value
                    return (
                      <button
                        key={value}
                        type="button"
                        onClick={() => handleSelect(section.key, value)}
                        className={cn(
                          "group relative aspect-square overflow-hidden rounded-xl transition-all duration-300",
                          isSelected 
                            ? "ring-2 ring-primary ring-offset-2 ring-offset-background scale-[1.02]" 
                            : "hover:scale-[1.01]"
                        )}
                      >
                        <div className="absolute inset-0 bg-muted">
                          {optionImageUrl ? (
                            <img
                              src={optionImageUrl}
                              alt={value}
                              className={cn(
                                "w-full h-full object-cover transition-transform duration-500",
                                "group-hover:scale-105",
                                isSelected && "scale-105"
                              )}
                            />
                          ) : (
                            <div className="w-full h-full bg-gradient-to-br from-muted to-muted/50" />
                          )}
                        </div>
                        
                        <div className={cn(
                          "absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent transition-opacity",
                          isSelected ? "opacity-80" : "opacity-60 group-hover:opacity-70"
                        )} />
                        
                        <div className="absolute inset-x-0 bottom-0 p-2">
                          <span className="text-white font-medium text-xs capitalize">
                            {value.replace(/-/g, " ")}
                          </span>
                        </div>

                        {isSelected && (
                          <div className="absolute top-2 right-2 w-4 h-4 rounded-full bg-primary flex items-center justify-center">
                            <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                          </div>
                        )}
                      </button>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>

          {/* Continue button */}
          <div className="flex justify-center">
            <button
              onClick={handleContinue}
              disabled={!isComplete}
              className={cn(
                "group flex items-center gap-2 px-8 py-4 rounded-full font-medium transition-all duration-300",
                isComplete
                  ? "bg-primary text-white hover:bg-primary/90 hover:gap-3"
                  : "bg-muted text-muted-foreground cursor-not-allowed"
              )}
            >
              Continue
              <ChevronRight className={cn(
                "w-4 h-4 transition-transform",
                isComplete && "group-hover:translate-x-1"
              )} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
