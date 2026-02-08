import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { getGiftsList, createGiftCheckout } from "@/lib/api/endpoints"
import type { GiftDefinition } from "@/lib/api/types"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { X, Heart, Sparkles, Crown, Gift, ArrowUpRight } from "lucide-react"

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

const RARITY_BADGE: Record<string, string> = {
  common: "",
  rare: "bg-primary/20 text-primary",
  legendary: "bg-amber-500/20 text-amber-300",
}

interface GiftModalProps {
  open: boolean
  onClose: () => void
  girlfriendName?: string
}

export default function GiftModal({ open, onClose, girlfriendName }: GiftModalProps) {
  const [tab, setTab] = useState<string>("everyday")
  const [purchasing, setPurchasing] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ["giftCatalog"],
    queryFn: getGiftsList,
    enabled: open,
    staleTime: 60_000,
  })

  const gifts = data?.gifts ?? []
  const filtered = gifts.filter((g) => g.tier === tab)

  const handleBuy = async (gift: GiftDefinition) => {
    setPurchasing(gift.id)
    setError(null)
    try {
      const res = await createGiftCheckout(gift.id)
      if (res.checkout_url) {
        window.location.href = res.checkout_url
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong")
    } finally {
      setPurchasing(null)
    }
  }

  if (!open) return null

  return (
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
                  onBuy={() => handleBuy(gift)}
                  purchasing={purchasing === gift.id}
                  disabled={purchasing !== null}
                />
              ))}
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="px-5 pb-3">
            <p className="text-xs text-destructive text-center">{error}</p>
          </div>
        )}
      </div>
    </div>
  )
}

function GiftCard({
  gift,
  onBuy,
  purchasing,
  disabled,
}: {
  gift: GiftDefinition
  onBuy: () => void
  purchasing: boolean
  disabled: boolean
}) {
  const hasAlbum = gift.image_reward.album_size > 0

  return (
    <div
      className={cn(
        "flex flex-col rounded-xl border p-4 transition-all",
        TIER_COLORS[gift.tier] || TIER_COLORS.everyday,
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{gift.emoji}</span>
          <div>
            <h3 className="font-semibold text-sm leading-tight">{gift.name}</h3>
            <p className="text-xs text-muted-foreground mt-0.5">{gift.description}</p>
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

      <div className="flex items-center gap-2 mt-1 mb-3 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <Heart className="h-3 w-3 text-primary" />
          +{gift.relationship_boost.trust} trust
        </span>
        <span>·</span>
        <span className="flex items-center gap-1">
          <Sparkles className="h-3 w-3 text-primary" />
          +{gift.relationship_boost.intimacy} intimacy
        </span>
        {hasAlbum && (
          <>
            <span>·</span>
            <span className="flex items-center gap-1">
              📸 {gift.image_reward.album_size} photos
            </span>
          </>
        )}
      </div>

      <Button
        size="sm"
        className={cn(
          "w-full rounded-lg gap-1.5 text-xs",
          gift.tier === "legendary" && "bg-amber-500 hover:bg-amber-600 text-black",
        )}
        onClick={onBuy}
        disabled={disabled}
      >
        {purchasing ? (
          "Redirecting…"
        ) : (
          <>
            €{gift.price_eur.toFixed(2)}
            <ArrowUpRight className="h-3 w-3" />
          </>
        )}
      </Button>
    </div>
  )
}
