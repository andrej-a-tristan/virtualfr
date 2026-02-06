import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { getOnboardingPromptImages } from "@/lib/api/endpoints"
import type { AppearancePrefs } from "@/lib/api/types"
import { useAppStore } from "@/lib/store/useAppStore"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

type AppearanceKey = keyof AppearancePrefs

const APPEARANCE_OPTIONS: Record<AppearanceKey, string[]> = {
  vibe: ["cute", "elegant", "sporty", "goth", "girl-next-door", "model"],
  age_range: ["18", "19-21", "22-26", "27+"],
  ethnicity: ["any", "asian", "black", "latina", "white", "middle-eastern", "south-asian"],
  breast_size: ["small", "medium", "large", "massive"],
  butt_size: ["small", "medium", "large", "massive"],
  hair_color: ["black", "brown", "blonde", "red", "ginger", "unnatural"],
  hair_style: ["long", "bob", "curly", "straight", "bun"],
  eye_color: ["brown", "blue", "green", "hazel"],
  body_type: ["slim", "athletic", "curvy"],
}

const LABELS: Record<AppearanceKey, string> = {
  vibe: "Overall vibe",
  age_range: "Apparent age range",
  ethnicity: "Ethnicity",
  breast_size: "Breast size",
  butt_size: "Butt size",
  hair_color: "Hair color",
  hair_style: "Hair style",
  eye_color: "Eye color",
  body_type: "Body type",
}

const PROMPT_KEYS: Record<AppearanceKey, string> = {
  vibe: "appearance_vibe",
  age_range: "appearance_age_range",
  ethnicity: "appearance_ethnicity",
  breast_size: "appearance_breast_size",
  butt_size: "appearance_butt_size",
  hair_color: "appearance_hair_color",
  hair_style: "appearance_hair_style",
  eye_color: "appearance_eye_color",
  body_type: "appearance_body_type",
}

function QuestionCard(props: {
  title: string
  imageUrl?: string
  children: React.ReactNode
}) {
  const { title, imageUrl, children } = props
  return (
    <Card className="overflow-hidden rounded-2xl border-white/10 bg-card/80">
      <CardHeader>
        <CardTitle className="text-base font-semibold">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] md:items-center">
          <div className="space-y-3">{children}</div>
          {imageUrl && (
            <div className="mt-2 md:mt-0">
              <div className="aspect-video w-full overflow-hidden rounded-xl bg-muted">
                <img
                  src={imageUrl}
                  alt={title}
                  className="h-full w-full object-cover"
                />
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export default function OnboardingAppearance() {
  const navigate = useNavigate()
  const setOnboardingAppearance = useAppStore((s) => s.setOnboardingAppearance)
  const [prefs, setPrefs] = useState<AppearancePrefs>({})

  const { data: promptImages } = useQuery({
    queryKey: ["onboardingPromptImages"],
    queryFn: getOnboardingPromptImages,
  })

  const updatePref = (key: AppearanceKey, value: string) => {
    setPrefs((prev) => ({ ...prev, [key]: value as any }))
  }

  const isComplete = (Object.keys(APPEARANCE_OPTIONS) as AppearanceKey[]).every(
    (key) => prefs[key]
  )

  const handleContinue = () => {
    if (!isComplete) return
    setOnboardingAppearance(prefs)
    navigate("/onboarding/preferences", { replace: true })
  }

  const handleBack = () => {
    navigate("/onboarding/traits", { replace: true })
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8 px-4 py-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight">Tune her appearance</h1>
        <p className="mt-2 text-muted-foreground">
          Choose how she looks. These preferences guide her portrait.
        </p>
      </div>

      <div className="space-y-6">
        {(Object.keys(APPEARANCE_OPTIONS) as AppearanceKey[]).map((key) => {
          const options = APPEARANCE_OPTIONS[key]
          const imageKey = PROMPT_KEYS[key]
          const imageUrl = promptImages?.[imageKey]

          return (
            <QuestionCard key={key} title={LABELS[key]} imageUrl={imageUrl}>
              <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
                {options.map((value) => {
                  const optionImageKey = `${imageKey}_${value}`
                  const optionImageUrl = promptImages?.[optionImageKey]
                  return (
                    <button
                      key={value}
                      type="button"
                      className={cn(
                        "flex flex-col overflow-hidden rounded-xl border-2 text-left transition-colors",
                        prefs[key] === value
                          ? "border-primary bg-primary/10"
                          : "border-white/10 hover:border-white/20"
                      )}
                      onClick={() => updatePref(key, value)}
                    >
                      <span className="px-3 py-2 text-sm font-medium capitalize">
                        {value.replace(/-/g, " ")}
                      </span>
                      <div className="aspect-video min-h-[80px] w-full shrink-0 overflow-hidden rounded-b-lg bg-muted">
                        {optionImageUrl ? (
                          <img
                            src={optionImageUrl}
                            alt=""
                            className="h-full w-full object-cover"
                          />
                        ) : (
                          <div className="flex h-full w-full items-center justify-center text-xs text-muted-foreground">
                            Image
                          </div>
                        )}
                      </div>
                    </button>
                  )
                })}
              </div>
            </QuestionCard>
          )
        })}
      </div>

      <div className="flex justify-center gap-4 pt-2">
        <Button variant="outline" size="lg" onClick={handleBack}>
          Back
        </Button>
        <Button size="lg" disabled={!isComplete} onClick={handleContinue}>
          Continue
        </Button>
      </div>
    </div>
  )
}

