import { useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { getGiftsList } from "@/lib/api/endpoints"
import type { GiftDefinition } from "@/lib/api/types"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import {
  X,
  Heart,
  Sparkles,
  Crown,
  Gift,
  Zap,
  Clock,
  ImageIcon,
  Flame,
  Lock,
  BookHeart,
  Check,
} from "lucide-react"
import UnifiedPaymentPanel from "@/components/billing/UnifiedPaymentPanel"

/* ─── constants ───────────────────────────────────────────────────────────── */

const TABS = [
  { id: "everyday", label: "Everyday", icon: Heart },
  { id: "dates", label: "Dates", icon: Sparkles },
  { id: "luxury", label: "Luxury", icon: Crown },
  { id: "legendary", label: "Legendary", icon: Gift },
] as const

const TIER_COLORS: Record<string, string> = {
  everyday: "border-white/10 hover:border-primary/40",
  dates: "border-white/10 hover:border-primary/40",
  luxury: "border-amber-500/20 hover:border-amber-400/50",
  legendary: "border-amber-500/30 hover:border-amber-300/60 bg-amber-500/5",
}

const TIER_ACCENTS: Record<string, string> = {
  everyday: "text-primary",
  dates: "text-primary",
  luxury: "text-amber-400",
  legendary: "text-amber-300",
}

const RARITY_BADGE: Record<string, string> = {
  common: "",
  rare: "bg-primary/20 text-primary",
  legendary: "bg-amber-500/20 text-amber-300",
}

/* ─── main modal ──────────────────────────────────────────────────────────── */

interface GiftModalProps {
  open: boolean
  onClose: () => void
  girlfriendName?: string
}

export default function GiftModal({ open, onClose, girlfriendName }: GiftModalProps) {
  const [tab, setTab] = useState<string>("everyday")
  const [previewGift, setPreviewGift] = useState<GiftDefinition | null>(null)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ["giftCatalog"],
    queryFn: getGiftsList,
    enabled: open,
    staleTime: 60_000,
  })

  const gifts = data?.gifts ?? []
  const filtered = gifts.filter((g) => g.tier === tab)

  const handleGiftSuccess = () => {
    setPreviewGift(null)
    onClose()
    // Refetch chat + relationship state to show the gift bubble
    queryClient.invalidateQueries({ queryKey: ["chatHistory"] })
    queryClient.invalidateQueries({ queryKey: ["chatState"] })
    // Refetch gift catalog (to update already_purchased flags) and collection
    queryClient.invalidateQueries({ queryKey: ["giftCatalog"] })
    queryClient.invalidateQueries({ queryKey: ["giftCollection"] })
  }

  if (!open) return null

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm px-0 sm:px-4">
        <div className="w-full max-w-2xl max-h-[85vh] flex flex-col rounded-t-3xl sm:rounded-2xl border border-white/10 bg-card shadow-2xl animate-in fade-in slide-in-from-bottom-4 duration-300">
          {/* Header */}
          <div className="flex items-center justify-between p-5 pb-3 border-b border-white/10">
            <div>
              <h2 className="text-lg font-bold flex items-center gap-2">
                <span className="text-xl">🎁</span>
                Buy {girlfriendName || "Her"} Something
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Gifts boost your relationship and create lasting memories
              </p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="rounded-full shrink-0"
              onClick={onClose}
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 px-5 pt-3 pb-2 overflow-x-auto">
            {TABS.map((t) => {
              const Icon = t.icon
              const isActive = tab === t.id
              return (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={cn(
                    "flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-medium transition-all whitespace-nowrap",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "bg-white/5 text-muted-foreground hover:bg-white/10"
                  )}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {t.label}
                </button>
              )
            })}
          </div>

          {/* Gift grid */}
          <div className="flex-1 overflow-y-auto px-5 py-3 space-y-2">
            {isLoading ? (
              <div className="flex items-center justify-center py-12 text-muted-foreground text-sm">
                Loading gifts...
              </div>
            ) : filtered.length === 0 ? (
              <div className="flex items-center justify-center py-12 text-muted-foreground text-sm">
                No gifts in this category
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {filtered.map((gift) => (
                  <GiftCard
                    key={gift.id}
                    gift={gift}
                    onSelect={() => setPreviewGift(gift)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Preview dialog */}
      {previewGift && (
        <GiftPreviewDialog
          gift={previewGift}
          girlfriendName={girlfriendName}
          onClose={() => setPreviewGift(null)}
          onSuccess={handleGiftSuccess}
        />
      )}
    </>
  )
}

/* ─── gift card (grid item) ───────────────────────────────────────────────── */

function GiftCard({
  gift,
  onSelect,
}: {
  gift: GiftDefinition
  onSelect: () => void
}) {
  const normalPhotos = gift.image_reward.normal_photos ?? 0
  const spicyPhotos = gift.image_reward.spicy_photos ?? 0
  const hasPhotos = normalPhotos > 0 || spicyPhotos > 0
  const alreadyPurchased = gift.already_purchased ?? false

  return (
    <button
      onClick={alreadyPurchased ? undefined : onSelect}
      disabled={alreadyPurchased}
      className={cn(
        "flex flex-col rounded-xl border p-4 transition-all text-left group",
        alreadyPurchased
          ? "border-green-500/20 bg-green-500/[0.04] cursor-default opacity-70"
          : cn("cursor-pointer", TIER_COLORS[gift.tier] || TIER_COLORS.everyday),
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{gift.emoji}</span>
          <div>
            <h3 className="font-semibold text-sm leading-tight">{gift.name}</h3>
            <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{gift.description}</p>
          </div>
        </div>
        {gift.rarity !== "common" && (
          <span
            className={cn(
              "text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full shrink-0",
              RARITY_BADGE[gift.rarity],
            )}
          >
            {gift.rarity}
          </span>
        )}
      </div>

      {/* Unique effect teaser */}
      {gift.unique_effect_name && (
        <div className="flex items-center gap-1.5 mb-2">
          <Zap className={cn("h-3 w-3 shrink-0", TIER_ACCENTS[gift.tier])} />
          <span className={cn("text-[11px] font-medium", TIER_ACCENTS[gift.tier])}>
            {gift.unique_effect_name}
          </span>
        </div>
      )}

      <div className="flex items-center gap-2 mt-auto mb-2 text-xs text-muted-foreground">
        {(gift.relationship_boost.trust > 0 || gift.relationship_boost.intimacy > 0) && (
          <>
            <span className="flex items-center gap-0.5">
              <Heart className="h-3 w-3 text-primary" />
              +{gift.relationship_boost.trust}
            </span>
            <span className="flex items-center gap-0.5">
              <Sparkles className="h-3 w-3 text-primary" />
              +{gift.relationship_boost.intimacy}
            </span>
          </>
        )}
        {hasPhotos && (
          <div className="flex items-center gap-1.5">
            {normalPhotos > 0 && (
              <span className="flex items-center gap-0.5" title="Normal photos">
                <ImageIcon className="h-3 w-3 text-blue-400" />
                <span className="text-blue-400 font-medium">{normalPhotos}</span>
              </span>
            )}
            {spicyPhotos > 0 && (
              <span className="flex items-center gap-0.5" title={gift.spicy_unlocked ? "Spicy photos" : "Spicy photos (locked)"}>
                <Flame className="h-3 w-3 text-rose-400" />
                <span className={cn(
                  "font-medium",
                  gift.spicy_unlocked ? "text-rose-400" : "text-rose-400/40"
                )}>
                  {spicyPhotos}
                </span>
                {!gift.spicy_unlocked && (
                  <Lock className="h-2.5 w-2.5 text-rose-400/40" />
                )}
              </span>
            )}
          </div>
        )}
        {gift.cooldown_days && (
          <span className="flex items-center gap-0.5">
            <Clock className="h-3 w-3" />
            {gift.cooldown_days}d
          </span>
        )}
      </div>

      <div
        className={cn(
          "w-full rounded-lg py-1.5 text-center text-xs font-semibold transition-colors",
          alreadyPurchased
            ? "bg-green-500/15 text-green-400"
            : gift.tier === "legendary"
              ? "bg-amber-500/20 text-amber-300 group-hover:bg-amber-500/30"
              : "bg-primary/15 text-primary group-hover:bg-primary/25",
        )}
      >
        {alreadyPurchased ? (
          <span className="flex items-center justify-center gap-1.5">
            <Check className="h-3 w-3" />
            Already Gifted
          </span>
        ) : (
          <>€{gift.price_eur.toFixed(2)}</>
        )}
      </div>
    </button>
  )
}

/* ─── gift preview dialog (inline payment, no redirect) ───────────────────── */

function GiftPreviewDialog({
  gift,
  girlfriendName,
  onClose,
  onSuccess,
}: {
  gift: GiftDefinition
  girlfriendName?: string
  onClose: () => void
  onSuccess: () => void
}) {
  const [showPayment, setShowPayment] = useState(false)
  const name = girlfriendName || "her"

  const isLegendary = gift.tier === "legendary"
  const isLuxury = gift.tier === "luxury"
  const accent = isLegendary
    ? "text-amber-300"
    : isLuxury
      ? "text-amber-400"
      : "text-primary"

  const borderAccent = isLegendary
    ? "border-amber-500/40"
    : isLuxury
      ? "border-amber-500/20"
      : "border-primary/30"

  const handleBuy = () => {
    setShowPayment(true)
  }

  const handlePaymentSuccess = () => {
    setShowPayment(false)
    onSuccess()
  }

  return (
    <>
      <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-md px-4">
        <div
          className={cn(
            "w-full max-w-md rounded-2xl border bg-card shadow-2xl animate-in fade-in zoom-in-95 duration-200 overflow-hidden",
            borderAccent,
          )}
        >
          {/* Top visual */}
          <div
            className={cn(
              "relative flex flex-col items-center justify-center py-8 px-6",
              isLegendary
                ? "bg-gradient-to-b from-amber-500/15 to-transparent"
                : isLuxury
                  ? "bg-gradient-to-b from-amber-500/10 to-transparent"
                  : "bg-gradient-to-b from-primary/10 to-transparent",
            )}
          >
            <span className="text-6xl mb-3">{gift.emoji}</span>
            <h3 className="text-xl font-bold">{gift.name}</h3>
            <p className="text-sm text-muted-foreground text-center mt-1 max-w-xs">
              {gift.description}
            </p>
            {gift.rarity !== "common" && (
              <span
                className={cn(
                  "mt-2 text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full",
                  RARITY_BADGE[gift.rarity],
                )}
              >
                {gift.rarity}
              </span>
            )}
          </div>

          {/* Details */}
          <div className="px-6 pb-6 space-y-4">
            {gift.unique_effect_name && (
              <div className={cn("rounded-xl border p-3.5 space-y-1.5", borderAccent)}>
                <div className="flex items-center gap-2">
                  <Zap className={cn("h-4 w-4", accent)} />
                  <span className={cn("text-sm font-semibold", accent)}>
                    {gift.unique_effect_name}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {gift.unique_effect_description}
                </p>
              </div>
            )}

            <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
              {gift.relationship_boost.trust > 0 && (
                <span className="flex items-center gap-1">
                  <Heart className="h-3.5 w-3.5 text-primary" />
                  <span className="font-medium text-foreground">+{gift.relationship_boost.trust}</span> trust
                </span>
              )}
              {gift.relationship_boost.intimacy > 0 && (
                <span className="flex items-center gap-1">
                  <Sparkles className="h-3.5 w-3.5 text-primary" />
                  <span className="font-medium text-foreground">+{gift.relationship_boost.intimacy}</span> intimacy
                </span>
              )}
              {(gift.image_reward.normal_photos > 0 || gift.image_reward.spicy_photos > 0) && (
                <div className="flex items-center gap-2">
                  {gift.image_reward.normal_photos > 0 && (
                    <span className="flex items-center gap-1" title="Normal photos">
                      <ImageIcon className="h-3.5 w-3.5 text-blue-400" />
                      <span className="font-medium text-blue-400">{gift.image_reward.normal_photos}</span>
                      <span className="text-muted-foreground">photo{gift.image_reward.normal_photos > 1 ? "s" : ""}</span>
                    </span>
                  )}
                  {gift.image_reward.spicy_photos > 0 && (
                    <span className="flex items-center gap-1" title={gift.spicy_unlocked ? "Spicy photos" : "Spicy photos — pass age verification to unlock"}>
                      <Flame className="h-3.5 w-3.5 text-rose-400" />
                      <span className={cn(
                        "font-medium",
                        gift.spicy_unlocked ? "text-rose-400" : "text-rose-400/40"
                      )}>
                        {gift.image_reward.spicy_photos}
                      </span>
                      <span className={cn(
                        gift.spicy_unlocked ? "text-rose-400/70" : "text-rose-400/30"
                      )}>
                        spicy
                      </span>
                      {!gift.spicy_unlocked && (
                        <Lock className="h-3 w-3 text-rose-400/40" />
                      )}
                    </span>
                  )}
                </div>
              )}
              {gift.cooldown_days && (
                <span className="flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  {gift.cooldown_days} day cooldown
                </span>
              )}
            </div>

            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <BookHeart className="h-3.5 w-3.5" />
              Creates a permanent memory for {name}
            </div>

            <div className="flex gap-3 pt-1">
              <Button
                variant="ghost"
                className="flex-1 rounded-xl"
                onClick={onClose}
              >
                Cancel
              </Button>
              <Button
                className={cn(
                  "flex-1 rounded-xl gap-1.5 font-semibold",
                  isLegendary && "bg-amber-500 hover:bg-amber-600 text-black",
                )}
                onClick={handleBuy}
              >
                Buy for €{gift.price_eur.toFixed(2)}
              </Button>
            </div>
          </div>
        </div>
      </div>

      <UnifiedPaymentPanel
        open={showPayment}
        payload={{ type: "gift", product_id: gift.id }}
        title={`Buy ${gift.name}`}
        description={`Send ${gift.emoji} ${gift.name} to ${name}`}
        amountLabel={`€${gift.price_eur.toFixed(2)}`}
        onSuccess={handlePaymentSuccess}
        onClose={() => setShowPayment(false)}
        autoCharge
      />
    </>
  )
}
