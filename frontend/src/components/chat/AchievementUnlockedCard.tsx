import { Card, CardContent } from "@/components/ui/card"
import { Trophy, Sparkles, Star } from "lucide-react"
import { cn } from "@/lib/utils"
import type { AchievementRarity } from "@/lib/api/types"

interface AchievementData {
  id: string
  title: string
  subtitle?: string
  rarity?: AchievementRarity
  region_index?: number
}

interface AchievementUnlockedCardProps {
  achievement: AchievementData
  className?: string
}

const REGION_NAMES = [
  "Early Connection",
  "Comfort & Familiarity",
  "Growing Closeness",
  "Emotional Trust",
  "Deep Bond",
  "Mutual Devotion",
  "Intimate Partnership",
  "Shared Life",
  "Enduring Companionship",
]

const RARITY_STYLES: Record<string, { border: string; bg: string; text: string; label: string }> = {
  COMMON:    { border: "border-zinc-400/20",   bg: "from-zinc-400/8 to-zinc-400/3",      text: "text-zinc-300",    label: "Common" },
  UNCOMMON:  { border: "border-emerald-400/20", bg: "from-emerald-400/8 to-emerald-400/3", text: "text-emerald-300", label: "Uncommon" },
  RARE:      { border: "border-blue-400/25",   bg: "from-blue-400/10 to-blue-400/3",     text: "text-blue-300",    label: "Rare" },
  EPIC:      { border: "border-purple-400/30", bg: "from-purple-400/12 to-purple-400/4",  text: "text-purple-300",  label: "Epic" },
  LEGENDARY: { border: "border-amber-400/35",  bg: "from-amber-400/15 to-amber-400/5",   text: "text-amber-300",   label: "Legendary" },
}

export default function AchievementUnlockedCard({ achievement, className }: AchievementUnlockedCardProps) {
  const rarity = achievement.rarity ?? "COMMON"
  const style = RARITY_STYLES[rarity] ?? RARITY_STYLES.COMMON
  const regionName = achievement.region_index != null ? REGION_NAMES[achievement.region_index] : null
  const isLegendary = rarity === "LEGENDARY"
  const isEpic = rarity === "EPIC"

  return (
    <div className={cn("flex w-full justify-center py-1.5", className)}>
      <Card className={cn(
        "w-full max-w-xs rounded-2xl shadow-sm",
        style.border,
        `bg-gradient-to-b ${style.bg}`,
      )}>
        <CardContent className="px-4 py-3 space-y-1.5">
          {/* Header */}
          <div className="flex items-center justify-center gap-1.5">
            {isLegendary ? (
              <Sparkles className="h-4 w-4 text-amber-400" />
            ) : isEpic ? (
              <Star className="h-4 w-4 text-purple-400" />
            ) : (
              <Trophy className={cn("h-4 w-4", style.text)} />
            )}
            <span className={cn("text-[11px] font-semibold uppercase tracking-wider", style.text, "opacity-80")}>
              Achievement Unlocked
            </span>
          </div>

          {/* Title */}
          <p className={cn("text-center text-sm font-bold", style.text)}>
            {achievement.title}
          </p>

          {/* Rarity badge */}
          <div className="flex justify-center">
            <span className={cn(
              "text-[9px] uppercase tracking-widest font-semibold px-2 py-0.5 rounded-full",
              rarity === "LEGENDARY" && "bg-amber-400/15 text-amber-400",
              rarity === "EPIC" && "bg-purple-400/15 text-purple-400",
              rarity === "RARE" && "bg-blue-400/15 text-blue-400",
              rarity === "UNCOMMON" && "bg-emerald-400/15 text-emerald-300",
              rarity === "COMMON" && "bg-zinc-400/15 text-zinc-400",
            )}>
              {style.label}
            </span>
          </div>

          {/* Subtitle */}
          {achievement.subtitle && (
            <p className="text-center text-[11px] italic text-muted-foreground/50 leading-relaxed">
              {achievement.subtitle}
            </p>
          )}

          {/* Region name */}
          {regionName && (
            <p className="text-center text-[10px] text-muted-foreground/30">
              Unlocked in {regionName}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
