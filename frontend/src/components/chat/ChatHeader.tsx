import { useQuery } from "@tanstack/react-query"
import { getCurrentGirlfriend, getBillingStatus } from "@/lib/api/endpoints"
import { getChatState } from "@/lib/api/endpoints"
import RelationshipMeter from "./RelationshipMeter"
import { Skeleton } from "@/components/ui/skeleton"
import { Sparkles, Crown, Heart } from "lucide-react"

export default function ChatHeader() {
  const { data: gf, isLoading: gfLoading } = useQuery({ queryKey: ["girlfriend"], queryFn: getCurrentGirlfriend })
  const { data: state, isLoading: stateLoading } = useQuery({ queryKey: ["chatState"], queryFn: getChatState })
  const { data: billing } = useQuery({ queryKey: ["billingStatus"], queryFn: getBillingStatus, retry: false })

  const plan = billing?.plan ?? "free"
  const planMeta: Record<string, { icon: typeof Heart; label: string; color: string }> = {
    free: { icon: Heart, label: "Free", color: "text-muted-foreground" },
    plus: { icon: Sparkles, label: "Plus", color: "text-primary" },
    premium: { icon: Crown, label: "Premium", color: "text-amber-400" },
  }
  const pm = planMeta[plan] ?? planMeta.free
  const PlanIcon = pm.icon

  if (gfLoading || !gf) {
    return (
      <header className="flex h-16 items-center gap-4 border-b border-white/10 px-4">
        <Skeleton className="h-10 w-10 rounded-full" />
        <Skeleton className="h-6 w-32" />
      </header>
    )
  }

  return (
    <header className="flex h-16 items-center justify-between gap-4 border-b border-white/10 px-4">
      <div className="flex items-center gap-3">
        <img
          src="/assets/companion-avatar.png"
          alt={gf.display_name ?? "Companion"}
          className="h-10 w-10 shrink-0 rounded-full object-cover"
        />
        <div>
          <h1 className="font-semibold">{gf.display_name}</h1>
          <div className="flex items-center gap-1.5">
            <PlanIcon className={`h-3 w-3 ${pm.color}`} />
            <p className={`text-xs font-medium ${pm.color}`}>{pm.label}</p>
          </div>
        </div>
      </div>
      {!stateLoading && state && <RelationshipMeter state={state} />}
    </header>
  )
}
