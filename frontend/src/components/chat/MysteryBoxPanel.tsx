import { useState, useEffect, useRef } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { apiGet, apiPost } from "@/lib/api/client"
import { cn } from "@/lib/utils"
import {
  ArrowLeft,
  Gift,
  Sparkles,
  Star,
  Crown,
  Flame,
  Heart,
  ImageIcon,
  Lock,
  X,
  ChevronRight,
} from "lucide-react"

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

interface MysteryBox {
  id: string
  name: string
  price_eur: number
  emoji: string
  description: string
  color: string
  tier_weights: Record<string, number>
  effective_odds: Record<string, number>
  has_eligible_gifts: boolean
  unowned_by_tier: Record<string, number>
}

interface MysteryBoxResponse {
  boxes: MysteryBox[]
  total_gifts: number
  owned_gifts: number
  unowned_gifts: number
}

interface RevealedGift {
  id: string
  name: string
  emoji: string
  tier: string
  price_eur: number
  description: string
  normal_photos: number
  spicy_photos: number
}

// ═══════════════════════════════════════════════════════════════════════════════
// TIER STYLING
// ═══════════════════════════════════════════════════════════════════════════════

const TIER_STYLES: Record<string, { label: string; color: string; textColor: string; icon: typeof Star }> = {
  everyday:  { label: "Everyday",  color: "rgb(236,72,153)",  textColor: "text-pink-400",   icon: Heart },
  dates:     { label: "Dates",     color: "rgb(168,85,247)",  textColor: "text-purple-400", icon: Star },
  luxury:    { label: "Luxury",    color: "rgb(245,158,11)",  textColor: "text-amber-400",  icon: Crown },
  legendary: { label: "Legendary", color: "rgb(251,191,36)",  textColor: "text-yellow-300", icon: Sparkles },
}

// ═══════════════════════════════════════════════════════════════════════════════
// BOX VISUAL STYLING
// ═══════════════════════════════════════════════════════════════════════════════

const BOX_STYLES: Record<string, {
  gradient: string
  border: string
  glow: string
  shadowColor: string
  shimmer: string
  badge: string
  text: string
  icon: typeof Gift
}> = {
  bronze: {
    gradient: "from-amber-900/40 via-orange-800/30 to-amber-900/40",
    border: "border-amber-600/30",
    glow: "rgba(205,127,50,0.15)",
    shadowColor: "rgba(205,127,50,0.3)",
    shimmer: "from-amber-400/0 via-amber-400/10 to-amber-400/0",
    badge: "bg-amber-700/30 text-amber-300 border-amber-500/20",
    text: "text-amber-200",
    icon: Gift,
  },
  gold: {
    gradient: "from-yellow-600/30 via-amber-500/20 to-yellow-600/30",
    border: "border-yellow-500/30",
    glow: "rgba(255,215,0,0.15)",
    shadowColor: "rgba(255,215,0,0.3)",
    shimmer: "from-yellow-300/0 via-yellow-300/15 to-yellow-300/0",
    badge: "bg-yellow-600/30 text-yellow-200 border-yellow-400/20",
    text: "text-yellow-200",
    icon: Sparkles,
  },
  diamond: {
    gradient: "from-cyan-500/20 via-blue-400/15 to-purple-500/20",
    border: "border-cyan-400/30",
    glow: "rgba(185,242,255,0.15)",
    shadowColor: "rgba(185,242,255,0.3)",
    shimmer: "from-cyan-300/0 via-cyan-300/20 to-cyan-300/0",
    badge: "bg-cyan-500/20 text-cyan-200 border-cyan-400/20",
    text: "text-cyan-200",
    icon: Crown,
  },
}

// ═══════════════════════════════════════════════════════════════════════════════
// FLOATING PARTICLES BACKGROUND
// ═══════════════════════════════════════════════════════════════════════════════

function FloatingParticles() {
  const particles = Array.from({ length: 40 }, (_, i) => ({
    left: `${(i * 29 + 7) % 100}%`,
    top: `${(i * 43 + 13) % 100}%`,
    size: 4 + (i % 4) * 3,
    opacity: 0.03 + (i % 5) * 0.015,
    delay: `${(i * 1.3) % 8}s`,
    dur: `${6 + (i % 4) * 3}s`,
    icon: i % 4,
  }))

  const icons = [Gift, Sparkles, Star, Heart]

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {particles.map((p, i) => {
        const Icon = icons[p.icon]
        return (
          <Icon
            key={i}
            className="absolute animate-pulse"
            style={{
              left: p.left,
              top: p.top,
              width: p.size,
              height: p.size,
              opacity: p.opacity,
              color: "rgba(200,170,255,0.5)",
              animationDelay: p.delay,
              animationDuration: p.dur,
            }}
          />
        )
      })}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// ODDS BAR COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

function OddsBar({ odds, unowned }: { odds: Record<string, number>; unowned: Record<string, number> }) {
  const tiers = ["everyday", "dates", "luxury", "legendary"].filter(t => (odds[t] ?? 0) > 0)

  return (
    <div className="space-y-2">
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-black/30">
        {tiers.map(t => {
          const pct = (odds[t] ?? 0) * 100
          const style = TIER_STYLES[t]
          return (
            <div
              key={t}
              className="h-full transition-all duration-500"
              style={{
                width: `${pct}%`,
                backgroundColor: style.color,
                opacity: 0.7,
              }}
            />
          )
        })}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {tiers.map(t => {
          const style = TIER_STYLES[t]
          const pct = ((odds[t] ?? 0) * 100).toFixed(0)
          return (
            <div key={t} className="flex items-center gap-1.5">
              <div className="h-2 w-2 rounded-full" style={{ backgroundColor: style.color }} />
              <span className={cn("text-[10px] font-bold", style.textColor)}>{style.label}</span>
              <span className="text-[10px] text-white/30">{pct}%</span>
              <span className="text-[9px] text-white/15">({unowned[t] ?? 0} left)</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// REVEAL OVERLAY
// ═══════════════════════════════════════════════════════════════════════════════

function RevealOverlay({
  gift,
  boxName,
  onClose,
}: {
  gift: RevealedGift
  boxName: string
  onClose: () => void
}) {
  const [phase, setPhase] = useState<"opening" | "revealed">("opening")
  const tierStyle = TIER_STYLES[gift.tier] ?? TIER_STYLES.everyday

  useEffect(() => {
    const timer = setTimeout(() => setPhase("revealed"), 1500)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div className="fixed inset-0 z-[99999] flex items-center justify-center bg-black/80 backdrop-blur-md">
      {/* Close button */}
      {phase === "revealed" && (
        <button
          onClick={onClose}
          className="absolute right-6 top-6 z-10 flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white/60 hover:bg-white/20 hover:text-white transition-all"
        >
          <X className="h-5 w-5" />
        </button>
      )}

      {phase === "opening" ? (
        /* Opening animation */
        <div className="flex flex-col items-center gap-6">
          <div className="relative">
            <div className="h-32 w-32 rounded-3xl bg-gradient-to-br from-purple-500/30 to-pink-500/30 animate-pulse flex items-center justify-center"
                 style={{ animationDuration: "0.5s" }}>
              <Gift className="h-16 w-16 text-white/80 animate-bounce" style={{ animationDuration: "0.6s" }} />
            </div>
            {/* Radiating rings */}
            <div className="absolute inset-0 rounded-3xl animate-ping opacity-20 bg-white" style={{ animationDuration: "1s" }} />
            <div className="absolute -inset-4 rounded-[2rem] animate-ping opacity-10 bg-purple-400" style={{ animationDuration: "1.2s" }} />
            <div className="absolute -inset-8 rounded-[2.5rem] animate-ping opacity-5 bg-pink-400" style={{ animationDuration: "1.5s" }} />
          </div>
          <p className="text-lg font-bold text-white/60 animate-pulse">Opening {boxName}...</p>
        </div>
      ) : (
        /* Revealed gift */
        <div className="flex flex-col items-center gap-6 px-6 max-w-sm animate-in fade-in zoom-in duration-500">
          {/* Glow background */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background: `radial-gradient(circle at 50% 45%, ${tierStyle.color}22 0%, transparent 60%)`,
            }}
          />

          {/* Tier label */}
          <div className="relative">
            <span
              className="px-4 py-1.5 rounded-full text-xs font-black uppercase tracking-widest border"
              style={{
                color: tierStyle.color,
                borderColor: `${tierStyle.color}40`,
                backgroundColor: `${tierStyle.color}15`,
              }}
            >
              {tierStyle.label} Gift
            </span>
          </div>

          {/* Gift emoji */}
          <div className="relative">
            <span className="text-8xl block">{gift.emoji}</span>
            {/* Sparkle effects */}
            <Sparkles className="absolute -top-2 -right-2 h-6 w-6 text-yellow-300 animate-pulse" />
            <Star className="absolute -bottom-1 -left-3 h-5 w-5 text-yellow-400/60 animate-pulse" style={{ animationDelay: "0.5s" }} />
          </div>

          {/* Gift name */}
          <div className="text-center">
            <h2 className="text-3xl font-extrabold text-white">{gift.name}</h2>
            <p className="text-sm text-white/40 mt-2 max-w-xs">{gift.description}</p>
            <p className="text-lg font-bold mt-2" style={{ color: tierStyle.color }}>
              Worth €{gift.price_eur.toFixed(2)}
            </p>
          </div>

          {/* Photos earned */}
          {(gift.normal_photos > 0 || gift.spicy_photos > 0) && (
            <div className="flex items-center gap-4">
              {gift.normal_photos > 0 && (
                <div className="flex items-center gap-1.5 rounded-full bg-purple-500/15 px-3 py-1.5 border border-purple-500/20">
                  <ImageIcon className="h-3.5 w-3.5 text-purple-400" />
                  <span className="text-xs font-bold text-purple-300">{gift.normal_photos} Photo{gift.normal_photos > 1 ? "s" : ""}</span>
                </div>
              )}
              {gift.spicy_photos > 0 && (
                <div className="flex items-center gap-1.5 rounded-full bg-rose-500/15 px-3 py-1.5 border border-rose-500/20">
                  <Flame className="h-3.5 w-3.5 text-rose-400" />
                  <span className="text-xs font-bold text-rose-300">{gift.spicy_photos} Spicy</span>
                </div>
              )}
            </div>
          )}

          {/* Collect button */}
          <button
            onClick={onClose}
            className="mt-2 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 px-8 py-3 text-sm font-bold text-white shadow-lg shadow-purple-500/20 hover:shadow-purple-500/30 hover:scale-105 transition-all duration-200 active:scale-95"
          >
            Collect Gift
          </button>
        </div>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN MYSTERY BOX PANEL
// ═══════════════════════════════════════════════════════════════════════════════

interface MysteryBoxPanelProps {
  onClose: () => void
}

export default function MysteryBoxPanel({ onClose }: MysteryBoxPanelProps) {
  const queryClient = useQueryClient()
  const [purchasing, setPurchasing] = useState<string | null>(null)
  const [revealedGift, setRevealedGift] = useState<{ gift: RevealedGift; boxName: string } | null>(null)
  const [error, setError] = useState("")

  const { data, isLoading, refetch } = useQuery<MysteryBoxResponse>({
    queryKey: ["mysteryBoxes"],
    queryFn: () => apiGet<MysteryBoxResponse>("/gifts/mystery-boxes"),
    staleTime: 10_000,
  })

  const boxes = data?.boxes ?? []
  const totalGifts = data?.total_gifts ?? 0
  const ownedGifts = data?.owned_gifts ?? 0

  // Lock body scroll
  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => { document.body.style.overflow = prev }
  }, [])

  const handleOpen = async (boxId: string) => {
    setError("")
    setPurchasing(boxId)
    try {
      const res = await apiPost<{
        status: string
        gift?: RevealedGift
        box?: { id: string; name: string; price_eur: number }
        error?: string
        client_secret?: string
      }>("/gifts/mystery-box/open", { box_id: boxId })

      if (res.status === "succeeded" && res.gift && res.box) {
        setRevealedGift({ gift: res.gift, boxName: res.box.name })
        // Invalidate queries to refresh collections
        queryClient.invalidateQueries({ queryKey: ["giftCatalog"] })
        queryClient.invalidateQueries({ queryKey: ["giftCollection"] })
        queryClient.invalidateQueries({ queryKey: ["mysteryBoxes"] })
      } else if (res.status === "no_card") {
        setError("No card on file. Add a payment card first.")
      } else if (res.status === "requires_action") {
        setError("3D Secure required — please complete in the gift shop.")
      } else {
        setError(res.error ?? "Payment failed")
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? "Something went wrong")
    } finally {
      setPurchasing(null)
    }
  }

  const handleRevealClose = () => {
    setRevealedGift(null)
    refetch()
  }

  return (
    <div className="fixed inset-0 z-[9999] flex flex-col" style={{ backgroundColor: "#07050d" }}>
      <FloatingParticles />

      {/* Gradient background */}
      <div className="pointer-events-none absolute inset-0" style={{
        background: "radial-gradient(ellipse 100% 60% at 50% 30%, rgba(120,60,200,0.06) 0%, transparent 70%)",
      }} />

      {/* Top bar */}
      <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between px-4 py-3 backdrop-blur-xl bg-black/50 border-b border-white/[0.06]">
        <button
          onClick={onClose}
          className="flex items-center gap-2 rounded-full bg-white/[0.06] pl-3 pr-4 py-2 text-white/70 border border-white/[0.08] transition-all hover:bg-white/10 hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm font-medium">Back</span>
        </button>

        <div className="flex items-center gap-2 rounded-full bg-white/[0.06] px-4 py-2 border border-white/[0.08]">
          <Gift className="h-3.5 w-3.5 text-purple-400" />
          <span className="text-xs font-bold text-white/90">{ownedGifts}/{totalGifts}</span>
          <span className="text-xs text-white/40">collected</span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto pt-16 pb-12 px-4 md:px-8">
        <div className="mx-auto max-w-lg">
          {/* Hero */}
          <div className="text-center pt-8 pb-10">
            <div className="flex items-center justify-center gap-2 mb-4">
              <Sparkles className="h-5 w-5 text-purple-400/60 animate-pulse" style={{ animationDuration: "3s" }} />
              <Gift className="h-8 w-8 text-purple-300/60 animate-pulse" style={{ animationDuration: "4s", animationDelay: "0.5s" }} />
              <Sparkles className="h-5 w-5 text-purple-400/60 animate-pulse" style={{ animationDuration: "3.5s", animationDelay: "1s" }} />
            </div>
            <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white/90">
              Mystery Boxes
            </h1>
            <p className="mt-3 text-base text-white/40 max-w-sm mx-auto leading-relaxed">
              Take a chance. Every box contains a real gift for her — and you'll always get more value than what you pay.
            </p>
          </div>

          {/* Error */}
          {error && (
            <div className="mb-6 rounded-xl bg-red-500/10 border border-red-500/20 p-3 text-center">
              <p className="text-sm text-red-300">{error}</p>
            </div>
          )}

          {/* Boxes */}
          <div className="space-y-5">
            {isLoading ? (
              <div className="space-y-4">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-56 rounded-2xl bg-white/[0.03] animate-pulse" />
                ))}
              </div>
            ) : (
              boxes.map((box) => {
                const style = BOX_STYLES[box.id] ?? BOX_STYLES.bronze
                const BoxIcon = style.icon
                const isOpening = purchasing === box.id
                const soldOut = !box.has_eligible_gifts

                // Calculate expected value
                const avgByTier: Record<string, number> = {
                  everyday: 4.5, dates: 22.14, luxury: 103.57, legendary: 184.75,
                }
                let ev = 0
                for (const [t, w] of Object.entries(box.effective_odds)) {
                  ev += (avgByTier[t] ?? 0) * w
                }

                return (
                  <div
                    key={box.id}
                    className={cn(
                      "relative rounded-2xl border overflow-hidden transition-all duration-300",
                      style.border,
                      soldOut && "opacity-40",
                    )}
                    style={{
                      boxShadow: `0 0 40px 8px ${style.glow}, inset 0 1px 0 rgba(255,255,255,0.04)`,
                    }}
                  >
                    {/* Background gradient */}
                    <div className={cn("absolute inset-0 bg-gradient-to-r", style.gradient)} />

                    {/* Shimmer sweep */}
                    <div className="absolute inset-0 overflow-hidden pointer-events-none">
                      <div
                        className={cn("absolute -left-full top-0 h-full w-1/2 bg-gradient-to-r", style.shimmer)}
                        style={{
                          animation: "shimmerSweep 3s ease-in-out infinite",
                        }}
                      />
                    </div>

                    <div className="relative z-10 p-5 md:p-6">
                      {/* Header row */}
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <div
                            className="flex h-14 w-14 items-center justify-center rounded-xl"
                            style={{
                              backgroundColor: `${style.glow}`,
                              boxShadow: `0 0 20px 4px ${style.glow}`,
                            }}
                          >
                            <BoxIcon className={cn("h-7 w-7", style.text)} />
                          </div>
                          <div>
                            <h3 className={cn("text-lg font-bold", style.text)}>{box.name}</h3>
                            <p className="text-xs text-white/30 mt-0.5 max-w-[200px]">{box.description}</p>
                          </div>
                        </div>

                        {/* Price badge */}
                        <div className={cn("flex flex-col items-end gap-1")}>
                          <span className={cn("text-2xl font-black", style.text)}>
                            €{box.price_eur.toFixed(2)}
                          </span>
                          {ev > 0 && (
                            <span className="text-[10px] font-medium text-emerald-400/70">
                              ~€{ev.toFixed(0)} avg value
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Odds visualization */}
                      <OddsBar odds={box.effective_odds} unowned={box.unowned_by_tier} />

                      {/* Open button */}
                      <button
                        onClick={() => handleOpen(box.id)}
                        disabled={isOpening || soldOut || purchasing !== null}
                        className={cn(
                          "w-full mt-4 rounded-xl py-3.5 text-sm font-bold transition-all duration-200",
                          "flex items-center justify-center gap-2",
                          soldOut
                            ? "bg-white/[0.04] text-white/20 cursor-not-allowed"
                            : isOpening
                              ? "bg-white/10 text-white/50"
                              : "bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg shadow-purple-500/20 hover:shadow-purple-500/30 hover:scale-[1.02] active:scale-[0.98]",
                        )}
                      >
                        {soldOut ? (
                          <>
                            <Lock className="h-4 w-4" />
                            All gifts collected!
                          </>
                        ) : isOpening ? (
                          <>
                            <div className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                            Opening...
                          </>
                        ) : (
                          <>
                            <Gift className="h-4 w-4" />
                            Open Box
                            <ChevronRight className="h-4 w-4" />
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                )
              })
            )}
          </div>

          {/* Info section */}
          <div className="mt-10 space-y-3 pb-8">
            <h3 className="text-center text-sm font-bold text-white/40 uppercase tracking-wider">How it works</h3>
            <div className="space-y-2">
              {[
                { icon: Gift, text: "Each box contains a real gift — delivered to her instantly with full photos and effects." },
                { icon: Sparkles, text: "You always get more value than what you pay. Higher boxes mean rarer drops." },
                { icon: Heart, text: "No duplicates — every box gives you a gift you don't own yet. She'll love the surprise." },
              ].map((item, i) => (
                <div key={i} className="flex items-start gap-3 rounded-lg bg-white/[0.02] p-3 border border-white/[0.04]">
                  <item.icon className="h-4 w-4 shrink-0 text-purple-400/50 mt-0.5" />
                  <p className="text-xs text-white/30 leading-relaxed">{item.text}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Reveal overlay */}
      {revealedGift && (
        <RevealOverlay
          gift={revealedGift.gift}
          boxName={revealedGift.boxName}
          onClose={handleRevealClose}
        />
      )}

      {/* Shimmer animation keyframes */}
      <style>{`
        @keyframes shimmerSweep {
          0% { transform: translateX(0); }
          100% { transform: translateX(400%); }
        }
      `}</style>
    </div>
  )
}
