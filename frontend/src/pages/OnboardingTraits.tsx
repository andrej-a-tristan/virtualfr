import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useAppStore } from "@/lib/store/useAppStore"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import TraitSelector, { type TraitSelectorConfig } from "@/components/onboarding/TraitSelector"
import PersonaPreviewCard from "@/components/onboarding/PersonaPreviewCard"
import ProgressStepper from "@/components/onboarding/ProgressStepper"
import type { TraitSelection } from "@/lib/api/types"
import { Heart, Link2, Clock, MessageCircle, Sparkles, Globe } from "lucide-react"
import OnboardingSignIn from "@/components/onboarding/OnboardingSignIn"

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
  const {
    onboardingDraft,
    updateTrait,
    setOnboardingTraits,
  } = useAppStore()
  const [currentStep, setCurrentStep] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const { traits } = onboardingDraft
  const completedCount = TRAIT_CONFIGS.filter((c) => traits[c.key]).length
  const isComplete = TRAIT_CONFIGS.every((c) => traits[c.key])

  const handleTraitChange = (key: keyof TraitSelection, value: string) => {
    updateTrait(key, value as TraitSelection[typeof key])
  }

  const handleSubmit = async () => {
    if (!isComplete) return
    setError(null)
    setLoading(true)
    try {
      // Convert camelCase traits to snake_case for the extended onboarding flow
      const snakeCaseTraits = {
        emotional_style: traits.emotionalStyle!,
        attachment_style: traits.attachmentStyle!,
        reaction_to_absence: traits.reactionToAbsence!,
        communication_style: traits.communicationStyle!,
        relationship_pace: traits.relationshipPace!,
        cultural_personality: traits.culturalPersonality!,
      }
      setOnboardingTraits(snakeCaseTraits)
      // Move to next step (preferences)
      // Girlfriend name is set in the identity step
      navigate("/onboarding/preferences", { replace: true })
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
    <div className="min-h-screen bg-background">
      <OnboardingSignIn />
      <div className="mx-auto max-w-6xl px-4 py-8 md:py-12">
        <div className="mb-10 text-center">
          <p className="text-primary text-sm font-medium tracking-[0.2em] uppercase mb-3">
            Step 2 of 5
          </p>
          <h1 className="text-3xl font-serif font-medium text-foreground md:text-4xl lg:text-5xl">
            Shape her <span className="text-primary">personality</span>.
          </h1>
          <p className="mt-4 text-muted-foreground max-w-lg mx-auto">
            Answer a few questions to define how she connects with you. Every choice shapes her unique character.
          </p>
        </div>

        <ProgressStepper
          steps={STEPS}
          completedCount={completedCount}
          currentIndex={currentStep}
          onStepClick={setCurrentStep}
          className="mb-10"
        />

        <div className="grid gap-8 lg:grid-cols-[1fr_360px]">
          {/* Left: wizard */}
          <Card className="rounded-2xl border-border/50 bg-card/40 backdrop-blur-sm">
            <CardHeader className="space-y-4 border-b border-border/30 pb-6">
              <CardTitle className="text-xl font-serif">Her Personality</CardTitle>
              <CardDescription className="text-muted-foreground">
                Each question reveals a different side of her. Pick what resonates with you.
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
            <div className="lg:rounded-2xl lg:border lg:border-border/50 lg:bg-card/40 lg:backdrop-blur-sm lg:p-5">
              <p className="mb-4 hidden text-xs font-medium uppercase tracking-[0.15em] text-primary lg:block">
                Live Preview
              </p>
              <PersonaPreviewCard
                displayName="Your Girl"
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

        <div className="mt-10 flex flex-col items-center gap-4">
          <Button
            size="lg"
            className="min-w-[200px] rounded-lg bg-primary hover:bg-primary/90 px-8 py-6 text-base"
            disabled={!isComplete || loading}
            onClick={handleSubmit}
          >
            {loading ? "Saving..." : "Continue"}
          </Button>
          <p className="text-sm text-muted-foreground">
            {completedCount} of {TRAIT_CONFIGS.length} traits selected
          </p>
        </div>
      </div>
    </div>
  )
}
