import { Card, CardContent } from "@/components/ui/card"
import { Heart, Sparkles, Gift, MessageCircle, MapPin, Lock } from "lucide-react"
import { cn } from "@/lib/utils"

interface GainData {
  trust_delta?: number
  trust_new?: number
  intimacy_delta?: number
  intimacy_new?: number
  reason?: string
  trust_micro_line?: string
  trust_label?: string
  intimacy_micro_line?: string
  intimacy_label?: string
  // Bank/release breakdown
  trust_banked_delta?: number
  trust_released_delta?: number
  trust_visible_new?: number
  trust_bank_new?: number
  trust_cap?: number
  intimacy_banked_delta?: number
  intimacy_released_delta?: number
  intimacy_visible_new?: number
  intimacy_bank_new?: number
  intimacy_cap?: number
  tease_line?: string
}

interface RelationshipGainCardProps {
  gainData: GainData
  className?: string
}

const REASON_ICONS: Record<string, typeof Heart> = {
  conversation: MessageCircle,
  gift: Gift,
  region: MapPin,
}

const REASON_LABELS: Record<string, string> = {
  conversation: "From Conversation",
  gift: "Gift Appreciated",
  region: "New Milestone",
}

export default function RelationshipGainCard({ gainData, className }: RelationshipGainCardProps) {
  const {
    trust_delta = 0,
    trust_new = 0,
    intimacy_delta = 0,
    intimacy_new = 0,
    reason = "conversation",
    trust_micro_line,
    trust_label,
    intimacy_micro_line,
    intimacy_label,
    trust_banked_delta = 0,
    trust_released_delta = 0,
    trust_visible_new,
    trust_bank_new = 0,
    trust_cap,
    intimacy_banked_delta = 0,
    intimacy_released_delta = 0,
    intimacy_visible_new,
    intimacy_bank_new = 0,
    intimacy_cap,
    tease_line,
  } = gainData

  if (trust_delta === 0 && intimacy_delta === 0) return null

  const ReasonIcon = REASON_ICONS[reason] || Heart
  const reasonLabel = REASON_LABELS[reason] || "Connection"

  // Determine if anything was released vs only banked
  const hasTrustRelease = trust_released_delta > 0
  const hasTrustBanked = trust_banked_delta > 0 && trust_released_delta === 0
  const hasIntimacyRelease = intimacy_released_delta > 0
  const hasIntimacyBanked = intimacy_banked_delta > 0 && intimacy_released_delta === 0

  return (
    <div className={cn("flex w-full justify-center py-1.5", className)}>
      <Card className="w-full max-w-xs rounded-2xl border-emerald-500/20 bg-gradient-to-b from-emerald-500/8 to-emerald-500/3 shadow-sm">
        <CardContent className="px-4 py-3 space-y-2">
          {/* Header */}
          <div className="flex items-center justify-center gap-1.5">
            <ReasonIcon className="h-3.5 w-3.5 text-emerald-400" />
            <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-400/80">
              {reasonLabel}
            </span>
          </div>

          {/* Gain badges */}
          <div className="flex items-center justify-center gap-3">
            {trust_delta > 0 && (
              <div className="flex items-center gap-1.5 rounded-full bg-blue-500/10 px-3 py-1 ring-1 ring-blue-500/20">
                <Heart className="h-3 w-3 text-blue-400 fill-blue-400/50" />
                <span className="text-xs font-bold text-blue-300">+{trust_delta}</span>
                <span className="text-[10px] text-blue-400/60">Trust</span>
              </div>
            )}
            {intimacy_delta > 0 && (
              <div className="flex items-center gap-1.5 rounded-full bg-pink-500/10 px-3 py-1 ring-1 ring-pink-500/20">
                <Sparkles className="h-3 w-3 text-pink-400" />
                <span className="text-xs font-bold text-pink-300">+{intimacy_delta}</span>
                <span className="text-[10px] text-pink-400/60">Intimacy</span>
              </div>
            )}
          </div>

          {/* Released / banked breakdown */}
          <div className="space-y-0.5">
            {/* Trust breakdown */}
            {hasTrustRelease && (
              <p className="text-center text-[10px] text-blue-300/70">
                +{trust_released_delta} Trust unlocked
              </p>
            )}
            {hasTrustBanked && (
              <p className="text-center text-[10px] text-blue-400/50 flex items-center justify-center gap-0.5">
                <Lock className="h-2.5 w-2.5" />
                +{trust_banked_delta} Trust banked (unlocks as you progress)
              </p>
            )}
            {trust_released_delta > 0 && trust_banked_delta > trust_released_delta && (
              <p className="text-center text-[10px] text-blue-400/50 flex items-center justify-center gap-0.5">
                <Lock className="h-2.5 w-2.5" />
                +{trust_banked_delta - trust_released_delta} Trust banked
              </p>
            )}

            {/* Intimacy breakdown */}
            {hasIntimacyRelease && (
              <p className="text-center text-[10px] text-pink-300/70">
                +{intimacy_released_delta} Intimacy unlocked
              </p>
            )}
            {hasIntimacyBanked && (
              <p className="text-center text-[10px] text-pink-400/50 flex items-center justify-center gap-0.5">
                <Lock className="h-2.5 w-2.5" />
                +{intimacy_banked_delta} Intimacy banked (unlocks as you progress)
              </p>
            )}
            {intimacy_released_delta > 0 && intimacy_banked_delta > intimacy_released_delta && (
              <p className="text-center text-[10px] text-pink-400/50 flex items-center justify-center gap-0.5">
                <Lock className="h-2.5 w-2.5" />
                +{intimacy_banked_delta - intimacy_released_delta} Intimacy banked
              </p>
            )}
          </div>

          {/* Current values with cap */}
          <div className="flex items-center justify-center gap-4 text-[10px] text-muted-foreground/60">
            {trust_delta > 0 && (
              <span>
                Trust {trust_visible_new ?? trust_new}/{trust_cap ?? 100}
                {trust_bank_new > 0 && (
                  <span className="ml-1 text-blue-400/40">(+{trust_bank_new} pending)</span>
                )}
                {trust_label && <span className="ml-1 text-blue-400/50">({trust_label})</span>}
              </span>
            )}
            {intimacy_delta > 0 && (
              <span>
                Intimacy {intimacy_visible_new ?? intimacy_new}/{intimacy_cap ?? 100}
                {intimacy_bank_new > 0 && (
                  <span className="ml-1 text-pink-400/40">(+{intimacy_bank_new} pending)</span>
                )}
                {intimacy_label && <span className="ml-1 text-pink-400/50">({intimacy_label})</span>}
              </span>
            )}
          </div>

          {/* Micro-reward line */}
          {(trust_micro_line || intimacy_micro_line) && (
            <p className="text-center text-[11px] italic text-muted-foreground/50 leading-relaxed">
              {trust_micro_line || intimacy_micro_line}
            </p>
          )}

          {/* Tease line when capped */}
          {tease_line && (
            <p className="text-center text-[10px] italic text-emerald-400/60 leading-relaxed">
              {tease_line}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
