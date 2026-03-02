import { useState, useEffect, useRef, useCallback } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { apiGet, apiPost } from "@/lib/api/client"
import { cn } from "@/lib/utils"
import {
  ArrowLeft,
  Gift,
  Sparkles,
  Star,
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

const TIER_STYLES: Record<string, { label: string; color: string; textColor: string; bg: string }> = {
  everyday:  { label: "Everyday",  color: "rgb(236,72,153)",  textColor: "text-pink-400",   bg: "bg-pink-500/15" },
  dates:     { label: "Dates",     color: "rgb(168,85,247)",  textColor: "text-purple-400", bg: "bg-purple-500/15" },
  luxury:    { label: "Luxury",    color: "rgb(245,158,11)",  textColor: "text-amber-400",  bg: "bg-amber-500/15" },
  legendary: { label: "Legendary", color: "rgb(251,191,36)",  textColor: "text-yellow-300", bg: "bg-yellow-500/15" },
}

// ═══════════════════════════════════════════════════════════════════════════════
// BOX VISUAL STYLING
// ═══════════════════════════════════════════════════════════════════════════════

const BOX_STYLES: Record<string, {
  gradient: string
  border: string
  glow: string
  shimmer: string
  text: string
}> = {
  bronze: {
    gradient: "from-amber-900/40 via-orange-800/30 to-amber-900/40",
    border: "border-amber-600/30",
    glow: "rgba(205,127,50,0.15)",
    shimmer: "from-amber-400/0 via-amber-400/10 to-amber-400/0",
    text: "text-amber-200",
  },
  gold: {
    gradient: "from-yellow-600/30 via-amber-500/20 to-yellow-600/30",
    border: "border-yellow-500/30",
    glow: "rgba(255,215,0,0.15)",
    shimmer: "from-yellow-300/0 via-yellow-300/15 to-yellow-300/0",
    text: "text-yellow-200",
  },
  diamond: {
    gradient: "from-cyan-500/20 via-blue-400/15 to-purple-500/20",
    border: "border-cyan-400/30",
    glow: "rgba(185,242,255,0.15)",
    shimmer: "from-cyan-300/0 via-cyan-300/20 to-cyan-300/0",
    text: "text-cyan-200",
  },
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLOT REEL DATA — emojis with tier colors for vibrant reel
// ═══════════════════════════════════════════════════════════════════════════════

const SLOT_ITEMS: { emoji: string; tier: string }[] = [
  { emoji: "🎀", tier: "everyday" }, { emoji: "🎵", tier: "everyday" },
  { emoji: "☕", tier: "everyday" }, { emoji: "🍬", tier: "everyday" },
  { emoji: "💌", tier: "everyday" }, { emoji: "💐", tier: "everyday" },
  { emoji: "🍫", tier: "everyday" }, { emoji: "🧸", tier: "everyday" },
  { emoji: "🍷", tier: "dates" },   { emoji: "🎬", tier: "dates" },
  { emoji: "🌹", tier: "dates" },   { emoji: "🧖‍♀️", tier: "dates" },
  { emoji: "🍽️", tier: "dates" },   { emoji: "👗", tier: "dates" },
  { emoji: "📸", tier: "dates" },
  { emoji: "🌃", tier: "luxury" },  { emoji: "💎", tier: "luxury" },
  { emoji: "🏔️", tier: "luxury" },  { emoji: "📷", tier: "luxury" },
  { emoji: "💍", tier: "luxury" },  { emoji: "🎁", tier: "luxury" },
  { emoji: "✈️", tier: "luxury" },
  { emoji: "🌹", tier: "legendary" }, { emoji: "👜", tier: "legendary" },
  { emoji: "👑", tier: "legendary" }, { emoji: "🏝️", tier: "legendary" },
]

const TIER_COLORS: Record<string, { from: string; to: string; ring: string }> = {
  everyday:  { from: "#ec4899", to: "#f472b6", ring: "rgba(236,72,153,0.4)" },
  dates:     { from: "#a855f7", to: "#c084fc", ring: "rgba(168,85,247,0.4)" },
  luxury:    { from: "#f59e0b", to: "#fbbf24", ring: "rgba(245,158,11,0.4)" },
  legendary: { from: "#eab308", to: "#facc15", ring: "rgba(234,179,8,0.5)" },
}

// ═══════════════════════════════════════════════════════════════════════════════
// FLOATING PARTICLES
// ═══════════════════════════════════════════════════════════════════════════════

function FloatingParticles() {
  const particles = Array.from({ length: 30 }, (_, i) => ({
    left: `${(i * 29 + 7) % 100}%`,
    top: `${(i * 43 + 13) % 100}%`,
    size: 4 + (i % 4) * 3,
    opacity: 0.03 + (i % 5) * 0.012,
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
// ODDS BAR
// ═══════════════════════════════════════════════════════════════════════════════

function OddsBar({ odds, unowned }: { odds: Record<string, number>; unowned: Record<string, number> }) {
  const tiers = ["everyday", "dates", "luxury", "legendary"].filter(t => (odds[t] ?? 0) > 0)

  return (
    <div className="space-y-2">
      <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-black/30">
        {tiers.map(t => {
          const pct = (odds[t] ?? 0) * 100
          const style = TIER_STYLES[t]
          return (
            <div
              key={t}
              className="h-full transition-all duration-500"
              style={{ width: `${pct}%`, backgroundColor: style.color, opacity: 0.7 }}
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
// SLOT MACHINE SPIN + REVEAL OVERLAY  (smooth, colorful, proper deceleration)
// ═══════════════════════════════════════════════════════════════════════════════

const CELL_W = 110 // px per reel cell
const WINNER_INDEX = 55 // winner placed here — plenty of items before AND after
const TOTAL_CELLS = 70 // total items on the reel
const SPIN_DURATION = 5500 // ms total spin

function buildReel(winnerEmoji: string, winnerTier: string) {
  const items: { emoji: string; tier: string }[] = []
  for (let i = 0; i < TOTAL_CELLS; i++) {
    if (i === WINNER_INDEX) {
      items.push({ emoji: winnerEmoji, tier: winnerTier })
    } else {
      items.push(SLOT_ITEMS[Math.floor(Math.random() * SLOT_ITEMS.length)])
    }
  }
  return items
}

function SlotRevealOverlay({
  gift,
  boxName,
  onClose,
}: {
  gift: RevealedGift
  boxName: string
  onClose: () => void
}) {
  const [phase, setPhase] = useState<"spinning" | "revealed">("spinning")
  const reelRef = useRef<HTMLDivElement>(null)
  const rafRef = useRef<number>(0)
  const tierStyle = TIER_STYLES[gift.tier] ?? TIER_STYLES.everyday

  const reel = useRef(buildReel(gift.emoji, gift.tier)).current

  // Target offset = center the winner cell in the viewport
  // offset = WINNER_INDEX * CELL_W
  const targetOffset = WINNER_INDEX * CELL_W

  useEffect(() => {
    const el = reelRef.current
    if (!el) return

    const startTime = performance.now()

    // Easing: fast start → long gradual deceleration → gentle stop
    function easeOutQuint(t: number) {
      return 1 - Math.pow(1 - t, 4.2)
    }

    function animate(now: number) {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / SPIN_DURATION, 1)
      const easedProgress = easeOutQuint(progress)

      const currentOffset = easedProgress * targetOffset
      el.style.transform = `translateX(-${currentOffset}px)`

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate)
      } else {
        // Spin complete — show result after a brief dramatic pause
        setTimeout(() => setPhase("revealed"), 400)
      }
    }

    rafRef.current = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(rafRef.current)
  }, [targetOffset])

  return (
    <div className="fixed inset-0 z-[99999] flex items-center justify-center bg-black/90 backdrop-blur-xl">
      {phase === "revealed" && (
        <button
          onClick={onClose}
          className="absolute right-6 top-6 z-10 flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white/60 hover:bg-white/20 hover:text-white transition-all"
        >
          <X className="h-5 w-5" />
        </button>
      )}

      <div className="flex flex-col items-center gap-8 w-full max-w-lg px-4">
        {/* Title */}
        <p className="text-center text-sm font-bold text-white/50 uppercase tracking-[0.2em]">
          {phase === "revealed" ? "You got..." : boxName}
        </p>

        {/* ── Slot machine housing ── */}
        <div className="w-full relative">
          {/* Decorative frame */}
          <div className="absolute -inset-1.5 rounded-3xl bg-gradient-to-r from-purple-500/20 via-pink-500/20 to-amber-500/20 blur-sm" />
          <div className="relative rounded-2xl border-2 border-white/10 bg-[#0a0812] overflow-hidden shadow-2xl"
               style={{ boxShadow: "0 0 60px 10px rgba(168,85,247,0.08), inset 0 0 30px rgba(0,0,0,0.5)" }}>

            {/* Center selection marker — golden bracket */}
            <div className="absolute left-1/2 top-0 bottom-0 z-20 pointer-events-none" style={{ width: CELL_W + 8, transform: "translateX(-50%)" }}>
              <div className="absolute inset-x-0 top-0 h-1.5 rounded-b bg-gradient-to-r from-yellow-400/0 via-yellow-400 to-yellow-400/0" />
              <div className="absolute inset-x-0 bottom-0 h-1.5 rounded-t bg-gradient-to-r from-yellow-400/0 via-yellow-400 to-yellow-400/0" />
              <div className="absolute inset-0 border-2 border-yellow-400/50 rounded-xl" />
              <div className="absolute inset-0 bg-yellow-400/[0.04]" />
            </div>

            {/* Edge fades */}
            <div className="absolute inset-y-0 left-0 w-20 z-10 bg-gradient-to-r from-[#0a0812] to-transparent pointer-events-none" />
            <div className="absolute inset-y-0 right-0 w-20 z-10 bg-gradient-to-l from-[#0a0812] to-transparent pointer-events-none" />

            {/* The scrolling reel strip */}
            <div className="h-28 flex items-center overflow-hidden" style={{ paddingLeft: `calc(50% - ${CELL_W / 2}px)` }}>
              <div ref={reelRef} className="flex items-center" style={{ willChange: "transform" }}>
                {reel.map((item, i) => {
                  const tc = TIER_COLORS[item.tier] ?? TIER_COLORS.everyday
                  const isWinner = i === WINNER_INDEX && phase === "revealed"
                  return (
                    <div
                      key={i}
                      className="shrink-0 flex items-center justify-center"
                      style={{ width: CELL_W, height: 112 }}
                    >
                      <div
                        className={cn(
                          "flex items-center justify-center rounded-2xl transition-all duration-500",
                          isWinner ? "w-[96px] h-[96px] scale-110" : "w-[88px] h-[88px]",
                        )}
                        style={{
                          background: `linear-gradient(135deg, ${tc.from}28, ${tc.to}15)`,
                          border: `2px solid ${tc.ring}`,
                          boxShadow: isWinner
                            ? `0 0 30px 8px ${tc.ring}, 0 0 60px 15px ${tc.from}20`
                            : `0 0 10px 2px ${tc.from}10`,
                        }}
                      >
                        <span className={cn(
                          "transition-all duration-300",
                          isWinner ? "text-6xl" : "text-4xl",
                        )}>
                          {item.emoji}
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Glow under the machine */}
          {phase === "revealed" && (
            <div
              className="absolute -bottom-6 left-1/2 -translate-x-1/2 w-48 h-12 rounded-full blur-2xl transition-opacity duration-1000"
              style={{ backgroundColor: tierStyle.color, opacity: 0.25 }}
            />
          )}
        </div>

        {/* ── Revealed gift details ── */}
        {phase === "revealed" ? (
          <div className="flex flex-col items-center gap-5 animate-in fade-in slide-in-from-bottom-6 duration-700">
            {/* Tier badge */}
            <span
              className="px-5 py-1.5 rounded-full text-xs font-black uppercase tracking-[0.15em] border"
              style={{
                color: tierStyle.color,
                borderColor: `${tierStyle.color}40`,
                backgroundColor: `${tierStyle.color}12`,
              }}
            >
              {tierStyle.label} Gift
            </span>

            {/* Name + value */}
            <div className="text-center">
              <h2 className="text-3xl font-extrabold text-white tracking-tight">{gift.name}</h2>
              <p className="text-sm text-white/30 mt-2 max-w-xs leading-relaxed">{gift.description}</p>
              <p className="text-xl font-black mt-3" style={{ color: tierStyle.color }}>
                Worth €{gift.price_eur.toFixed(2)}
              </p>
            </div>

            {/* Photos earned */}
            {(gift.normal_photos > 0 || gift.spicy_photos > 0) && (
              <div className="flex items-center gap-3">
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

            {/* Collect */}
            <button
              onClick={onClose}
              className="mt-1 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 px-10 py-3.5 text-sm font-bold text-white shadow-lg shadow-purple-500/25 hover:shadow-purple-500/40 hover:scale-105 transition-all active:scale-95"
            >
              Collect Gift
            </button>
          </div>
        ) : (
          /* Spinning label */
          <div className="flex items-center gap-3">
            <div className="h-5 w-5 rounded-full border-2 border-purple-400/30 border-t-purple-400 animate-spin" />
            <span className="text-base text-white/40 font-semibold tracking-wide">Spinning...</span>
          </div>
        )}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN PANEL
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

  const handleOpen = useCallback(async (boxId: string) => {
    setError("")
    setPurchasing(boxId)
    try {
      const res = await apiPost<{
        status: string
        gift?: RevealedGift
        box?: { id: string; name: string; price_eur: number }
        error?: string
        client_secret?: string
        payment_intent_id?: string
      }>("/gifts/mystery-box/open", { box_id: boxId })

      // No card on file
      if (res.status === "no_card") {
        setError(res.error ?? "No card on file. Add one in Payment Options first.")
        return
      }

      // Payment failed
      if (res.status === "failed") {
        setError(res.error ?? "Payment failed. Please try again.")
        return
      }

      // 3DS authentication required
      if (res.status === "requires_action" && res.client_secret) {
        try {
          const { loadStripe } = await import("@stripe/stripe-js")
          const stripeKey = (import.meta as any).env?.VITE_STRIPE_PUBLISHABLE_KEY
          if (stripeKey) {
            const stripeJs = await loadStripe(stripeKey)
            if (stripeJs) {
              const { error: stripeErr } = await stripeJs.confirmCardPayment(res.client_secret)
              if (stripeErr) {
                setError(stripeErr.message || "3D Secure authentication failed")
                return
              }
              // 3DS succeeded — gift data is in the response already
              if (res.gift && res.box) {
                setRevealedGift({ gift: res.gift, boxName: res.box.name })
                queryClient.invalidateQueries({ queryKey: ["giftCatalog"] })
                queryClient.invalidateQueries({ queryKey: ["giftCollection"] })
                queryClient.invalidateQueries({ queryKey: ["mysteryBoxes"] })
                return
              }
            }
          }
          setError("Could not complete 3D Secure. Please try again.")
        } catch (e3ds: any) {
          setError(e3ds?.message || "3D Secure failed")
        }
        return
      }

      // Payment succeeded
      if (res.status === "succeeded" && res.gift && res.box) {
        setRevealedGift({ gift: res.gift, boxName: res.box.name })
        queryClient.invalidateQueries({ queryKey: ["giftCatalog"] })
        queryClient.invalidateQueries({ queryKey: ["giftCollection"] })
        queryClient.invalidateQueries({ queryKey: ["mysteryBoxes"] })
      } else {
        setError(res.error ?? "Something went wrong")
      }
    } catch (e: any) {
      const msg = e?.message ?? "Something went wrong"
      setError(msg)
    } finally {
      setPurchasing(null)
    }
  }, [queryClient])

  const handleRevealClose = () => {
    setRevealedGift(null)
    refetch()
  }

  // Avg values by tier for EV display
  const avgByTier: Record<string, number> = {
    everyday: 4.5, dates: 22.14, luxury: 103.57, legendary: 184.75,
  }

  return (
    <div className="fixed inset-0 z-[9999] flex flex-col" style={{ backgroundColor: "#07050d" }}>
      <FloatingParticles />

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
              <Heart className="h-5 w-5 text-pink-400/60 fill-pink-400/30 animate-pulse" style={{ animationDuration: "3s" }} />
              <Gift className="h-8 w-8 text-purple-300/60 animate-pulse" style={{ animationDuration: "4s", animationDelay: "0.5s" }} />
              <Heart className="h-5 w-5 text-pink-400/60 fill-pink-400/30 animate-pulse" style={{ animationDuration: "3.5s", animationDelay: "1s" }} />
            </div>
            <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white/90">
              Surprise Her
            </h1>
            <p className="mt-3 text-base text-white/40 max-w-sm mx-auto leading-relaxed">
              Spin the wheel of love. Every surprise is a real gift — and you always get more than what you pay.
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
                  <div key={i} className="h-52 rounded-2xl bg-white/[0.03] animate-pulse" />
                ))}
              </div>
            ) : (
              boxes.map((box) => {
                const style = BOX_STYLES[box.id] ?? BOX_STYLES.bronze
                const isOpening = purchasing === box.id
                const soldOut = !box.has_eligible_gifts

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
                    <div className={cn("absolute inset-0 bg-gradient-to-r", style.gradient)} />

                    {/* Shimmer */}
                    <div className="absolute inset-0 overflow-hidden pointer-events-none">
                      <div
                        className={cn("absolute -left-full top-0 h-full w-1/2 bg-gradient-to-r", style.shimmer)}
                        style={{ animation: "shimmerSweep 3s ease-in-out infinite" }}
                      />
                    </div>

                    <div className="relative z-10 p-5">
                      {/* Header */}
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <div
                            className="flex h-14 w-14 items-center justify-center rounded-xl"
                            style={{ backgroundColor: style.glow, boxShadow: `0 0 20px 4px ${style.glow}` }}
                          >
                            <span className="text-2xl">{box.emoji}</span>
                          </div>
                          <div>
                            <h3 className={cn("text-lg font-bold", style.text)}>{box.name}</h3>
                            <p className="text-xs text-white/30 mt-0.5 max-w-[200px]">{box.description}</p>
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-1">
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

                      <OddsBar odds={box.effective_odds} unowned={box.unowned_by_tier} />

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
                          <><Lock className="h-4 w-4" /> All gifts collected!</>
                        ) : isOpening ? (
                          <><div className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" /> Spinning...</>
                        ) : (
                          <><Sparkles className="h-4 w-4" /> Spin &amp; Surprise<ChevronRight className="h-4 w-4" /></>
                        )}
                      </button>
                    </div>
                  </div>
                )
              })
            )}
          </div>

          {/* How it works */}
          <div className="mt-10 space-y-3 pb-8">
            <h3 className="text-center text-sm font-bold text-white/40 uppercase tracking-wider">How it works</h3>
            <div className="space-y-2">
              {[
                { icon: Gift, text: "Every surprise is a real gift — delivered instantly with photos and all the love." },
                { icon: Sparkles, text: "Spin and the reel picks a gift for her. Bigger surprises mean rarer, more romantic drops." },
                { icon: Heart, text: "No duplicates — you'll never get a gift you've already given her." },
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

      {/* Slot reveal overlay */}
      {revealedGift && (
        <SlotRevealOverlay
          gift={revealedGift.gift}
          boxName={revealedGift.boxName}
          onClose={handleRevealClose}
        />
      )}

      <style>{`
        @keyframes shimmerSweep {
          0% { transform: translateX(0); }
          100% { transform: translateX(400%); }
        }
      `}</style>
    </div>
  )
}
