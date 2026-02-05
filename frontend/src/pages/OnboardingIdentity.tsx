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
    <div className="mx-auto max-w-4xl space-y-8 px-4 py-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight">Choose her identity</h1>
        <p className="mt-2 text-muted-foreground">
          Give her a name, a vibe, and a story.
        </p>
      </div>

      {/* Name Section */}
      <Card className="overflow-hidden rounded-2xl border-white/10 bg-card/80">
        <CardHeader>
          <CardTitle className="text-base font-semibold">What&apos;s her name?</CardTitle>
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
      <Card className="overflow-hidden rounded-2xl border-white/10 bg-card/80">
        <CardHeader>
          <CardTitle className="text-base font-semibold">What&apos;s her job vibe?</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {JOB_VIBES.map((job) => (
              <button
                key={job.id}
                type="button"
                className={`rounded-xl border-2 px-4 py-3 text-left transition-colors ${
                  jobVibe === job.id
                    ? "border-primary bg-primary/10"
                    : "border-white/10 hover:border-white/20"
                }`}
                onClick={() => setJobVibeLocal(job.id)}
              >
                <div className="font-medium text-sm">{job.title}</div>
                <div className="text-xs text-muted-foreground">{job.subtitle}</div>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Hobbies Section */}
      <Card className="overflow-hidden rounded-2xl border-white/10 bg-card/80">
        <CardHeader>
          <CardTitle className="text-base font-semibold">
            What are her hobbies?{" "}
            <span className="font-normal text-muted-foreground">
              (Pick 3 — {hobbies.length}/3)
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
                  className={`rounded-full border-2 px-4 py-2 text-sm transition-colors ${
                    selected
                      ? "border-primary bg-primary/10"
                      : disabled
                        ? "border-white/5 text-muted-foreground/50 cursor-not-allowed"
                        : "border-white/10 hover:border-white/20"
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
      <Card className="overflow-hidden rounded-2xl border-white/10 bg-card/80">
        <CardHeader>
          <CardTitle className="text-base font-semibold">Where does she vibe?</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {CITY_VIBES.map((city) => (
              <button
                key={city.id}
                type="button"
                className={`rounded-xl border-2 px-4 py-3 text-center transition-colors ${
                  originVibe === city.id
                    ? "border-primary bg-primary/10"
                    : "border-white/10 hover:border-white/20"
                }`}
                onClick={() => setOriginVibeLocal(city.id)}
              >
                <div className="font-medium text-sm">{city.title}</div>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Navigation Buttons */}
      <div className="flex justify-center gap-4 pt-2">
        <Button variant="outline" size="lg" onClick={handleBack}>
          Back
        </Button>
        <Button size="lg" disabled={!canContinue} onClick={handleContinue}>
          Continue
        </Button>
      </div>
    </div>
  )
}
