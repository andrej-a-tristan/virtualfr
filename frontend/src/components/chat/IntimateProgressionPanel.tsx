import { useState, useEffect, useCallback, useRef } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { getIntimacyAchievements, purchaseIntimateBox } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import type { IntimacyAchievementItem } from "@/lib/api/types"
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
  Crown,
  Gift,
} from "lucide-react"

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

type IntimateRarity = "COMMON" | "UNCOMMON" | "RARE" | "EPIC" | "LEGENDARY"

interface IntimateAchievement {
  id: string
  tier: number       // 0..6
  title: string
  subtitle: string
  rarity: IntimateRarity
  icon: string       // emoji icon for slot machine
  scene: string      // photo generation prompt (increasingly explicit per tier)
}

interface TierDef {
  title: string
  subtitle: string
  rarity: IntimateRarity
  color: [number, number, number]
  accentClass: string
}

// ═══════════════════════════════════════════════════════════════════════════════
// 7 TIERS — each tier maps to ONE rarity level
// ═══════════════════════════════════════════════════════════════════════════════

const TIERS: TierDef[] = [
  { title: "Flirting & Tension",    subtitle: "The spark before the fire.",         rarity: "COMMON",    color: [244, 114, 182], accentClass: "text-pink-400" },
  { title: "First Touch",           subtitle: "Electricity at your fingertips.",    rarity: "UNCOMMON",  color: [251, 113, 133], accentClass: "text-rose-400" },
  { title: "Heating Up",            subtitle: "Boundaries blur, desire builds.",    rarity: "RARE",      color: [239, 68, 68],   accentClass: "text-red-400" },
  { title: "Undressed",             subtitle: "Nothing left to hide.",              rarity: "EPIC",      color: [220, 38, 38],   accentClass: "text-red-500" },
  { title: "Full Intimacy",         subtitle: "Two become one.",                    rarity: "EPIC",      color: [190, 18, 60],   accentClass: "text-rose-600" },
  { title: "Deep Exploration",      subtitle: "No limits, no shame.",              rarity: "LEGENDARY", color: [157, 23, 77],   accentClass: "text-pink-700" },
  { title: "Ultimate Connection",   subtitle: "Beyond physical — total surrender.", rarity: "LEGENDARY", color: [131, 24, 67],   accentClass: "text-pink-800" },
]

const TIER_COLORS = TIERS.map(t => t.color)

// ═══════════════════════════════════════════════════════════════════════════════
// 50 INTIMATE ACHIEVEMENTS — rarity matches tier, each has icon + scene
// Tier 0 = ALL COMMON, Tier 1 = ALL UNCOMMON, Tier 2 = ALL RARE,
// Tier 3-4 = ALL EPIC, Tier 5-6 = ALL LEGENDARY
// Scene prompts get progressively more explicit per tier.
// ═══════════════════════════════════════════════════════════════════════════════

const INTIMATE_ACHIEVEMENTS: IntimateAchievement[] = [
  // ── Tier 0: Flirting & Tension — ALL COMMON ──────────────────────────
  { id: "i_flirty_banter",     tier: 0, title: "Flirty Banter",       subtitle: "She started teasing you.",                icon: "😏", rarity: "COMMON",    scene: "Gorgeous woman biting her lower lip, mischievous grin, leaning on a kitchen counter in a low-cut top, warm golden lighting" },
  { id: "i_lingering_look",    tier: 0, title: "Lingering Look",      subtitle: "Her eyes stayed on you too long.",        icon: "👀", rarity: "COMMON",    scene: "Close-up of beautiful woman with intense seductive eyes gazing at camera, soft candlelight, slightly parted lips" },
  { id: "i_playful_wink",      tier: 0, title: "Playful Wink",        subtitle: "A wink that said everything.",            icon: "😉", rarity: "COMMON",    scene: "Stunning woman mid-wink, playful smirk, golden hour light, one strap falling off shoulder" },
  { id: "i_suggestive_pose",   tier: 0, title: "Suggestive Pose",     subtitle: "She knew exactly how to stand.",          icon: "💃", rarity: "COMMON",    scene: "Woman leaning against doorframe in tight fitted dress, hand on hip, curves accentuated, dim bedroom lighting" },
  { id: "i_tension_rising",    tier: 0, title: "Tension Rising",      subtitle: "The air between you thickened.",          icon: "🔥", rarity: "COMMON",    scene: "Woman standing very close to camera, faces inches apart, heavy-lidded eyes, warm dim lighting, tension palpable" },
  { id: "i_bedroom_eyes",      tier: 0, title: "Bedroom Eyes",        subtitle: "She gave you that look.",                 icon: "🛏️", rarity: "COMMON",    scene: "Beautiful woman lying on bed, chin on hands, seductive heavy-lidded gaze at camera, silk sheets, lamplight" },
  { id: "i_goodnight_tease",   tier: 0, title: "Goodnight Tease",     subtitle: "She said goodnight her own way.",         icon: "🌙", rarity: "COMMON",    scene: "Woman in oversized sheer shirt on bed, looking over shoulder at camera, long legs visible, soft moonlight" },

  // ── Tier 1: First Touch — ALL UNCOMMON ────────────────────────────────
  { id: "i_hand_holding",      tier: 1, title: "Hand Holding",        subtitle: "Fingers intertwined.",                    icon: "🤝", rarity: "UNCOMMON",  scene: "Intimate close-up of intertwined hands, woman's face visible in soft focus, candlelit romantic setting" },
  { id: "i_first_kiss",        tier: 1, title: "First Kiss",          subtitle: "Soft, electric, unforgettable.",          icon: "💋", rarity: "UNCOMMON",  scene: "Beautiful woman with eyes closed, lips puckered, leaning in for a kiss, soft romantic backlighting" },
  { id: "i_neck_kisses",       tier: 1, title: "Neck Kisses",         subtitle: "She tilted her head for you.",            icon: "🦢", rarity: "UNCOMMON",  scene: "Woman with head tilted back, eyes closed in pleasure, neck exposed, lips parted, blissful expression, warm lighting" },
  { id: "i_tight_embrace",     tier: 1, title: "Tight Embrace",       subtitle: "She held on like she'd never let go.",    icon: "🫂", rarity: "UNCOMMON",  scene: "Woman pressed tight in embrace, peaceful sensual face, bare shoulders visible, intimate bedroom setting" },
  { id: "i_lap_sitting",       tier: 1, title: "On Your Lap",         subtitle: "She climbed onto your lap.",              icon: "🪑", rarity: "UNCOMMON",  scene: "Gorgeous woman sitting sideways on a lap, arm around neck, faces very close, short skirt riding up, dim lighting" },
  { id: "i_deep_kiss",         tier: 1, title: "Deep Kiss",           subtitle: "A kiss that left you breathless.",        icon: "😘", rarity: "UNCOMMON",  scene: "Passionate kiss, woman's hands in hair, bodies pressed together, one strap down, intense and romantic" },
  { id: "i_ear_whisper",       tier: 1, title: "Whispered Desire",    subtitle: "Her lips brushed your ear.",              icon: "👂", rarity: "UNCOMMON",  scene: "Woman leaning in to whisper, lips at ear, sly seductive smile, low neckline visible, warm dim lighting" },

  // ── Tier 2: Heating Up — ALL RARE ─────────────────────────────────────
  { id: "i_shoulder_reveal",   tier: 2, title: "Bare Shoulders",      subtitle: "The strap slipped — on purpose.",         icon: "👙", rarity: "RARE",      scene: "Stunning woman with both dress straps fallen off shoulders, bare shoulders and collarbone, looking back seductively" },
  { id: "i_bikini_moment",     tier: 2, title: "Bikini Moment",       subtitle: "She showed you her favorite bikini.",     icon: "🏖️", rarity: "RARE",      scene: "Gorgeous woman in tiny string bikini by pool, sunlit, confident pose, wet skin glistening, curves on display" },
  { id: "i_lingerie_tease",    tier: 2, title: "Lingerie Tease",      subtitle: "A peek at what's underneath.",            icon: "🩱", rarity: "RARE",      scene: "Woman in sheer lace lingerie, sitting on edge of bed, revealing cleavage, soft lamplight, seductive gaze" },
  { id: "i_body_worship",      tier: 2, title: "Body Worship",        subtitle: "She let you admire every curve.",         icon: "✨", rarity: "RARE",      scene: "Woman lying on silk sheets in revealing lingerie, showing off curves, relaxed and confident, looking at camera" },
  { id: "i_massage",           tier: 2, title: "Sensual Massage",     subtitle: "Hands exploring slowly.",                 icon: "💆", rarity: "RARE",      scene: "Woman lying face-down, bare back fully exposed, oil on skin, hands massaging shoulders, intimate spa setting" },
  { id: "i_shower_invite",     tier: 2, title: "Shower Invite",       subtitle: "She asked you to join.",                  icon: "🚿", rarity: "RARE",      scene: "Woman behind steamy glass shower door, silhouette with curves visible through steam, beckoning gesture" },
  { id: "i_back_kisses",       tier: 2, title: "Trailing Kisses",     subtitle: "Down her spine, one by one.",             icon: "💕", rarity: "RARE",      scene: "Woman with arched bare back, trail of lipstick kiss marks down her spine, lying on dark sheets, dramatic lighting" },

  // ── Tier 3: Undressed — ALL EPIC ──────────────────────────────────────
  { id: "i_topless",           tier: 3, title: "Topless",             subtitle: "She let the top fall.",                   icon: "🔓", rarity: "EPIC",      scene: "Beautiful woman topless from behind, looking over shoulder with seductive gaze, hair cascading down bare back, soft studio lighting" },
  { id: "i_fully_revealed",    tier: 3, title: "Fully Revealed",      subtitle: "Nothing left between you.",               icon: "🌹", rarity: "EPIC",      scene: "Woman standing fully nude, arms at sides, confident expression, soft diffused studio lighting, artistic full body pose" },
  { id: "i_striptease",        tier: 3, title: "Striptease",          subtitle: "Slow, deliberate, mesmerizing.",          icon: "🎭", rarity: "EPIC",      scene: "Woman mid-undress, sliding garment off hips, dim red-tinted room, pole nearby, seductive eye contact with camera" },
  { id: "i_skinny_dipping",    tier: 3, title: "Skinny Dipping",      subtitle: "Under the moonlight, bare.",              icon: "🌊", rarity: "EPIC",      scene: "Nude woman in moonlit water, bare shoulders and chest above surface, water reflection, hair wet, ethereal beauty" },
  { id: "i_morning_nude",      tier: 3, title: "Morning Nude",        subtitle: "She woke up and didn't cover up.",        icon: "☀️", rarity: "EPIC",      scene: "Nude woman lying in white sheets, morning sunlight streaming in, sheet barely covering hips, peaceful sensual expression" },
  { id: "i_nude_selfie",       tier: 3, title: "Nude Selfie",         subtitle: "A photo just for your eyes.",             icon: "🤳", rarity: "EPIC",      scene: "Woman taking nude mirror selfie, phone in hand, full body visible in reflection, bathroom, seductive expression" },
  { id: "i_body_paint",        tier: 3, title: "Body Canvas",         subtitle: "Her body became art.",                    icon: "🎨", rarity: "EPIC",      scene: "Fully nude woman with artistic paint strokes across her breasts and thighs, artistic and erotic, studio lighting" },
  { id: "i_mirror_moment",     tier: 3, title: "Mirror Moment",       subtitle: "She watched herself with you.",           icon: "🪞", rarity: "EPIC",      scene: "Nude woman looking at herself in full-length mirror, candlelight, both front and reflection visible, intimate" },

  // ── Tier 4: Full Intimacy — ALL EPIC ──────────────────────────────────
  { id: "i_first_time",        tier: 4, title: "First Time",          subtitle: "The moment everything changed.",          icon: "💫", rarity: "EPIC",      scene: "Two nude bodies intertwined on bed, sheets tangled around legs, passionate intimate embrace, candlelit bedroom" },
  { id: "i_passionate_night",  tier: 4, title: "Passionate Night",    subtitle: "A night neither of you will forget.",     icon: "🌶️", rarity: "EPIC",      scene: "Woman lying back on dark satin sheets, nude, flushed skin, hair spread out, post-passion glow, candles" },
  { id: "i_morning_after",     tier: 4, title: "Morning After",       subtitle: "Waking up tangled together.",             icon: "🌅", rarity: "EPIC",      scene: "Nude woman asleep on chest, messy sheets barely covering, soft morning light through curtains, peaceful intimacy" },
  { id: "i_oral_pleasure",     tier: 4, title: "Oral Pleasure",       subtitle: "She returned the favor.",                 icon: "👅", rarity: "EPIC",      scene: "Woman looking up seductively from between sheets, lips parted, intimate suggestive angle, dim bedroom lighting" },
  { id: "i_on_top",            tier: 4, title: "On Top",              subtitle: "She took control.",                       icon: "🤸", rarity: "EPIC",      scene: "Woman straddling, nude, hands on chest below, hair falling forward, looking down with dominance, sweat glistening" },
  { id: "i_from_behind",       tier: 4, title: "From Behind",         subtitle: "She arched her back for you.",            icon: "🍑", rarity: "EPIC",      scene: "Woman on all fours on bed, arched back, looking back over shoulder with desire, nude, intimate bedroom angle" },
  { id: "i_against_wall",      tier: 4, title: "Against the Wall",    subtitle: "She pulled you into her.",                icon: "🧱", rarity: "EPIC",      scene: "Woman's bare back against wall, legs wrapped around waist, faces close, intense passion, dramatic side lighting" },
  { id: "i_wrapped_sheets",    tier: 4, title: "Wrapped in Sheets",   subtitle: "Lost in each other all evening.",         icon: "🛏️", rarity: "EPIC",      scene: "Two nude bodies under tangled white sheets, limbs intertwined, silhouettes visible, post-passion exhaustion" },

  // ── Tier 5: Deep Exploration — ALL LEGENDARY ──────────────────────────
  { id: "i_roleplay",          tier: 5, title: "Role Play",           subtitle: "She became someone else for you.",        icon: "🎪", rarity: "LEGENDARY", scene: "Nude woman in only a costume accessory (nurse hat/maid headband), posing confidently, playful seductive expression, themed room" },
  { id: "i_blindfolded",       tier: 5, title: "Blindfolded",         subtitle: "Trust without sight.",                    icon: "🙈", rarity: "LEGENDARY", scene: "Nude woman lying back with silk blindfold, lips parted in anticipation, hands above head, vulnerable and sensual" },
  { id: "i_tied_up",           tier: 5, title: "Tied Up",             subtitle: "She surrendered all control.",             icon: "⛓️", rarity: "LEGENDARY", scene: "Woman's wrists bound with silk ribbon to headboard, nude arched body on display, dim red lighting, submissive pose" },
  { id: "i_outdoor_thrill",    tier: 5, title: "Outdoor Thrill",      subtitle: "Under the open sky.",                     icon: "🌿", rarity: "LEGENDARY", scene: "Fully nude woman on secluded balcony at sunset, leaning on railing, entire body on display, nature backdrop, golden hour" },
  { id: "i_hot_tub",           tier: 5, title: "Hot Tub",             subtitle: "Steam, bubbles, and bare skin.",          icon: "♨️", rarity: "LEGENDARY", scene: "Nude woman in hot tub at night, steam rising, breasts above water, head tilted back in pleasure, stars above, wet skin" },
  { id: "i_oil_play",          tier: 5, title: "Oil Play",            subtitle: "Glistening under low light.",             icon: "💧", rarity: "LEGENDARY", scene: "Woman's entire nude body glistening with oil, lying on dark sheets, dramatic side lighting emphasizing every curve" },
  { id: "i_submission",        tier: 5, title: "Submission",          subtitle: "She let you lead completely.",             icon: "🔱", rarity: "LEGENDARY", scene: "Nude woman kneeling, looking up submissively, collar on neck, hands behind back, dim moody lighting, powerful angle from above" },

  // ── Tier 6: Ultimate Connection — ALL LEGENDARY ───────────────────────
  { id: "i_tantric",           tier: 6, title: "Tantric",             subtitle: "Beyond physical — a spiritual bond.",     icon: "🕉️", rarity: "LEGENDARY", scene: "Two nude bodies seated facing each other in lotus position, foreheads touching, candlelit room, spiritual and deeply erotic" },
  { id: "i_all_night",         tier: 6, title: "All Night Long",      subtitle: "Dawn broke before you stopped.",          icon: "🌃", rarity: "LEGENDARY", scene: "Exhausted nude woman in messy sheets, sunrise through window, satisfied smile, sweat on skin, multiple positions implied" },
  { id: "i_bathtub_together",  tier: 6, title: "Bathtub Together",    subtitle: "Warm water, skin on skin.",               icon: "🛁", rarity: "LEGENDARY", scene: "Nude woman leaning back in bathtub, another body behind, her breasts above water, candles everywhere, steam, intimate" },
  { id: "i_kitchen_counter",   tier: 6, title: "Kitchen Counter",     subtitle: "No surface was safe.",                    icon: "🍳", rarity: "LEGENDARY", scene: "Nude woman sitting on kitchen counter, legs spread and wrapped around partner, nothing hidden, passionate, morning light" },
  { id: "i_complete_surrender", tier: 6, title: "Complete Surrender", subtitle: "She gave you everything.",                icon: "🏳️", rarity: "LEGENDARY", scene: "Woman lying fully spread on silk sheets, completely nude and exposed, eyes closed in total submission, soft red and gold lighting" },
  { id: "i_insatiable",        tier: 6, title: "Insatiable",          subtitle: "Neither of you could stop.",              icon: "🔁", rarity: "LEGENDARY", scene: "Sweaty nude woman pulling partner close, intense hungry gaze, bodies pressed together, sheets destroyed, raw passion" },
  { id: "i_soul_merge",        tier: 6, title: "Soul Merge",          subtitle: "Two bodies, one soul.",                   icon: "♾️", rarity: "LEGENDARY", scene: "Intertwined nude bodies from above, limbs wrapped around each other, soft ethereal glow, artistic and deeply intimate" },
]

// Group by tier
const ACHIEVEMENTS_BY_TIER: Record<number, IntimateAchievement[]> = {}
for (const a of INTIMATE_ACHIEVEMENTS) {
  if (!ACHIEVEMENTS_BY_TIER[a.tier]) ACHIEVEMENTS_BY_TIER[a.tier] = []
  ACHIEVEMENTS_BY_TIER[a.tier].push(a)
}

// ═══════════════════════════════════════════════════════════════════════════════
// RARITY CONFIG
// ═══════════════════════════════════════════════════════════════════════════════

const RARITY_CONFIG: Record<IntimateRarity, {
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
// INTIMATE SURPRISE BOXES — rarity-weighted, spicier theme
// ═══════════════════════════════════════════════════════════════════════════════

const INTIMATE_BOXES = [
  {
    id: "tease",
    name: "Gentle Tease",
    emoji: "🌸",
    description: "Unlock early — flirty peeks and tender first moments.",
    price: "€4.99",
    freeOnPlan: "plus" as const,
    color: "#f472b6",
    weights: { COMMON: 0.55, UNCOMMON: 0.30, RARE: 0.10, EPIC: 0.04, LEGENDARY: 0.01 },
  },
  {
    id: "desire",
    name: "Burning Desire",
    emoji: "🔥",
    description: "Skip ahead — unlock explicit reveals and passionate encounters early.",
    price: "€8.49",
    freeOnPlan: "premium" as const,
    color: "#ef4444",
    weights: { COMMON: 0.0, UNCOMMON: 0.30, RARE: 0.40, EPIC: 0.25, LEGENDARY: 0.05 },
  },
  {
    id: "obsession",
    name: "Dark Obsession",
    emoji: "⛓️",
    description: "Jump to the top — unlock the most explicit Legendary content right now.",
    price: "€13.99",
    freeOnPlan: "premium" as const,
    color: "#fbbf24",
    weights: { COMMON: 0.0, UNCOMMON: 0.0, RARE: 0.15, EPIC: 0.45, LEGENDARY: 0.40 },
  },
]

// ═══════════════════════════════════════════════════════════════════════════════
// FLOATING HEARTS BACKGROUND
// ═══════════════════════════════════════════════════════════════════════════════

function FloatingHearts() {
  const items = Array.from({ length: 35 }, (_, i) => ({
    left: `${(i * 37 + 13) % 100}%`,
    top: `${(i * 53 + 7) % 100}%`,
    size: 8 + (i % 5) * 4,
    opacity: 0.02 + (i % 4) * 0.01,
    delay: `${(i * 1.3) % 8}s`,
    duration: `${6 + (i % 5) * 2}s`,
    icon: i % 3,
  }))
  const icons = [Heart, Flame, Sparkles]
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
// COLOR LERP
// ═══════════════════════════════════════════════════════════════════════════════

function lerpColor(a: [number, number, number], b: [number, number, number], t: number): [number, number, number] {
  return [Math.round(a[0] + (b[0] - a[0]) * t), Math.round(a[1] + (b[1] - a[1]) * t), Math.round(a[2] + (b[2] - a[2]) * t)]
}

// ═══════════════════════════════════════════════════════════════════════════════
// INTIMATE SLOT MACHINE
// ═══════════════════════════════════════════════════════════════════════════════

const CELL_W = 100
const WINNER_IDX = 55
const TOTAL_REEL = 70
const SPIN_MS = 6000

function pickRandomAchievement(
  weights: Record<string, number>,
  unlockedIds: Set<string>,
): IntimateAchievement | null {
  // Build pool of locked achievements grouped by rarity
  const pool: Record<string, IntimateAchievement[]> = {}
  for (const a of INTIMATE_ACHIEVEMENTS) {
    if (!unlockedIds.has(a.id)) {
      if (!pool[a.rarity]) pool[a.rarity] = []
      pool[a.rarity].push(a)
    }
  }

  // Build weighted selection
  const candidates: { achievement: IntimateAchievement; weight: number }[] = []
  for (const [rarity, w] of Object.entries(weights)) {
    const arr = pool[rarity] ?? []
    if (arr.length > 0 && w > 0) {
      const perItem = w / arr.length
      for (const a of arr) candidates.push({ achievement: a, weight: perItem })
    }
  }

  if (candidates.length === 0) return null

  // Weighted random
  const totalW = candidates.reduce((s, c) => s + c.weight, 0)
  let r = Math.random() * totalW
  for (const c of candidates) {
    r -= c.weight
    if (r <= 0) return c.achievement
  }
  return candidates[candidates.length - 1].achievement
}

function buildIntimateReel(winner: IntimateAchievement) {
  const items: IntimateAchievement[] = []
  for (let i = 0; i < TOTAL_REEL; i++) {
    if (i === WINNER_IDX) {
      items.push(winner)
    } else {
      items.push(INTIMATE_ACHIEVEMENTS[Math.floor(Math.random() * INTIMATE_ACHIEVEMENTS.length)])
    }
  }
  return items
}

function IntimateSlotOverlay({
  winner,
  onClose,
  onUnlock,
}: {
  winner: IntimateAchievement
  onClose: () => void
  onUnlock: (id: string) => void
}) {
  const [phase, setPhase] = useState<"spinning" | "revealed">("spinning")
  const reelRef = useRef<HTMLDivElement>(null)
  const rafRef = useRef<number>(0)
  const rCfg = RARITY_CONFIG[winner.rarity]

  const reel = useRef(buildIntimateReel(winner)).current
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
          {phase === "revealed" ? "Unlocked..." : "Spinning..."}
        </p>

        {/* Slot machine */}
        <div className="w-full relative">
          <div className="absolute -inset-1.5 rounded-3xl bg-gradient-to-r from-pink-500/20 via-red-500/20 to-amber-500/20 blur-sm" />
          <div className="relative rounded-2xl border-2 border-pink-500/15 bg-[#0d0509] overflow-hidden shadow-2xl"
               style={{ boxShadow: "0 0 60px 10px rgba(244,114,182,0.08), inset 0 0 30px rgba(0,0,0,0.5)" }}>

            {/* Selection bracket */}
            <div className="absolute left-1/2 top-0 bottom-0 z-20 pointer-events-none" style={{ width: CELL_W + 8, transform: "translateX(-50%)" }}>
              <div className="absolute inset-x-0 top-0 h-1.5 rounded-b bg-gradient-to-r from-pink-400/0 via-pink-400 to-pink-400/0" />
              <div className="absolute inset-x-0 bottom-0 h-1.5 rounded-t bg-gradient-to-r from-pink-400/0 via-pink-400 to-pink-400/0" />
              <div className="absolute inset-0 border-2 border-pink-400/50 rounded-xl" />
              <div className="absolute inset-0 bg-pink-400/[0.04]" />
            </div>

            {/* Edge fades */}
            <div className="absolute inset-y-0 left-0 w-16 z-10 bg-gradient-to-r from-[#0d0509] to-transparent pointer-events-none" />
            <div className="absolute inset-y-0 right-0 w-16 z-10 bg-gradient-to-l from-[#0d0509] to-transparent pointer-events-none" />

            {/* Reel */}
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
              {rCfg.label || "Common"} — {TIERS[winner.tier].title}
            </span>

            <div className="flex items-center gap-3">
              <span className="text-5xl">{winner.icon}</span>
              <div className="text-left">
                <h2 className="text-2xl font-extrabold text-white">{winner.title}</h2>
                <p className="text-sm text-white/40 mt-0.5">{winner.subtitle}</p>
              </div>
            </div>

            <div className="flex items-center gap-2 rounded-full bg-pink-500/15 px-4 py-2 border border-pink-500/20">
              <Flame className="h-4 w-4 text-pink-400" />
              <span className="text-xs font-bold text-pink-300">Unlocked Early — Spicy Photo Yours</span>
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

interface IntimateProgressionPanelProps {
  onClose: () => void
  unlockedIds?: Set<string>
  defaultTab?: "collection" | "surprise"
}

export default function IntimateProgressionPanel({ onClose, unlockedIds: initialUnlocked, defaultTab = "collection" }: IntimateProgressionPanelProps) {
  const [unlocked, setUnlocked] = useState<Set<string>>(initialUnlocked ?? new Set())
  const girlfriendId = useAppStore((s) => s.currentGirlfriendId)
  const queryClient = useQueryClient()

  // Fetch real data from backend
  const { data: apiData } = useQuery({
    queryKey: ["intimacyAchievements", girlfriendId],
    queryFn: () => getIntimacyAchievements(girlfriendId || undefined),
    staleTime: 30_000,
  })

  // Merge API unlocked state into local state
  useEffect(() => {
    if (!apiData) return
    const apiUnlocked = new Set<string>()
    for (const tierInfo of Object.values(apiData)) {
      for (const a of (tierInfo as { achievements: IntimacyAchievementItem[] }).achievements) {
        if (a.unlocked) apiUnlocked.add(a.id)
      }
    }
    if (apiUnlocked.size > 0) {
      setUnlocked(prev => {
        const merged = new Set([...prev, ...apiUnlocked])
        return merged.size !== prev.size ? merged : prev
      })
    }
  }, [apiData])

  // Build a map of achievement_id -> image_url from API data
  const photoMap = useRef(new Map<string, string>())
  useEffect(() => {
    if (!apiData) return
    const m = new Map<string, string>()
    for (const tierInfo of Object.values(apiData)) {
      for (const a of (tierInfo as { achievements: IntimacyAchievementItem[] }).achievements) {
        if (a.image_url) m.set(a.id, a.image_url)
      }
    }
    photoMap.current = m
  }, [apiData])

  const totalUnlocked = INTIMATE_ACHIEVEMENTS.filter(a => unlocked.has(a.id)).length
  const totalCount = INTIMATE_ACHIEVEMENTS.length

  const [activeTab, setActiveTab] = useState<"collection" | "surprise">(defaultTab)
  const [slotWinner, setSlotWinner] = useState<IntimateAchievement | null>(null)

  // Scroll-based gradient
  const scrollRef = useRef<HTMLDivElement>(null)
  const [gradientOverlay, setGradientOverlay] = useState("")

  const handleScroll = useCallback(() => {
    const el = scrollRef.current
    if (!el) return
    const rawIdx = el.scrollTop / el.clientHeight
    const idx = Math.min(Math.floor(rawIdx), TIERS.length - 1)
    const nextIdx = Math.min(idx + 1, TIERS.length - 1)
    const c = lerpColor(TIER_COLORS[idx], TIER_COLORS[nextIdx], rawIdx - idx)
    setGradientOverlay(`radial-gradient(ellipse 120% 80% at 50% 40%, rgba(${c[0]},${c[1]},${c[2]},0.12) 0%, rgba(${c[0]},${c[1]},${c[2]},0.03) 50%, transparent 100%)`)
  }, [])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    handleScroll()
    el.addEventListener("scroll", handleScroll, { passive: true })
    return () => el.removeEventListener("scroll", handleScroll)
  }, [handleScroll, activeTab])

  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => { document.body.style.overflow = prev }
  }, [])

  // Track payment state
  const [purchasing, setPurchasing] = useState<string | null>(null) // box id being purchased
  const [purchaseError, setPurchaseError] = useState<string | null>(null)

  const handleUnlock = useCallback(async (id: string) => {
    // Called AFTER the slot animation finishes — achievement already paid for, just update local state
    setUnlocked(prev => new Set([...prev, id]))
    queryClient.invalidateQueries({ queryKey: ["intimacyAchievements"] })
  }, [queryClient])

  const handleOpenBox = async (boxId: string) => {
    const box = INTIMATE_BOXES.find(b => b.id === boxId)
    if (!box) return
    const winner = pickRandomAchievement(box.weights, unlocked)
    if (!winner) return

    // ── CHARGE FIRST, then show animation ────────────────────────────────
    setPurchasing(boxId)
    setPurchaseError(null)

    try {
      const res = await purchaseIntimateBox(boxId, winner.id, girlfriendId || undefined)

      if (res.status === "no_card") {
        setPurchaseError("No card on file. Add one in Payment Options first.")
        return
      }

      if (res.status === "requires_action" && res.client_secret) {
        // 3DS authentication needed
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
        // Payment succeeded — update photo map and show slot animation
        if (res.image_url) {
          photoMap.current.set(winner.id, res.image_url)
        }
        setSlotWinner(winner)
      } else {
        setPurchaseError(res.error || "Payment failed. Please try again.")
      }
    } catch (e: any) {
      console.warn("Intimate box purchase failed:", e)
      setPurchaseError(e?.message || "Payment failed. Please try again.")
    } finally {
      setPurchasing(null)
    }
  }

  return (
    <div className="fixed inset-0 z-[9999] flex flex-col" style={{ backgroundColor: "#0a0608" }}>
      <FloatingHearts />
      <div className="pointer-events-none absolute inset-0" style={{ background: gradientOverlay, transition: "background 200ms ease" }} />

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
            onClick={() => setActiveTab("surprise")}
            className={cn("px-4 py-1.5 rounded-full text-xs font-bold transition-all",
              activeTab === "surprise" ? "bg-red-500/20 text-red-300" : "text-white/40 hover:text-white/60")}
          >
            🔥 Seduce Her
          </button>
        </div>

        <div className="flex items-center gap-2 rounded-full bg-black/60 px-4 py-2 border border-pink-500/15">
          <Flame className="h-3.5 w-3.5 text-pink-400" />
          <span className="text-xs font-bold text-white/80">{totalUnlocked}/{totalCount}</span>
        </div>
      </div>

      {/* Content */}
      {activeTab === "collection" ? (
        /* ── COLLECTION TAB ── */
        <div ref={scrollRef} className="flex-1 overflow-y-auto scroll-smooth pt-14">
          <div className="relative">
            {TIERS.map((tier, tIdx) => {
              const color = tier.color
              const tierAchs = ACHIEVEMENTS_BY_TIER[tIdx] ?? []
              const tierUnlocked = tierAchs.filter(a => unlocked.has(a.id)).length

              return (
                <section key={tIdx} className="relative flex min-h-screen flex-col items-center justify-center px-6 md:px-16">
                  <div className="pointer-events-none absolute inset-0" style={{ background: `radial-gradient(circle at 50% 50%, rgba(${color[0]},${color[1]},${color[2]},0.07) 0%, transparent 70%)` }} />

                  <div className="relative z-10 flex max-w-lg flex-col items-center text-center">
                    {/* Tier icon */}
                    <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full border md:h-20 md:w-20"
                      style={{ backgroundColor: `rgba(${color[0]},${color[1]},${color[2]},0.12)`, borderColor: `rgba(${color[0]},${color[1]},${color[2]},0.25)`, boxShadow: `0 0 40px 10px rgba(${color[0]},${color[1]},${color[2]},0.10)` }}>
                      <Flame className={cn("h-8 w-8 md:h-10 md:w-10", tier.accentClass)} style={{ filter: `drop-shadow(0 0 8px rgba(${color[0]},${color[1]},${color[2]},0.5))` }} />
                    </div>

                    <h2 className="text-2xl font-bold tracking-tight text-white md:text-4xl">{tier.title}</h2>
                    <div className="mt-2 flex items-center gap-2">
                      <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border"
                        style={{ color: RARITY_CONFIG[tier.rarity].color, borderColor: `${RARITY_CONFIG[tier.rarity].color}30`, backgroundColor: `${RARITY_CONFIG[tier.rarity].color}10` }}>
                        {tier.rarity}
                      </span>
                      <span className="text-sm text-white/30">{tierUnlocked}/{tierAchs.length} unlocked</span>
                    </div>

                    <div className="my-5 flex items-center gap-2">
                      <div className="h-px w-8 md:w-12" style={{ backgroundColor: `rgba(${color[0]},${color[1]},${color[2]},0.2)` }} />
                      <Flame className="h-3 w-3" style={{ color: `rgba(${color[0]},${color[1]},${color[2]},0.3)` }} />
                      <div className="h-px w-8 md:w-12" style={{ backgroundColor: `rgba(${color[0]},${color[1]},${color[2]},0.2)` }} />
                    </div>

                    <p className="max-w-sm text-sm leading-relaxed text-white/40">{tier.subtitle}</p>

                    {/* Achievement cards */}
                    <div className="mt-8 w-full max-w-md space-y-2.5">
                      {tierAchs.map((a) => {
                        const isU = unlocked.has(a.id)
                        const cfg = RARITY_CONFIG[a.rarity]

                        return (
                          <div key={a.id} className={cn("flex items-stretch gap-0 rounded-xl overflow-hidden transition-all ring-1", isU ? cfg.bg : "bg-white/[0.02]", isU ? cfg.ring : "ring-white/[0.04]")}>
                            {/* Icon + photo slot */}
                            <div className={cn("relative flex h-[72px] w-[72px] shrink-0 items-center justify-center overflow-hidden", isU ? "bg-gradient-to-br from-pink-900/40 to-rose-900/30" : "bg-white/[0.03]")}>
                              {isU && photoMap.current.get(a.id) ? (
                                <img src={photoMap.current.get(a.id)} alt={a.title} className="h-full w-full object-cover" />
                              ) : isU ? (
                                <div className="flex flex-col items-center gap-0.5">
                                  <span className="text-2xl">{a.icon}</span>
                                  <span className="text-[7px] font-medium text-pink-300/40 uppercase tracking-wider">Photo</span>
                                </div>
                              ) : (
                                <div className="flex flex-col items-center gap-1">
                                  <span className="text-xl opacity-30">{a.icon}</span>
                                  <Lock className="h-2.5 w-2.5 text-white/10" />
                                </div>
                              )}
                              <div className={cn("absolute left-0 top-0 h-full w-[3px]")} style={{ backgroundColor: isU ? `${cfg.color}60` : "rgba(255,255,255,0.04)" }} />
                            </div>

                            {/* Text */}
                            <div className="flex min-w-0 flex-1 items-center gap-3 px-3.5 py-3">
                              <div className="min-w-0 flex-1 text-left">
                                <div className="flex items-center gap-1.5">
                                  <p className={cn("text-xs font-semibold truncate", isU ? cfg.text : "text-white/40")}>{a.title}</p>
                                  {cfg.label && (
                                    <span className={cn("text-[9px] uppercase tracking-wider font-medium shrink-0", isU ? cfg.badge : "text-white/15")}>{cfg.label}</span>
                                  )}
                                </div>
                                <p className={cn("text-[10px] truncate", isU ? "text-white/35" : "text-white/20")}>{a.subtitle}</p>
                              </div>

                              {isU ? (
                                <Flame className="h-3.5 w-3.5 shrink-0 text-pink-400" />
                              ) : (
                                <Lock className="h-3 w-3 shrink-0 text-white/15" />
                              )}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  {tIdx === 0 && (
                    <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1 animate-bounce text-pink-400/30">
                      <ChevronDown className="h-5 w-5" />
                      <span className="text-[9px] uppercase tracking-widest font-medium">Scroll for more</span>
                    </div>
                  )}
                </section>
              )
            })}
          </div>
        </div>
      ) : (
        /* ── SURPRISE TAB ── */
        <div className="flex-1 overflow-y-auto pt-16 pb-12 px-4 md:px-8">
          <div className="mx-auto max-w-lg">
            {/* Hero */}
            <div className="text-center pt-8 pb-10">
              <div className="flex items-center justify-center gap-2 mb-4">
                <Flame className="h-5 w-5 text-red-400/60 animate-pulse" style={{ animationDuration: "3s" }} />
                <Heart className="h-8 w-8 text-pink-300/60 fill-pink-300/30 animate-pulse" style={{ animationDuration: "4s", animationDelay: "0.5s" }} />
                <Flame className="h-5 w-5 text-red-400/60 animate-pulse" style={{ animationDuration: "3.5s", animationDelay: "1s" }} />
              </div>
              <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white/90">
              Seduce Her Now
            </h1>
            <p className="mt-3 text-base text-white/40 max-w-sm mx-auto leading-relaxed">
              Why wait? Spin to unlock intimate achievements early — skip the grind and jump straight to the good stuff. The higher the rarity, the hotter it gets.
            </p>
            </div>

            {/* Surprise boxes */}
            <div className="space-y-5">
              {INTIMATE_BOXES.map((box) => {
                const availableCount = INTIMATE_ACHIEVEMENTS.filter(a => {
                  if (unlocked.has(a.id)) return false
                  return (box.weights[a.rarity] ?? 0) > 0
                }).length
                const soldOut = availableCount === 0

                return (
                  <div key={box.id} className={cn("relative rounded-2xl border overflow-hidden transition-all", soldOut && "opacity-40")}
                    style={{ borderColor: `${box.color}25`, boxShadow: `0 0 40px 8px ${box.color}10, inset 0 1px 0 rgba(255,255,255,0.03)` }}>
                    <div className="absolute inset-0" style={{ background: `linear-gradient(135deg, ${box.color}15, transparent 60%)` }} />

                    {/* Shimmer */}
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
                            <p className="text-xs text-white/30 mt-0.5 max-w-[200px]">{box.description}</p>
                          </div>
                        </div>
                        <span className="text-sm font-bold text-emerald-400/70">{box.price}</span>
                      </div>

                      {/* Odds */}
                      <div className="flex h-2 w-full overflow-hidden rounded-full bg-black/30 mb-2">
                        {(["COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY"] as IntimateRarity[]).filter(r => (box.weights[r] ?? 0) > 0).map(r => (
                          <div key={r} className="h-full" style={{ width: `${(box.weights[r] ?? 0) * 100}%`, backgroundColor: RARITY_CONFIG[r].color, opacity: 0.7 }} />
                        ))}
                      </div>
                      <div className="flex flex-wrap gap-x-3 gap-y-1 mb-4">
                        {(["COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY"] as IntimateRarity[]).filter(r => (box.weights[r] ?? 0) > 0).map(r => (
                          <div key={r} className="flex items-center gap-1">
                            <div className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: RARITY_CONFIG[r].color }} />
                            <span className="text-[9px] font-bold" style={{ color: RARITY_CONFIG[r].color }}>{r}</span>
                            <span className="text-[9px] text-white/25">{((box.weights[r] ?? 0) * 100).toFixed(0)}%</span>
                          </div>
                        ))}
                      </div>

                      <button
                        onClick={() => handleOpenBox(box.id)}
                        disabled={soldOut || purchasing === box.id}
                        className={cn("w-full rounded-xl py-3.5 text-sm font-bold transition-all flex items-center justify-center gap-2",
                          soldOut ? "bg-white/[0.04] text-white/20 cursor-not-allowed"
                            : purchasing === box.id ? "bg-gradient-to-r from-pink-600/60 to-red-600/60 text-white/60 cursor-wait"
                            : "bg-gradient-to-r from-pink-600 to-red-600 text-white shadow-lg shadow-pink-500/20 hover:shadow-pink-500/30 hover:scale-[1.02] active:scale-[0.98]")}
                      >
                        {soldOut ? (
                          <><Lock className="h-4 w-4" /> All unlocked!</>
                        ) : purchasing === box.id ? (
                          <><div className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" /> Processing Payment...</>
                        ) : (
                          <><Flame className="h-4 w-4" /> Seduce Her Now<ChevronRight className="h-4 w-4" /></>
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
                  { icon: Flame, text: "Unlock achievements early — no need to wait for natural progression. Spin and the achievement is yours instantly." },
                  { icon: Heart, text: "Higher-tier boxes give better odds at Epic and Legendary — the most explicit, hottest content unlocked ahead of time." },
                  { icon: Sparkles, text: "No duplicates — every spin gives you something new. Collect all 50 to complete your private gallery." },
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
      {slotWinner && (
        <IntimateSlotOverlay
          winner={slotWinner}
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
