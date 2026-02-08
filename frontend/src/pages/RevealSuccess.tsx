import { useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { useAppStore } from "@/lib/store/useAppStore"
import { getBillingStatus } from "@/lib/api/endpoints"
import { Button } from "@/components/ui/button"
import { MessageCircle, Sparkles, Crown, Heart } from "lucide-react"

const PLAN_LABELS: Record<string, { label: string; icon: typeof Heart; color: string }> = {
  free: { label: "Free", icon: Heart, color: "text-muted-foreground" },
  plus: { label: "Plus", icon: Sparkles, color: "text-primary" },
  premium: { label: "Premium", icon: Crown, color: "text-amber-400" },
}

export default function RevealSuccess() {
  const navigate = useNavigate()
  const girlfriend = useAppStore((s) => s.girlfriend)

  const { data: billing } = useQuery({
    queryKey: ["billingStatus"],
    queryFn: getBillingStatus,
    retry: false,
  })

  const girlfriendName =
    girlfriend?.display_name || girlfriend?.name || "Your Girl"
  const avatarUrl = girlfriend?.avatar_url || "/assets/companion-avatar.png"
  const plan = billing?.plan ?? "free"
  const planInfo = PLAN_LABELS[plan] ?? PLAN_LABELS.free
  const PlanIcon = planInfo.icon

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-background to-background/95 px-4 py-12">
      <div className="w-full max-w-md space-y-8">
        {/* Sparkle header */}
        <div className="text-center space-y-2">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 animate-in zoom-in duration-500">
            <Sparkles className="h-7 w-7 text-primary" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight md:text-4xl animate-in fade-in slide-in-from-bottom-4 duration-500">
            Meet {girlfriendName}
          </h1>
          <p className="text-muted-foreground animate-in fade-in slide-in-from-bottom-4 duration-700">
            She&apos;s all yours
          </p>
        </div>

        {/* Unblurred photo */}
        <div className="relative mx-auto w-72 overflow-hidden rounded-3xl border-2 border-white/10 shadow-2xl shadow-primary/20 animate-in fade-in zoom-in-95 duration-700">
          <div className="aspect-[3/4] w-full overflow-hidden bg-muted">
            <img
              src={avatarUrl}
              alt={girlfriendName}
              className="h-full w-full object-cover"
            />
          </div>
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
          <div className="absolute bottom-0 left-0 right-0 p-5">
            <p className="text-xl font-bold text-white">{girlfriendName}</p>
            <div className="mt-1 flex items-center gap-1.5">
              <PlanIcon className={`h-3.5 w-3.5 ${planInfo.color}`} />
              <span className={`text-xs font-medium ${planInfo.color}`}>
                {planInfo.label} plan
              </span>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="flex flex-col items-center gap-3 animate-in fade-in slide-in-from-bottom-4 duration-700 delay-300">
          <Button
            size="lg"
            className="w-full max-w-xs rounded-xl gap-2 text-base"
            onClick={() => navigate("/app/chat", { replace: true })}
          >
            <MessageCircle className="h-5 w-5" />
            Let&apos;s chat
          </Button>
          <p className="text-xs text-muted-foreground text-center">
            Start your conversation with {girlfriendName}
          </p>
        </div>
      </div>
    </div>
  )
}
