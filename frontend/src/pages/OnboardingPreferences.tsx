import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { getOnboardingPromptImages } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

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

export default function OnboardingPreferences() {
  const navigate = useNavigate()
  const setOnboardingContentPrefs = useAppStore((s) => s.setOnboardingContentPrefs)
  const [wantsSpicyPhotos, setWantsSpicyPhotos] = useState<boolean | null>(null)

  const { data: promptImages } = useQuery({
    queryKey: ["onboardingPromptImages"],
    queryFn: getOnboardingPromptImages,
  })

  const handleContinue = () => {
    if (wantsSpicyPhotos == null) return
    setOnboardingContentPrefs({ wants_spicy_photos: wantsSpicyPhotos })
    navigate("/onboarding/identity", { replace: true })
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8 px-4 py-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight">Content preferences</h1>
        <p className="mt-2 text-muted-foreground">
          Set boundaries for how playful and spicy your connection can be.
        </p>
      </div>

      <QuestionCard
        title="Do you want her to occasionally send spicy photos?"
        imageUrl={promptImages?.content_spicy}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            className={`rounded-xl border-2 px-4 py-3 text-left text-sm transition-colors ${
              wantsSpicyPhotos === true
                ? "border-primary bg-primary/10"
                : "border-white/10 hover:border-white/20"
            }`}
            onClick={() => setWantsSpicyPhotos(true)}
          >
            Yes, I&apos;m okay with spicy photos
          </button>
          <button
            type="button"
            className={`rounded-xl border-2 px-4 py-3 text-left text-sm transition-colors ${
              wantsSpicyPhotos === false
                ? "border-primary bg-primary/10"
                : "border-white/10 hover:border-white/20"
            }`}
            onClick={() => setWantsSpicyPhotos(false)}
          >
            No, keep things non-explicit
          </button>
        </div>
      </QuestionCard>

      <div className="flex justify-center pt-2">
        <Button size="lg" disabled={wantsSpicyPhotos == null} onClick={handleContinue}>
          Continue
        </Button>
      </div>
    </div>
  )
}

