import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAppStore } from "@/lib/store/useAppStore"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import TraitSelector, { type TraitOption } from "@/components/onboarding/TraitSelector"
import PersonaPreviewCard from "@/components/onboarding/PersonaPreviewCard"
import type { TraitsInput } from "@/lib/api/zod"

const TRAIT_OPTIONS: Record<keyof TraitsInput, TraitOption[]> = {
  emotional_style: [
    { value: "warm", label: "Warm", description: "Affectionate and expressive" },
    { value: "reserved", label: "Reserved", description: "Thoughtful and measured" },
    { value: "playful", label: "Playful", description: "Light-hearted and fun" },
    { value: "intense", label: "Intense", description: "Deep and passionate" },
  ],
  attachment_style: [
    { value: "secure", label: "Secure", description: "Comfortable with closeness" },
    { value: "anxious", label: "Anxious", description: "Craves reassurance" },
    { value: "avoidant", label: "Avoidant", description: "Values independence" },
    { value: "balanced", label: "Balanced", description: "Flexible and adaptive" },
  ],
  jealousy_level: [
    { value: "low", label: "Low", description: "Trusting and relaxed" },
    { value: "moderate", label: "Moderate", description: "Occasionally protective" },
    { value: "high", label: "High", description: "Very possessive" },
    { value: "none", label: "None", description: "Completely open" },
  ],
  communication_tone: [
    { value: "sweet", label: "Sweet", description: "Gentle and caring" },
    { value: "sassy", label: "Sassy", description: "Witty and teasing" },
    { value: "direct", label: "Direct", description: "Clear and honest" },
    { value: "flirty", label: "Flirty", description: "Playful and suggestive" },
  ],
  intimacy_pace: [
    { value: "slow", label: "Slow", description: "Takes time to open up" },
    { value: "medium", label: "Medium", description: "Natural progression" },
    { value: "fast", label: "Fast", description: "Quick to connect" },
    { value: "variable", label: "Variable", description: "Depends on mood" },
  ],
  cultural_personality: [
    { value: "romantic", label: "Romantic", description: "Loves gestures and dates" },
    { value: "adventurous", label: "Adventurous", description: "Loves new experiences" },
    { value: "homebody", label: "Homebody", description: "Prefers cozy nights" },
    { value: "intellectual", label: "Intellectual", description: "Loves deep conversation" },
  ],
}

const TRAIT_LABELS: Record<keyof TraitsInput, string> = {
  emotional_style: "Emotional style",
  attachment_style: "Attachment style",
  jealousy_level: "Jealousy level",
  communication_tone: "Communication tone",
  intimacy_pace: "Intimacy pace",
  cultural_personality: "Cultural personality",
}

const defaultTraits: Partial<TraitsInput> = {
  emotional_style: "",
  attachment_style: "",
  jealousy_level: "",
  communication_tone: "",
  intimacy_pace: "",
  cultural_personality: "",
}

export default function OnboardingTraits() {
  const navigate = useNavigate()
  const setOnboardingTraits = useAppStore((s) => s.setOnboardingTraits)
  const [traits, setTraits] = useState<Partial<TraitsInput>>(defaultTraits)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const updateTrait = (key: keyof TraitsInput, value: string) => {
    setTraits((prev) => ({ ...prev, [key]: value }))
  }

  const isComplete = (Object.keys(TRAIT_OPTIONS) as (keyof TraitsInput)[]).every((k) => traits[k])

  const handleSubmit = async () => {
    if (!isComplete) return
    setError(null)
    setLoading(true)
    try {
      setOnboardingTraits(traits as TraitsInput)
      navigate("/onboarding/appearance", { replace: true })
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8 px-4 py-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight">Create your companion</h1>
        <p className="mt-2 text-muted-foreground">Choose traits that define your persona.</p>
      </div>
      <Card className="rounded-2xl border-white/10">
        <CardHeader>
          <CardTitle>Traits</CardTitle>
          <CardDescription>Select one option per category. Your companion will reflect these choices.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-8">
          {(Object.keys(TRAIT_OPTIONS) as (keyof TraitsInput)[]).map((key) => (
            <TraitSelector
              key={key}
              traitKey={key}
              label={TRAIT_LABELS[key]}
              options={TRAIT_OPTIONS[key]}
              value={traits[key] ?? ""}
              onChange={updateTrait}
            />
          ))}
        </CardContent>
      </Card>
      <PersonaPreviewCard traits={traits} />
      {error && <p className="text-center text-sm text-destructive">{error}</p>}
      <div className="flex justify-center">
        <Button size="lg" disabled={!isComplete || loading} onClick={handleSubmit}>
          {loading ? "Creating…" : "Continue to preview"}
        </Button>
      </div>
    </div>
  )
}
