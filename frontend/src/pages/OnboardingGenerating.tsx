import { useEffect, useRef, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { completeOnboarding, createAdditionalGirlfriend, getImageJob, guestSession } from "@/lib/api/endpoints"
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
    user,
    girlfriends,
    currentGirlfriendId,
    onboardingTraits,
    onboardingAppearance,
    onboardingContentPrefs,
    onboardingIdentity,
    onboardingImageJobId,
    onboardingMode,
    setGirlfriend,
    setUser,
    setGirlfriends,
    setOnboardingImageJobId,
    setOnboardingIdentityPackage,
    setOnboardingImageJob,
    clearOnboarding,
  } = useAppStore()

  const hasExistingGirlfriend = Boolean(user?.has_girlfriend || currentGirlfriendId || girlfriends.length > 0)
  const wantsAdditional = onboardingMode === "additional" || searchParams.get("mode") === "additional"
  const isAdditional = wantsAdditional && hasExistingGirlfriend

  // Mutation for first-time onboarding
  const firstMutation = useMutation({
    mutationFn: completeOnboarding,
    onSuccess: (res) => {
      setGirlfriend(res.girlfriend)
      setOnboardingImageJobId(res.image_job_id)
      setOnboardingImageJob(res.image_job ?? undefined)
      if (res.identity_package) {
        setOnboardingIdentityPackage(res.identity_package)
      }
      setStatusText("Generating 4 identity candidates...")
      queryClient.invalidateQueries({ queryKey: ["me"] })
    },
    onError: async (err: any) => {
      const msg = err?.message || ""
      if (msg.includes("unauthorized") || msg.includes("session_expired")) {
        setStatusText("Reconnecting session...")
        try {
          const res = await guestSession()
          setUser(res.user)
          if (payload) {
            firstMutation.mutate(payload)
            return
          }
        } catch {
          navigate("/login", { replace: true })
          return
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

  useEffect(() => {
    if (isAdditional) return
    const jobId = onboardingImageJobId
    if (!jobId) return

    let active = true
    const timer = window.setInterval(async () => {
      if (!active) return
      try {
        const job = await getImageJob(jobId)
        setOnboardingImageJob(job)
        if (job.progress_message) {
          setStatusText(job.progress_message)
        }
        if (job.status === "completed" || job.status === "done") {
          if (job.identity_package) {
            setOnboardingIdentityPackage(job.identity_package)
            const currentGf = useAppStore.getState().girlfriend
            if (currentGf) {
              setGirlfriend({
                ...currentGf,
                avatar_url: job.identity_package.main_avatar_url || currentGf.avatar_url,
                identity_images: {
                  main_avatar_url: job.identity_package.main_avatar_url,
                  face_ref_primary_url: job.identity_package.face_ref_primary_url,
                  face_ref_secondary_url: job.identity_package.face_ref_secondary_url,
                  upper_body_ref_url: job.identity_package.upper_body_ref_url,
                  body_ref_url: job.identity_package.body_ref_url,
                  candidate_urls: job.identity_package.candidate_urls,
                },
                identity_metadata: job.identity_package.metadata,
              })
            }
          }
          navigate("/onboarding/reveal", { replace: true })
        } else if (job.status === "failed") {
          setStatusText(job.error || "Avatar generation failed. Please retry.")
        }
      } catch {
        // Keep polling; transient backend/network errors are expected during startup.
      }
    }, 1800)

    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [isAdditional, onboardingImageJobId, setOnboardingImageJob, setOnboardingIdentityPackage, navigate, setGirlfriend])

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
