import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAppStore } from "@/lib/store/useAppStore"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  JOB_VIBES,
  HOBBIES,
  CITY_VIBES,
  isValidName,
  getRandomName,
} from "@/lib/constants/identity"
import { Sparkles } from "lucide-react"
import OnboardingSignIn from "@/components/onboarding/OnboardingSignIn"

export default function OnboardingIdentity() {
  const navigate = useNavigate()
  const onboardingIdentity = useAppStore((s) => s.onboardingIdentity)

  // Local state for form fields
  const [name, setName] = useState(onboardingIdentity?.girlfriend_name ?? "")
  const [jobVibe, setJobVibeLocal] = useState(onboardingIdentity?.job_vibe ?? "")
  const [hobbies, setHobbies] = useState<string[]>(onboardingIdentity?.hobbies ?? [])
  const [originVibe, setOriginVibeLocal] = useState(onboardingIdentity?.origin_vibe ?? "")

  const nameValid = isValidName(name)
  const canContinue = nameValid && jobVibe && hobbies.length === 3 && originVibe

  const handleSurpriseMe = () => {
    const randomName = getRandomName()
    setName(randomName)
  }

  const handleToggleHobby = (hobby: string) => {
    setHobbies((prev) => {
      if (prev.includes(hobby)) {
        return prev.filter((h) => h !== hobby)
      }
      if (prev.length >= 3) return prev
      return [...prev, hobby]
    })
  }

  const handleContinue = () => {
    if (!canContinue) return
    // Save all identity data to store at once (single setState to avoid race)
    useAppStore.setState({
      onboardingIdentity: {
        girlfriend_name: name.trim(),
        job_vibe: jobVibe,
        hobbies: hobbies,
        origin_vibe: originVibe,
      },
    })
    navigate("/onboarding/generating", { replace: true })
  }

  const handleBack = () => {
    navigate("/onboarding/preferences", { replace: true })
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-4xl space-y-8 px-4 py-10">
        <OnboardingSignIn />
        <div className="text-center space-y-4">
          <p className="text-primary text-sm font-medium tracking-[0.2em] uppercase">
            Step 4 of 5
          </p>
          <h1 className="text-3xl font-serif font-medium md:text-4xl lg:text-5xl">
            Give her an <span className="text-primary">identity</span>.
          </h1>
          <p className="text-muted-foreground max-w-md mx-auto">
            A name, a story, a life. Make her uniquely yours.
          </p>
        </div>

      {/* Name Section */}
      <Card className="overflow-hidden rounded-2xl border-border/50 bg-card/40 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-lg font-serif">What's her name?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-3">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter a name..."
              maxLength={20}
              className="flex-1"
            />
            <Button
              type="button"
              variant="outline"
              onClick={handleSurpriseMe}
              className="gap-2"
            >
              <Sparkles className="h-4 w-4" />
              Surprise me
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Letters, spaces, hyphens, and apostrophes allowed. 1–20 characters.
          </p>
          {name && !nameValid && (
            <p className="text-xs text-destructive">
              Please enter a valid name (1-20 characters, letters only).
            </p>
          )}
        </CardContent>
      </Card>

      {/* Job Vibe Section */}
      <Card className="overflow-hidden rounded-2xl border-border/50 bg-card/40 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-lg font-serif">What's her vibe?</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {JOB_VIBES.map((job) => {
              const isSelected = jobVibe === job.id
              return (
                <button
                  key={job.id}
                  type="button"
                  className={`rounded-xl border px-4 py-4 text-left transition-all duration-200 ${
                    isSelected
                      ? "border-primary bg-primary/10 ring-1 ring-primary/30"
                      : "border-border/50 hover:border-primary/50"
                  }`}
                  onClick={() => setJobVibeLocal(job.id)}
                >
                  <div className="font-medium text-sm">{job.title}</div>
                  <div className="text-xs text-muted-foreground mt-1">{job.subtitle}</div>
                </button>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Hobbies Section */}
      <Card className="overflow-hidden rounded-2xl border-border/50 bg-card/40 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-lg font-serif flex items-baseline gap-2">
            What are her hobbies?
            <span className="text-sm font-normal text-muted-foreground">
              ({hobbies.length}/3 selected)
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {HOBBIES.map((hobby) => {
              const selected = hobbies.includes(hobby)
              const disabled = !selected && hobbies.length >= 3
              return (
                <button
                  key={hobby}
                  type="button"
                  disabled={disabled}
                  className={`rounded-full border px-4 py-2 text-sm transition-all duration-200 ${
                    selected
                      ? "border-primary bg-primary/10 text-primary"
                      : disabled
                        ? "border-border/30 text-muted-foreground/40 cursor-not-allowed"
                        : "border-border/50 hover:border-primary/50"
                  }`}
                  onClick={() => handleToggleHobby(hobby)}
                >
                  {hobby}
                </button>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* City/Region Vibe Section */}
      <Card className="overflow-hidden rounded-2xl border-border/50 bg-card/40 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-lg font-serif">Where is she from?</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {CITY_VIBES.map((city) => {
              const isSelected = originVibe === city.id
              return (
                <button
                  key={city.id}
                  type="button"
                  className={`rounded-xl border px-4 py-4 text-center transition-all duration-200 ${
                    isSelected
                      ? "border-primary bg-primary/10 ring-1 ring-primary/30"
                      : "border-border/50 hover:border-primary/50"
                  }`}
                  onClick={() => setOriginVibeLocal(city.id)}
                >
                  <div className="font-medium text-sm">{city.title}</div>
                </button>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Navigation Buttons */}
      <div className="flex flex-col items-center gap-4 pt-4">
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
            Create Her
          </Button>
        </div>
        <p className="text-sm text-muted-foreground">
          Almost there. One more step to meet her.
        </p>
      </div>
      </div>
    </div>
  )
}
