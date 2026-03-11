import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { getOnboardingPromptImages } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import { cn } from "@/lib/utils"
import { ChevronLeft, ChevronRight } from "lucide-react"

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

  // Calculate progress based on total flow (appearance vibe + detail steps + traits + preferences + identity)
  const progressPercent = ((stepNumber + 1) / (totalSteps + 1)) * 40 // Appearance takes ~40% of total progress

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Progress bar */}
      <div className="fixed top-0 inset-x-0 z-50">
        <div className="h-1 bg-muted">
          <div 
            className="h-full bg-primary transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center px-4 py-16">
        <div className={cn("w-full", columns && columns > 3 ? "max-w-4xl" : "max-w-2xl")}>
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
            <h1 className="text-3xl md:text-4xl font-serif text-foreground mb-3">{title}</h1>
            <p className="text-muted-foreground">{subtitle}</p>
          </div>

          {/* Options grid */}
          <div className={cn(
            "grid gap-4 mb-10",
            columns === 4 ? "grid-cols-2 sm:grid-cols-4" :
            columns === 7 ? "grid-cols-2 sm:grid-cols-4" :
            "grid-cols-2 sm:grid-cols-3"
          )}>
            {options.map((value) => {
              const optionImageUrl = promptImages?.[`${promptKey}_${value}`]
              const isSelected = selected === value
              return (
                <button
                  key={value}
                  type="button"
                  onClick={() => handleSelect(value)}
                  className={cn(
                    "group relative aspect-[3/4] overflow-hidden rounded-xl transition-all duration-300",
                    isSelected 
                      ? "ring-2 ring-primary ring-offset-2 ring-offset-background scale-[1.02]" 
                      : "hover:scale-[1.01]"
                  )}
                >
                  {/* Image */}
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
                  
                  {/* Gradient overlay */}
                  <div className={cn(
                    "absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent transition-opacity",
                    isSelected ? "opacity-80" : "opacity-60 group-hover:opacity-70"
                  )} />
                  
                  {/* Label */}
                  <div className="absolute inset-x-0 bottom-0 p-3">
                    <span className="text-white font-medium text-sm capitalize">
                      {/^\d+[-–]\d+/.test(value) ? value.replace(/-/g, " – ") : value.replace(/-/g, " ")}
                    </span>
                  </div>

                  {/* Selection indicator */}
                  {isSelected && (
                    <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-primary flex items-center justify-center">
                      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  )}
                </button>
              )
            })}
          </div>

          {/* Continue button */}
          <div className="flex justify-center">
            <button
              onClick={handleContinue}
              disabled={!selected}
              className={cn(
                "group flex items-center gap-2 px-8 py-4 rounded-full font-medium transition-all duration-300",
                selected
                  ? "bg-primary text-white hover:bg-primary/90 hover:gap-3"
                  : "bg-muted text-muted-foreground cursor-not-allowed"
              )}
            >
              Continue
              <ChevronRight className={cn(
                "w-4 h-4 transition-transform",
                selected && "group-hover:translate-x-1"
              )} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
