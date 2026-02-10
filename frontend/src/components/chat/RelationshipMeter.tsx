import type { RelationshipState } from "@/lib/api/types"
import { cn } from "@/lib/utils"
import { Heart, Sparkles, Lock } from "lucide-react"

interface RelationshipMeterProps {
  state: RelationshipState
  className?: string
}

export default function RelationshipMeter({ state, className }: RelationshipMeterProps) {
  // Progress within the current region
  const regionSpan = Math.max(1, state.region_max_level - state.region_min_level)
  const regionProgress = Math.min(
    100,
    Math.round(((state.level - state.region_min_level) / regionSpan) * 100)
  )
  // Ensure at least a sliver is visible when level > 0
  const barPct = state.level === 0 ? 0 : Math.max(5, regionProgress)

  // Bank/cap values (fallback to legacy trust/intimacy if not provided)
  const trustVisible = state.trust_visible ?? state.trust
  const trustCap = state.trust_cap ?? 100
  const trustBank = state.trust_bank ?? 0
  const intimacyVisible = state.intimacy_visible ?? state.intimacy
  const intimacyCap = state.intimacy_cap ?? 100
  const intimacyBank = state.intimacy_bank ?? 0

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {/* Level / Region row */}
      <div className="flex items-center gap-2">
        <Heart className="h-5 w-5 text-primary" />
        <div className="flex flex-col items-end">
          <span className="text-xs font-medium">
            Level {state.level} — {state.region_title}
          </span>
          <div className="h-1.5 w-24 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${barPct}%` }}
            />
          </div>
        </div>
      </div>

      {/* Trust meter */}
      <div className="flex items-center gap-1.5">
        <Heart className="h-3.5 w-3.5 text-blue-400 fill-blue-400/50" />
        <div className="flex flex-col">
          <div className="flex items-baseline gap-1">
            <span className="text-[11px] font-semibold text-blue-300">
              Trust {trustVisible}/{trustCap}
            </span>
            {trustBank > 0 && (
              <span className="text-[9px] text-blue-400/50 flex items-center gap-0.5">
                <Lock className="h-2.5 w-2.5" />
                +{trustBank} pending
              </span>
            )}
          </div>
          <div className="h-1 w-20 overflow-hidden rounded-full bg-blue-500/10">
            <div
              className="h-full rounded-full bg-blue-400 transition-all"
              style={{ width: `${Math.round((trustVisible / trustCap) * 100)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Intimacy meter */}
      <div className="flex items-center gap-1.5">
        <Sparkles className="h-3.5 w-3.5 text-pink-400" />
        <div className="flex flex-col">
          <div className="flex items-baseline gap-1">
            <span className="text-[11px] font-semibold text-pink-300">
              Intimacy {intimacyVisible}/{intimacyCap}
            </span>
            {intimacyBank > 0 && (
              <span className="text-[9px] text-pink-400/50 flex items-center gap-0.5">
                <Lock className="h-2.5 w-2.5" />
                +{intimacyBank} pending
              </span>
            )}
          </div>
          <div className="h-1 w-20 overflow-hidden rounded-full bg-pink-500/10">
            <div
              className="h-full rounded-full bg-pink-400 transition-all"
              style={{ width: `${Math.round((intimacyVisible / intimacyCap) * 100)}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
