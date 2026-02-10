import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQueryClient } from "@tanstack/react-query"
import { login, postAgeGate, getMe } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"

export default function Landing() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const setUser = useAppStore((s) => s.setUser)
  const setGirlfriend = useAppStore((s) => s.setGirlfriend)
  const clearOnboarding = useAppStore((s) => s.clearOnboarding)
  const [status, setStatus] = useState("Starting up...")

  useEffect(() => {
    let cancelled = false
    async function autoSetup() {
      try {
        // Clear ALL stale state: onboarding, girlfriend, and React Query cache
        clearOnboarding()
        setGirlfriend(null)
        queryClient.clear()

        if (!cancelled) setStatus("Signing in...")
        const randomId = `dev-${Date.now()}`
        const { user } = await login(randomId + "@devtest.com", "dev123")
        if (!cancelled) setUser(user)

        if (!user.age_gate_passed) {
          if (!cancelled) setStatus("Passing age gate...")
          await postAgeGate()
          // Update local store + invalidate cache so RequireAgeGate guard sees it
          if (!cancelled) setUser({ ...user, age_gate_passed: true })
          await queryClient.invalidateQueries({ queryKey: ["me"] })
        }

        if (!cancelled) navigate("/onboarding/appearance", { replace: true })
      } catch (e) {
        if (!cancelled) setStatus(`Error: ${e instanceof Error ? e.message : String(e)}`)
      }
    }
    autoSetup()
    return () => { cancelled = true }
  }, [navigate, setUser, setGirlfriend, clearOnboarding])

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-background to-background/95">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      <p className="mt-4 text-sm text-muted-foreground">{status}</p>
    </div>
  )
}
