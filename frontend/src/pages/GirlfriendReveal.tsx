import { useNavigate } from "react-router-dom"
import { useAppStore } from "@/lib/store/useAppStore"
import { Button } from "@/components/ui/button"
import { Eye, Sparkles } from "lucide-react"

export default function GirlfriendReveal() {
  const navigate = useNavigate()
  const girlfriend = useAppStore((s) => s.girlfriend)
  const identityPackage = useAppStore((s) => s.onboardingIdentityPackage)

  const girlfriendName =
    girlfriend?.display_name || girlfriend?.name || "Your Girl"
  const avatarUrl =
    identityPackage?.main_avatar_url ||
    (girlfriend?.identity_images?.main_avatar_url as string | undefined) ||
    girlfriend?.avatar_url ||
    null

  const handleContinue = () => {
    navigate("/onboarding/subscribe", { replace: true })
  }

  const handleStartChatting = () => {
    navigate("/app/girl", { replace: true })
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-background to-background/95 px-4 py-12 animate-in fade-in duration-500">
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
            <p className="mt-1 text-sm text-white/60">Your companion is waiting</p>
          </div>
        </div>

        {/* CTAs */}
        <div className="flex flex-col items-center gap-3">
          <Button
            size="lg"
            className="w-full max-w-xs rounded-xl gap-2 text-base"
            onClick={handleContinue}
          >
            <Eye className="h-5 w-5" />
            Choose your plan
          </Button>
          <button
            type="button"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            onClick={handleStartChatting}
          >
            Start chatting now (free)
          </button>
        </div>
      </div>
    </div>
  )
}
