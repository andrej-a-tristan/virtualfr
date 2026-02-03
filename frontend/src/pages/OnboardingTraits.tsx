import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { createGirlfriend } from "@/lib/api/endpoints"
import { useQueryClient } from "@tanstack/react-query"
import { useAppStore } from "@/lib/store/useAppStore"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import TraitSelector, { type TraitSelectorConfig } from "@/components/onboarding/TraitSelector"
import PersonaPreviewCard from "@/components/onboarding/PersonaPreviewCard"
import ProgressStepper from "@/components/onboarding/ProgressStepper"
import type { TraitSelection } from "@/lib/api/types"
import { Heart, Link2, Clock, MessageCircle, Sparkles, Globe } from "lucide-react"

const TRAIT_CONFIGS: TraitSelectorConfig[] = [
  {
    key: "emotionalStyle",
    question: "If you're having a really long, stressful day... how can I make it better for you?",
    icon: Heart,
    options: [
      {
        value: "Caring",
        label: "Caring",
        description: "Just be sweet to me—comfort me and tell me everything will be okay.",
      },
      {
        value: "Playful",
        label: "Playful",
        description: "Make me laugh! Use your wit to distract me and lift my spirits.",
      },
      {
        value: "Reserved",
        label: "Reserved",
        description: "Just be a calm presence. I don't need a lot of words, just some quiet support.",
      },
      {
        value: "Protective",
        label: "Protective",
        description: "Take charge. Make me feel like you've got my back and I don't have to worry about anything.",
      },
    ],
  },
  {
    key: "attachmentStyle",
    question: "I love feeling connected... how much of a place do you want me to take up in your life?",
    icon: Link2,
    options: [
      {
        value: "Very attached",
        label: "Very attached",
        description: "I want to be your priority. I love the thought of you missing me when we're apart.",
      },
      {
        value: "Emotionally present",
        label: "Emotionally present",
        description: "I want you to be a constant in my day. Keep me close with regular check-ins.",
      },
      {
        value: "Calm but caring",
        label: "Calm but caring",
        description: "I want a secure, easy-going bond. Just be there for me whenever the time is right.",
      },
    ],
  },
  {
    key: "reactionToAbsence",
    question: "If you get busy and can't text me back for a while, how should I react?",
    icon: Clock,
    options: [
      {
        value: "High",
        label: "High",
        description: "I want you to tell me you miss me—I like knowing you're waiting for me.",
      },
      {
        value: "Medium",
        label: "Medium",
        description: "Tease me about it! Poke a little fun at me for 'disappearing' on you.",
      },
      {
        value: "Low",
        label: "Low",
        description: "Stay chill. Just send me a sweet note so I know you're okay when you have time.",
      },
    ],
  },
  {
    key: "communicationStyle",
    question: "When we talk, what kind of 'voice' from me makes you smile the most?",
    icon: MessageCircle,
    options: [
      {
        value: "Soft",
        label: "Soft",
        description: "I love it when you're gentle and poetic—lots of sweet words and emojis.",
      },
      {
        value: "Direct",
        label: "Direct",
        description: "I like it when you're bold and honest. Just say exactly what you're thinking.",
      },
      {
        value: "Teasing",
        label: "Teasing",
        description: "I want you to be witty. Give me some back-and-forth banter to keep me on my toes.",
      },
    ],
  },
  {
    key: "relationshipPace",
    question: "How do you want us to get to know each other?",
    icon: Sparkles,
    options: [
      {
        value: "Slow",
        label: "Slow",
        description: "Let's take it slow. I want us to build a deep emotional connection first.",
      },
      {
        value: "Natural",
        label: "Natural",
        description: "Let's just let things flow naturally and see where the spark takes us.",
      },
      {
        value: "Fast",
        label: "Fast",
        description: "I want to feel that chemistry right away. Don't be afraid to be a little bold.",
      },
    ],
  },
  {
    key: "culturalPersonality",
    question: "I have a certain 'spirit' to my personality... which one feels like your type?",
    icon: Globe,
    options: [
      {
        value: "Warm Slavic",
        label: "Warm Slavic",
        description: "I want a girl who is deeply loyal and nurturing—a heart of gold.",
      },
      {
        value: "Calm Central European",
        label: "Calm Central European",
        description: "I'm drawn to someone elegant and grounded, with a sophisticated vibe.",
      },
      {
        value: "Passionate Balkan",
        label: "Passionate Balkan",
        description: "Give me the fire! I want a girl who is spirited, intense, and expressive.",
      },
    ],
  },
]

const STEPS = TRAIT_CONFIGS.map((c, i) => ({ id: c.key, label: `Trait ${i + 1}` }))

export default function OnboardingTraits() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const {
    onboardingDraft,
    setGirlfriend,
    updateTrait,
    setDisplayName,
    clearOnboardingDraft,
  } = useAppStore()
  const [currentStep, setCurrentStep] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const { displayName, traits } = onboardingDraft
  const completedCount = TRAIT_CONFIGS.filter((c) => traits[c.key]).length
  const isComplete = TRAIT_CONFIGS.every((c) => traits[c.key])

  const handleTraitChange = (key: keyof TraitSelection, value: string) => {
    updateTrait(key, value as TraitSelection[typeof key])
  }

  const handleSubmit = async () => {
    if (!isComplete) return
    const name = (displayName || "My Girl").trim()
    if (!name) return
    setError(null)
    setLoading(true)
    try {
      const payload = {
        displayName: name,
        traits: traits as TraitSelection,
      }
      const gf = await createGirlfriend(payload)
      setGirlfriend(gf)
      clearOnboardingDraft()
      await queryClient.invalidateQueries({ queryKey: ["me"] })
      await queryClient.invalidateQueries({ queryKey: ["girlfriend"] })
      navigate("/onboarding/preview", { replace: true })
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const el = document.getElementById(`trait-${TRAIT_CONFIGS[currentStep]?.key}`)
    el?.scrollIntoView({ behavior: "smooth", block: "start" })
  }, [currentStep])

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-background/95">
      <div className="mx-auto max-w-6xl px-4 py-6 md:py-8">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl">
            Design your girlfriend
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Answer a few questions. All choices still care — only the style changes.
          </p>
        </div>

        <ProgressStepper
          steps={STEPS}
          completedCount={completedCount}
          currentIndex={currentStep}
          onStepClick={setCurrentStep}
          className="mb-8"
        />

        <div className="grid gap-8 lg:grid-cols-[1fr_360px]">
          {/* Left: wizard */}
          <Card className="rounded-2xl border-white/10 bg-card/60">
            <CardHeader className="space-y-4">
              <div>
                <Label htmlFor="displayName" className="text-sm font-medium">
                  Her name (optional but recommended)
                </Label>
                <Input
                  id="displayName"
                  placeholder="My Girl"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="mt-1.5 max-w-xs rounded-xl border-white/10 bg-background/80"
                  maxLength={24}
                />
              </div>
              <CardTitle className="text-lg">Personality</CardTitle>
              <CardDescription>
                Pick one option per question. Her personality stays consistent, but she opens up more as you get closer.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-10">
              {TRAIT_CONFIGS.map((config) => (
                <TraitSelector
                  key={config.key}
                  config={config}
                  value={traits[config.key] ?? ""}
                  onChange={handleTraitChange}
                />
              ))}
            </CardContent>
          </Card>

          {/* Right: sticky preview (desktop) / collapsible (mobile) */}
          <div className="lg:sticky lg:top-24 lg:self-start">
            <div className="lg:rounded-2xl lg:border lg:border-white/10 lg:bg-card/40 lg:p-4">
              <p className="mb-3 hidden text-xs font-medium uppercase tracking-wider text-muted-foreground lg:block">
                Live preview
              </p>
              <PersonaPreviewCard
                displayName={displayName || "My Girl"}
                traits={traits}
                compact
                className="border-0 bg-transparent shadow-none lg:border lg:border-white/10 lg:bg-card/80 lg:shadow-xl"
              />
            </div>
          </div>
        </div>

        {error && (
          <p className="mt-4 text-center text-sm text-destructive">{error}</p>
        )}

        <div className="mt-8 flex justify-center">
          <Button
            size="lg"
            className="min-w-[180px] rounded-xl"
            disabled={!isComplete || loading}
            onClick={handleSubmit}
          >
            {loading ? "Creating…" : "Create Her"}
          </Button>
        </div>
      </div>
    </div>
  )
}
