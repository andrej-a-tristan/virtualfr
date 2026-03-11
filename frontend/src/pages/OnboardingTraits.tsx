import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAppStore } from "@/lib/store/useAppStore"
import type { TraitSelection } from "@/lib/api/types"
import { ChevronRight, ChevronLeft, Heart, MessageCircle, Clock, Sparkles, Link2, Globe } from "lucide-react"
import { cn } from "@/lib/utils"

interface TraitQuestion {
  key: keyof TraitSelection
  question: string
  subtext: string
  icon: typeof Heart
  options: { value: string; label: string; emoji: string }[]
}

const QUESTIONS: TraitQuestion[] = [
  {
    key: "emotionalStyle",
    question: "When you need comfort...",
    subtext: "How should she be there for you?",
    icon: Heart,
    options: [
      { value: "Caring", label: "Nurturing & warm", emoji: "💝" },
      { value: "Playful", label: "Light & playful", emoji: "✨" },
      { value: "Reserved", label: "Calm presence", emoji: "🌙" },
      { value: "Protective", label: "Strong & reassuring", emoji: "🛡️" },
    ],
  },
  {
    key: "attachmentStyle",
    question: "How close do you want to feel?",
    subtext: "The intensity of your connection",
    icon: Link2,
    options: [
      { value: "Very attached", label: "Deeply intertwined", emoji: "💫" },
      { value: "Emotionally present", label: "Always there", emoji: "🤍" },
      { value: "Calm but caring", label: "Easy & secure", emoji: "☁️" },
    ],
  },
  {
    key: "reactionToAbsence",
    question: "When you're away...",
    subtext: "How should she respond?",
    icon: Clock,
    options: [
      { value: "High", label: "Miss me intensely", emoji: "💭" },
      { value: "Medium", label: "Playfully tease", emoji: "😏" },
      { value: "Low", label: "Patiently wait", emoji: "🕊️" },
    ],
  },
  {
    key: "communicationStyle",
    question: "Her voice should be...",
    subtext: "How she expresses herself",
    icon: MessageCircle,
    options: [
      { value: "Soft", label: "Gentle & poetic", emoji: "🌸" },
      { value: "Direct", label: "Bold & honest", emoji: "⚡" },
      { value: "Teasing", label: "Witty & playful", emoji: "😈" },
    ],
  },
  {
    key: "relationshipPace",
    question: "How fast should things move?",
    subtext: "The rhythm of your relationship",
    icon: Sparkles,
    options: [
      { value: "Slow", label: "Build it slowly", emoji: "🌱" },
      { value: "Natural", label: "Let it flow", emoji: "🌊" },
      { value: "Fast", label: "Dive right in", emoji: "🔥" },
    ],
  },
  {
    key: "culturalPersonality",
    question: "Her spirit feels...",
    subtext: "The essence of her personality",
    icon: Globe,
    options: [
      { value: "Warm Slavic", label: "Loyal & nurturing", emoji: "❄️" },
      { value: "Calm Central European", label: "Elegant & grounded", emoji: "🏔️" },
      { value: "Passionate Balkan", label: "Fiery & expressive", emoji: "🌶️" },
    ],
  },
]

export default function OnboardingTraits() {
  const navigate = useNavigate()
  const { onboardingDraft, updateTrait, setOnboardingTraits } = useAppStore()
  const [currentIndex, setCurrentIndex] = useState(0)

  const { traits } = onboardingDraft
  const currentQuestion = QUESTIONS[currentIndex]
  const selectedValue = traits[currentQuestion.key] ?? ""
  const answeredCount = QUESTIONS.filter((q) => traits[q.key]).length
  const allAnswered = answeredCount === QUESTIONS.length
  const Icon = currentQuestion.icon

  const handleSelect = (value: string) => {
    updateTrait(currentQuestion.key, value as TraitSelection[typeof currentQuestion.key])
    
    // Auto-advance after brief delay
    if (currentIndex < QUESTIONS.length - 1) {
      setTimeout(() => setCurrentIndex(currentIndex + 1), 400)
    }
  }

  const handleBack = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1)
    } else {
      navigate("/onboarding/appearance", { replace: true })
    }
  }

  const handleContinue = () => {
    if (!allAnswered) return
    
    const snakeCaseTraits = {
      emotional_style: traits.emotionalStyle!,
      attachment_style: traits.attachmentStyle!,
      reaction_to_absence: traits.reactionToAbsence!,
      communication_style: traits.communicationStyle!,
      relationship_pace: traits.relationshipPace!,
      cultural_personality: traits.culturalPersonality!,
    }
    setOnboardingTraits(snakeCaseTraits)
    navigate("/onboarding/preferences", { replace: true })
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Progress bar */}
      <div className="fixed top-0 inset-x-0 z-50">
        <div className="h-1 bg-muted">
          <div 
            className="h-full bg-primary transition-all duration-500 ease-out"
            style={{ width: `${((currentIndex + 1) / QUESTIONS.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-16">
        <div className="w-full max-w-lg">
          {/* Step indicator */}
          <div className="flex items-center justify-between mb-8">
            <button 
              onClick={handleBack}
              className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              <span className="text-sm">Back</span>
            </button>
            <span className="text-xs text-muted-foreground tracking-wider uppercase">
              {currentIndex + 1} of {QUESTIONS.length}
            </span>
          </div>

          {/* Question */}
          <div className="text-center mb-10">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary/10 text-primary mb-5">
              <Icon className="w-5 h-5" />
            </div>
            <h1 className="text-3xl md:text-4xl font-serif text-foreground mb-2">
              {currentQuestion.question}
            </h1>
            <p className="text-muted-foreground">
              {currentQuestion.subtext}
            </p>
          </div>

          {/* Options */}
          <div className="space-y-3 mb-10">
            {currentQuestion.options.map((option) => {
              const isSelected = selectedValue === option.value
              return (
                <button
                  key={option.value}
                  onClick={() => handleSelect(option.value)}
                  className={cn(
                    "w-full flex items-center gap-4 p-4 rounded-xl border transition-all duration-200 text-left",
                    isSelected
                      ? "border-primary bg-primary/5 scale-[1.02]"
                      : "border-border/50 hover:border-primary/50 hover:bg-muted/30"
                  )}
                >
                  <span className="text-2xl">{option.emoji}</span>
                  <span className={cn(
                    "font-medium",
                    isSelected ? "text-primary" : "text-foreground"
                  )}>
                    {option.label}
                  </span>
                  {isSelected && (
                    <div className="ml-auto w-5 h-5 rounded-full bg-primary flex items-center justify-center">
                      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  )}
                </button>
              )
            })}
          </div>

          {/* Progress dots */}
          <div className="flex items-center justify-center gap-2 mb-8">
            {QUESTIONS.map((q, i) => (
              <button
                key={q.key}
                onClick={() => setCurrentIndex(i)}
                className={cn(
                  "w-2 h-2 rounded-full transition-all duration-300",
                  i === currentIndex 
                    ? "bg-primary w-6" 
                    : traits[q.key] 
                      ? "bg-primary/50" 
                      : "bg-muted"
                )}
              />
            ))}
          </div>

          {/* Continue button - only show on last question when all answered */}
          {currentIndex === QUESTIONS.length - 1 && allAnswered && (
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
        </div>
      </div>
    </div>
  )
}
