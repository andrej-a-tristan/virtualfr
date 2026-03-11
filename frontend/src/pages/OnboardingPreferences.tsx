import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAppStore } from "@/lib/store/useAppStore"
import { ChevronRight, ChevronLeft, Lock } from "lucide-react"
import { cn } from "@/lib/utils"

export default function OnboardingPreferences() {
  const navigate = useNavigate()
  const setOnboardingContentPrefs = useAppStore((s) => s.setOnboardingContentPrefs)
  const [confirmed, setConfirmed] = useState<boolean | null>(null)

  const handleBack = () => {
    navigate("/onboarding/traits", { replace: true })
  }

  const handleContinue = () => {
    if (confirmed !== true) return
    setOnboardingContentPrefs({ wants_spicy_photos: true })
    navigate("/onboarding/identity", { replace: true })
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Progress bar */}
      <div className="fixed top-0 inset-x-0 z-50">
        <div className="h-1 bg-muted">
          <div className="h-full bg-primary w-[50%]" />
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-16">
        <div className="w-full max-w-md">
          {/* Back button */}
          <button 
            onClick={handleBack}
            className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors mb-8"
          >
            <ChevronLeft className="w-4 h-4" />
            <span className="text-sm">Back</span>
          </button>

          {/* Icon */}
          <div className="flex justify-center mb-8">
            <div className="w-16 h-16 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
              <Lock className="w-7 h-7 text-primary" />
            </div>
          </div>

          {/* Content */}
          <div className="text-center mb-10">
            <h1 className="text-3xl md:text-4xl font-serif text-foreground mb-3">
              One quick thing
            </h1>
            <p className="text-muted-foreground leading-relaxed">
              This experience is designed for adults and includes mature themes. 
              Please confirm you meet the age requirement.
            </p>
          </div>

          {/* Options */}
          <div className="space-y-3 mb-8">
            <button
              onClick={() => setConfirmed(true)}
              className={cn(
                "w-full flex items-center justify-center gap-3 p-5 rounded-xl border transition-all duration-200",
                confirmed === true
                  ? "border-primary bg-primary/5"
                  : "border-border/50 hover:border-primary/50"
              )}
            >
              <span className={cn(
                "font-medium",
                confirmed === true ? "text-primary" : "text-foreground"
              )}>
                I'm 18 or older
              </span>
              {confirmed === true && (
                <div className="w-5 h-5 rounded-full bg-primary flex items-center justify-center">
                  <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              )}
            </button>

            <button
              onClick={() => setConfirmed(false)}
              className={cn(
                "w-full flex items-center justify-center p-4 rounded-xl border transition-all duration-200",
                confirmed === false
                  ? "border-destructive/50 bg-destructive/5 text-destructive"
                  : "border-border/30 text-muted-foreground hover:border-border/50"
              )}
            >
              <span className="text-sm">I'm under 18</span>
            </button>
          </div>

          {/* Error state */}
          {confirmed === false && (
            <div className="text-center mb-8 p-4 rounded-xl bg-destructive/5 border border-destructive/20">
              <p className="text-sm text-destructive">
                This experience is only available to adults. Please close this page.
              </p>
            </div>
          )}

          {/* Continue */}
          {confirmed === true && (
            <div className="flex justify-center">
              <button
                onClick={handleContinue}
                className="group flex items-center gap-2 px-8 py-4 rounded-full bg-primary text-white font-medium hover:bg-primary/90 transition-all duration-300 hover:gap-3"
              >
                Continue
                <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          )}

          {/* Privacy note */}
          <p className="text-center text-xs text-muted-foreground/60 mt-8">
            Your privacy matters. All conversations are encrypted and never shared.
          </p>
        </div>
      </div>
    </div>
  )
}
