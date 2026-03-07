import { useEffect } from "react"
import { useNavigate } from "react-router-dom"
import {
  getMe,
  getCurrentGirlfriend,
  listGirlfriends,
  switchGirlfriend,
  guestSession,
} from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"

export default function Landing() {
  const navigate = useNavigate()
  const setUser = useAppStore((s) => s.setUser)
  const setGirlfriend = useAppStore((s) => s.setGirlfriend)
  const setOnboardingMode = useAppStore((s) => s.setOnboardingMode)

  useEffect(() => {
    let cancelled = false
    async function checkSession() {
      try {
        const existingUser = await getMe()
        if (cancelled) return
        setUser(existingUser)

        if (existingUser?.has_girlfriend && existingUser?.age_gate_passed) {
          const currentGf = await getCurrentGirlfriend()
          if (!cancelled && currentGf) {
            setGirlfriend(currentGf)
            navigate("/app/girl", { replace: true })
            return
          }

          // Recover from a stale current_girlfriend_id by falling back to list[0].
          const list = await listGirlfriends().catch(() => null)
          const fallbackGf = list?.girlfriends?.[0]
          if (!cancelled && fallbackGf) {
            if (!list?.current_girlfriend_id || list.current_girlfriend_id !== fallbackGf.id) {
              await switchGirlfriend(fallbackGf.id).catch(() => undefined)
            }
            setGirlfriend(fallbackGf)
            navigate("/app/girl", { replace: true })
            return
          }

          if (!cancelled) {
            navigate("/onboarding/appearance", { replace: true })
            return
          }
        }

        if (!cancelled && existingUser?.age_gate_passed && !existingUser?.has_girlfriend) {
          navigate("/onboarding/appearance", { replace: true })
          return
        }

        if (!cancelled && !existingUser?.age_gate_passed) {
          navigate("/age-gate", { replace: true })
          return
        }
      } catch {
        // No valid session — create a guest session for onboarding.
      }
      try {
        const res = await guestSession()
        if (!cancelled) {
          setOnboardingMode("first")
          setUser(res.user)
          navigate("/onboarding/appearance", { replace: true })
          return
        }
      } catch {
        // fall through to legacy onboarding route even if guest bootstrap fails
      }
      if (!cancelled) navigate("/onboarding/appearance", { replace: true })
    }
    checkSession()
    return () => { cancelled = true }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-background to-background/95">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      <p className="mt-4 text-sm text-muted-foreground">Loading...</p>
    </div>
  )
}
