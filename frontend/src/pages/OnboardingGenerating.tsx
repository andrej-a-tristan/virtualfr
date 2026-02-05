import { useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { completeOnboarding } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export default function OnboardingGenerating() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const {
    onboardingTraits,
    onboardingAppearance,
    onboardingContentPrefs,
    onboardingIdentity,
    setGirlfriend,
    clearOnboarding,
  } = useAppStore()

  const mutation = useMutation({
    mutationFn: completeOnboarding,
    onSuccess: async (gf) => {
      setGirlfriend(gf)
      clearOnboarding()
      await queryClient.invalidateQueries({ queryKey: ["me"] })
      navigate("/onboarding/preview", { replace: true })
    },
    onError: () => {
      navigate("/onboarding/traits", { replace: true })
    },
  })

  useEffect(() => {
    if (!onboardingTraits || !onboardingAppearance || !onboardingContentPrefs || !onboardingIdentity) {
      navigate("/onboarding/traits", { replace: true })
      return
    }
    if (!mutation.isPending && !mutation.isSuccess && !mutation.isError) {
      mutation.mutate({
        traits: onboardingTraits,
        appearance_prefs: onboardingAppearance,
        content_prefs: onboardingContentPrefs,
        identity: onboardingIdentity,
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onboardingTraits, onboardingAppearance, onboardingContentPrefs, onboardingIdentity])

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4 py-12">
      <Card className="w-full max-w-md rounded-2xl border-white/10 bg-card/80">
        <CardHeader className="space-y-2 text-center">
          <CardTitle className="text-2xl font-semibold">
            Crafting your companion
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            We&apos;re generating her portrait and wiring everything up behind the scenes.
          </p>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-4 py-8">
          <div className="flex items-center gap-2">
            <Skeleton className="h-8 w-8 rounded-full" />
            <Skeleton className="h-3 w-20" />
          </div>
          <p className="text-sm text-muted-foreground">
            This is a one-time step and only takes a moment.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

