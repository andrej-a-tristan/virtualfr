import { useEffect, useRef, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { completeOnboarding, createAdditionalGirlfriend, guestSession } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export default function OnboardingGenerating() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const started = useRef(false)
  const [statusText, setStatusText] = useState("This only takes a moment.")

  const {
    onboardingTraits,
    onboardingAppearance,
    onboardingContentPrefs,
    onboardingIdentity,
    onboardingMode,
    setGirlfriend,
    setUser,
    setGirlfriends,
    clearOnboarding,
  } = useAppStore()

  const isAdditional = onboardingMode === "additional" || searchParams.get("mode") === "additional"

  // Mutation for first-time onboarding
  const firstMutation = useMutation({
    mutationFn: completeOnboarding,
    onSuccess: (res) => {
      setGirlfriend(res.girlfriend)
      clearOnboarding()
      navigate("/onboarding/reveal", { replace: true })
      queryClient.invalidateQueries({ queryKey: ["me"] })
    },
    onError: async (err: any) => {
      const msg = err?.message || ""
      // If session was lost (401), try to recover and retry
      if (msg.includes("unauthorized") || msg.includes("session_expired")) {
        setStatusText("Reconnecting session...")
        try {
          const res = await guestSession()
          setUser(res.user)
          // Retry the mutation
          if (payload) firstMutation.mutate(payload)
          return
        } catch {
          // Recovery failed
        }
      }
      navigate("/onboarding/traits", { replace: true })
    },
  })

  // Mutation for additional girlfriend creation
  const additionalMutation = useMutation({
    mutationFn: createAdditionalGirlfriend,
    onSuccess: (res) => {
      setGirlfriends(res.girlfriends, res.current_girlfriend_id)
      clearOnboarding()
      queryClient.invalidateQueries({ queryKey: ["me"] })
      queryClient.invalidateQueries({ queryKey: ["girlfriend"] })
      queryClient.invalidateQueries({ queryKey: ["girlfriendsList"] })
      queryClient.invalidateQueries({ queryKey: ["chatHistory"] })
      queryClient.invalidateQueries({ queryKey: ["chatState"] })
      queryClient.invalidateQueries({ queryKey: ["billingStatus"] })
      navigate("/app/girl", { replace: true })
    },
    onError: (err: any) => {
      const detail = err?.message || "Failed to create girlfriend"
      alert(detail)
      navigate("/app/girl", { replace: true })
    },
  })

  // Build the payload (used in both initial attempt and retry)
  const payload = onboardingTraits && onboardingAppearance && onboardingContentPrefs && onboardingIdentity
    ? {
        traits: onboardingTraits,
        appearance_prefs: onboardingAppearance,
        content_prefs: onboardingContentPrefs,
        identity: onboardingIdentity,
      }
    : null

  useEffect(() => {
    if (started.current) return
    if (!payload) {
      navigate("/onboarding/traits", { replace: true })
      return
    }
    started.current = true

    if (isAdditional) {
      additionalMutation.mutate(payload)
    } else {
      firstMutation.mutate(payload)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4 py-12">
      <Card className="w-full max-w-md rounded-2xl border-white/10 bg-card/80">
        <CardHeader className="space-y-2 text-center">
          <CardTitle className="text-2xl font-semibold">
            {isAdditional ? "Creating your new companion" : "Crafting your companion"}
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            {isAdditional
              ? "Setting up her personality and wiring everything up..."
              : "We're generating her portrait and wiring everything up behind the scenes."}
          </p>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-4 py-8">
          <div className="flex items-center gap-2">
            <Skeleton className="h-8 w-8 rounded-full" />
            <Skeleton className="h-3 w-20" />
          </div>
          <p className="text-sm text-muted-foreground">
            {statusText}
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
