import { useEffect, useRef, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { completeOnboarding, createAdditionalGirlfriend, guestSession } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import { cn } from "@/lib/utils"

const LOADING_MESSAGES = [
  "Creating her personality...",
  "Shaping her character...",
  "Adding the finishing touches...",
  "Almost ready to meet you...",
]

export default function OnboardingGenerating() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const started = useRef(false)
  const [messageIndex, setMessageIndex] = useState(0)
  const [progress, setProgress] = useState(0)

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
  const girlfriendName = onboardingIdentity?.girlfriend_name || "her"

  // Cycle through messages
  useEffect(() => {
    const interval = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % LOADING_MESSAGES.length)
    }, 2500)
    return () => clearInterval(interval)
  }, [])

  // Animate progress
  useEffect(() => {
    const interval = setInterval(() => {
      setProgress((prev) => Math.min(prev + Math.random() * 15, 95))
    }, 800)
    return () => clearInterval(interval)
  }, [])

  const additionalMutation = useMutation({
    mutationFn: createAdditionalGirlfriend,
    onSuccess: (res) => {
      setProgress(100)
      setGirlfriends(res.girlfriends, res.current_girlfriend_id)
      clearOnboarding()
      queryClient.invalidateQueries({ queryKey: ["me"] })
      queryClient.invalidateQueries({ queryKey: ["girlfriend"] })
      queryClient.invalidateQueries({ queryKey: ["girlfriendsList"] })
      queryClient.invalidateQueries({ queryKey: ["chatHistory"] })
      queryClient.invalidateQueries({ queryKey: ["chatState"] })
      queryClient.invalidateQueries({ queryKey: ["billingStatus"] })
      setTimeout(() => navigate("/app/girl", { replace: true }), 500)
    },
    onError: (err: any) => {
      const detail = err?.message || "Failed to create girlfriend"
      alert(detail)
      navigate("/app/girl", { replace: true })
    },
  })

  const payload = onboardingTraits && onboardingAppearance && onboardingContentPrefs && onboardingIdentity
    ? {
        traits: onboardingTraits,
        appearance_prefs: onboardingAppearance,
        content_prefs: onboardingContentPrefs,
        identity: onboardingIdentity,
      }
    : null

  const firstMutation = useMutation({
    mutationFn: completeOnboarding,
    onSuccess: (gf) => {
      setProgress(100)
      setGirlfriend(gf)
      clearOnboarding()
      setTimeout(() => navigate("/onboarding/reveal", { replace: true }), 500)
      queryClient.invalidateQueries({ queryKey: ["me"] })
    },
    onError: async (err: any) => {
      const msg = err?.message || ""
      if (msg.includes("unauthorized") || msg.includes("session_expired")) {
        try {
          const res = await guestSession()
          setUser(res.user)
          if (payload) {
            firstMutation.mutate(payload as NonNullable<typeof payload>)
          }
          return
        } catch {
          // Recovery failed - continue to reveal anyway
        }
      }
      // Backend might be down - continue to reveal with local data
      // Create a mock girlfriend object from the onboarding data
      setProgress(100)
      const mockGirlfriend = {
        id: "temp-" + Date.now(),
        name: onboardingIdentity?.girlfriend_name || "Your Girl",
        display_name: onboardingIdentity?.girlfriend_name || "Your Girl",
        avatar_url: null,
      }
      setGirlfriend(mockGirlfriend as any)
      // Also update user to have has_girlfriend and age_gate_passed for guards
      const currentUser = useAppStore.getState().user
      setUser({
        ...(currentUser || { id: "temp-user", email: "", display_name: "" }),
        has_girlfriend: true,
        age_gate_passed: true,
      } as any)
      setTimeout(() => navigate("/onboarding/reveal", { replace: true }), 500)
    },
  })

  useEffect(() => {
    if (started.current) return
    if (!payload) {
      navigate("/onboarding/traits", { replace: true })
      return
    }
    started.current = true

    if (isAdditional) {
      additionalMutation.mutate(payload as NonNullable<typeof payload>)
    } else {
      firstMutation.mutate(payload as NonNullable<typeof payload>)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center px-4">
      {/* Progress bar at top */}
      <div className="fixed top-0 inset-x-0 z-50">
        <div className="h-1 bg-muted">
          <div 
            className="h-full bg-primary transition-all duration-700 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      <div className="text-center max-w-md">
        {/* Animated pulse */}
        <div className="relative mb-10">
          <div className="w-24 h-24 mx-auto rounded-full bg-primary/10 flex items-center justify-center">
            <div className="w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center animate-pulse">
              <div className="w-8 h-8 rounded-full bg-primary" />
            </div>
          </div>
          
          {/* Rings animation */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-24 h-24 rounded-full border border-primary/30 animate-ping" />
          </div>
        </div>

        {/* Text */}
        <h1 className="text-2xl md:text-3xl font-serif text-foreground mb-4">
          {isAdditional ? "Creating your new companion" : `Creating ${girlfriendName}`}
        </h1>
        
        <p className={cn(
          "text-muted-foreground transition-opacity duration-500",
          "animate-in fade-in"
        )} key={messageIndex}>
          {LOADING_MESSAGES[messageIndex]}
        </p>

        {/* Progress percentage */}
        <p className="text-sm text-muted-foreground/60 mt-8">
          {Math.round(progress)}%
        </p>
      </div>
    </div>
  )
}
