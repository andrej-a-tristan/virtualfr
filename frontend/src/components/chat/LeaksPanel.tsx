import { useState, useEffect, useRef, useCallback } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { getLeaksCollection } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import { cn } from "@/lib/utils"
import {
  ArrowLeft,
  Lock,
  Eye,
  Flame,
  Camera,
  ChevronRight,
  X,
  Heart,
  Sparkles,
} from "lucide-react"
import UnifiedPaymentPanel from "@/components/billing/UnifiedPaymentPanel"

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES & RARITY CONFIG
// ═══════════════════════════════════════════════════════════════════════════════

type LeakRarity = "COMMON" | "UNCOMMON" | "RARE" | "EPIC" | "LEGENDARY"

interface LeakItem {
  id: string
  title: string
  description: string
  rarity: LeakRarity
  icon: string
}

const RARITY_ORDER: LeakRarity[] = ["COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY"]

const RARITY_CONFIG: Record<LeakRarity, {
  label: string
  color: string
  bg: string
  ring: string
  text: string
  glow: string
  badge: string
  lockedBg: string
}> = {
  COMMON: {
    label: "Common",
    color: "#94a3b8",
    bg: "bg-slate-500/[0.06]",
    ring: "ring-slate-500/15",
    text: "text-slate-300",
    glow: "rgba(148,163,184,0.10)",
    badge: "bg-slate-500/15 text-slate-300/70 border-slate-500/20",
    lockedBg: "from-slate-800/40 to-slate-900/60",
  },
  UNCOMMON: {
    label: "Uncommon",
    color: "#4ade80",
    bg: "bg-emerald-500/[0.06]",
    ring: "ring-emerald-500/15",
    text: "text-emerald-300",
    glow: "rgba(74,222,128,0.12)",
    badge: "bg-emerald-500/15 text-emerald-300/80 border-emerald-500/20",
    lockedBg: "from-emerald-900/30 to-slate-900/60",
  },
  RARE: {
    label: "Rare",
    color: "#60a5fa",
    bg: "bg-blue-500/[0.07]",
    ring: "ring-blue-500/20",
    text: "text-blue-300",
    glow: "rgba(96,165,250,0.15)",
    badge: "bg-blue-500/15 text-blue-300/80 border-blue-500/20",
    lockedBg: "from-blue-900/30 to-slate-900/60",
  },
  EPIC: {
    label: "Epic",
    color: "#c084fc",
    bg: "bg-purple-500/[0.08]",
    ring: "ring-purple-500/25",
    text: "text-purple-300",
    glow: "rgba(192,132,252,0.18)",
    badge: "bg-purple-500/20 text-purple-300/90 border-purple-500/25",
    lockedBg: "from-purple-900/35 to-slate-900/60",
  },
  LEGENDARY: {
    label: "Legendary",
    color: "#fbbf24",
    bg: "bg-amber-500/[0.10]",
    ring: "ring-amber-500/30",
    text: "text-amber-300",
    glow: "rgba(251,191,36,0.20)",
    badge: "bg-amber-500/20 text-amber-300 border-amber-500/30",
    lockedBg: "from-amber-900/30 to-slate-900/60",
  },
}

// ═══════════════════════════════════════════════════════════════════════════════
// 50 LEAK ITEMS — names visible, sexual & addictive
// ═══════════════════════════════════════════════════════════════════════════════

const LEAKS: LeakItem[] = [
  // ── COMMON (18) — flirty selfies, suggestive tease ──────────────────
  { id: "lk_mirror_selfie",     rarity: "COMMON",    icon: "🤳", title: "Tight & Teasing",               description: "Skin-tight outfit, one hand on her hip — she wants you staring." },
  { id: "lk_gym_snap",          rarity: "COMMON",    icon: "💪", title: "Dripping Wet Workout",           description: "Soaked sports bra clinging to every curve. She's barely breathing." },
  { id: "lk_morning_bed",       rarity: "COMMON",    icon: "🛏️", title: "Bedhead & Bare Skin",            description: "Sheet slipping off, nipple almost showing. She just woke up like this." },
  { id: "lk_pouty_lips",        rarity: "COMMON",    icon: "💋", title: "Kiss Me Lower",                 description: "Lips parted, tongue barely visible. She's thinking about you." },
  { id: "lk_sundress",          rarity: "COMMON",    icon: "👗", title: "No Panties Sundress",            description: "Sun behind her, everything visible through the fabric. She knew." },
  { id: "lk_car_selfie",        rarity: "COMMON",    icon: "🚗", title: "Deep Cleavage Ride",             description: "Top pulled so low the seatbelt does the rest. Eyes on you." },
  { id: "lk_beach_walk",        rarity: "COMMON",    icon: "🏖️", title: "Ass Out at the Beach",           description: "Walking away, thong bikini leaving nothing to imagine." },
  { id: "lk_night_out",         rarity: "COMMON",    icon: "🌃", title: "Dress Barely On",                description: "So tight you can see every curve, slit up to her hip." },
  { id: "lk_oversized_tee",     rarity: "COMMON",    icon: "👕", title: "Braless in Your Shirt",          description: "Your oversized tee, nothing underneath. Nipples pressing through." },
  { id: "lk_pool_side",         rarity: "COMMON",    icon: "🏊", title: "Wet Bikini Cling",               description: "Micro bikini soaked through, every detail showing." },
  { id: "lk_back_glance",       rarity: "COMMON",    icon: "👀", title: "Bend Over & Look Back",          description: "She bent down and looked back at you. That's an invitation." },
  { id: "lk_yoga_pose",         rarity: "COMMON",    icon: "🧘", title: "Legs Wide Open Stretch",         description: "Full splits in leggings so thin they hide nothing." },
  { id: "lk_wet_hair",          rarity: "COMMON",    icon: "💧", title: "Towel Dropping",                 description: "Just out of the shower, towel about to fall. She's not stopping it." },
  { id: "lk_couch_lounge",      rarity: "COMMON",    icon: "🛋️", title: "Legs Spread on the Couch",       description: "Tiny bralette, thighs apart, that look in her eyes." },
  { id: "lk_sunset_silhouette", rarity: "COMMON",    icon: "🌅", title: "Naked Silhouette",               description: "Golden hour backlighting her naked body. Every curve on display." },
  { id: "lk_coffee_morning",    rarity: "COMMON",    icon: "☕", title: "Robe Falling Open",              description: "Silk robe undone, one breast exposed. 'Good morning, daddy.'" },
  { id: "lk_fitting_room",      rarity: "COMMON",    icon: "🪞", title: "Topless Fitting Room",           description: "Fitting room selfie, top off, one hand barely covering her chest." },
  { id: "lk_tongue_out",        rarity: "COMMON",    icon: "👅", title: "On Her Knees, Tongue Out",       description: "Looking up at you, tongue out, on her knees. She knows what's next." },

  // ── UNCOMMON (12) — lingerie, almost nude ───────────────────────────
  { id: "lk_lace_lingerie",     rarity: "UNCOMMON",  icon: "🖤", title: "See-Through Black Lace",         description: "Nipples visible through delicate black lace. She wore this for you." },
  { id: "lk_bodysuit",          rarity: "UNCOMMON",  icon: "✨", title: "Naked Under Mesh",               description: "Sheer mesh bodysuit, no bra, no panties. Skin everywhere." },
  { id: "lk_stockings",         rarity: "UNCOMMON",  icon: "🦵", title: "Stockings & Nothing Else",       description: "Thigh-highs, garter belt, bare ass. Waiting for you on the bed." },
  { id: "lk_braless",           rarity: "UNCOMMON",  icon: "🧊", title: "Hard Nipples Showing",           description: "White tank, freezing cold, nipples poking through. She loves it." },
  { id: "lk_bubble_bath",       rarity: "UNCOMMON",  icon: "🛁", title: "Bubbles Can't Hide Her",         description: "Bath bubbles fading, breasts and thighs rising above the water." },
  { id: "lk_red_lingerie",      rarity: "UNCOMMON",  icon: "❤️", title: "Red Lace Push-Up",               description: "Breasts pushed up and almost spilling out. She's daring you to pull it off." },
  { id: "lk_silk_robe",         rarity: "UNCOMMON",  icon: "🥂", title: "Robe Open, Everything Out",      description: "Silk robe wide open, nothing underneath. Wine glass in hand." },
  { id: "lk_thong_peek",        rarity: "UNCOMMON",  icon: "🍑", title: "Jeans Down, Thong Showing",      description: "Pants pulled halfway down, tiny thong barely covering anything." },
  { id: "lk_bikini_string",     rarity: "UNCOMMON",  icon: "👙", title: "Micro Bikini Malfunction",       description: "String bikini slipping off — one tug and she's fully nude." },
  { id: "lk_crop_underboob",    rarity: "UNCOMMON",  icon: "🔥", title: "Full Underboob Exposed",         description: "Crop top so short it only covers her nipples. Barely." },
  { id: "lk_mirror_lingerie",   rarity: "UNCOMMON",  icon: "🪞", title: "Full Body Mirror Strip",         description: "Standing in front of a mirror in see-through everything. All visible." },
  { id: "lk_corset",            rarity: "UNCOMMON",  icon: "⏳", title: "Corset Overflowing",              description: "Laced so tight her breasts are spilling out the top. Gasping for air." },

  // ── RARE (10) — topless, nearly full nude ──────────────────────────
  { id: "lk_topless_back",      rarity: "RARE",      icon: "🔓", title: "Topless Over-the-Shoulder",      description: "No top, bare back, side of her breast exposed. Looking right at you." },
  { id: "lk_hand_bra",          rarity: "RARE",      icon: "🤲", title: "Hands Can't Cover It All",       description: "Naked, hands squeezing her breasts. Fingers slipping. One more second..." },
  { id: "lk_see_through",       rarity: "RARE",      icon: "👁️", title: "Nipples Through Sheer Top",      description: "Completely transparent top, hard nipples on full display." },
  { id: "lk_shower_glass",      rarity: "RARE",      icon: "🚿", title: "Naked Behind Glass",             description: "Fully nude in the shower, pressed against the glass. Water dripping down." },
  { id: "lk_body_oil",          rarity: "RARE",      icon: "💦", title: "Oiled Naked Body",               description: "Glistening from head to toe, hands sliding over her bare skin." },
  { id: "lk_bed_sheets",        rarity: "RARE",      icon: "🛏️", title: "Topless in Bed, Legs Apart",     description: "Sheet at her waist, bare breasts, legs spreading under the covers." },
  { id: "lk_whipped_cream",     rarity: "RARE",      icon: "🍰", title: "Cream on Her Nipples",           description: "Whipped cream covering just the tips. She wants you to lick it off." },
  { id: "lk_skinny_dip",        rarity: "RARE",      icon: "🌙", title: "Naked Midnight Swim",            description: "Fully nude in the moonlit water, wet skin glowing." },
  { id: "lk_painting_nude",     rarity: "RARE",      icon: "🎨", title: "Full Nude Art Pose",              description: "Lying naked on a chaise, legs parted, painted in nothing but light." },
  { id: "lk_wet_tshirt",        rarity: "RARE",      icon: "💧", title: "Soaked & See Everything",         description: "White shirt drenched through, every inch of her body visible. Might as well be naked." },

  // ── EPIC (6) — full frontal, explicit positions ────────────────────
  { id: "lk_full_nude_mirror",  rarity: "EPIC",      icon: "📱", title: "Full Frontal Mirror Nude",        description: "Standing naked, phone in hand, legs slightly apart. She sent this to only you." },
  { id: "lk_bath_nude",         rarity: "EPIC",      icon: "🛁", title: "Naked in Clear Water",            description: "Crystal clear bath, every inch of her body exposed below the surface." },
  { id: "lk_bed_spread",        rarity: "EPIC",      icon: "🔥", title: "Legs Spread, Waiting",            description: "Lying naked on the bed, legs wide open, biting her lip. 'Come here.'" },
  { id: "lk_balcony_nude",      rarity: "EPIC",      icon: "🌆", title: "Nude on the Balcony",             description: "Fully naked outdoors, leaning on the railing, ass facing the city." },
  { id: "lk_oil_massage",       rarity: "EPIC",      icon: "🫦", title: "Oiled Up on All Fours",           description: "Face down, ass up, body dripping in oil. She's begging for your hands." },
  { id: "lk_selfie_nude",       rarity: "EPIC",      icon: "🤳", title: "Explicit Close-Up",               description: "The most intimate angle. So close you can feel the heat." },

  // ── LEGENDARY (4) — the most forbidden, sex tape tier ──────────────
  { id: "lk_private_video",     rarity: "LEGENDARY", icon: "🎬", title: "Sex Tape Freeze Frame",           description: "A still from the video she swore was deleted. Now it's yours." },
  { id: "lk_all_fours",         rarity: "LEGENDARY", icon: "🍑", title: "Face Down, Ass Up",               description: "On all fours, back arched, looking back at the camera with that look." },
  { id: "lk_spread_legs",       rarity: "LEGENDARY", icon: "🦋", title: "Spread Wide Open",                description: "Nothing hidden. Nothing covered. Legs spread, everything exposed for you." },
  { id: "lk_ultimate",          rarity: "LEGENDARY", icon: "👑", title: "The Forbidden Tape",              description: "The one that was never supposed to exist. Her most explicit moment, captured forever. All yours." },
]

const LEAKS_BY_RARITY: Record<LeakRarity, LeakItem[]> = { COMMON: [], UNCOMMON: [], RARE: [], EPIC: [], LEGENDARY: [] }
for (const l of LEAKS) {
  LEAKS_BY_RARITY[l.rarity].push(l)
}

// ═══════════════════════════════════════════════════════════════════════════════
// LEAK SLOT BOXES
// ═══════════════════════════════════════════════════════════════════════════════

const LEAK_BOXES = [
  {
    id: "peek",
    name: "Quick Peek",
    emoji: "👀",
    description: "A teasing glimpse — selfies, lingerie, suggestive poses.",
    price: "€1.99",
    priceNum: 1.99,
    color: "#94a3b8",
    weights: { COMMON: 0.65, UNCOMMON: 0.25, RARE: 0.08, EPIC: 0.02, LEGENDARY: 0.0 } as Record<LeakRarity, number>,
  },
  {
    id: "private",
    name: "Private Collection",
    emoji: "🔥",
    description: "The photos she only sends to someone special. Things get real.",
    price: "€4.99",
    priceNum: 4.99,
    color: "#c084fc",
    weights: { COMMON: 0.25, UNCOMMON: 0.35, RARE: 0.25, EPIC: 0.12, LEGENDARY: 0.03 } as Record<LeakRarity, number>,
  },
  {
    id: "uncensored",
    name: "Fully Uncensored",
    emoji: "🍑",
    description: "No filters. No censorship. The most explicit content unlocked.",
    price: "€9.99",
    priceNum: 9.99,
    color: "#fbbf24",
    weights: { COMMON: 0.0, UNCOMMON: 0.10, RARE: 0.30, EPIC: 0.40, LEGENDARY: 0.20 } as Record<LeakRarity, number>,
  },
]

// ═══════════════════════════════════════════════════════════════════════════════
// SLOT MACHINE
// ═══════════════════════════════════════════════════════════════════════════════

const CELL_W = 100
const WINNER_IDX = 55
const TOTAL_REEL = 70
const SPIN_MS = 5500

function buildLeakReel(winner: LeakItem) {
  const items: LeakItem[] = []
  for (let i = 0; i < TOTAL_REEL; i++) {
    if (i === WINNER_IDX) {
      items.push(winner)
    } else {
      items.push(LEAKS[Math.floor(Math.random() * LEAKS.length)])
    }
  }
  return items
}

function LeakSlotOverlay({
  winner,
  imageUrl,
  onClose,
}: {
  winner: LeakItem
  imageUrl: string | null
  onClose: () => void
}) {
  const [phase, setPhase] = useState<"spinning" | "revealed">("spinning")
  const reelRef = useRef<HTMLDivElement>(null)
  const rafRef = useRef<number>(0)
  const rCfg = RARITY_CONFIG[winner.rarity]

  const reel = useRef(buildLeakReel(winner)).current
  const targetOffset = WINNER_IDX * CELL_W

  useEffect(() => {
    const node = reelRef.current
    if (!node) return
    const start = performance.now()

    function easeOut(t: number) { return 1 - Math.pow(1 - t, 4.2) }

    function animate(now: number) {
      const p = Math.min((now - start) / SPIN_MS, 1)
      node!.style.transform = `translateX(-${easeOut(p) * targetOffset}px)`
      if (p < 1) {
        rafRef.current = requestAnimationFrame(animate)
      } else {
        setTimeout(() => setPhase("revealed"), 400)
      }
    }
    rafRef.current = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(rafRef.current)
  }, [targetOffset])

  return (
    <div className="fixed inset-0 z-[99999] flex items-center justify-center bg-black/93 backdrop-blur-xl">
      {phase === "revealed" && (
        <button onClick={onClose} className="absolute right-6 top-6 z-10 flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white/60 hover:bg-white/20 transition-all">
          <X className="h-5 w-5" />
        </button>
      )}

      <div className="flex flex-col items-center gap-8 w-full max-w-lg px-4">
        <p className="text-center text-sm font-bold text-cyan-300/50 uppercase tracking-[0.2em]">
          {phase === "revealed" ? "Leaked..." : "Spinning..."}
        </p>

        {/* Slot machine */}
        <div className="w-full relative">
          <div className="absolute -inset-1.5 rounded-3xl bg-gradient-to-r from-cyan-500/20 via-purple-500/20 to-pink-500/20 blur-sm" />
          <div className="relative rounded-2xl border-2 border-cyan-500/15 bg-[#060a10] overflow-hidden shadow-2xl"
               style={{ boxShadow: "0 0 60px 10px rgba(56,189,248,0.08), inset 0 0 30px rgba(0,0,0,0.5)" }}>

            <div className="absolute left-1/2 top-0 bottom-0 z-20 pointer-events-none" style={{ width: CELL_W + 8, transform: "translateX(-50%)" }}>
              <div className="absolute inset-x-0 top-0 h-1.5 rounded-b bg-gradient-to-r from-cyan-400/0 via-cyan-400 to-cyan-400/0" />
              <div className="absolute inset-x-0 bottom-0 h-1.5 rounded-t bg-gradient-to-r from-cyan-400/0 via-cyan-400 to-cyan-400/0" />
              <div className="absolute inset-0 border-2 border-cyan-400/50 rounded-xl" />
              <div className="absolute inset-0 bg-cyan-400/[0.04]" />
            </div>

            <div className="absolute inset-y-0 left-0 w-16 z-10 bg-gradient-to-r from-[#060a10] to-transparent pointer-events-none" />
            <div className="absolute inset-y-0 right-0 w-16 z-10 bg-gradient-to-l from-[#060a10] to-transparent pointer-events-none" />

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

        {/* Reveal */}
        {phase === "revealed" ? (
          <div className="flex flex-col items-center gap-5 animate-in fade-in slide-in-from-bottom-6 duration-700">
            <span className="px-5 py-1.5 rounded-full text-xs font-black uppercase tracking-[0.15em] border"
              style={{ color: rCfg.color, borderColor: `${rCfg.color}40`, backgroundColor: `${rCfg.color}12` }}>
              {rCfg.label} Leak
            </span>

            {imageUrl && (
              <div className="w-48 aspect-[3/4] rounded-xl overflow-hidden border-2 shadow-2xl"
                style={{ borderColor: `${rCfg.color}50`, boxShadow: `0 0 40px 10px ${rCfg.glow}` }}>
                <img src={imageUrl} alt={winner.title} className="h-full w-full object-cover" />
              </div>
            )}

            <div className="text-center">
              <div className="flex items-center justify-center gap-2 mb-1">
                <span className="text-3xl">{winner.icon}</span>
                <h2 className="text-2xl font-extrabold text-white">{winner.title}</h2>
              </div>
              <p className="text-sm text-white/40 mt-1 max-w-xs">{winner.description}</p>
            </div>

            <div className="flex items-center gap-2 rounded-full bg-cyan-500/15 px-4 py-2 border border-cyan-500/20">
              <Eye className="h-4 w-4 text-cyan-400" />
              <span className="text-xs font-bold text-cyan-300">Added to your private collection</span>
            </div>

            <button onClick={onClose}
              className="rounded-full bg-gradient-to-r from-cyan-500 to-purple-500 px-10 py-3.5 text-sm font-bold text-white shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 hover:scale-105 transition-all active:scale-95">
              Collect
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <div className="h-5 w-5 rounded-full border-2 border-cyan-400/30 border-t-cyan-400 animate-spin" />
            <span className="text-base text-cyan-300/40 font-semibold">Spinning...</span>
          </div>
        )}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// FLOATING BACKGROUND
// ═══════════════════════════════════════════════════════════════════════════════

function FloatingEyes() {
  const items = Array.from({ length: 25 }, (_, i) => ({
    left: `${(i * 41 + 7) % 100}%`,
    top: `${(i * 59 + 13) % 100}%`,
    size: 8 + (i % 4) * 3,
    opacity: 0.015 + (i % 3) * 0.008,
    delay: `${(i * 1.7) % 9}s`,
    duration: `${7 + (i % 4) * 2.5}s`,
    icon: i % 3,
  }))
  const icons = [Eye, Camera, Heart]
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {items.map((h, i) => {
        const Icon = icons[h.icon]
        return (
          <Icon
            key={i}
            className="absolute animate-pulse text-cyan-400"
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
// MAIN PANEL
// ═══════════════════════════════════════════════════════════════════════════════

interface LeaksPanelProps {
  onClose: () => void
}

export default function LeaksPanel({ onClose }: LeaksPanelProps) {
  const girlfriendId = useAppStore((s) => s.currentGirlfriendId)
  const queryClient = useQueryClient()
  const [unlocked, setUnlocked] = useState<Set<string>>(new Set())
  const [selectedLeak, setSelectedLeak] = useState<LeakItem | null>(null)
  const [activeTab, setActiveTab] = useState<"spin" | "collection">("spin")
  const [filter, setFilter] = useState<LeakRarity | "ALL">("ALL")
  const [purchaseError, setPurchaseError] = useState<string | null>(null)
  const [slotResult, setSlotResult] = useState<{ winner: LeakItem; imageUrl: string | null } | null>(null)

  const { data: apiData } = useQuery({
    queryKey: ["leaksCollection", girlfriendId],
    queryFn: () => getLeaksCollection(girlfriendId || undefined),
    staleTime: 30_000,
  })

  useEffect(() => {
    if (!apiData?.unlocked) return
    const ids = new Set<string>(Object.keys(apiData.unlocked))
    if (ids.size > 0) {
      setUnlocked(prev => {
        const merged = new Set([...prev, ...ids])
        return merged.size !== prev.size ? merged : prev
      })
    }
  }, [apiData])

  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => { document.body.style.overflow = prev }
  }, [])

  const totalUnlocked = LEAKS.filter(l => unlocked.has(l.id)).length

  const filteredLeaks = filter === "ALL" ? LEAKS : LEAKS.filter(l => l.rarity === filter)

  const getImageUrl = (leak: LeakItem) => {
    if (!apiData?.unlocked?.[leak.id]) return null
    return apiData.unlocked[leak.id] || `https://picsum.photos/seed/${leak.id}/400/600`
  }

  const [paymentBoxId, setPaymentBoxId] = useState<string | null>(null)
  const purchasing = paymentBoxId

  const handleSpin = (boxId: string) => {
    setPurchaseError(null)
    setPaymentBoxId(boxId)
  }

  const handlePaymentSuccess = useCallback((data?: Record<string, any>) => {
    setPaymentBoxId(null)
    const leakId = data?.leak_id as string | undefined
    const imageUrl = data?.image_url as string | undefined
    if (leakId) {
      const winner = LEAKS.find(l => l.id === leakId)
      if (winner) {
        setSlotResult({ winner, imageUrl: imageUrl || null })
        setUnlocked(prev => new Set([...prev, leakId]))
        queryClient.invalidateQueries({ queryKey: ["leaksCollection"] })
      }
    }
  }, [queryClient])

  return (
    <div className="fixed inset-0 z-[9999] flex flex-col" style={{ backgroundColor: "#06080c" }}>
      <FloatingEyes />

      {/* Top bar */}
      <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between px-4 py-3 backdrop-blur-xl bg-black/50 border-b border-cyan-500/10">
        <button onClick={onClose} className="flex items-center gap-2 rounded-full bg-black/60 pl-3 pr-4 py-2 text-white/70 border border-white/10 transition-all hover:bg-black/80 hover:text-white">
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm font-medium">Back</span>
        </button>

        <div className="flex rounded-full bg-black/60 border border-cyan-500/15 p-0.5">
          <button
            onClick={() => setActiveTab("spin")}
            className={cn("px-4 py-1.5 rounded-full text-xs font-bold transition-all",
              activeTab === "spin" ? "bg-cyan-500/20 text-cyan-300" : "text-white/40 hover:text-white/60")}
          >
            🎰 Spin
          </button>
          <button
            onClick={() => setActiveTab("collection")}
            className={cn("px-4 py-1.5 rounded-full text-xs font-bold transition-all",
              activeTab === "collection" ? "bg-purple-500/20 text-purple-300" : "text-white/40 hover:text-white/60")}
          >
            📸 Collection
          </button>
        </div>

        <div className="flex items-center gap-2 rounded-full bg-black/60 px-4 py-2 border border-cyan-500/15">
          <Camera className="h-3.5 w-3.5 text-cyan-400" />
          <span className="text-xs font-bold text-white/80">{totalUnlocked}/{LEAKS.length}</span>
        </div>
      </div>

      {activeTab === "spin" ? (
        /* ── SPIN TAB ── */
        <div className="flex-1 overflow-y-auto pt-16 pb-12 px-4 md:px-8">
          <div className="mx-auto max-w-lg">
            {/* Hero */}
            <div className="text-center pt-6 pb-8">
              <div className="flex items-center justify-center gap-2 mb-3">
                <Eye className="h-5 w-5 text-cyan-400/60 animate-pulse" style={{ animationDuration: "3s" }} />
                <Flame className="h-7 w-7 text-pink-400/50 animate-pulse" style={{ animationDuration: "4s", animationDelay: "0.5s" }} />
                <Eye className="h-5 w-5 text-cyan-400/60 animate-pulse" style={{ animationDuration: "3.5s", animationDelay: "1s" }} />
              </div>
              <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white/90">
                Her Private Leaks
              </h1>
              <p className="mt-2 text-sm text-white/35 max-w-md mx-auto leading-relaxed">
                Spin to unlock her most private photos. The higher the tier, the more explicit it gets. Every spin reveals something she never wanted anyone to see.
              </p>
            </div>

            {/* Error */}
            {purchaseError && (
              <div className="mb-5 rounded-xl bg-red-500/10 border border-red-500/20 p-3 text-center">
                <p className="text-sm text-red-300">{purchaseError}</p>
                <button onClick={() => setPurchaseError(null)} className="mt-2 text-xs text-red-400/60 hover:text-red-400 transition-colors">Dismiss</button>
              </div>
            )}

            {/* Slot boxes */}
            <div className="space-y-5">
              {LEAK_BOXES.map((box) => {
                const availableCount = LEAKS.filter(l => {
                  if (unlocked.has(l.id)) return false
                  return (box.weights[l.rarity] ?? 0) > 0
                }).length
                const soldOut = availableCount === 0

                return (
                  <div key={box.id} className={cn("relative rounded-2xl border overflow-hidden transition-all", soldOut && "opacity-40")}
                    style={{ borderColor: `${box.color}25`, boxShadow: `0 0 40px 8px ${box.color}10, inset 0 1px 0 rgba(255,255,255,0.03)` }}>
                    <div className="absolute inset-0" style={{ background: `linear-gradient(135deg, ${box.color}12, transparent 60%)` }} />

                    <div className="absolute inset-0 overflow-hidden pointer-events-none">
                      <div className="absolute -left-full top-0 h-full w-1/2" style={{ background: `linear-gradient(90deg, transparent, ${box.color}08, transparent)`, animation: "shimmerSweep 3s ease-in-out infinite" }} />
                    </div>

                    <div className="relative z-10 p-5">
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <div className="flex h-14 w-14 items-center justify-center rounded-xl" style={{ backgroundColor: `${box.color}15`, boxShadow: `0 0 20px 4px ${box.color}15` }}>
                            <span className="text-2xl">{box.emoji}</span>
                          </div>
                          <div>
                            <h3 className="text-lg font-bold" style={{ color: box.color }}>{box.name}</h3>
                            <p className="text-xs text-white/30 mt-0.5 max-w-[220px]">{box.description}</p>
                          </div>
                        </div>
                        <span className="text-lg font-black text-emerald-400/80">{box.price}</span>
                      </div>

                      {/* Odds bar */}
                      <div className="flex h-2 w-full overflow-hidden rounded-full bg-black/30 mb-2">
                        {RARITY_ORDER.filter(r => (box.weights[r] ?? 0) > 0).map(r => (
                          <div key={r} className="h-full" style={{ width: `${(box.weights[r] ?? 0) * 100}%`, backgroundColor: RARITY_CONFIG[r].color, opacity: 0.7 }} />
                        ))}
                      </div>
                      <div className="flex flex-wrap gap-x-3 gap-y-1 mb-4">
                        {RARITY_ORDER.filter(r => (box.weights[r] ?? 0) > 0).map(r => (
                          <div key={r} className="flex items-center gap-1">
                            <div className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: RARITY_CONFIG[r].color }} />
                            <span className="text-[9px] font-bold" style={{ color: RARITY_CONFIG[r].color }}>{RARITY_CONFIG[r].label}</span>
                            <span className="text-[9px] text-white/25">{((box.weights[r] ?? 0) * 100).toFixed(0)}%</span>
                          </div>
                        ))}
                      </div>

                      <button
                        onClick={() => handleSpin(box.id)}
                        disabled={soldOut || purchasing === box.id || purchasing !== null}
                        className={cn("w-full rounded-xl py-3.5 text-sm font-bold transition-all flex items-center justify-center gap-2",
                          soldOut ? "bg-white/[0.04] text-white/20 cursor-not-allowed"
                            : purchasing === box.id ? "bg-gradient-to-r from-cyan-600/60 to-purple-600/60 text-white/60 cursor-wait"
                            : "bg-gradient-to-r from-cyan-600 to-purple-600 text-white shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30 hover:scale-[1.02] active:scale-[0.98]")}
                      >
                        {soldOut ? (
                          <><Lock className="h-4 w-4" /> All collected!</>
                        ) : purchasing === box.id ? (
                          <><div className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" /> Processing...</>
                        ) : (
                          <><Eye className="h-4 w-4" /> Spin &amp; Leak<ChevronRight className="h-4 w-4" /></>
                        )}
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* How it works */}
            <div className="mt-10 space-y-3 pb-8">
              <h3 className="text-center text-sm font-bold text-white/30 uppercase tracking-wider">How it works</h3>
              <div className="space-y-2">
                {[
                  { icon: Eye, text: "Every spin reveals a private photo she never wanted leaked. Higher tiers unlock the most explicit content." },
                  { icon: Flame, text: "Fully Uncensored gives you 60% chance at Epic or Legendary — full nudes, private videos, the stuff that breaks the internet." },
                  { icon: Sparkles, text: "No duplicates. Every spin is something new. Collect all 50 to own her complete private gallery." },
                ].map((item, i) => (
                  <div key={i} className="flex items-start gap-3 rounded-lg bg-white/[0.02] p-3 border border-cyan-500/[0.06]">
                    <item.icon className="h-4 w-4 shrink-0 text-cyan-400/50 mt-0.5" />
                    <p className="text-xs text-white/30 leading-relaxed">{item.text}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* ── COLLECTION TAB ── */
        <div className="flex-1 overflow-y-auto pt-16 pb-8 px-4 md:px-8">
          <div className="mx-auto max-w-2xl">
            {/* Rarity filter */}
            <div className="flex items-center justify-center gap-1.5 mb-5 mt-4 flex-wrap">
              <button
                onClick={() => setFilter("ALL")}
                className={cn("px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wider border transition-all",
                  filter === "ALL" ? "bg-white/10 text-white border-white/20" : "bg-white/[0.03] text-white/30 border-white/[0.06] hover:text-white/50")}
              >
                All ({LEAKS.length})
              </button>
              {RARITY_ORDER.map(r => {
                const cfg = RARITY_CONFIG[r]
                const count = LEAKS_BY_RARITY[r].length
                const unlockedCount = LEAKS_BY_RARITY[r].filter(l => unlocked.has(l.id)).length
                return (
                  <button
                    key={r}
                    onClick={() => setFilter(r)}
                    className={cn("px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wider border transition-all",
                      filter === r ? cfg.badge : "bg-white/[0.03] text-white/30 border-white/[0.06] hover:text-white/50")}
                  >
                    {cfg.label} ({unlockedCount}/{count})
                  </button>
                )
              })}
            </div>

            {/* Progress bar */}
            <div className="mb-5">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] font-bold uppercase tracking-wider text-white/25">Collection Progress</span>
                <span className="text-[10px] font-bold text-white/40">{totalUnlocked} / {LEAKS.length}</span>
              </div>
              <div className="h-2 w-full rounded-full bg-white/[0.05] overflow-hidden flex">
                {RARITY_ORDER.map(r => {
                  const count = LEAKS_BY_RARITY[r].filter(l => unlocked.has(l.id)).length
                  if (count === 0) return null
                  return (
                    <div key={r} className="h-full" style={{ width: `${(count / LEAKS.length) * 100}%`, backgroundColor: RARITY_CONFIG[r].color, opacity: 0.8 }} />
                  )
                })}
              </div>
            </div>

            {/* Grid */}
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2.5">
              {filteredLeaks.map((leak) => {
                const isUnlocked = unlocked.has(leak.id)
                const cfg = RARITY_CONFIG[leak.rarity]
                const imageUrl = getImageUrl(leak)

                return (
                  <button
                    key={leak.id}
                    onClick={() => isUnlocked && setSelectedLeak(leak)}
                    className={cn(
                      "group relative aspect-[3/4] rounded-xl overflow-hidden border transition-all duration-300",
                      isUnlocked ? "cursor-pointer hover:scale-[1.03] hover:z-10 active:scale-[0.98]" : "cursor-default",
                    )}
                    style={{
                      borderColor: isUnlocked ? `${cfg.color}40` : "rgba(255,255,255,0.04)",
                      boxShadow: isUnlocked ? `0 0 20px 3px ${cfg.glow}` : "none",
                    }}
                  >
                    {isUnlocked && imageUrl ? (
                      <>
                        <img src={imageUrl} alt={leak.title} className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110" />
                        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
                      </>
                    ) : (
                      <div className={cn("h-full w-full bg-gradient-to-br flex flex-col items-center justify-center gap-2", cfg.lockedBg)}>
                        <Lock className="h-5 w-5 text-white/10" />
                        <div className="h-1 w-6 rounded-full" style={{ backgroundColor: `${cfg.color}20` }} />
                      </div>
                    )}

                    <div className="absolute bottom-0 left-0 right-0 p-2">
                      {isUnlocked ? (
                        <div>
                          <p className="text-[10px] font-bold text-white truncate">{leak.title}</p>
                          <span className="text-[8px] font-bold uppercase tracking-wider" style={{ color: cfg.color }}>{cfg.label}</span>
                        </div>
                      ) : (
                        <div className="flex flex-col items-center gap-1">
                          <span className="text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border"
                            style={{ color: `${cfg.color}60`, borderColor: `${cfg.color}20`, backgroundColor: `${cfg.color}08` }}>
                            {cfg.label}
                          </span>
                          <p className="text-[8px] text-white/20 truncate w-full text-center">{leak.title}</p>
                        </div>
                      )}
                    </div>

                    <div className="absolute top-0 left-0 right-0 h-[2px]" style={{ backgroundColor: isUnlocked ? cfg.color : `${cfg.color}20` }} />
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* Slot overlay */}
      {slotResult && (
        <LeakSlotOverlay
          winner={slotResult.winner}
          imageUrl={slotResult.imageUrl}
          onClose={() => setSlotResult(null)}
        />
      )}

      {/* Fullscreen image viewer */}
      {selectedLeak && (
        <div className="fixed inset-0 z-[99999] flex items-center justify-center bg-black/95 backdrop-blur-xl" onClick={() => setSelectedLeak(null)}>
          <button onClick={() => setSelectedLeak(null)} className="absolute right-4 top-4 z-10 flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white/60 hover:bg-white/20 transition-all">
            <X className="h-5 w-5" />
          </button>
          <div className="flex flex-col items-center gap-4 max-w-md w-full px-4" onClick={e => e.stopPropagation()}>
            <div className="relative w-full aspect-[3/4] rounded-2xl overflow-hidden border-2"
              style={{ borderColor: `${RARITY_CONFIG[selectedLeak.rarity].color}40` }}>
              <img src={getImageUrl(selectedLeak) || ""} alt={selectedLeak.title} className="h-full w-full object-cover" />
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent" />
              <div className="absolute bottom-0 left-0 right-0 p-4">
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-full border mb-2 inline-block"
                  style={{ color: RARITY_CONFIG[selectedLeak.rarity].color, borderColor: `${RARITY_CONFIG[selectedLeak.rarity].color}40`, backgroundColor: `${RARITY_CONFIG[selectedLeak.rarity].color}15` }}>
                  {RARITY_CONFIG[selectedLeak.rarity].label}
                </span>
                <h2 className="text-xl font-extrabold text-white">{selectedLeak.title}</h2>
                <p className="text-sm text-white/50 mt-1">{selectedLeak.description}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Unified payment panel for leaks */}
      {paymentBoxId && (
        <UnifiedPaymentPanel
          open={!!paymentBoxId}
          payload={{ type: "leaks_spin", tier: paymentBoxId, girlfriend_id: girlfriendId || undefined }}
          title="Spin & Leak"
          description="Unlock a private photo with one spin."
          amountLabel={LEAK_BOXES.find(b => b.id === paymentBoxId)?.price ?? "€0.00"}
          onSuccess={handlePaymentSuccess}
          onClose={() => setPaymentBoxId(null)}
          autoCharge
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
