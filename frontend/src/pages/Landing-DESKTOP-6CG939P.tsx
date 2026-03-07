import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQueryClient } from "@tanstack/react-query"
import { guestSession, getMe, getCurrentGirlfriend, logout as apiLogout } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import hero1 from "@/assets/landing/hero-1.png"
import hero2 from "@/assets/landing/hero-2.png"
import hero3 from "@/assets/landing/hero-3.png"
import hero4 from "@/assets/landing/hero-4.png"
import hero5 from "@/assets/landing/hero-5.png"
import hero6 from "@/assets/landing/hero-6.png"

export default function Landing() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const setUser = useAppStore((s) => s.setUser)
  const setGirlfriend = useAppStore((s) => s.setGirlfriend)
  const clearOnboarding = useAppStore((s) => s.clearOnboarding)
  const reset = useAppStore((s) => s.reset)
  const [status, setStatus] = useState("Starting up...")
  const showcaseImages = [hero1, hero2, hero3, hero4, hero5, hero6]

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
    <div className="relative min-h-screen overflow-hidden bg-background text-foreground">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_20%,rgba(236,72,153,0.25),transparent_45%),radial-gradient(circle_at_80%_0%,rgba(192,132,252,0.2),transparent_40%),radial-gradient(circle_at_50%_90%,rgba(56,189,248,0.16),transparent_45%)]" />

      <div className="relative mx-auto grid min-h-screen max-w-7xl grid-cols-1 gap-10 px-6 py-10 lg:grid-cols-[1.15fr_1fr] lg:items-center">
        <section className="space-y-7">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-xs font-medium tracking-wide text-primary">
            <span className="h-2 w-2 rounded-full bg-primary" />
            AI Companion Experience
          </div>

          <div className="space-y-4">
            <h1 className="text-4xl font-bold leading-tight tracking-tight md:text-5xl lg:text-6xl">
              Your virtual girlfriend, crafted from your vibe.
            </h1>
            <p className="max-w-xl text-base text-muted-foreground md:text-lg">
              We are preparing your personalized experience with high-quality visuals and instant chat chemistry.
            </p>
          </div>

          <div className="w-full max-w-xl rounded-2xl border border-border/70 bg-card/80 p-4 backdrop-blur">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              <div>
                <p className="text-sm font-medium text-foreground">Launching your session</p>
                <p className="text-sm text-muted-foreground">{status}</p>
              </div>
            </div>
          </div>
        </section>

        <section className="grid grid-cols-2 gap-4 sm:gap-5">
          {showcaseImages.map((imageSrc, index) => (
            <article
              key={imageSrc}
              className="group relative overflow-hidden rounded-2xl border border-white/10 bg-card/80 shadow-[0_20px_55px_rgba(0,0,0,0.35)]"
            >
              <img
                src={imageSrc}
                alt={`Featured AI companion ${index + 1}`}
                className="h-48 w-full object-cover object-top transition-transform duration-500 group-hover:scale-105 sm:h-64"
                loading={index === 0 ? "eager" : "lazy"}
              />
              <div className="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/60 to-transparent" />
            </article>
          ))}
        </section>
      </div>
    </div>
  )
}
