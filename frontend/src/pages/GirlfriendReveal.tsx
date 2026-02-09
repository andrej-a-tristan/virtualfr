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
import { Eye, Sparkles } from "lucide-react"

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

  const girlfriendName =
    girlfriend?.display_name || girlfriend?.name || "Your Girl"
  const avatarUrl = girlfriend?.avatar_url || null

  const onSubmit = async (data: SignupInput) => {
    setError(null)
    try {
      const res = await signup(data.email, data.password, data.display_name)
      setUser(res.user)
      await postAgeGate()
      await queryClient.invalidateQueries({ queryKey: ["me"] })
      // After account creation, go to subscription page
      navigate("/onboarding/subscribe", { replace: true })
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sign up failed")
    }
  }

  // Skip signup — already have a session (dev auto-login)
  const handleSkipToSubscribe = () => {
    navigate("/onboarding/subscribe", { replace: true })
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-background to-background/95 px-4 py-12">
      <div className="w-full max-w-md space-y-8">
        {/* Title */}
        <div className="text-center space-y-2">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <Sparkles className="h-6 w-6 text-primary" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight md:text-4xl">
            {girlfriendName} is ready
          </h1>
          <p className="text-muted-foreground">
            We&apos;ve crafted her just for you
          </p>
        </div>

        {/* Blurred photo card */}
        <div className="relative mx-auto w-72 overflow-hidden rounded-3xl border-2 border-white/10 shadow-2xl shadow-primary/10">
          <div className="aspect-[3/4] w-full overflow-hidden bg-muted">
            {avatarUrl ? (
              <img
                src={avatarUrl}
                alt={girlfriendName}
                className="h-full w-full object-cover blur-xl scale-110"
              />
            ) : (
              <div className="h-full w-full bg-gradient-to-br from-primary/30 via-primary/10 to-background blur-xl scale-110" />
            )}
          </div>
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-7xl font-bold text-white/20">{(girlfriendName ?? "?")[0]}</span>
          </div>
          <div className="absolute bottom-0 left-0 right-0 p-6 text-center">
            <p className="text-lg font-semibold text-white">{girlfriendName}</p>
            <p className="mt-1 text-sm text-white/60">Create an account to continue</p>
          </div>
        </div>

        {/* CTA or Signup form */}
        {!showSignup ? (
          <div className="flex flex-col items-center gap-3">
            <Button
              size="lg"
              className="w-full max-w-xs rounded-xl gap-2 text-base"
              onClick={() => setShowSignup(true)}
            >
              <Eye className="h-5 w-5" />
              View your girlfriend
            </Button>
            <p className="text-xs text-muted-foreground text-center">
              Create a free account to see her and start chatting
            </p>
          </div>
        ) : (
          <div className="rounded-2xl border border-white/10 bg-card/80 p-6 space-y-5 animate-in fade-in slide-in-from-bottom-4 duration-300">
            <div className="text-center space-y-1">
              <h2 className="text-xl font-semibold">Create your account</h2>
              <p className="text-sm text-muted-foreground">
                Sign up to meet {girlfriendName} and start your conversation
              </p>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {error && (
                <p className="text-sm text-destructive text-center">{error}</p>
              )}
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  {...register("email")}
                />
                {errors.email && (
                  <p className="text-xs text-destructive">
                    {errors.email.message}
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="At least 6 characters"
                  {...register("password")}
                />
                {errors.password && (
                  <p className="text-xs text-destructive">
                    {errors.password.message}
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="display_name">
                  Your name{" "}
                  <span className="text-muted-foreground font-normal">
                    (optional)
                  </span>
                </Label>
                <Input
                  id="display_name"
                  placeholder="How should she call you?"
                  {...register("display_name")}
                />
              </div>
              <Button
                type="submit"
                className="w-full rounded-xl"
                size="lg"
                disabled={isSubmitting}
              >
                {isSubmitting ? "Creating account…" : "Create account"}
              </Button>
            </form>

            <button
              type="button"
              className="w-full text-center text-sm text-muted-foreground hover:text-foreground transition-colors"
              onClick={handleSkipToSubscribe}
            >
              Skip for now
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
