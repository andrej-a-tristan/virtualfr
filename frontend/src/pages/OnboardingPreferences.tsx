import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAppStore } from "@/lib/store/useAppStore"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Shield, AlertTriangle } from "lucide-react"
import OnboardingSignIn from "@/components/onboarding/OnboardingSignIn"

export default function OnboardingPreferences() {
  const navigate = useNavigate()
  const setOnboardingContentPrefs = useAppStore((s) => s.setOnboardingContentPrefs)
  const [confirmedOver18, setConfirmedOver18] = useState<boolean | null>(null)

  const canContinue = confirmedOver18 === true

  const handleContinue = () => {
    if (!canContinue) return
    // Since user confirmed 18+, always enable spicy photos
    setOnboardingContentPrefs({ wants_spicy_photos: true })
    navigate("/onboarding/identity", { replace: true })
  }

  const handleBack = () => {
    navigate("/onboarding/traits", { replace: true })
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="mx-auto max-w-lg space-y-8 px-4 py-8">
        <OnboardingSignIn />
        <div className="text-center space-y-4">
          <p className="text-primary text-sm font-medium tracking-[0.2em] uppercase">
            Step 3 of 5
          </p>
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 border border-primary/20">
            <Shield className="h-7 w-7 text-primary" />
          </div>
          <h1 className="text-3xl font-serif font-medium">
            Before we continue...
          </h1>
          <p className="text-muted-foreground">
            This experience contains mature content. Please confirm you're 18+.
          </p>
        </div>

      <Card className="overflow-hidden rounded-2xl border-border/50 bg-card/40 backdrop-blur-sm">
        <CardHeader className="text-center pb-2">
          <CardTitle className="text-lg font-serif">Confirm your age</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Warning */}
          <div className="flex items-start gap-3 rounded-lg border border-primary/20 bg-primary/5 px-4 py-3">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            <p className="text-xs leading-relaxed text-muted-foreground">
              This experience contains mature themes. By continuing, you confirm you are of legal age in your jurisdiction.
            </p>
          </div>

          <div className="grid gap-3">
            <button
              type="button"
              className={`rounded-xl border px-4 py-5 text-center text-sm font-medium transition-all duration-200 ${
                confirmedOver18 === true
                  ? "border-primary bg-primary/10 text-primary ring-1 ring-primary/30"
                  : "border-border/50 hover:border-primary/50"
              }`}
              onClick={() => setConfirmedOver18(true)}
            >
              Yes, I'm 18 or older
            </button>
            <button
              type="button"
              className={`rounded-xl border px-4 py-4 text-center text-sm transition-all duration-200 ${
                confirmedOver18 === false
                  ? "border-destructive/50 bg-destructive/10 text-destructive"
                  : "border-border/30 text-muted-foreground hover:border-border/50"
              }`}
              onClick={() => setConfirmedOver18(false)}
            >
              No, I'm under 18
            </button>
          </div>

          {confirmedOver18 === false && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-4 text-center">
              <p className="text-sm text-destructive">
                This experience is only available to adults.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex flex-col items-center gap-4 pt-2">
        <div className="flex gap-4">
          <Button variant="outline" size="lg" onClick={handleBack} className="rounded-lg px-6">
            Back
          </Button>
          <Button
            size="lg"
            disabled={!canContinue}
            onClick={handleContinue}
            className="rounded-lg bg-primary hover:bg-primary/90 px-8"
          >
            Continue
          </Button>
        </div>
      </div>
      </div>
    </div>
  )
}
