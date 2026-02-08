import { useQuery } from "@tanstack/react-query"
import { getCurrentGirlfriend } from "@/lib/api/endpoints"
import { getChatState } from "@/lib/api/endpoints"
import RelationshipMeter from "./RelationshipMeter"
import { Skeleton } from "@/components/ui/skeleton"

export default function ChatHeader() {
  const { data: gf, isLoading: gfLoading } = useQuery({ queryKey: ["girlfriend"], queryFn: getCurrentGirlfriend })
  const { data: state, isLoading: stateLoading } = useQuery({ queryKey: ["chatState"], queryFn: getChatState })

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
          <p className="text-xs text-muted-foreground">Your companion</p>
        </div>
      </div>
      {!stateLoading && state && <RelationshipMeter state={state} />}
    </header>
  )
}
