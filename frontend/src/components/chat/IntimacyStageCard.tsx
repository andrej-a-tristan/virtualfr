import { Card, CardContent } from "@/components/ui/card"
import { Sparkles, Flame } from "lucide-react"
import { cn } from "@/lib/utils"

interface IntimacyAchievementData {
  id: string
  title: string
  subtitle?: string
  tier?: number
  rarity?: string
  icon?: string
}

interface IntimacyStageCardProps {
  achievement: IntimacyAchievementData
  className?: string
}

const TIER_LABELS: Record<number, string> = {
  0: "Flirting & Tension",
  1: "First Touch",
  2: "Heating Up",
  3: "Undressed",
  4: "Full Intimacy",
  5: "Deep Exploration",
  6: "Ultimate Connection",
}

export default function IntimacyStageCard({ achievement, className }: IntimacyStageCardProps) {
  const icon = achievement.icon || "🔥"
  const tierLabel = achievement.tier != null ? TIER_LABELS[achievement.tier] ?? `Tier ${achievement.tier + 1}` : null

  return (
    <div className={cn("flex w-full justify-center py-1.5", className)}>
      <Card className="w-full max-w-xs rounded-2xl border-pink-500/25 bg-gradient-to-b from-pink-500/10 via-pink-500/5 to-slate-900/40 shadow-sm">
        <CardContent className="px-4 py-3 space-y-1.5">
          {/* Header */}
          <div className="flex items-center justify-center gap-1.5">
            <Flame className="h-4 w-4 text-pink-300" />
            <span className="text-[11px] font-semibold uppercase tracking-wider text-pink-200/80">
              Intimacy Stage Unlocked
            </span>
          </div>

          {/* Title + emoji */}
          <div className="flex flex-col items-center gap-1">
            <span className="text-2xl leading-none">{icon}</span>
            <p className="text-center text-sm font-bold text-pink-50">
              {achievement.title}
            </p>
          </div>

          {/* Tier label */}
          {tierLabel && (
            <div className="flex justify-center">
              <span className="text-[10px] uppercase tracking-widest font-semibold px-2 py-0.5 rounded-full bg-pink-500/15 text-pink-200">
                {tierLabel}
              </span>
            </div>
          )}

          {/* Subtitle */}
          {achievement.subtitle && (
            <p className="text-center text-[11px] italic text-pink-100/60 leading-relaxed">
              {achievement.subtitle}
            </p>
          )}

          {/* Flavor line */}
          <div className="flex items-center justify-center gap-1 pt-0.5">
            <Sparkles className="h-3 w-3 text-pink-200/80" />
            <span className="text-[10px] text-pink-100/70">
              Your connection just became more intimate.
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

