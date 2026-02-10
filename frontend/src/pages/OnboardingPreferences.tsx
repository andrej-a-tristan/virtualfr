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
    <div className="mx-auto max-w-3xl space-y-8 px-4 py-8">
      <OnboardingSignIn />
      <div className="text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-amber-500/10">
          <Shield className="h-8 w-8 text-amber-500" />
        </div>
        <h1 className="text-3xl font-bold tracking-tight">Age Verification</h1>
        <p className="mt-2 text-muted-foreground">
          This app contains sexual and adult content. You must be 18 or older to continue.
        </p>
      </div>

      <Card className="overflow-hidden rounded-2xl border-white/10 bg-card/80">
        <CardHeader>
          <CardTitle className="text-base font-semibold">Are you 18 years or older?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Warning */}
          <div className="flex items-start gap-3 rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
            <p className="text-xs leading-relaxed text-white/60">
              This application contains explicit sexual content including nudity and intimate scenarios.
              By confirming you are 18+, you consent to viewing this content.
              If you are under 18, you are <span className="font-semibold text-white/80">not permitted</span> to use this service.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <button
              type="button"
              className={`rounded-xl border-2 px-4 py-4 text-center text-sm font-semibold transition-all ${
                confirmedOver18 === true
                  ? "border-emerald-500 bg-emerald-500/10 text-emerald-400"
                  : "border-white/10 hover:border-white/20"
              }`}
              onClick={() => setConfirmedOver18(true)}
            >
              Yes, I am 18 or older
            </button>
            <button
              type="button"
              className={`rounded-xl border-2 px-4 py-4 text-center text-sm font-semibold transition-all ${
                confirmedOver18 === false
                  ? "border-red-500 bg-red-500/10 text-red-400"
                  : "border-white/10 hover:border-white/20"
              }`}
              onClick={() => setConfirmedOver18(false)}
            >
              No, I am under 18
            </button>
          </div>

          {confirmedOver18 === false && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-4 text-center">
              <p className="text-sm font-semibold text-red-400">
                You cannot use this app.
              </p>
              <p className="mt-1 text-xs text-red-400/70">
                This service is only available to users aged 18 and over. Please close this page.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex justify-center gap-4 pt-2">
        <Button variant="outline" size="lg" onClick={handleBack}>
          Back
        </Button>
        <Button
          size="lg"
          disabled={!canContinue}
          onClick={handleContinue}
          className="min-w-[140px]"
        >
          Continue
        </Button>
      </div>
    </div>
  )
}
