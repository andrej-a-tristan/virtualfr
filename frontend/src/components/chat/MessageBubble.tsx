import type { ChatMessage } from "@/lib/api/types"
import { cn } from "@/lib/utils"
import { Gift, Heart, Sparkles, Zap, ImageIcon, Flame } from "lucide-react"
import AvatarCircle from "@/components/ui/AvatarCircle"
import ImageTeaseCard from "./ImageTeaseCard"
import BlurredImageCard from "./BlurredImageCard"
import RelationshipGainCard from "./RelationshipGainCard"
import AchievementUnlockedCard from "./AchievementUnlockedCard"
import IntimacyStageCard from "./IntimacyStageCard"

interface MessageBubbleProps {
  message: ChatMessage
  className?: string
}

export default function MessageBubble({ message, className }: MessageBubbleProps) {
  const isUser = message.role === "user"
  const isMilestone = message.event_type === "milestone"
  const isGift = message.event_type === "gift_received"
  const isImageDecision = message.event_type === "image_decision"
  const isBlurredPreview = message.event_type === "blurred_preview"
  const isRelationshipGain = message.event_type === "relationship_gain"
  const isAchievement = message.event_type === "relationship_achievement"
  const isIntimacyStage =
    message.event_type === "intimacy_achievement" || message.event_type === "intimacy_stage_unlocked"

  // Don't render system/memory messages
  if (message.role === "system") return null

  if (isGift) {
    return <GiftBubble message={message} className={className} />
  }

  // Achievement unlocked card
  if (isAchievement) {
    const achData = (message as unknown as Record<string, unknown>).achievement as
      | { id: string; title: string; subtitle?: string; region_index?: number }
      | undefined
    if (achData) {
      return <AchievementUnlockedCard achievement={achData} className={className} />
    }
    return null
  }

  // Intimacy stage / intimacy achievement card
  if (isIntimacyStage) {
    const achData = (message as unknown as Record<string, unknown>).achievement as
      | { id: string; title: string; subtitle?: string; tier?: number; rarity?: string; icon?: string }
      | undefined
    if (achData) {
      return <IntimacyStageCard achievement={achData} className={className} />
    }
    return null
  }

  // Relationship gain card (trust/intimacy change)
  if (isRelationshipGain) {
    const gainData = (message as unknown as Record<string, unknown>).gain_data as
      | Record<string, unknown>
      | undefined
    if (gainData) {
      return <RelationshipGainCard gainData={gainData as Parameters<typeof RelationshipGainCard>[0]["gainData"]} className={className} />
    }
    return null
  }

  // Blurred paywall — proactive surprise or explicit request gated by free plan
  if (isBlurredPreview) {
    const msgAny = message as unknown as Record<string, unknown>
    return (
      <BlurredImageCard
        uiCopy={message.content || "She sent you something special... Upgrade to see it."}
        blurredImageUrl={(msgAny.blurred_image_url as string) || undefined}
        reason={(message.event_key as string) || "free_plan_upgrade"}
      />
    )
  }

  if (isImageDecision) {
    const decisionData = (message as unknown as Record<string, unknown>).decision as
      | { ui_copy?: string; suggested_prompts?: string[]; reason?: string; blurred_image_url?: string; action?: string }
      | undefined

    // If the decision is blurred_paywall, show the blurred card instead
    if (decisionData?.action === "blurred_paywall") {
      return (
        <BlurredImageCard
          uiCopy={decisionData?.ui_copy || message.content || "She sent you something special... Upgrade to see it."}
          blurredImageUrl={decisionData?.blurred_image_url}
          reason={decisionData?.reason || "free_plan_upgrade"}
        />
      )
    }

    return (
      <ImageTeaseCard
        uiCopy={decisionData?.ui_copy || message.content || "This content requires a deeper connection."}
        suggestedPrompts={decisionData?.suggested_prompts}
        reason={decisionData?.reason || message.event_key || undefined}
      />
    )
  }

  return (
    <div
      className={cn(
        "flex w-full",
        isUser ? "justify-end" : "justify-start",
        className
      )}
    >
      <div className={cn("flex items-end gap-2", isUser ? "flex-row-reverse" : "flex-row")}>
        {!isUser && (
          <AvatarCircle name={null} size="sm" />
        )}
        <div
          className={cn(
            "max-w-[85%] rounded-2xl px-4 py-2.5 text-sm",
            isUser
              ? "bg-primary text-primary-foreground"
              : isMilestone
                ? "bg-primary/20 text-primary border border-primary/30"
                : "bg-muted/80 text-foreground"
          )}
        >
          {message.content && <p className="whitespace-pre-wrap">{message.content}</p>}
        </div>
      </div>
    </div>
  )
}

function GiftBubble({ message, className }: MessageBubbleProps) {
  // Try to extract gift_data from the message
  const giftData = (message as unknown as Record<string, unknown>).gift_data as
    | {
        gift_name?: string
        emoji?: string
        tier?: string
        trust_gained?: number
        intimacy_gained?: number
        unique_effect_name?: string
        unique_effect_description?: string
        normal_photos?: number
        spicy_photos?: number
      }
    | undefined

  const emoji = giftData?.emoji || "🎁"
  const giftName = giftData?.gift_name || "a gift"
  const tier = giftData?.tier || "everyday"
  const trustGained = giftData?.trust_gained ?? 0
  const intimacyGained = giftData?.intimacy_gained ?? 0
  const effectName = giftData?.unique_effect_name || ""
  const normalPhotos = giftData?.normal_photos ?? 0
  const spicyPhotos = giftData?.spicy_photos ?? 0

  const tierColors: Record<string, string> = {
    everyday: "from-primary/20 to-primary/5 border-primary/30",
    dates: "from-primary/25 to-primary/10 border-primary/40",
    luxury: "from-amber-500/20 to-amber-500/5 border-amber-500/30",
    legendary: "from-amber-500/30 to-amber-400/10 border-amber-400/40",
  }

  const effectAccent: Record<string, string> = {
    everyday: "text-primary",
    dates: "text-primary",
    luxury: "text-amber-400",
    legendary: "text-amber-300",
  }

  return (
    <div className={cn("flex w-full justify-center py-2", className)}>
      <div
        className={cn(
          "w-full max-w-sm rounded-2xl border bg-gradient-to-b p-4 space-y-3",
          tierColors[tier] || tierColors.everyday,
        )}
      >
        {/* Gift header */}
        <div className="flex items-center justify-center gap-2">
          <Gift className="h-4 w-4 text-primary" />
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            Gift Received
          </span>
        </div>

        {/* Gift icon + name */}
        <div className="text-center">
          <span className="text-4xl block mb-1">{emoji}</span>
          <p className="font-bold text-sm">{giftName}</p>
        </div>

        {/* Reaction text */}
        {message.content && (
          <div className="flex gap-2">
            <AvatarCircle name={null} size="xs" className="mt-0.5" />
            <p className="text-sm italic text-muted-foreground">{message.content}</p>
          </div>
        )}

        {/* Unique effect badge */}
        {effectName && (
          <div className="flex items-center justify-center gap-1.5">
            <Zap className={cn("h-3 w-3", effectAccent[tier] || effectAccent.everyday)} />
            <span className={cn("text-xs font-medium", effectAccent[tier] || effectAccent.everyday)}>
              {effectName}
            </span>
          </div>
        )}

        {/* Photo reward indicator */}
        {(normalPhotos > 0 || spicyPhotos > 0) && (
          <div className="flex items-center justify-center gap-3 pt-1">
            {normalPhotos > 0 && (
              <span className="flex items-center gap-1 text-xs font-medium text-blue-400">
                <ImageIcon className="h-3 w-3" />
                {normalPhotos} photo{normalPhotos > 1 ? "s" : ""}
              </span>
            )}
            {spicyPhotos > 0 && (
              <span className="flex items-center gap-1 text-xs font-medium text-rose-400">
                <Flame className="h-3 w-3" />
                {spicyPhotos} spicy
              </span>
            )}
          </div>
        )}

        {/* Boost indicator */}
        {(trustGained > 0 || intimacyGained > 0) && (
          <div className="flex items-center justify-center gap-3 pt-1">
            {trustGained > 0 && (
              <span className="flex items-center gap-1 text-xs text-primary font-medium">
                <Heart className="h-3 w-3" />
                +{trustGained} trust
              </span>
            )}
            {intimacyGained > 0 && (
              <span className="flex items-center gap-1 text-xs text-primary font-medium">
                <Sparkles className="h-3 w-3" />
                +{intimacyGained} intimacy
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
