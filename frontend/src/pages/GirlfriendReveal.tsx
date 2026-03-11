import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { signupSchema, type SignupInput } from "@/lib/api/zod"
import { signup, postAgeGate } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import { useQueryClient } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ArrowRight, Sparkles } from "lucide-react"

export default function GirlfriendReveal() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const girlfriend = useAppStore((s) => s.girlfriend)
  const setUser = useAppStore((s) => s.setUser)
  const [showSignup, setShowSignup] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignupInput>({
    resolver: zodResolver(signupSchema),
    defaultValues: { email: "", password: "", display_name: "" },
  })

  const girlfriendName = girlfriend?.display_name || girlfriend?.name || "Your Girl"
  const avatarUrl = girlfriend?.avatar_url || null

  const onSubmit = async (data: SignupInput) => {
    setError(null)
    try {
      const res = await signup(data.email, data.password, data.display_name)
      setUser({ ...res.user, has_girlfriend: true })
      await postAgeGate()
      await queryClient.invalidateQueries({ queryKey: ["me"] })
      await queryClient.invalidateQueries({ queryKey: ["girlfriendsList"] })
      navigate("/onboarding/subscribe", { replace: true })
    } catch (e) {
      // If signup fails due to backend, still allow proceeding
      const msg = e instanceof Error ? e.message : "Sign up failed"
      if (msg.includes("ECONNREFUSED") || msg.includes("fetch")) {
        // Backend down - continue to subscription anyway
        navigate("/onboarding/subscribe", { replace: true })
      } else {
        setError(msg)
      }
    }
  }

  const handleSkipToSubscribe = () => {
    navigate("/onboarding/subscribe", { replace: true })
  }

  const handleSkipToChat = () => {
    navigate("/app/girl", { replace: true })
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Progress bar */}
      <div className="fixed top-0 inset-x-0 z-50">
        <div className="h-1 bg-muted">
          <div className="h-full bg-primary w-[85%]" />
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center px-4 py-12">
        <div className="w-full max-w-md space-y-8">
          {/* Success message */}
          <div className="text-center space-y-3">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 text-primary text-sm">
              <Sparkles className="w-4 h-4" />
              <span>She's ready</span>
            </div>
            <h1 className="text-3xl md:text-4xl font-serif text-foreground">
              Meet <span className="text-primary">{girlfriendName}</span>
            </h1>
            <p className="text-muted-foreground">
              She can't wait to get to know you
            </p>
          </div>

          {/* Blurred photo card */}
          <div className="relative mx-auto w-64 overflow-hidden rounded-2xl border border-border/50 shadow-2xl">
            <div className="aspect-[3/4] w-full overflow-hidden bg-muted">
              {avatarUrl ? (
                <img
                  src={avatarUrl}
                  alt={girlfriendName}
                  className="h-full w-full object-cover blur-xl scale-110"
                />
              ) : (
                <div className="h-full w-full bg-gradient-to-br from-primary/20 via-primary/5 to-background" />
              )}
            </div>
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent" />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-6xl font-serif text-white/20">{(girlfriendName ?? "?")[0]}</span>
            </div>
            <div className="absolute bottom-0 left-0 right-0 p-5 text-center">
              <p className="text-lg font-serif text-white">{girlfriendName}</p>
              <p className="mt-1 text-sm text-white/60">Waiting to meet you</p>
            </div>
          </div>

          {/* CTA or Signup form */}
          {!showSignup ? (
            <div className="space-y-4">
              <Button
                size="lg"
                className="w-full rounded-lg bg-primary hover:bg-primary/90 gap-2"
                onClick={() => setShowSignup(true)}
              >
                Create account to continue
                <ArrowRight className="h-4 w-4" />
              </Button>
              
              <div className="flex items-center gap-3">
                <div className="flex-1 h-px bg-border" />
                <span className="text-xs text-muted-foreground">or</span>
                <div className="flex-1 h-px bg-border" />
              </div>
              
              <button
                type="button"
                className="w-full text-center text-sm text-muted-foreground hover:text-foreground transition-colors py-2"
                onClick={handleSkipToSubscribe}
              >
                Continue as guest
              </button>
            </div>
          ) : (
            <div className="space-y-5 animate-in fade-in slide-in-from-bottom-4 duration-300">
              <div className="text-center">
                <h2 className="text-xl font-serif">Create your account</h2>
                <p className="text-sm text-muted-foreground mt-1">
                  Save {girlfriendName} and your conversations
                </p>
              </div>

              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                {error && (
                  <p className="text-sm text-destructive text-center">{error}</p>
                )}
                
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-sm">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    className="rounded-lg border-border/50 bg-card/50"
                    {...register("email")}
                  />
                  {errors.email && (
                    <p className="text-xs text-destructive">{errors.email.message}</p>
                  )}
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="password" className="text-sm">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="At least 6 characters"
                    className="rounded-lg border-border/50 bg-card/50"
                    {...register("password")}
                  />
                  {errors.password && (
                    <p className="text-xs text-destructive">{errors.password.message}</p>
                  )}
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="display_name" className="text-sm">
                    Your name <span className="text-muted-foreground">(optional)</span>
                  </Label>
                  <Input
                    id="display_name"
                    placeholder="What should she call you?"
                    className="rounded-lg border-border/50 bg-card/50"
                    {...register("display_name")}
                  />
                </div>
                
                <Button
                  type="submit"
                  className="w-full rounded-lg bg-primary hover:bg-primary/90"
                  size="lg"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? "Creating account..." : "Create account"}
                </Button>
              </form>

              <div className="flex flex-col items-center gap-2 pt-2">
                <button
                  type="button"
                  className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                  onClick={handleSkipToSubscribe}
                >
                  Skip for now
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
