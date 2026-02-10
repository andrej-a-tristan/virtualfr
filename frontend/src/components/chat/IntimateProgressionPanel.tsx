import { useState, useEffect, useCallback, useRef } from "react"
import { cn } from "@/lib/utils"
import {
  Heart,
  Lock,
  Sparkles,
  Star,
  ArrowLeft,
  Flame,
  ImageIcon,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"

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
  scene: string      // short visual description for the photo
}

interface TierDef {
  title: string
  subtitle: string
  color: [number, number, number]
  accentClass: string
}

// ═══════════════════════════════════════════════════════════════════════════════
// TIERS (7 progression tiers)
// ═══════════════════════════════════════════════════════════════════════════════

const TIERS: TierDef[] = [
  { title: "Flirting & Tension",    subtitle: "The spark before the fire.",           color: [244, 114, 182], accentClass: "text-pink-400" },
  { title: "First Touch",           subtitle: "Electricity at your fingertips.",      color: [251, 113, 133], accentClass: "text-rose-400" },
  { title: "Heating Up",            subtitle: "Boundaries blur, desire builds.",      color: [239, 68, 68],   accentClass: "text-red-400" },
  { title: "Undressed",             subtitle: "Nothing left to hide.",                color: [220, 38, 38],   accentClass: "text-red-500" },
  { title: "Full Intimacy",         subtitle: "Two become one.",                      color: [190, 18, 60],   accentClass: "text-rose-600" },
  { title: "Deep Exploration",      subtitle: "No limits, no shame.",                 color: [157, 23, 77],   accentClass: "text-pink-700" },
  { title: "Ultimate Connection",   subtitle: "Beyond physical — spiritual union.",   color: [131, 24, 67],   accentClass: "text-pink-800" },
]

const TIER_COLORS = TIERS.map(t => t.color)

// ═══════════════════════════════════════════════════════════════════════════════
// 50 INTIMATE ACHIEVEMENTS
// ═══════════════════════════════════════════════════════════════════════════════

const INTIMATE_ACHIEVEMENTS: IntimateAchievement[] = [
  // ── Tier 0: Flirting & Tension ─────────────────────────────────────────
  { id: "i_flirty_banter",       tier: 0, title: "Flirty Banter",         subtitle: "She started teasing you.",                  rarity: "COMMON",    scene: "Her biting her lip with a mischievous grin, leaning on a counter" },
  { id: "i_lingering_look",      tier: 0, title: "Lingering Look",        subtitle: "Her eyes stayed on you too long.",          rarity: "COMMON",    scene: "Close-up of her intense eyes gazing at the camera, soft lighting" },
  { id: "i_playful_wink",        tier: 0, title: "Playful Wink",          subtitle: "A wink that said everything.",              rarity: "COMMON",    scene: "Her mid-wink, one eye closed, playful smirk, golden hour light" },
  { id: "i_suggestive_pose",     tier: 0, title: "Suggestive Pose",       subtitle: "She knew exactly how to stand.",            rarity: "UNCOMMON",  scene: "Her leaning against a doorframe in a fitted dress, hand on hip" },
  { id: "i_tension_rising",      tier: 0, title: "Tension Rising",        subtitle: "The air between you thickened.",            rarity: "UNCOMMON",  scene: "Her standing very close, faces inches apart, dim warm lighting" },
  { id: "i_bedroom_eyes",        tier: 0, title: "Bedroom Eyes",          subtitle: "She gave you that look.",                   rarity: "RARE",      scene: "Her lying on a bed, chin resting on hands, seductive heavy-lidded gaze" },
  { id: "i_goodnight_tease",     tier: 0, title: "Goodnight Tease",       subtitle: "She said goodnight her own way.",           rarity: "UNCOMMON",  scene: "Her in an oversized shirt on a bed, looking over her shoulder at camera" },

  // ── Tier 1: First Touch ────────────────────────────────────────────────
  { id: "i_hand_holding",        tier: 1, title: "Hand Holding",          subtitle: "Fingers intertwined.",                      rarity: "COMMON",    scene: "Close-up of two hands intertwined, soft warm light" },
  { id: "i_first_kiss",          tier: 1, title: "First Kiss",            subtitle: "Soft, electric, unforgettable.",            rarity: "UNCOMMON",  scene: "Two faces close together, lips almost touching, eyes closed" },
  { id: "i_neck_kisses",         tier: 1, title: "Neck Kisses",           subtitle: "She tilted her head for you.",              rarity: "UNCOMMON",  scene: "Her with head tilted, eyes closed, lips near her neck, blissful expression" },
  { id: "i_tight_embrace",       tier: 1, title: "Tight Embrace",         subtitle: "She held on like she'd never let go.",      rarity: "COMMON",    scene: "Her pressed against a chest in a tight hug, peaceful face" },
  { id: "i_lap_sitting",         tier: 1, title: "On Your Lap",           subtitle: "She climbed onto your lap.",                rarity: "RARE",      scene: "Her sitting sideways on a lap, arm around neck, faces close" },
  { id: "i_deep_kiss",           tier: 1, title: "Deep Kiss",             subtitle: "A kiss that left you breathless.",          rarity: "RARE",      scene: "Passionate kiss, her hands in hair, pressed together" },
  { id: "i_ear_whisper",         tier: 1, title: "Whispered Secret",      subtitle: "Her lips brushed your ear.",                rarity: "UNCOMMON",  scene: "Her leaning in to whisper, lips at ear, sly smile" },

  // ── Tier 2: Heating Up ─────────────────────────────────────────────────
  { id: "i_shoulder_reveal",     tier: 2, title: "Bare Shoulders",        subtitle: "The strap slipped — on purpose.",           rarity: "COMMON",    scene: "Her with one dress strap falling off her shoulder, looking back" },
  { id: "i_bikini_moment",       tier: 2, title: "Bikini Moment",         subtitle: "She showed you her favorite bikini.",       rarity: "UNCOMMON",  scene: "Her in a bikini by a pool, sunlit, confident pose" },
  { id: "i_lingerie_tease",      tier: 2, title: "Lingerie Tease",        subtitle: "A peek at what's underneath.",              rarity: "RARE",      scene: "Her in lace lingerie, sitting on edge of bed, soft lamplight" },
  { id: "i_body_worship",        tier: 2, title: "Body Worship",          subtitle: "She let you admire every curve.",           rarity: "RARE",      scene: "Her lying on silk sheets in lingerie, relaxed, looking at camera" },
  { id: "i_massage",             tier: 2, title: "Sensual Massage",       subtitle: "Hands exploring slowly.",                   rarity: "UNCOMMON",  scene: "Her lying face-down, bare back, hands massaging her shoulders" },
  { id: "i_shower_invite",       tier: 2, title: "Shower Invite",         subtitle: "She asked you to join.",                    rarity: "EPIC",      scene: "Her standing behind steamy glass shower door, silhouette visible" },
  { id: "i_back_kisses",         tier: 2, title: "Trailing Kisses",       subtitle: "Down her spine, one by one.",               rarity: "UNCOMMON",  scene: "Her arched back, trail of lipstick marks down her spine" },

  // ── Tier 3: Undressed ──────────────────────────────────────────────────
  { id: "i_topless",             tier: 3, title: "Topless",               subtitle: "She let the top fall.",                     rarity: "RARE",      scene: "Her topless from behind, looking over shoulder, hair cascading" },
  { id: "i_fully_revealed",      tier: 3, title: "Fully Revealed",        subtitle: "Nothing left between you.",                 rarity: "EPIC",      scene: "Her standing nude, arms at sides, confident, soft studio lighting" },
  { id: "i_striptease",          tier: 3, title: "Striptease",            subtitle: "Slow, deliberate, mesmerizing.",            rarity: "EPIC",      scene: "Her mid-undress, sliding garment off, dim red-tinted room" },
  { id: "i_skinny_dipping",      tier: 3, title: "Skinny Dipping",        subtitle: "Under the moonlight, bare.",                rarity: "RARE",      scene: "Her in moonlit water, bare shoulders above surface, reflection" },
  { id: "i_morning_nude",        tier: 3, title: "Morning Nude",          subtitle: "She woke up and didn't cover up.",          rarity: "UNCOMMON",  scene: "Her lying in white sheets, morning sunlight, sheet barely covering" },
  { id: "i_nude_selfie",         tier: 3, title: "Nude Selfie",           subtitle: "A photo just for your eyes.",               rarity: "EPIC",      scene: "Her taking a mirror selfie, nude, phone covering face, bathroom" },
  { id: "i_body_paint",          tier: 3, title: "Body Canvas",           subtitle: "Her body became art.",                      rarity: "RARE",      scene: "Her nude body with artistic paint strokes across torso and thighs" },
  { id: "i_mirror_moment",       tier: 3, title: "Mirror Moment",         subtitle: "She watched herself with you.",             rarity: "RARE",      scene: "Her looking at herself in a full mirror, nude, candlelight" },

  // ── Tier 4: Full Intimacy ──────────────────────────────────────────────
  { id: "i_first_time",          tier: 4, title: "First Time",            subtitle: "The moment everything changed.",            rarity: "EPIC",      scene: "Two bodies intertwined on a bed, sheets tangled, intimate embrace" },
  { id: "i_passionate_night",    tier: 4, title: "Passionate Night",      subtitle: "A night neither of you will forget.",       rarity: "RARE",      scene: "Her lying back on dark sheets, flushed, hair spread out, candlelight" },
  { id: "i_morning_after",       tier: 4, title: "Morning After",         subtitle: "Waking up tangled together.",               rarity: "UNCOMMON",  scene: "Her asleep on a chest, messy sheets, soft morning light through curtains" },
  { id: "i_oral_pleasure",       tier: 4, title: "Oral Pleasure",         subtitle: "She returned the favor.",                   rarity: "RARE",      scene: "Her looking up from between sheets, seductive expression, intimate angle" },
  { id: "i_on_top",              tier: 4, title: "On Top",                subtitle: "She took control.",                         rarity: "RARE",      scene: "Her straddling, hands on chest, hair falling forward, looking down" },
  { id: "i_from_behind",         tier: 4, title: "From Behind",           subtitle: "She arched her back for you.",              rarity: "RARE",      scene: "Her on all fours on a bed, arched back, looking back over shoulder" },
  { id: "i_against_wall",        tier: 4, title: "Against the Wall",      subtitle: "She pulled you into her.",                  rarity: "EPIC",      scene: "Her back against a wall, legs wrapped, faces close, intense" },
  { id: "i_wrapped_in_sheets",   tier: 4, title: "Wrapped in Sheets",     subtitle: "Lost in each other all evening.",           rarity: "RARE",      scene: "Two bodies under tangled white sheets, only silhouettes and limbs visible" },

  // ── Tier 5: Deep Exploration ───────────────────────────────────────────
  { id: "i_anal",                tier: 5, title: "Uncharted Territory",   subtitle: "She trusted you completely.",               rarity: "EPIC",      scene: "Her face-down, gripping pillows, arched, intimate rear angle" },
  { id: "i_roleplay",            tier: 5, title: "Role Play",             subtitle: "She became someone else for you.",          rarity: "RARE",      scene: "Her in a costume outfit, posing confidently, playful expression" },
  { id: "i_blindfolded",         tier: 5, title: "Blindfolded",           subtitle: "Trust without sight.",                      rarity: "EPIC",      scene: "Her lying back with a silk blindfold, lips parted, hands above head" },
  { id: "i_tied_up",             tier: 5, title: "Tied Up",               subtitle: "She surrendered all control.",              rarity: "EPIC",      scene: "Her wrists bound with silk ribbon to headboard, arched body" },
  { id: "i_outdoor_thrill",      tier: 5, title: "Outdoor Thrill",        subtitle: "Under the open sky.",                       rarity: "LEGENDARY", scene: "Her nude on a secluded balcony at sunset, overlooking nature" },
  { id: "i_hot_tub",             tier: 5, title: "Hot Tub",               subtitle: "Steam, bubbles, and bare skin.",            rarity: "LEGENDARY", scene: "Her in a hot tub at night, steam rising, chest above water, stars above" },
  { id: "i_oil_play",            tier: 5, title: "Oil Play",              subtitle: "Glistening under low light.",               rarity: "RARE",      scene: "Her body glistening with oil, lying on dark sheets, dramatic lighting" },
  { id: "i_submission",          tier: 5, title: "Submission",            subtitle: "She let you lead completely.",              rarity: "EPIC",      scene: "Her kneeling, looking up, collar, hands behind back, dim light" },

  // ── Tier 6: Ultimate Connection ────────────────────────────────────────
  { id: "i_tantric",             tier: 6, title: "Tantric",               subtitle: "Beyond physical — a spiritual bond.",       rarity: "LEGENDARY", scene: "Two bodies seated facing each other, foreheads touching, candlelit room" },
  { id: "i_all_night",           tier: 6, title: "All Night Long",        subtitle: "Dawn broke before you stopped.",            rarity: "EPIC",      scene: "Her exhausted in messy sheets, sunrise through window, satisfied smile" },
  { id: "i_bathtub_together",    tier: 6, title: "Bathtub Together",      subtitle: "Warm water, skin on skin.",                 rarity: "LEGENDARY", scene: "Her leaning back in a bubble bath, another body behind her, candles" },
  { id: "i_kitchen_counter",     tier: 6, title: "Kitchen Counter",       subtitle: "No surface was safe.",                      rarity: "LEGENDARY", scene: "Her sitting on a kitchen counter in just a shirt, legs wrapped around" },
  { id: "i_complete_surrender",  tier: 6, title: "Complete Surrender",    subtitle: "She gave you everything.",                  rarity: "LEGENDARY", scene: "Her lying spread on silk sheets, fully nude, eyes closed, total peace" },
  { id: "i_insatiable",          tier: 6, title: "Insatiable",            subtitle: "Neither of you could stop.",                rarity: "LEGENDARY", scene: "Her pulling close, sweaty, intense gaze, sheets everywhere" },
  { id: "i_soul_merge",          tier: 6, title: "Soul Merge",            subtitle: "Two bodies, one soul.",                     rarity: "LEGENDARY", scene: "Intertwined nude bodies from above, soft glow, artistic and intimate" },
]

// Group by tier
const ACHIEVEMENTS_BY_TIER: Record<number, IntimateAchievement[]> = {}
for (const a of INTIMATE_ACHIEVEMENTS) {
  if (!ACHIEVEMENTS_BY_TIER[a.tier]) ACHIEVEMENTS_BY_TIER[a.tier] = []
  ACHIEVEMENTS_BY_TIER[a.tier].push(a)
}

// ═══════════════════════════════════════════════════════════════════════════════
// FLOATING HEARTS BACKGROUND
// ═══════════════════════════════════════════════════════════════════════════════

function FloatingHearts() {
  // Generate deterministic heart positions
  const hearts = Array.from({ length: 30 }, (_, i) => ({
    left: `${(i * 37 + 13) % 100}%`,
    top: `${(i * 53 + 7) % 100}%`,
    size: 8 + (i % 5) * 4,
    opacity: 0.02 + (i % 4) * 0.01,
    delay: `${(i * 1.3) % 8}s`,
    duration: `${6 + (i % 5) * 2}s`,
  }))

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {hearts.map((h, i) => (
        <Heart
          key={i}
          className="absolute animate-pulse fill-current text-pink-500"
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

// ═══════════════════════════════════════════════════════════════════════════════
// RARITY HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

const RARITY_CONFIG: Record<IntimateRarity, { text: string; icon: string; label: string; bg: string; badge: string }> = {
  COMMON:    { text: "text-pink-200/70",   icon: "text-pink-300/50",   label: "",          bg: "bg-white/[0.03]", badge: "" },
  UNCOMMON:  { text: "text-pink-200",      icon: "text-pink-300",      label: "Uncommon",  bg: "bg-pink-500/[0.04]", badge: "text-pink-300/60" },
  RARE:      { text: "text-rose-200",      icon: "text-rose-400",      label: "Rare",      bg: "bg-rose-500/[0.06]", badge: "text-rose-300/70" },
  EPIC:      { text: "text-red-200",       icon: "text-red-400",       label: "Epic",      bg: "bg-red-500/[0.07]", badge: "text-red-300/80" },
  LEGENDARY: { text: "text-amber-200",     icon: "text-amber-400",     label: "Legendary", bg: "bg-amber-500/[0.08]", badge: "text-amber-300/90" },
}

function RarityIcon({ rarity, unlocked }: { rarity: IntimateRarity; unlocked: boolean }) {
  if (!unlocked) return <Lock className="h-3.5 w-3.5 shrink-0 text-white/10" />
  switch (rarity) {
    case "LEGENDARY": return <Sparkles className="h-3.5 w-3.5 shrink-0 text-amber-400" />
    case "EPIC":      return <Flame className="h-3.5 w-3.5 shrink-0 text-red-400" />
    case "RARE":      return <Star className="h-3.5 w-3.5 shrink-0 text-rose-400" />
    default:          return <Heart className="h-3.5 w-3.5 shrink-0 text-pink-400 fill-pink-400/50" />
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// COLOR LERP
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
// MAIN PANEL
// ═══════════════════════════════════════════════════════════════════════════════

interface IntimateProgressionPanelProps {
  onClose: () => void
  unlockedIds?: Set<string>  // IDs of unlocked achievements (from backend later)
}

export default function IntimateProgressionPanel({ onClose, unlockedIds }: IntimateProgressionPanelProps) {
  const unlocked = unlockedIds ?? new Set<string>()
  const totalUnlocked = INTIMATE_ACHIEVEMENTS.filter(a => unlocked.has(a.id)).length
  const totalCount = INTIMATE_ACHIEVEMENTS.length

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
      `radial-gradient(ellipse 120% 80% at 50% 40%, rgba(${c[0]},${c[1]},${c[2]},0.12) 0%, rgba(${c[0]},${c[1]},${c[2]},0.03) 50%, transparent 100%)`
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
    <div className="fixed inset-0 z-[9999] flex flex-col" style={{ backgroundColor: "#0a0608" }}>
      {/* Floating hearts background */}
      <FloatingHearts />

      {/* Color tint overlay */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{ background: gradientOverlay, transition: "background 200ms ease" }}
      />

      {/* ── Back button ─────────────────────────────────────────────── */}
      <button
        onClick={onClose}
        className="absolute left-4 top-4 z-10 flex items-center gap-2 rounded-full bg-black/60 pl-3 pr-4 py-2.5 text-white/70 backdrop-blur-md border border-white/10 transition-all duration-200 hover:bg-black/80 hover:text-white hover:border-white/20 hover:scale-[1.03] active:scale-[0.97]"
      >
        <ArrowLeft className="h-4 w-4" />
        <span className="text-sm font-medium">Back</span>
      </button>

      {/* ── Floating counter pill ───────────────────────────────────── */}
      <div className="absolute right-4 top-4 z-10 flex items-center gap-2 rounded-full bg-black/60 px-4 py-2.5 backdrop-blur-md border border-pink-500/20">
        <Heart className="h-3.5 w-3.5 text-pink-400 fill-pink-400/60" />
        <span className="text-xs font-semibold text-white/80">{totalUnlocked} / {totalCount}</span>
        <span className="text-xs text-white/40">collected</span>
      </div>

      {/* ── Scrollable tiers ────────────────────────────────────────── */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto scroll-smooth">
        <div className="relative">

          {/* ── Heart-chain SVG connecting tiers ───────────────────── */}
          <svg
            aria-hidden
            className="pointer-events-none absolute inset-0 z-0 h-full w-full"
            viewBox={`0 0 600 ${TIERS.length * 1000}`}
            preserveAspectRatio="none"
            style={{ height: `${TIERS.length * 100}vh` }}
          >
            <defs>
              <linearGradient id="heartChainGrad" x1="0" y1="0" x2="0" y2="1">
                {TIER_COLORS.map((c, i) => (
                  <stop
                    key={i}
                    offset={`${(i / (TIERS.length - 1)) * 100}%`}
                    stopColor={`rgb(${c[0]},${c[1]},${c[2]})`}
                    stopOpacity={0.25}
                  />
                ))}
              </linearGradient>
            </defs>
            {/* Vertical pulsing line */}
            <line x1="300" y1="0" x2="300" y2={TIERS.length * 1000} stroke="url(#heartChainGrad)" strokeWidth="2" />
            {/* Heart dots at each tier center */}
            {TIERS.map((_, i) => {
              const cy = i * 1000 + 500
              const c = TIER_COLORS[i]
              return (
                <g key={i}>
                  <circle cx="300" cy={cy} r="12" fill={`rgba(${c[0]},${c[1]},${c[2]},0.15)`} />
                  <circle cx="300" cy={cy} r="6" fill={`rgba(${c[0]},${c[1]},${c[2]},0.4)`} />
                </g>
              )
            })}
          </svg>

          {TIERS.map((tier, tIdx) => {
            const color = tier.color
            const tierAchievements = ACHIEVEMENTS_BY_TIER[tIdx] ?? []
            const tierUnlocked = tierAchievements.filter(a => unlocked.has(a.id)).length

            return (
              <section
                key={tIdx}
                className="relative flex min-h-screen flex-col items-center justify-center px-6 md:px-16"
              >
                {/* Radial glow */}
                <div
                  className="pointer-events-none absolute inset-0"
                  style={{
                    background: `radial-gradient(circle at 50% 50%, rgba(${color[0]},${color[1]},${color[2]},0.07) 0%, transparent 70%)`,
                  }}
                />

                <div className="relative z-10 flex max-w-lg flex-col items-center text-center">
                  {/* Heart icon for tier */}
                  <div
                    className="mb-6 flex h-16 w-16 items-center justify-center rounded-full border md:h-20 md:w-20"
                    style={{
                      backgroundColor: `rgba(${color[0]},${color[1]},${color[2]},0.12)`,
                      borderColor: `rgba(${color[0]},${color[1]},${color[2]},0.25)`,
                      boxShadow: `0 0 40px 10px rgba(${color[0]},${color[1]},${color[2]},0.10)`,
                    }}
                  >
                    <Heart
                      className={cn("h-8 w-8 md:h-10 md:w-10 fill-current", tier.accentClass)}
                      style={{ filter: `drop-shadow(0 0 8px rgba(${color[0]},${color[1]},${color[2]},0.5))` }}
                    />
                  </div>

                  {/* Tier title */}
                  <h2 className="text-2xl font-bold tracking-tight text-white md:text-4xl">
                    {tier.title}
                  </h2>

                  {/* Progress */}
                  <p className="mt-2 text-sm font-medium text-white/30">
                    {tierUnlocked} / {tierAchievements.length} unlocked
                  </p>

                  {/* Divider with hearts */}
                  <div className="my-5 flex items-center gap-2">
                    <div className="h-px w-8 md:w-12" style={{ backgroundColor: `rgba(${color[0]},${color[1]},${color[2]},0.2)` }} />
                    <Heart className="h-3 w-3 fill-current" style={{ color: `rgba(${color[0]},${color[1]},${color[2]},0.3)` }} />
                    <div className="h-px w-8 md:w-12" style={{ backgroundColor: `rgba(${color[0]},${color[1]},${color[2]},0.2)` }} />
                  </div>

                  {/* Subtitle */}
                  <p className="max-w-sm text-sm leading-relaxed text-white/40 md:text-base">
                    {tier.subtitle}
                  </p>

                  {/* ── Achievement collection grid ──────────────────── */}
                  <div className="mt-8 w-full max-w-md space-y-2.5">
                    {tierAchievements.map((a) => {
                      const isUnlocked = unlocked.has(a.id)
                      const cfg = RARITY_CONFIG[a.rarity]

                      return (
                        <div
                          key={a.id}
                          className={cn(
                            "group flex items-stretch gap-0 rounded-xl overflow-hidden transition-all duration-300",
                            isUnlocked ? cfg.bg : "bg-white/[0.02]",
                            "ring-1",
                            isUnlocked && a.rarity === "LEGENDARY" && "ring-amber-500/25",
                            isUnlocked && a.rarity === "EPIC" && "ring-red-500/20",
                            isUnlocked && a.rarity === "RARE" && "ring-rose-500/15",
                            isUnlocked && (a.rarity === "UNCOMMON" || a.rarity === "COMMON") && "ring-pink-500/10",
                            !isUnlocked && "ring-white/[0.04]",
                          )}
                        >
                          {/* Photo thumbnail */}
                          <div className={cn(
                            "relative flex h-[72px] w-[72px] shrink-0 items-center justify-center overflow-hidden",
                            isUnlocked
                              ? "bg-gradient-to-br from-pink-900/40 to-rose-900/30"
                              : "bg-white/[0.03]",
                          )}>
                            {isUnlocked ? (
                              /* When unlocked — placeholder showing scene will be generated */
                              <div className="flex flex-col items-center justify-center gap-1">
                                <Heart className="h-5 w-5 fill-current text-pink-400/50" />
                                <span className="text-[7px] font-medium text-pink-300/40 uppercase tracking-wider">Photo</span>
                              </div>
                            ) : (
                              /* When locked — silhouette/blur placeholder */
                              <div className="flex flex-col items-center justify-center gap-1">
                                <ImageIcon className="h-5 w-5 text-white/10" />
                                <Lock className="h-2.5 w-2.5 text-white/10" />
                              </div>
                            )}
                            {/* Rarity strip on the left edge */}
                            <div
                              className={cn(
                                "absolute left-0 top-0 h-full w-[3px]",
                                isUnlocked && a.rarity === "LEGENDARY" && "bg-amber-400/60",
                                isUnlocked && a.rarity === "EPIC" && "bg-red-400/50",
                                isUnlocked && a.rarity === "RARE" && "bg-rose-400/40",
                                isUnlocked && a.rarity === "UNCOMMON" && "bg-pink-400/30",
                                isUnlocked && a.rarity === "COMMON" && "bg-pink-300/20",
                                !isUnlocked && "bg-white/[0.04]",
                              )}
                            />
                          </div>

                          {/* Content area */}
                          <div className="flex min-w-0 flex-1 items-center gap-3 px-3.5 py-3">
                            {/* Rarity icon */}
                            <RarityIcon rarity={a.rarity} unlocked={isUnlocked} />

                            {/* Text */}
                            <div className="min-w-0 flex-1 text-left">
                              <div className="flex items-center gap-1.5">
                                <p className={cn(
                                  "text-xs font-semibold truncate",
                                  isUnlocked ? cfg.text : "text-white/40",
                                )}>
                                  {a.title}
                                </p>
                                {cfg.label && (
                                  <span className={cn(
                                    "text-[9px] uppercase tracking-wider font-medium shrink-0",
                                    isUnlocked ? cfg.badge : "text-white/15",
                                  )}>
                                    {cfg.label}
                                  </span>
                                )}
                              </div>
                              <p className={cn(
                                "text-[10px] truncate",
                                isUnlocked ? "text-white/35" : "text-white/20",
                              )}>
                                {a.subtitle}
                              </p>
                            </div>

                            {/* Heart / lock badge */}
                            {isUnlocked ? (
                              <Heart className="h-3.5 w-3.5 shrink-0 fill-current text-pink-400/70" />
                            ) : (
                              <Lock className="h-3 w-3 shrink-0 text-white/15" />
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Scroll hint on first tier */}
                {tIdx === 0 && (
                  <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce text-pink-400/20">
                    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                    </svg>
                  </div>
                )}
              </section>
            )
          })}
        </div>
      </div>
    </div>
  )
}
