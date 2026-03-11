import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { getOnboardingPromptImages, guestSession } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import { cn } from "@/lib/utils"
import { ChevronRight } from "lucide-react"

const VIBE_OPTIONS = ["cute", "elegant", "sporty", "goth", "girl-next-door", "model"] as const
type VibeOption = (typeof VIBE_OPTIONS)[number]

const VIBE_DESCRIPTIONS: Record<VibeOption, string> = {
  "cute": "Sweet, playful, and irresistibly charming",
  "elegant": "Sophisticated, graceful, and refined",
  "sporty": "Active, energetic, and adventurous", 
  "goth": "Mysterious, artistic, and uniquely beautiful",
  "girl-next-door": "Warm, approachable, and genuine",
  "model": "Stunning, confident, and captivating"
}

export default function OnboardingAppearance() {
  const navigate = useNavigate()
  const appearance = useAppStore((s) => s.onboardingAppearance)
  const setOnboardingAppearance = useAppStore((s) => s.setOnboardingAppearance)
  const user = useAppStore((s) => s.user)
  const setUser = useAppStore((s) => s.setUser)
  const [selected, setSelected] = useState<VibeOption | "">(appearance?.vibe ?? "")

  useEffect(() => {
    if (!user) {
      guestSession()
        .then(({ user }) => setUser(user))
        .catch(() => {})
    }
  }, [user, setUser])

  const { data: promptImages } = useQuery({
    queryKey: ["onboardingPromptImages"],
    queryFn: getOnboardingPromptImages,
  })

  const handleContinue = () => {
    if (!selected) return
    setOnboardingAppearance({ ...appearance, vibe: selected as VibeOption })
    // Go to detailed appearance flow or directly to traits
    navigate("/onboarding/appearance/age", { replace: true })
  }

  const handleSelect = (value: VibeOption) => {
    setSelected(value)
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Subtle top gradient */}
      <div className="absolute inset-x-0 top-0 h-[400px] bg-gradient-to-b from-primary/5 to-transparent pointer-events-none" />
      
      <div className="relative max-w-6xl mx-auto px-4 py-12 md:py-20">
        {/* Header */}
        <div className="text-center mb-12 md:mb-16">
          <p className="text-primary/80 text-xs font-medium tracking-[0.3em] uppercase mb-4">
            Step 1
          </p>
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-serif text-foreground mb-4">
            Who catches your eye?
          </h1>
          <p className="text-muted-foreground text-lg max-w-md mx-auto">
            Choose a style that speaks to you. This shapes her overall aesthetic.
          </p>
        </div>

        {/* Selection Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 md:gap-6 mb-12">
          {VIBE_OPTIONS.map((value) => {
            const optionImageUrl = promptImages?.[`appearance_vibe_${value}`]
            const isSelected = selected === value
            return (
              <button
                key={value}
                type="button"
                onClick={() => handleSelect(value)}
                className={cn(
                  "group relative aspect-[3/4] overflow-hidden rounded-2xl transition-all duration-300",
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
                        "w-full h-full object-cover transition-transform duration-700",
                        "group-hover:scale-110",
                        isSelected && "scale-110"
                      )}
                    />
                  ) : (
                    <div className="w-full h-full bg-gradient-to-br from-muted to-muted/50" />
                  )}
                </div>
                
                {/* Gradient overlay */}
                <div className={cn(
                  "absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent transition-opacity duration-300",
                  isSelected ? "opacity-90" : "opacity-70 group-hover:opacity-80"
                )} />
                
                {/* Content */}
                <div className="absolute inset-x-0 bottom-0 p-4 md:p-5">
                  <h3 className="text-white font-medium text-lg md:text-xl capitalize mb-1">
                    {value.replace(/-/g, " ")}
                  </h3>
                  <p className={cn(
                    "text-white/70 text-sm transition-opacity duration-300",
                    isSelected ? "opacity-100" : "opacity-0 group-hover:opacity-100"
                  )}>
                    {VIBE_DESCRIPTIONS[value]}
                  </p>
                </div>

                {/* Selection indicator */}
                {isSelected && (
                  <div className="absolute top-3 right-3 w-6 h-6 rounded-full bg-primary flex items-center justify-center">
                    <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                )}
              </button>
            )
          })}
        </div>

        {/* Continue Button */}
        <div className="flex flex-col items-center gap-4">
          <button
            onClick={handleContinue}
            disabled={!selected}
            className={cn(
              "group flex items-center gap-2 px-8 py-4 rounded-full font-medium text-base transition-all duration-300",
              selected
                ? "bg-primary text-white hover:bg-primary/90 hover:gap-3"
                : "bg-muted text-muted-foreground cursor-not-allowed"
            )}
          >
            Continue
            <ChevronRight className={cn(
              "w-4 h-4 transition-transform duration-300",
              selected && "group-hover:translate-x-1"
            )} />
          </button>
          
          {!selected && (
            <p className="text-muted-foreground/60 text-sm">
              Select a style to continue
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
