import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQueryClient } from "@tanstack/react-query"
import { guestSession, getMe, getCurrentGirlfriend, logout as apiLogout } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"

export default function Landing() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const setUser = useAppStore((s) => s.setUser)
  const setGirlfriend = useAppStore((s) => s.setGirlfriend)
  const reset = useAppStore((s) => s.reset)
  const [status, setStatus] = useState("Starting up...")

  useEffect(() => {
    let cancelled = false
    async function autoSetup() {
      try {
        // Check if the user already has a valid session with a working girlfriend
        try {
          const existingUser = await getMe()
          if (!cancelled && existingUser?.has_girlfriend && existingUser?.age_gate_passed) {
            // Verify the girlfriend actually exists before redirecting to app
            const gf = await getCurrentGirlfriend()
            if (!cancelled && gf) {
              setUser(existingUser)
              setGirlfriend(gf)
              navigate("/app/girl", { replace: true })
              return
            }
            // Girlfriend doesn't exist — fall through to fresh onboarding
          }
        } catch {
          // No valid session — proceed with guest setup
        }

        // Clear ALL stale state for a fresh onboarding
        reset()
        queryClient.clear()

        // Also clear the backend session cookie
        try { await apiLogout() } catch { /* ignore */ }

        if (!cancelled) setStatus("Setting up...")

        // Create a fresh guest session so onboarding pages work
        const { user } = await guestSession()
        if (!cancelled) {
          setUser(user)
          // Go straight to appearance (first onboarding step)
          navigate("/onboarding/appearance", { replace: true })
        }
      } catch (e) {
        if (!cancelled) setStatus(`Error: ${e instanceof Error ? e.message : String(e)}`)
      }
    }
    autoSetup()
    return () => { cancelled = true }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-background to-background/95">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      <p className="mt-4 text-sm text-muted-foreground">{status}</p>
    </div>
  )
}
