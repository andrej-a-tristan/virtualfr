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
        <div className="h-10 w-10 overflow-hidden rounded-full bg-muted">
          {gf.avatar_url ? (
            <img src={gf.avatar_url} alt={gf.name} className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-lg font-semibold text-muted-foreground">
              {gf.name[0]}
            </div>
          )}
        </div>
        <div>
          <h1 className="font-semibold">{gf.name}</h1>
          <p className="text-xs text-muted-foreground">Your companion</p>
        </div>
      </div>
      {!stateLoading && state && <RelationshipMeter state={state} />}
    </header>
  )
}
