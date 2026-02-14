import { useState, useEffect, useCallback, useRef } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { getSpicyLeaksCollection, spinSpicyLeak } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import type { SpicyLeakPhoto, SpicyLeakBox } from "@/lib/api/types"
import { cn } from "@/lib/utils"
import {
  Heart,
  Lock,
  Sparkles,
  ArrowLeft,
  Flame,
  ImageIcon,
  X,
  ChevronRight,
  ChevronDown,
  Camera,
} from "lucide-react"

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

type LeakRarity = "COMMON" | "UNCOMMON" | "RARE" | "EPIC" | "LEGENDARY"

// Frontend-only catalog for slot machine icons and reel display
interface LeakItem {
  id: string
  title: string
  subtitle: string
  rarity: LeakRarity
  icon: string
}

// ═══════════════════════════════════════════════════════════════════════════════
// RARITY CONFIG
// ═══════════════════════════════════════════════════════════════════════════════

const RARITY_CONFIG: Record<LeakRarity, {
  text: string; icon: string; label: string
  bg: string; badge: string; ring: string
  color: string; glow: string
}> = {
  COMMON:    { text: "text-pink-200/70",  icon: "text-pink-300/50",  label: "",          bg: "bg-pink-500/[0.04]",  badge: "",                   ring: "ring-pink-500/10",   color: "#f472b6", glow: "rgba(244,114,182,0.15)" },
  UNCOMMON:  { text: "text-pink-200",     icon: "text-pink-300",     label: "Uncommon",  bg: "bg-rose-500/[0.05]",  badge: "text-pink-300/60",   ring: "ring-rose-500/15",   color: "#fb7185", glow: "rgba(251,113,133,0.15)" },
  RARE:      { text: "text-rose-200",     icon: "text-rose-400",     label: "Rare",      bg: "bg-red-500/[0.06]",   badge: "text-rose-300/70",   ring: "ring-red-500/20",    color: "#ef4444", glow: "rgba(239,68,68,0.15)" },
  EPIC:      { text: "text-red-200",      icon: "text-red-400",      label: "Epic",      bg: "bg-red-500/[0.08]",   badge: "text-red-300/80",    ring: "ring-red-600/25",    color: "#dc2626", glow: "rgba(220,38,38,0.2)" },
  LEGENDARY: { text: "text-amber-200",    icon: "text-amber-400",    label: "Legendary", bg: "bg-amber-500/[0.08]", badge: "text-amber-300/90",  ring: "ring-amber-500/30",  color: "#fbbf24", glow: "rgba(251,191,36,0.2)" },
}

// ═══════════════════════════════════════════════════════════════════════════════
// FLOATING BACKGROUND
// ═══════════════════════════════════════════════════════════════════════════════

function FloatingLeaks() {
  const items = Array.from({ length: 30 }, (_, i) => ({
    left: `${(i * 37 + 13) % 100}%`,
    top: `${(i * 53 + 7) % 100}%`,
    size: 8 + (i % 5) * 4,
    opacity: 0.02 + (i % 4) * 0.01,
    delay: `${(i * 1.3) % 8}s`,
    duration: `${6 + (i % 5) * 2}s`,
    icon: i % 3,
  }))
  const icons = [Camera, Flame, Sparkles]
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {items.map((h, i) => {
        const Icon = icons[h.icon]
        return (
          <Icon
            key={i}
            className="absolute animate-pulse fill-current text-pink-500"
            style={{
              left: h.left, top: h.top, width: h.size, height: h.size,
              opacity: h.opacity, animationDelay: h.delay, animationDuration: h.duration,
            }}
          />
        )
      })}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLOT MACHINE
// ═══════════════════════════════════════════════════════════════════════════════

const CELL_W = 100
const WINNER_IDX = 55
const TOTAL_REEL = 70
const SPIN_MS = 6000

function pickRandomPhoto(
  weights: Record<string, number>,
  allPhotos: LeakItem[],
  unlockedIds: Set<string>,
): LeakItem | null {
  // Build pool of locked photos grouped by rarity
  const pool: Record<string, LeakItem[]> = {}
  for (const p of allPhotos) {
    if (!unlockedIds.has(p.id)) {
      if (!pool[p.rarity]) pool[p.rarity] = []
      pool[p.rarity].push(p)
    }
  }

  // Build weighted selection
  const candidates: { photo: LeakItem; weight: number }[] = []
  for (const [rarity, w] of Object.entries(weights)) {
    const arr = pool[rarity] ?? []
    if (arr.length > 0 && w > 0) {
      const perItem = w / arr.length
      for (const p of arr) candidates.push({ photo: p, weight: perItem })
    }
  }

  if (candidates.length === 0) return null

  const totalW = candidates.reduce((s, c) => s + c.weight, 0)
  let r = Math.random() * totalW
  for (const c of candidates) {
    r -= c.weight
    if (r <= 0) return c.photo
  }
  return candidates[candidates.length - 1].photo
}

function buildReel(winner: LeakItem, allPhotos: LeakItem[]) {
  const items: LeakItem[] = []
  for (let i = 0; i < TOTAL_REEL; i++) {
    if (i === WINNER_IDX) {
      items.push(winner)
    } else {
      items.push(allPhotos[Math.floor(Math.random() * allPhotos.length)])
    }
  }
  return items
}

// Slot overlay with reel data
function SlotOverlayWithReel({
  winner,
  allPhotos,
  onClose,
  onUnlock,
}: {
  winner: LeakItem
  allPhotos: LeakItem[]
  onClose: () => void
  onUnlock: (id: string) => void
}) {
  const [phase, setPhase] = useState<"spinning" | "revealed">("spinning")
  const reelRef = useRef<HTMLDivElement>(null)
  const rafRef = useRef<number>(0)
  const rCfg = RARITY_CONFIG[winner.rarity]

  const reel = useRef(buildReel(winner, allPhotos)).current
  const targetOffset = WINNER_IDX * CELL_W

  useEffect(() => {
    const el = reelRef.current
    if (!el) return
    const start = performance.now()

    function easeOut(t: number) { return 1 - Math.pow(1 - t, 4.5) }

    function animate(now: number) {
      const p = Math.min((now - start) / SPIN_MS, 1)
      el.style.transform = `translateX(-${easeOut(p) * targetOffset}px)`
      if (p < 1) {
        rafRef.current = requestAnimationFrame(animate)
      } else {
        setTimeout(() => {
          setPhase("revealed")
          onUnlock(winner.id)
        }, 500)
      }
    }
    rafRef.current = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(rafRef.current)
  }, [targetOffset, winner.id, onUnlock])

  return (
    <div className="fixed inset-0 z-[99999] flex items-center justify-center bg-black/92 backdrop-blur-xl">
      {phase === "revealed" && (
        <button onClick={onClose} className="absolute right-6 top-6 z-10 flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white/60 hover:bg-white/20 transition-all">
          <X className="h-5 w-5" />
        </button>
      )}

      <div className="flex flex-col items-center gap-8 w-full max-w-lg px-4">
        <p className="text-center text-sm font-bold text-pink-300/50 uppercase tracking-[0.2em]">
          {phase === "revealed" ? "Leaked!" : "Spinning..."}
        </p>

        {/* Slot machine */}
        <div className="w-full relative">
          <div className="absolute -inset-1.5 rounded-3xl bg-gradient-to-r from-pink-500/20 via-red-500/20 to-amber-500/20 blur-sm" />
          <div className="relative rounded-2xl border-2 border-pink-500/15 bg-[#0d0509] overflow-hidden shadow-2xl"
               style={{ boxShadow: "0 0 60px 10px rgba(244,114,182,0.08), inset 0 0 30px rgba(0,0,0,0.5)" }}>

            <div className="absolute left-1/2 top-0 bottom-0 z-20 pointer-events-none" style={{ width: CELL_W + 8, transform: "translateX(-50%)" }}>
              <div className="absolute inset-x-0 top-0 h-1.5 rounded-b bg-gradient-to-r from-pink-400/0 via-pink-400 to-pink-400/0" />
              <div className="absolute inset-x-0 bottom-0 h-1.5 rounded-t bg-gradient-to-r from-pink-400/0 via-pink-400 to-pink-400/0" />
              <div className="absolute inset-0 border-2 border-pink-400/50 rounded-xl" />
              <div className="absolute inset-0 bg-pink-400/[0.04]" />
            </div>

            <div className="absolute inset-y-0 left-0 w-16 z-10 bg-gradient-to-r from-[#0d0509] to-transparent pointer-events-none" />
            <div className="absolute inset-y-0 right-0 w-16 z-10 bg-gradient-to-l from-[#0d0509] to-transparent pointer-events-none" />

            <div className="h-28 flex items-center overflow-hidden" style={{ paddingLeft: `calc(50% - ${CELL_W / 2}px)` }}>
              <div ref={reelRef} className="flex items-center" style={{ willChange: "transform" }}>
                {reel.map((item, i) => {
                  const tc = RARITY_CONFIG[item.rarity]
                  const isW = i === WINNER_IDX && phase === "revealed"
                  return (
                    <div key={i} className="shrink-0 flex items-center justify-center" style={{ width: CELL_W, height: 112 }}>
                      <div
                        className={cn("flex items-center justify-center rounded-2xl transition-all duration-500", isW ? "w-[90px] h-[90px] scale-110" : "w-[80px] h-[80px]")}
                        style={{
                          background: `linear-gradient(135deg, ${tc.color}30, ${tc.color}10)`,
                          border: `2px solid ${tc.color}50`,
                          boxShadow: isW ? `0 0 30px 8px ${tc.glow}, 0 0 60px 15px ${tc.color}15` : `0 0 8px 2px ${tc.color}08`,
                        }}
                      >
                        <span className={cn("transition-all", isW ? "text-5xl" : "text-3xl")}>{item.icon}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {phase === "revealed" && (
            <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 w-40 h-10 rounded-full blur-2xl" style={{ backgroundColor: rCfg.color, opacity: 0.3 }} />
          )}
        </div>

        {/* Result */}
        {phase === "revealed" ? (
          <div className="flex flex-col items-center gap-5 animate-in fade-in slide-in-from-bottom-6 duration-700">
            <span className="px-5 py-1.5 rounded-full text-xs font-black uppercase tracking-[0.15em] border"
              style={{ color: rCfg.color, borderColor: `${rCfg.color}40`, backgroundColor: `${rCfg.color}12` }}>
              {rCfg.label || "Common"} Leak
            </span>

            <div className="flex items-center gap-3">
              <span className="text-5xl">{winner.icon}</span>
              <div className="text-left">
                <h2 className="text-2xl font-extrabold text-white">{winner.title}</h2>
                <p className="text-sm text-white/40 mt-0.5">{winner.subtitle}</p>
              </div>
            </div>

            <div className="flex items-center gap-2 rounded-full bg-pink-500/15 px-4 py-2 border border-pink-500/20">
              <Camera className="h-4 w-4 text-pink-400" />
              <span className="text-xs font-bold text-pink-300">New Leaked Photo Collected!</span>
            </div>

            <button onClick={onClose}
              className="rounded-full bg-gradient-to-r from-pink-500 to-red-500 px-10 py-3.5 text-sm font-bold text-white shadow-lg shadow-pink-500/25 hover:shadow-pink-500/40 hover:scale-105 transition-all active:scale-95">
              Collect
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <div className="h-5 w-5 rounded-full border-2 border-pink-400/30 border-t-pink-400 animate-spin" />
            <span className="text-base text-pink-300/40 font-semibold">Spinning...</span>
          </div>
        )}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN PANEL
// ═══════════════════════════════════════════════════════════════════════════════

interface SpicyLeaksPanelProps {
  onClose: () => void
  defaultTab?: "collection" | "slots"
}

export default function SpicyLeaksPanel({ onClose, defaultTab = "collection" }: SpicyLeaksPanelProps) {
  const girlfriendId = useAppStore((s) => s.currentGirlfriendId)
  const queryClient = useQueryClient()

  // Fetch data from backend
  const { data: apiData } = useQuery({
    queryKey: ["spicyLeaks", girlfriendId],
    queryFn: () => getSpicyLeaksCollection(girlfriendId || undefined),
    staleTime: 30_000,
  })

  const photos = apiData?.photos ?? []
  const boxes = apiData?.boxes ?? []
  const totalCount = apiData?.total ?? 50
  const totalUnlocked = apiData?.unlocked ?? 0

  // Local unlocked tracking (optimistic updates)
  const [localUnlocked, setLocalUnlocked] = useState<Set<string>>(new Set())
  useEffect(() => {
    if (!photos.length) return
    const ids = new Set(photos.filter(p => p.unlocked).map(p => p.id))
    setLocalUnlocked(ids)
  }, [photos])

  // Build LeakItem array for slot machine
  const allLeakItems: LeakItem[] = photos.map(p => ({
    id: p.id,
    title: p.title,
    subtitle: p.subtitle,
    rarity: p.rarity as LeakRarity,
    icon: p.icon,
  }))

  // Build photo map for collection view
  const photoMap = new Map<string, string>()
  for (const p of photos) {
    if (p.image_url) photoMap.set(p.id, p.image_url)
  }

  const [activeTab, setActiveTab] = useState<"collection" | "slots">(defaultTab)
  const [slotWinner, setSlotWinner] = useState<LeakItem | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Track payment state
  const [purchasing, setPurchasing] = useState<string | null>(null)
  const [purchaseError, setPurchaseError] = useState<string | null>(null)

  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => { document.body.style.overflow = prev }
  }, [])

  const handleUnlock = useCallback(async (id: string) => {
    setLocalUnlocked(prev => new Set([...prev, id]))
    queryClient.invalidateQueries({ queryKey: ["spicyLeaks"] })
  }, [queryClient])

  const handleSpin = async (boxId: string) => {
    const box = boxes.find(b => b.id === boxId)
    if (!box) return
    const winner = pickRandomPhoto(box.weights, allLeakItems, localUnlocked)
    if (!winner) return

    setPurchasing(boxId)
    setPurchaseError(null)

    try {
      const res = await spinSpicyLeak(boxId, winner.id, girlfriendId || undefined)

      if (res.status === "no_card") {
        setPurchaseError("No card on file. Add one in Payment Options first.")
        return
      }

      if (res.status === "requires_action" && res.client_secret) {
        const { loadStripe } = await import("@stripe/stripe-js")
        const stripeKey = (import.meta as any).env?.VITE_STRIPE_PUBLISHABLE_KEY
        if (stripeKey) {
          const stripeJs = await loadStripe(stripeKey)
          if (stripeJs) {
            const { error } = await stripeJs.confirmCardPayment(res.client_secret)
            if (error) {
              setPurchaseError(error.message || "3D Secure authentication failed")
              return
            }
          }
        }
      }

      if (res.ok || res.status === "succeeded" || res.status === "free") {
        if (res.image_url) {
          photoMap.set(winner.id, res.image_url)
        }
        setSlotWinner(winner)
      } else {
        setPurchaseError(res.error || "Payment failed. Please try again.")
      }
    } catch (e: any) {
      console.warn("Spicy leak spin failed:", e)
      setPurchaseError(e?.message || "Payment failed. Please try again.")
    } finally {
      setPurchasing(null)
    }
  }

  // Group photos by rarity for collection display
  const rarityOrder: LeakRarity[] = ["COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY"]
  const photosByRarity: Record<string, SpicyLeakPhoto[]> = {}
  for (const p of photos) {
    if (!photosByRarity[p.rarity]) photosByRarity[p.rarity] = []
    photosByRarity[p.rarity].push(p)
  }

  return (
    <div className="fixed inset-0 z-[9999] flex flex-col" style={{ backgroundColor: "#0a0608" }}>
      <FloatingLeaks />

      {/* Top bar */}
      <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between px-4 py-3 backdrop-blur-xl bg-black/50 border-b border-pink-500/10">
        <button onClick={onClose} className="flex items-center gap-2 rounded-full bg-black/60 pl-3 pr-4 py-2 text-white/70 border border-white/10 transition-all hover:bg-black/80 hover:text-white">
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm font-medium">Back</span>
        </button>

        {/* Tab toggle */}
        <div className="flex rounded-full bg-black/60 border border-pink-500/15 p-0.5">
          <button
            onClick={() => setActiveTab("collection")}
            className={cn("px-4 py-1.5 rounded-full text-xs font-bold transition-all",
              activeTab === "collection" ? "bg-pink-500/20 text-pink-300" : "text-white/40 hover:text-white/60")}
          >
            Collection
          </button>
          <button
            onClick={() => setActiveTab("slots")}
            className={cn("px-4 py-1.5 rounded-full text-xs font-bold transition-all",
              activeTab === "slots" ? "bg-red-500/20 text-red-300" : "text-white/40 hover:text-white/60")}
          >
            📸 Leaked Photos
          </button>
        </div>

        <div className="flex items-center gap-2 rounded-full bg-black/60 px-4 py-2 border border-pink-500/15">
          <Camera className="h-3.5 w-3.5 text-pink-400" />
          <span className="text-xs font-bold text-white/80">{totalUnlocked}/{totalCount}</span>
        </div>
      </div>

      {/* Content */}
      {activeTab === "collection" ? (
        /* ── COLLECTION TAB ── */
        <div ref={scrollRef} className="flex-1 overflow-y-auto scroll-smooth pt-16 pb-8 px-4 md:px-8">
          <div className="mx-auto max-w-lg">
            {/* Hero */}
            <div className="text-center pt-8 pb-8">
              <div className="flex items-center justify-center gap-2 mb-4">
                <Camera className="h-6 w-6 text-pink-400/60 animate-pulse" style={{ animationDuration: "3s" }} />
                <Sparkles className="h-5 w-5 text-pink-300/40 animate-pulse" style={{ animationDuration: "4s", animationDelay: "0.5s" }} />
              </div>
              <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white/90">
                Her Spicy Leaks
              </h1>
              <p className="mt-3 text-base text-white/40 max-w-sm mx-auto leading-relaxed">
                Your private collection of leaked photos. Spin the slots to unlock more.
              </p>
            </div>

            {/* Collection by rarity */}
            {rarityOrder.map(rarity => {
              const group = photosByRarity[rarity] ?? []
              if (group.length === 0) return null
              const cfg = RARITY_CONFIG[rarity]
              const groupUnlocked = group.filter(p => localUnlocked.has(p.id)).length

              return (
                <div key={rarity} className="mb-8">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: cfg.color }} />
                    <h2 className="text-sm font-bold uppercase tracking-wider" style={{ color: cfg.color }}>
                      {cfg.label || "Common"}
                    </h2>
                    <span className="text-xs text-white/30">{groupUnlocked}/{group.length}</span>
                  </div>

                  <div className="space-y-2">
                    {group.map(p => {
                      const isU = localUnlocked.has(p.id)
                      return (
                        <div key={p.id} className={cn("flex items-stretch gap-0 rounded-xl overflow-hidden transition-all ring-1", isU ? cfg.bg : "bg-white/[0.02]", isU ? cfg.ring : "ring-white/[0.04]")}>
                          {/* Photo slot */}
                          <div className={cn("relative flex h-[72px] w-[72px] shrink-0 items-center justify-center overflow-hidden", isU ? "bg-gradient-to-br from-pink-900/40 to-rose-900/30" : "bg-white/[0.03]")}>
                            {isU && p.image_url ? (
                              <img src={p.image_url} alt={p.title} className="h-full w-full object-cover" />
                            ) : isU ? (
                              <div className="flex flex-col items-center gap-0.5">
                                <span className="text-2xl">{p.icon}</span>
                                <span className="text-[7px] font-medium text-pink-300/40 uppercase tracking-wider">Photo</span>
                              </div>
                            ) : (
                              <div className="flex flex-col items-center gap-1">
                                <span className="text-xl opacity-30">{p.icon}</span>
                                <Lock className="h-2.5 w-2.5 text-white/10" />
                              </div>
                            )}
                            <div className={cn("absolute left-0 top-0 h-full w-[3px]")} style={{ backgroundColor: isU ? `${cfg.color}60` : "rgba(255,255,255,0.04)" }} />
                          </div>

                          {/* Text */}
                          <div className="flex min-w-0 flex-1 items-center gap-3 px-3.5 py-3">
                            <div className="min-w-0 flex-1 text-left">
                              <div className="flex items-center gap-1.5">
                                <p className={cn("text-xs font-semibold truncate", isU ? cfg.text : "text-white/40")}>{p.title}</p>
                                {cfg.label && (
                                  <span className={cn("text-[9px] uppercase tracking-wider font-medium shrink-0", isU ? cfg.badge : "text-white/15")}>{cfg.label}</span>
                                )}
                              </div>
                              <p className={cn("text-[10px] truncate", isU ? "text-white/35" : "text-white/20")}>{p.subtitle}</p>
                            </div>

                            {isU ? (
                              <Camera className="h-3.5 w-3.5 shrink-0 text-pink-400" />
                            ) : (
                              <Lock className="h-3 w-3 shrink-0 text-white/15" />
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ) : (
        /* ── SLOTS TAB ── */
        <div className="flex-1 overflow-y-auto pt-16 pb-12 px-4 md:px-8">
          <div className="mx-auto max-w-lg">
            {/* Hero */}
            <div className="text-center pt-8 pb-10">
              <div className="flex items-center justify-center gap-2 mb-4">
                <Camera className="h-5 w-5 text-red-400/60 animate-pulse" style={{ animationDuration: "3s" }} />
                <Heart className="h-8 w-8 text-pink-300/60 fill-pink-300/30 animate-pulse" style={{ animationDuration: "4s", animationDelay: "0.5s" }} />
                <Camera className="h-5 w-5 text-red-400/60 animate-pulse" style={{ animationDuration: "3.5s", animationDelay: "1s" }} />
              </div>
              <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white/90">
                Leaked Photos
              </h1>
              <p className="mt-3 text-base text-white/40 max-w-sm mx-auto leading-relaxed">
                Spin to unlock exclusive leaked photos. The higher the tier, the spicier the leak. Collect all 50 for the complete private collection.
              </p>
            </div>

            {/* Slot boxes */}
            <div className="space-y-5">
              {boxes.map((box) => {
                const availableCount = allLeakItems.filter(p => {
                  if (localUnlocked.has(p.id)) return false
                  return (box.weights[p.rarity] ?? 0) > 0
                }).length
                const soldOut = availableCount === 0

                return (
                  <div key={box.id} className={cn("relative rounded-2xl border overflow-hidden transition-all", soldOut && "opacity-40")}
                    style={{ borderColor: `${RARITY_CONFIG[box.weights.LEGENDARY > 0.3 ? "LEGENDARY" : box.weights.EPIC > 0.2 ? "EPIC" : "COMMON"].color}25`, boxShadow: `0 0 40px 8px ${RARITY_CONFIG[box.weights.LEGENDARY > 0.3 ? "LEGENDARY" : box.weights.EPIC > 0.2 ? "EPIC" : "COMMON"].color}10, inset 0 1px 0 rgba(255,255,255,0.03)` }}>
                    <div className="absolute inset-0" style={{ background: `linear-gradient(135deg, ${RARITY_CONFIG[box.weights.LEGENDARY > 0.3 ? "LEGENDARY" : box.weights.EPIC > 0.2 ? "EPIC" : "COMMON"].color}15, transparent 60%)` }} />

                    {/* Shimmer */}
                    <div className="absolute inset-0 overflow-hidden pointer-events-none">
                      <div className="absolute -left-full top-0 h-full w-1/2" style={{ background: `linear-gradient(90deg, transparent, ${RARITY_CONFIG[box.weights.LEGENDARY > 0.3 ? "LEGENDARY" : box.weights.EPIC > 0.2 ? "EPIC" : "COMMON"].color}08, transparent)`, animation: "shimmerSweep 3s ease-in-out infinite" }} />
                    </div>

                    <div className="relative z-10 p-5">
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <div className="flex h-14 w-14 items-center justify-center rounded-xl" style={{ backgroundColor: `${RARITY_CONFIG[box.weights.LEGENDARY > 0.3 ? "LEGENDARY" : box.weights.EPIC > 0.2 ? "EPIC" : "COMMON"].color}15`, boxShadow: `0 0 20px 4px ${RARITY_CONFIG[box.weights.LEGENDARY > 0.3 ? "LEGENDARY" : box.weights.EPIC > 0.2 ? "EPIC" : "COMMON"].color}15` }}>
                            <span className="text-2xl">{box.emoji}</span>
                          </div>
                          <div>
                            <h3 className="text-lg font-bold" style={{ color: RARITY_CONFIG[box.weights.LEGENDARY > 0.3 ? "LEGENDARY" : box.weights.EPIC > 0.2 ? "EPIC" : "COMMON"].color }}>{box.name}</h3>
                            <p className="text-xs text-white/30 mt-0.5 max-w-[200px]">{box.description}</p>
                          </div>
                        </div>
                        <span className="text-sm font-bold text-emerald-400/70">€{box.price_eur.toFixed(2)}</span>
                      </div>

                      {/* Odds */}
                      <div className="flex h-2 w-full overflow-hidden rounded-full bg-black/30 mb-2">
                        {(["COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY"] as LeakRarity[]).filter(r => (box.weights[r] ?? 0) > 0).map(r => (
                          <div key={r} className="h-full" style={{ width: `${(box.weights[r] ?? 0) * 100}%`, backgroundColor: RARITY_CONFIG[r].color, opacity: 0.7 }} />
                        ))}
                      </div>
                      <div className="flex flex-wrap gap-x-3 gap-y-1 mb-4">
                        {(["COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY"] as LeakRarity[]).filter(r => (box.weights[r] ?? 0) > 0).map(r => (
                          <div key={r} className="flex items-center gap-1">
                            <div className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: RARITY_CONFIG[r].color }} />
                            <span className="text-[9px] font-bold" style={{ color: RARITY_CONFIG[r].color }}>{r}</span>
                            <span className="text-[9px] text-white/25">{((box.weights[r] ?? 0) * 100).toFixed(0)}%</span>
                          </div>
                        ))}
                      </div>

                      <button
                        onClick={() => handleSpin(box.id)}
                        disabled={soldOut || purchasing === box.id}
                        className={cn("w-full rounded-xl py-3.5 text-sm font-bold transition-all flex items-center justify-center gap-2",
                          soldOut ? "bg-white/[0.04] text-white/20 cursor-not-allowed"
                            : purchasing === box.id ? "bg-gradient-to-r from-pink-600/60 to-red-600/60 text-white/60 cursor-wait"
                            : "bg-gradient-to-r from-pink-600 to-red-600 text-white shadow-lg shadow-pink-500/20 hover:shadow-pink-500/30 hover:scale-[1.02] active:scale-[0.98]")}
                      >
                        {soldOut ? (
                          <><Lock className="h-4 w-4" /> All collected!</>
                        ) : purchasing === box.id ? (
                          <><div className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" /> Processing...</>
                        ) : (
                          <><Camera className="h-4 w-4" /> Spin for Leaked Photo<ChevronRight className="h-4 w-4" /></>
                        )}
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Purchase error */}
            {purchaseError && (
              <div className="mt-4 rounded-xl bg-red-500/10 border border-red-500/20 p-3 text-center">
                <p className="text-sm text-red-300">{purchaseError}</p>
                <button
                  onClick={() => setPurchaseError(null)}
                  className="mt-2 text-xs text-red-400/60 hover:text-red-400 transition-colors"
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* How it works */}
            <div className="mt-10 space-y-3 pb-8">
              <h3 className="text-center text-sm font-bold text-white/40 uppercase tracking-wider">How it works</h3>
              <div className="space-y-2">
                {[
                  { icon: Camera, text: "Spin to unlock exclusive leaked photos from her private collection. Every spin reveals a new photo." },
                  { icon: Heart, text: "Higher-tier spins give better odds at Epic and Legendary — the rarest, most explicit leaked content." },
                  { icon: Sparkles, text: "No duplicates — every spin gives you something new. Collect all 50 for the complete set." },
                ].map((item, i) => (
                  <div key={i} className="flex items-start gap-3 rounded-lg bg-white/[0.02] p-3 border border-pink-500/[0.06]">
                    <item.icon className="h-4 w-4 shrink-0 text-pink-400/50 mt-0.5" />
                    <p className="text-xs text-white/30 leading-relaxed">{item.text}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Slot overlay */}
      {slotWinner && allLeakItems.length > 0 && (
        <SlotOverlayWithReel
          winner={slotWinner}
          allPhotos={allLeakItems}
          onClose={() => setSlotWinner(null)}
          onUnlock={handleUnlock}
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
