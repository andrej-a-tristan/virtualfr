import type { RelationshipState } from "@/lib/api/types"
import { cn } from "@/lib/utils"
import { Heart } from "lucide-react"

interface RelationshipMeterProps {
  state: RelationshipState
  className?: string
}

export default function RelationshipMeter({ state, className }: RelationshipMeterProps) {
  const pct = Math.min(100, Math.round((state.trust + state.intimacy) / 2))
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <Heart className="h-5 w-5 text-primary" />
      <div className="flex flex-col items-end">
        <span className="text-xs font-medium">Level {state.level}</span>
        <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  )
}
