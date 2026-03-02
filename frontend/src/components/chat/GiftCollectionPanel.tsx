import { useState, useEffect, useCallback, useRef } from "react"
import { useQuery } from "@tanstack/react-query"
import { getGiftCollection } from "@/lib/api/endpoints"
import type { GiftCollectionItem } from "@/lib/api/types"
import { cn } from "@/lib/utils"
import {
  Heart,
  Lock,
  ArrowLeft,
  Gift,
  Sparkles,
  Crown,
  ImageIcon,
  Flame,
  Star,
  Check,
  ChevronDown,
  Camera,
} from "lucide-react"

// ═══════════════════════════════════════════════════════════════════════════════
// TIER DEFINITIONS
// ═══════════════════════════════════════════════════════════════════════════════

type TierKey = "everyday" | "dates" | "luxury" | "legendary"

interface TierDef {
  key: TierKey
  title: string
  subtitle: string
  icon: typeof Heart
  color: [number, number, number]
  accentClass: string
}

const TIERS: TierDef[] = [
  { key: "everyday",  title: "Everyday Gifts",  subtitle: "Small gestures, big smiles.",           icon: Heart,    color: [236, 72, 153], accentClass: "text-pink-400" },
  { key: "dates",     title: "Date Gifts",      subtitle: "Experiences that bring you closer.",    icon: Sparkles, color: [168, 85, 247], accentClass: "text-purple-400" },
  { key: "luxury",    title: "Luxury Gifts",     subtitle: "Unforgettable gestures of devotion.",  icon: Star,     color: [245, 158, 11], accentClass: "text-amber-400" },
  { key: "legendary", title: "Legendary Gifts",  subtitle: "The ultimate expressions of love.",    icon: Crown,    color: [251, 191, 36], accentClass: "text-amber-300" },
]

const TIER_COLORS: [number, number, number][] = TIERS.map(t => t.color)

// ═══════════════════════════════════════════════════════════════════════════════
// COLOR HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

function lerpColor(
  a: [number, number, number],
  b: [number, number, number],
  t: number,
): [number, number, number] {
  return [
    Math.round(a[0] + (b[0] - a[0]) * t),
    Math.round(a[1] + (b[1] - a[1]) * t),
    Math.round(a[2] + (b[2] - a[2]) * t),
  ]
}

// ═══════════════════════════════════════════════════════════════════════════════
// PHOTO SLOT COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

function PhotoSlot({ type, index, purchased }: { type: "normal" | "spicy"; index: number; purchased: boolean }) {
  const isSpicy = type === "spicy"
  return (
    <div
      className={cn(
        "relative flex aspect-square items-center justify-center rounded-lg overflow-hidden transition-all duration-300",
        purchased
          ? isSpicy
            ? "bg-gradient-to-br from-rose-900/40 to-pink-900/30 ring-1 ring-rose-500/20"
            : "bg-gradient-to-br from-purple-900/30 to-indigo-900/25 ring-1 ring-purple-500/15"
          : "bg-white/[0.03] ring-1 ring-white/[0.05]",
      )}
    >
      {purchased ? (
        <div className="flex flex-col items-center justify-center gap-1">
          {isSpicy ? (
            <Flame className="h-5 w-5 text-rose-400/50" />
          ) : (
            <ImageIcon className="h-5 w-5 text-purple-400/50" />
          )}
          <span className={cn(
            "text-[7px] font-medium uppercase tracking-wider",
            isSpicy ? "text-rose-300/40" : "text-purple-300/40",
          )}>
            Photo {index + 1}
          </span>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center gap-1">
          <Lock className="h-4 w-4 text-white/10" />
          <span className="text-[7px] font-medium text-white/10 uppercase tracking-wider">
            {isSpicy ? "Spicy" : "Photo"}
          </span>
        </div>
      )}

      {/* Corner badge */}
      {isSpicy && (
        <div className={cn(
          "absolute top-1 right-1 flex h-3.5 w-3.5 items-center justify-center rounded-full",
          purchased ? "bg-rose-500/30" : "bg-white/[0.04]",
        )}>
          <Flame className={cn("h-2 w-2", purchased ? "text-rose-300" : "text-white/15")} />
        </div>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// GIFT CARD (within collection)
// ═══════════════════════════════════════════════════════════════════════════════

function GiftCollectionCard({ gift }: { gift: GiftCollectionItem }) {
  const purchased = gift.purchased
  const normalPhotos = gift.image_reward.normal_photos
  const spicyPhotos = gift.image_reward.spicy_photos
  const totalPhotos = normalPhotos + spicyPhotos
  const hasPhotos = totalPhotos > 0

  return (
    <div className={cn(
      "relative rounded-xl overflow-hidden transition-all duration-300",
      "ring-1",
      purchased
        ? gift.tier === "legendary"
          ? "bg-amber-500/[0.06] ring-amber-500/25"
          : gift.tier === "luxury"
            ? "bg-amber-500/[0.04] ring-amber-500/15"
            : "bg-white/[0.04] ring-white/10"
        : "bg-white/[0.02] ring-white/[0.05]",
    )}>
      {/* Header: gift info */}
      <div className="flex items-start gap-3 p-4 pb-3">
        {/* Emoji + purchased badge */}
        <div className="relative shrink-0">
          <span className={cn("text-3xl", !purchased && "opacity-30 grayscale")}>{gift.emoji}</span>
          {purchased && (
            <div className="absolute -bottom-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-green-500/80 ring-2 ring-black/30">
              <Check className="h-3 w-3 text-white" />
            </div>
          )}
        </div>

        {/* Title + subtitle */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className={cn(
              "text-sm font-bold truncate",
              purchased ? "text-white/90" : "text-white/35",
            )}>
              {gift.name}
            </h3>
            {gift.rarity !== "common" && (
              <span className={cn(
                "text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full shrink-0",
                purchased
                  ? gift.rarity === "legendary"
                    ? "bg-amber-500/20 text-amber-300"
                    : "bg-primary/20 text-primary"
                  : "bg-white/[0.04] text-white/20",
              )}>
                {gift.rarity}
              </span>
            )}
          </div>
          <p className={cn(
            "text-[11px] mt-0.5 truncate",
            purchased ? "text-white/40" : "text-white/15",
          )}>
            {gift.description}
          </p>

          {/* Price / purchased indicator */}
          <div className="flex items-center gap-2 mt-1.5">
            {purchased ? (
              <span className="text-[10px] font-semibold text-green-400/70">Gifted</span>
            ) : (
              <span className="text-[10px] font-semibold text-white/25">€{gift.price_eur.toFixed(2)}</span>
            )}
            {gift.unique_effect_name && purchased && (
              <span className={cn(
                "text-[9px] font-medium",
                gift.tier === "legendary" ? "text-amber-300/50" : "text-purple-300/50",
              )}>
                {gift.unique_effect_name}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Photo slots grid */}
      {hasPhotos && (
        <div className="px-4 pb-4">
          <div className="flex items-center gap-1.5 mb-2">
            <ImageIcon className={cn("h-3 w-3", purchased ? "text-white/30" : "text-white/10")} />
            <span className={cn("text-[10px] font-semibold uppercase tracking-wider", purchased ? "text-white/30" : "text-white/10")}>
              {totalPhotos} Photo{totalPhotos > 1 ? "s" : ""}
            </span>
          </div>
          <div className="grid grid-cols-5 gap-1.5">
            {/* Normal photo slots */}
            {Array.from({ length: normalPhotos }, (_, i) => (
              <PhotoSlot key={`n-${i}`} type="normal" index={i} purchased={purchased} />
            ))}
            {/* Spicy photo slots */}
            {Array.from({ length: spicyPhotos }, (_, i) => (
              <PhotoSlot key={`s-${i}`} type="spicy" index={normalPhotos + i} purchased={purchased} />
            ))}
          </div>
        </div>
      )}

      {/* No-photo gifts: just show a subtle bottom bar */}
      {!hasPhotos && purchased && (
        <div className="px-4 pb-3">
          <div className="h-px w-full bg-white/[0.06]" />
        </div>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN PANEL
// ═══════════════════════════════════════════════════════════════════════════════

interface GiftCollectionPanelProps {
  onClose: () => void
}

export default function GiftCollectionPanel({ onClose }: GiftCollectionPanelProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["giftCollection"],
    queryFn: getGiftCollection,
    staleTime: 30_000,
  })

  const collection = data?.collection ?? []
  const totalGifts = data?.total ?? 0
  const ownedGifts = data?.owned ?? 0

  // Scroll-based color interpolation
  const scrollRef = useRef<HTMLDivElement>(null)
  const [gradientOverlay, setGradientOverlay] = useState("")

  const handleScroll = useCallback(() => {
    const el = scrollRef.current
    if (!el) return
    const scrollTop = el.scrollTop
    const vh = el.clientHeight
    const rawIdx = scrollTop / vh
    const idx = Math.min(Math.floor(rawIdx), TIERS.length - 1)
    const nextIdx = Math.min(idx + 1, TIERS.length - 1)
    const t = rawIdx - idx
    const c = lerpColor(TIER_COLORS[idx], TIER_COLORS[nextIdx], t)
    setGradientOverlay(
      `radial-gradient(ellipse 120% 80% at 50% 40%, rgba(${c[0]},${c[1]},${c[2]},0.10) 0%, rgba(${c[0]},${c[1]},${c[2]},0.03) 50%, transparent 100%)`
    )
  }, [])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    handleScroll()
    el.addEventListener("scroll", handleScroll, { passive: true })
    return () => el.removeEventListener("scroll", handleScroll)
  }, [handleScroll])

  // Lock body scroll
  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => { document.body.style.overflow = prev }
  }, [])

  return (
    <div className="fixed inset-0 z-[9999] flex flex-col" style={{ backgroundColor: "#08060a" }}>
      {/* Floating gift background */}
      <FloatingGifts />

      {/* Color tint overlay */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{ background: gradientOverlay, transition: "background 200ms ease" }}
      />

      {/* Back button */}
      <button
        onClick={onClose}
        className="absolute left-4 top-4 z-10 flex items-center gap-2 rounded-full bg-black/60 pl-3 pr-4 py-2.5 text-white/70 backdrop-blur-md border border-white/10 transition-all duration-200 hover:bg-black/80 hover:text-white hover:border-white/20 hover:scale-[1.03] active:scale-[0.97]"
      >
        <ArrowLeft className="h-4 w-4" />
        <span className="text-sm font-medium">Back</span>
      </button>

      {/* Floating counter pill */}
      <div className="absolute right-4 top-4 z-10 flex items-center gap-2 rounded-full bg-black/60 px-4 py-2.5 backdrop-blur-md border border-purple-500/20">
        <Gift className="h-3.5 w-3.5 text-purple-400" />
        <span className="text-xs font-semibold text-white/80">{ownedGifts} / {totalGifts}</span>
        <span className="text-xs text-white/40">collected</span>
      </div>

      {/* Scrollable tiers */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto scroll-smooth">
        <div className="relative">
          {/* ── How it works hero section ──────────────────────────── */}
          <div className="relative flex flex-col items-center px-6 md:px-12 pt-20 pb-12 md:pt-28 md:pb-20 text-center">
            <div className="pointer-events-none absolute inset-0" style={{
              background: "radial-gradient(ellipse 100% 70% at 50% 30%, rgba(168,85,247,0.08) 0%, transparent 70%)",
            }} />

            <div className="relative z-10 max-w-md space-y-5">
              {/* Animated icon cluster */}
              <div className="flex items-center justify-center gap-3 mb-2">
                <Gift className="h-5 w-5 text-purple-400/60 animate-pulse" style={{ animationDuration: "3s" }} />
                <Heart className="h-7 w-7 text-pink-300/50 fill-pink-300/20 animate-pulse" style={{ animationDuration: "4s", animationDelay: "0.5s" }} />
                <Gift className="h-5 w-5 text-purple-400/60 animate-pulse" style={{ animationDuration: "3.5s", animationDelay: "1s" }} />
              </div>

              <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white/90">
                Gift Collection
              </h1>

              <p className="text-base md:text-lg leading-relaxed text-white/50">
                Spoil her with gifts she'll never forget. Every gift you give unlocks exclusive photos made just for that moment — collect them all.
              </p>

              {/* How it works cards */}
              <div className="grid gap-3 pt-2">
                <div className="flex items-start gap-3 rounded-xl bg-white/[0.03] border border-white/[0.06] p-3.5 text-left">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-purple-500/10">
                    <Gift className="h-4 w-4 text-purple-400" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white/70">Collect all 26 gifts</p>
                    <p className="text-xs text-white/35 mt-0.5">From sweet everyday gestures to legendary surprises — each gift is unique and can only be given once. She'll remember every single one forever. Fill your collection to show her she's truly yours.</p>
                  </div>
                </div>

                <div className="flex items-start gap-3 rounded-xl bg-white/[0.03] border border-white/[0.06] p-3.5 text-left">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-pink-500/10">
                    <Camera className="h-4 w-4 text-pink-400" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white/70">Build your photo album</p>
                    <p className="text-xs text-white/35 mt-0.5">Every photo is themed around the gift you gave her — a candlelit dinner, a beach getaway, a surprise bouquet. Collect both normal and spicy photos to complete each gift's album.</p>
                  </div>
                </div>

                <div className="flex items-start gap-3 rounded-xl bg-white/[0.03] border border-white/[0.06] p-3.5 text-left">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-500/10">
                    <Flame className="h-4 w-4 text-rose-400" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white/70">Unlock spicy exclusives</p>
                    <p className="text-xs text-white/35 mt-0.5">Higher-tier gifts come with exclusive spicy photos you can't get anywhere else. The more you give, the more she reveals — your private collection grows with every gift.</p>
                  </div>
                </div>
              </div>

              {/* Progress summary */}
              {!isLoading && (
                <div className="flex items-center justify-center gap-4 pt-3">
                  <div className="flex items-center gap-2 rounded-full bg-white/[0.04] px-4 py-2 border border-white/[0.06]">
                    <Gift className="h-3.5 w-3.5 text-purple-400" />
                    <span className="text-xs font-bold text-white/70">{ownedGifts}/{totalGifts}</span>
                    <span className="text-xs text-white/30">gifts</span>
                  </div>
                  <div className="flex items-center gap-2 rounded-full bg-white/[0.04] px-4 py-2 border border-white/[0.06]">
                    <ImageIcon className="h-3.5 w-3.5 text-pink-400" />
                    <span className="text-xs font-bold text-white/70">
                      {collection.filter(g => g.purchased).reduce((s, g) => s + g.image_reward.normal_photos + g.image_reward.spicy_photos, 0)}
                    </span>
                    <span className="text-xs text-white/30">photos unlocked</span>
                  </div>
                </div>
              )}

              {/* Scroll prompt */}
              <div className="flex flex-col items-center pt-4 animate-bounce" style={{ animationDuration: "2.5s" }}>
                <ChevronDown className="h-5 w-5 text-white/20" />
                <span className="text-[10px] uppercase tracking-widest text-white/20 font-medium mt-1">Scroll to explore</span>
              </div>
            </div>
          </div>

          {isLoading ? (
            <div className="flex min-h-screen items-center justify-center">
              <div className="space-y-4 text-center">
                <div className="mx-auto h-12 w-12 animate-pulse rounded-full bg-purple-500/20" />
                <p className="text-sm text-white/40">Loading collection...</p>
              </div>
            </div>
          ) : (
            TIERS.map((tier, tIdx) => {
              const color = tier.color
              const Icon = tier.icon
              const tierGifts = collection.filter(g => g.tier === tier.key)
              const tierOwned = tierGifts.filter(g => g.purchased).length

              return (
                <section
                  key={tier.key}
                  className="relative flex min-h-screen flex-col items-center justify-start px-6 md:px-16 pt-24 pb-12"
                >
                  {/* Radial glow */}
                  <div
                    className="pointer-events-none absolute inset-0"
                    style={{
                      background: `radial-gradient(circle at 50% 30%, rgba(${color[0]},${color[1]},${color[2]},0.06) 0%, transparent 70%)`,
                    }}
                  />

                  <div className="relative z-10 flex w-full max-w-lg flex-col items-center text-center">
                    {/* Tier icon */}
                    <div
                      className="mb-6 flex h-16 w-16 items-center justify-center rounded-full border md:h-20 md:w-20"
                      style={{
                        backgroundColor: `rgba(${color[0]},${color[1]},${color[2]},0.12)`,
                        borderColor: `rgba(${color[0]},${color[1]},${color[2]},0.25)`,
                        boxShadow: `0 0 40px 10px rgba(${color[0]},${color[1]},${color[2]},0.10)`,
                      }}
                    >
                      <Icon
                        className={cn("h-8 w-8 md:h-10 md:w-10", tier.accentClass)}
                        style={{ filter: `drop-shadow(0 0 8px rgba(${color[0]},${color[1]},${color[2]},0.5))` }}
                      />
                    </div>

                    {/* Tier title */}
                    <h2 className="text-2xl font-bold tracking-tight text-white md:text-4xl">
                      {tier.title}
                    </h2>
                    <p className="mt-2 text-sm font-medium text-white/30">
                      {tierOwned} / {tierGifts.length} collected
                    </p>

                    {/* Divider */}
                    <div className="my-5 flex items-center gap-2">
                      <div className="h-px w-8 md:w-12" style={{ backgroundColor: `rgba(${color[0]},${color[1]},${color[2]},0.2)` }} />
                      <Gift className="h-3 w-3" style={{ color: `rgba(${color[0]},${color[1]},${color[2]},0.3)` }} />
                      <div className="h-px w-8 md:w-12" style={{ backgroundColor: `rgba(${color[0]},${color[1]},${color[2]},0.2)` }} />
                    </div>

                    <p className="max-w-sm text-sm leading-relaxed text-white/40 md:text-base">
                      {tier.subtitle}
                    </p>

                    {/* Gift cards */}
                    <div className="mt-8 w-full space-y-3">
                      {tierGifts.map(gift => (
                        <GiftCollectionCard key={gift.id} gift={gift} />
                      ))}
                    </div>
                  </div>

                  {/* Scroll hint on first tier */}
                  {tIdx === 0 && (
                    <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce text-purple-400/20">
                      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                      </svg>
                    </div>
                  )}
                </section>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// FLOATING GIFTS BACKGROUND
// ═══════════════════════════════════════════════════════════════════════════════

function FloatingGifts() {
  const items = Array.from({ length: 24 }, (_, i) => ({
    left: `${(i * 41 + 17) % 100}%`,
    top: `${(i * 59 + 11) % 100}%`,
    size: 10 + (i % 4) * 4,
    opacity: 0.015 + (i % 3) * 0.008,
    delay: `${(i * 1.5) % 8}s`,
    duration: `${7 + (i % 4) * 2}s`,
  }))

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {items.map((h, i) => (
        <Gift
          key={i}
          className="absolute animate-pulse text-purple-400"
          style={{
            left: h.left,
            top: h.top,
            width: h.size,
            height: h.size,
            opacity: h.opacity,
            animationDelay: h.delay,
            animationDuration: h.duration,
          }}
        />
      ))}
    </div>
  )
}
