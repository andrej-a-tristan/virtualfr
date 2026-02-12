import { useState, useEffect, useCallback, useRef } from "react"
import { createPortal } from "react-dom"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useSearchParams } from "react-router-dom"
import { getChatHistory, getChatState, getGallery, getAchievementsCatalog } from "@/lib/api/endpoints"
import { useChatStore } from "@/lib/store/useChatStore"
import { useAppStore } from "@/lib/store/useAppStore"
import ChatHeader from "@/components/chat/ChatHeader"
import MessageList from "@/components/chat/MessageList"
import Composer from "@/components/chat/Composer"
import GalleryGrid from "@/components/gallery/GalleryGrid"
import ImageViewerModal from "@/components/gallery/ImageViewerModal"
import type { GalleryItem, RegionKey, RelationshipState, AchievementsByRegion, RelationshipAchievement, AchievementRarity } from "@/lib/api/types"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import {
  MessageCircle,
  Image as ImageIcon,
  Gift,
  ArrowLeft,
  Heart,
  Sparkles,
  Sun,
  Shield,
  Flame,
  Star,
  Infinity as InfinityIcon,
  Gem,
  Crown,
  Trophy,
  Lock,
  CheckCircle2,
  ChevronDown,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import IntimateProgressionPanel from "@/components/chat/IntimateProgressionPanel"
import GiftCollectionPanel from "@/components/chat/GiftCollectionPanel"
import MysteryBoxPanel from "@/components/chat/MysteryBoxPanel"
import MilestoneInbox from "@/components/chat/MilestoneInbox"

type Tab = "chat" | "gallery"

// ═══════════════════════════════════════════════════════════════════════════════
// Region data & theme definitions
// ═══════════════════════════════════════════════════════════════════════════════

type RegionDef = {
  key: RegionKey
  title: string
  levelRange: string
  subtitle: string
  icon: React.ReactNode
  accentClass: string
}

const REGIONS: RegionDef[] = [
  { key: "EARLY_CONNECTION",       title: "Early Connection",       levelRange: "1–10",   subtitle: "Warmth, safety, and quick bonding.",           icon: <Sparkles className="h-4 w-4" />,      accentClass: "text-emerald-400" },
  { key: "COMFORT_FAMILIARITY",    title: "Comfort & Familiarity",  levelRange: "11–25",  subtitle: "Ease and recognition. Becoming familiar.",     icon: <Sun className="h-4 w-4" />,            accentClass: "text-green-400" },
  { key: "GROWING_CLOSENESS",      title: "Growing Closeness",      levelRange: "26–45",  subtitle: "Deeper conversations, early vulnerability.",   icon: <Heart className="h-4 w-4" />,          accentClass: "text-lime-400" },
  { key: "EMOTIONAL_TRUST",        title: "Emotional Trust",        levelRange: "46–70",  subtitle: "Real openness. Sharing what matters.",         icon: <Shield className="h-4 w-4" />,         accentClass: "text-sky-400" },
  { key: "DEEP_BOND",              title: "Deep Bond",              levelRange: "71–105", subtitle: "Routines, strong attachment, rich callbacks.",  icon: <Flame className="h-4 w-4" />,          accentClass: "text-amber-400" },
  { key: "MUTUAL_DEVOTION",        title: "Mutual Devotion",        levelRange: "106–135",subtitle: "Belonging. Steady devotion without question.",  icon: <Star className="h-4 w-4" />,           accentClass: "text-rose-400" },
  { key: "INTIMATE_PARTNERSHIP",   title: "Intimate Partnership",   levelRange: "136–165",subtitle: "Quiet permanence. Nuance, trust, comfort.",    icon: <InfinityIcon className="h-4 w-4" />,   accentClass: "text-purple-400" },
  { key: "SHARED_LIFE",            title: "Shared Life",            levelRange: "166–185",subtitle: "Intertwined routines. A life together.",       icon: <Gem className="h-4 w-4" />,            accentClass: "text-violet-400" },
  { key: "ENDURING_COMPANIONSHIP", title: "Enduring Companionship", levelRange: "186–200",subtitle: "Timeless bond. Everything has been said.",     icon: <Crown className="h-4 w-4" />,          accentClass: "text-slate-300" },
]

function regionIdx(key: RegionKey): number {
  return REGIONS.findIndex((r) => r.key === key)
}

// ═══════════════════════════════════════════════════════════════════════════════
// Color interpolation for scroll-based gradient
// ═══════════════════════════════════════════════════════════════════════════════

// RGB tuples for each region's primary color (dark-friendly, rich)
const REGION_COLORS: [number, number, number][] = [
  [16, 185, 129],   // EARLY_CONNECTION — emerald
  [34, 197, 94],    // COMFORT_FAMILIARITY — green
  [132, 204, 22],   // GROWING_CLOSENESS — lime
  [14, 165, 233],   // EMOTIONAL_TRUST — sky
  [245, 158, 11],   // DEEP_BOND — amber
  [244, 63, 94],    // MUTUAL_DEVOTION — rose
  [168, 85, 247],   // INTIMATE_PARTNERSHIP — purple
  [139, 92, 246],   // SHARED_LIFE — violet
  [148, 163, 184],  // ENDURING_COMPANIONSHIP — slate
]

function lerpColor(
  a: [number, number, number],
  b: [number, number, number],
  t: number
): [number, number, number] {
  return [
    Math.round(a[0] + (b[0] - a[0]) * t),
    Math.round(a[1] + (b[1] - a[1]) * t),
    Math.round(a[2] + (b[2] - a[2]) * t),
  ]
}

// ═══════════════════════════════════════════════════════════════════════════════
// Beautiful floating relationship button (right side of chat)
// ═══════════════════════════════════════════════════════════════════════════════

function RelationshipButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "group relative hidden md:flex flex-col items-center justify-center gap-2.5",
        "w-[4.5rem] rounded-2xl border border-pink-500/15",
        "bg-gradient-to-b from-pink-500/8 via-purple-500/5 to-rose-500/8",
        "px-1.5 py-6 transition-all duration-500 ease-out",
        "hover:border-pink-500/35",
        "hover:bg-gradient-to-b hover:from-pink-500/15 hover:via-purple-500/8 hover:to-rose-500/12",
        "hover:shadow-[0_0_40px_6px_rgba(236,72,153,0.14),inset_0_0_30px_0_rgba(236,72,153,0.04)]",
        "hover:scale-[1.04] active:scale-[0.97]",
      )}
    >
      {/* Outer glow ring */}
      <div className="absolute -inset-px rounded-2xl bg-gradient-to-b from-pink-500/10 via-transparent to-purple-500/10 opacity-0 transition-opacity duration-500 group-hover:opacity-100" />

      {/* Heart orb */}
      <div className="relative">
        <div className="absolute -inset-2 animate-pulse rounded-full bg-pink-500/15 blur-lg transition-all group-hover:bg-pink-500/25 group-hover:blur-xl" />
        <div className="relative flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-pink-500 via-rose-500 to-pink-600 shadow-lg shadow-pink-500/30 ring-2 ring-pink-400/15 transition-all duration-300 group-hover:shadow-pink-500/50 group-hover:ring-pink-400/30">
          <Heart className="h-5 w-5 text-white fill-white/90 drop-shadow-sm" />
        </div>
      </div>

      {/* Label — vertical */}
      <div className="relative flex flex-col items-center gap-0.5">
        <span className="text-[9px] font-bold uppercase tracking-[0.08em] text-white/55 transition-colors group-hover:text-pink-200/80">
          My
        </span>
        <span className="text-[8px] font-bold uppercase tracking-[0.06em] text-white/40 transition-colors group-hover:text-pink-200/60">
          Relationship
        </span>
      </div>

      {/* Shimmer line */}
      <div className="h-px w-8 bg-gradient-to-r from-transparent via-pink-400/20 to-transparent transition-all group-hover:via-pink-400/50" />
    </button>
  )
}

// Desktop intimate button — shows only when 18+
function IntimateButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "group relative hidden md:flex flex-col items-center justify-center gap-2.5",
        "w-[4.5rem] rounded-2xl border border-rose-500/15",
        "bg-gradient-to-b from-rose-500/8 via-red-500/5 to-pink-500/8",
        "px-1.5 py-6 transition-all duration-500 ease-out",
        "hover:border-rose-500/35",
        "hover:bg-gradient-to-b hover:from-rose-500/15 hover:via-red-500/8 hover:to-pink-500/12",
        "hover:shadow-[0_0_40px_6px_rgba(244,63,94,0.14),inset_0_0_30px_0_rgba(244,63,94,0.04)]",
        "hover:scale-[1.04] active:scale-[0.97]",
      )}
    >
      {/* Outer glow ring */}
      <div className="absolute -inset-px rounded-2xl bg-gradient-to-b from-rose-500/10 via-transparent to-red-500/10 opacity-0 transition-opacity duration-500 group-hover:opacity-100" />

      {/* Flame orb */}
      <div className="relative">
        <div className="absolute -inset-2 animate-pulse rounded-full bg-rose-500/15 blur-lg transition-all group-hover:bg-rose-500/25 group-hover:blur-xl" />
        <div className="relative flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-rose-500 via-red-500 to-pink-600 shadow-lg shadow-rose-500/30 ring-2 ring-rose-400/15 transition-all duration-300 group-hover:shadow-rose-500/50 group-hover:ring-rose-400/30">
          <Flame className="h-5 w-5 text-white drop-shadow-sm" />
        </div>
      </div>

      {/* Label — vertical */}
      <div className="relative flex flex-col items-center gap-0.5">
        <span className="text-[9px] font-bold uppercase tracking-[0.08em] text-white/55 transition-colors group-hover:text-rose-200/80">
          Intimate
        </span>
        <span className="text-[8px] font-bold uppercase tracking-[0.06em] text-white/40 transition-colors group-hover:text-rose-200/60">
          Progression
        </span>
      </div>

      {/* Shimmer line */}
      <div className="h-px w-8 bg-gradient-to-r from-transparent via-rose-400/20 to-transparent transition-all group-hover:via-rose-400/50" />
    </button>
  )
}

// Mobile version — horizontal strip
function RelationshipButtonMobile({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex md:hidden items-center gap-3 w-full mt-3",
        "rounded-xl border border-pink-500/15 px-4 py-3",
        "bg-gradient-to-r from-pink-500/8 via-purple-500/5 to-rose-500/8",
        "transition-all duration-300",
        "hover:border-pink-500/30 hover:shadow-[0_0_24px_3px_rgba(236,72,153,0.12)]",
        "active:scale-[0.98]",
      )}
    >
      <div className="relative">
        <div className="absolute -inset-1 animate-pulse rounded-full bg-pink-500/20 blur-md" />
        <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-pink-500 via-rose-500 to-pink-600 shadow-lg shadow-pink-500/30 ring-1 ring-pink-400/20">
          <Heart className="h-4 w-4 text-white fill-white/90" />
        </div>
      </div>
      <span className="text-sm font-semibold text-white/80">My Relationship</span>
      <span className="ml-auto text-white/20 text-lg">&rsaquo;</span>
    </button>
  )
}

// Desktop gift collection button
function GiftCollectionButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "group relative hidden md:flex flex-col items-center justify-center gap-2.5",
        "w-[4.5rem] rounded-2xl border border-purple-500/15",
        "bg-gradient-to-b from-purple-500/8 via-indigo-500/5 to-violet-500/8",
        "px-1.5 py-6 transition-all duration-500 ease-out",
        "hover:border-purple-500/35",
        "hover:bg-gradient-to-b hover:from-purple-500/15 hover:via-indigo-500/8 hover:to-violet-500/12",
        "hover:shadow-[0_0_40px_6px_rgba(168,85,247,0.14),inset_0_0_30px_0_rgba(168,85,247,0.04)]",
        "hover:scale-[1.04] active:scale-[0.97]",
      )}
    >
      {/* Outer glow ring */}
      <div className="absolute -inset-px rounded-2xl bg-gradient-to-b from-purple-500/10 via-transparent to-indigo-500/10 opacity-0 transition-opacity duration-500 group-hover:opacity-100" />

      {/* Gift orb */}
      <div className="relative">
        <div className="absolute -inset-2 animate-pulse rounded-full bg-purple-500/15 blur-lg transition-all group-hover:bg-purple-500/25 group-hover:blur-xl" />
        <div className="relative flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 via-indigo-500 to-violet-600 shadow-lg shadow-purple-500/30 ring-2 ring-purple-400/15 transition-all duration-300 group-hover:shadow-purple-500/50 group-hover:ring-purple-400/30">
          <Gift className="h-5 w-5 text-white drop-shadow-sm" />
        </div>
      </div>

      {/* Label — vertical */}
      <div className="relative flex flex-col items-center gap-0.5">
        <span className="text-[9px] font-bold uppercase tracking-[0.08em] text-white/55 transition-colors group-hover:text-purple-200/80">
          Gift
        </span>
        <span className="text-[8px] font-bold uppercase tracking-[0.06em] text-white/40 transition-colors group-hover:text-purple-200/60">
          Collection
        </span>
      </div>

      {/* Shimmer line */}
      <div className="h-px w-8 bg-gradient-to-r from-transparent via-purple-400/20 to-transparent transition-all group-hover:via-purple-400/50" />
    </button>
  )
}

// Mobile intimate button — horizontal strip (18+ only)
function IntimateButtonMobile({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex md:hidden items-center gap-3 w-full mt-2",
        "rounded-xl border border-rose-500/15 px-4 py-3",
        "bg-gradient-to-r from-rose-500/8 via-red-500/5 to-pink-500/8",
        "transition-all duration-300",
        "hover:border-rose-500/30 hover:shadow-[0_0_24px_3px_rgba(244,63,94,0.12)]",
        "active:scale-[0.98]",
      )}
    >
      <div className="relative">
        <div className="absolute -inset-1 animate-pulse rounded-full bg-rose-500/20 blur-md" />
        <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-rose-500 via-red-500 to-pink-600 shadow-lg shadow-rose-500/30 ring-1 ring-rose-400/20">
          <Flame className="h-4 w-4 text-white" />
        </div>
      </div>
      <span className="text-sm font-semibold text-white/80">Intimate Progression</span>
      <span className="ml-auto text-white/20 text-lg">&rsaquo;</span>
    </button>
  )
}

// Mobile gift collection button — horizontal strip
function GiftCollectionButtonMobile({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex md:hidden items-center gap-3 w-full mt-2",
        "rounded-xl border border-purple-500/15 px-4 py-3",
        "bg-gradient-to-r from-purple-500/8 via-indigo-500/5 to-violet-500/8",
        "transition-all duration-300",
        "hover:border-purple-500/30 hover:shadow-[0_0_24px_3px_rgba(168,85,247,0.12)]",
        "active:scale-[0.98]",
      )}
    >
      <div className="relative">
        <div className="absolute -inset-1 animate-pulse rounded-full bg-purple-500/20 blur-md" />
        <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 via-indigo-500 to-violet-600 shadow-lg shadow-purple-500/30 ring-1 ring-purple-400/20">
          <Gift className="h-4 w-4 text-white" />
        </div>
      </div>
      <span className="text-sm font-semibold text-white/80">Gift Collection</span>
      <span className="ml-auto text-white/20 text-lg">&rsaquo;</span>
    </button>
  )
}

// Desktop surprise her sidebar button
function MysteryBoxButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "group relative flex flex-col items-center gap-2.5 rounded-2xl border border-cyan-500/20",
        "w-16 bg-gradient-to-b from-cyan-500/8 via-purple-500/5 to-blue-500/8",
        "px-1.5 py-6 transition-all duration-500 ease-out",
        "hover:border-cyan-400/35",
        "hover:bg-gradient-to-b hover:from-cyan-500/15 hover:via-purple-500/8 hover:to-blue-500/12",
        "hover:shadow-[0_0_40px_6px_rgba(56,189,248,0.14),inset_0_0_30px_0_rgba(56,189,248,0.04)]",
        "hover:scale-[1.04] active:scale-[0.97]",
      )}
    >
      <div className="absolute -inset-px rounded-2xl bg-gradient-to-b from-cyan-500/10 via-transparent to-purple-500/10 opacity-0 transition-opacity duration-500 group-hover:opacity-100" />
      <div className="relative">
        <div className="absolute -inset-2 animate-pulse rounded-full bg-cyan-500/15 blur-lg transition-all group-hover:bg-cyan-500/25 group-hover:blur-xl" />
        <div className="relative flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600 shadow-lg shadow-cyan-500/30 ring-2 ring-cyan-400/15 transition-all duration-300 group-hover:shadow-cyan-500/50 group-hover:ring-cyan-400/30">
          <span className="text-lg">🌸</span>
        </div>
      </div>
      <div className="relative flex flex-col items-center gap-0.5">
        <span className="text-[9px] font-bold uppercase tracking-[0.08em] text-white/55 transition-colors group-hover:text-cyan-200/80">
          Surprise
        </span>
        <span className="text-[8px] font-bold uppercase tracking-[0.06em] text-white/40 transition-colors group-hover:text-cyan-200/60">
          Her
        </span>
      </div>
      <div className="h-px w-8 bg-gradient-to-r from-transparent via-cyan-400/20 to-transparent transition-all group-hover:via-cyan-400/50" />
    </button>
  )
}

// Mobile surprise her button — horizontal strip
function MysteryBoxButtonMobile({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex md:hidden items-center gap-3 w-full mt-2",
        "rounded-xl border border-cyan-500/15 px-4 py-3",
        "bg-gradient-to-r from-cyan-500/8 via-blue-500/5 to-purple-500/8",
        "transition-all duration-300",
        "hover:border-cyan-400/30 hover:shadow-[0_0_24px_3px_rgba(56,189,248,0.12)]",
        "active:scale-[0.98]",
      )}
    >
      <div className="relative">
        <div className="absolute -inset-1 animate-pulse rounded-full bg-cyan-500/20 blur-md" />
        <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600 shadow-lg shadow-cyan-500/30 ring-1 ring-cyan-400/20">
          <span className="text-sm">🌸</span>
        </div>
      </div>
      <span className="text-sm font-semibold text-white/80">Surprise Her</span>
      <span className="ml-auto text-white/20 text-lg">&rsaquo;</span>
    </button>
  )
}

// Desktop "Seduce Her Now" sidebar button
function SeduceHerButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "group relative flex flex-col items-center gap-2.5 rounded-2xl border border-red-500/25",
        "w-16 bg-gradient-to-b from-red-500/10 via-rose-500/6 to-pink-500/10",
        "px-1.5 py-6 transition-all duration-500 ease-out",
        "hover:border-red-400/40",
        "hover:bg-gradient-to-b hover:from-red-500/18 hover:via-rose-500/10 hover:to-pink-500/15",
        "hover:shadow-[0_0_40px_6px_rgba(239,68,68,0.18),inset_0_0_30px_0_rgba(239,68,68,0.05)]",
        "hover:scale-[1.04] active:scale-[0.97]",
      )}
    >
      <div className="absolute -inset-px rounded-2xl bg-gradient-to-b from-red-500/10 via-transparent to-pink-500/10 opacity-0 transition-opacity duration-500 group-hover:opacity-100" />
      <div className="relative">
        <div className="absolute -inset-2 animate-pulse rounded-full bg-red-500/20 blur-lg transition-all group-hover:bg-red-500/30 group-hover:blur-xl" style={{ animationDuration: "2s" }} />
        <div className="relative flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-red-500 via-rose-600 to-pink-600 shadow-lg shadow-red-500/30 ring-2 ring-red-400/20 transition-all duration-300 group-hover:shadow-red-500/50 group-hover:ring-red-400/35">
          <Flame className="h-5 w-5 text-white drop-shadow-sm" />
        </div>
      </div>
      <div className="relative flex flex-col items-center gap-0.5">
        <span className="text-[9px] font-bold uppercase tracking-[0.08em] text-white/60 transition-colors group-hover:text-red-200/80">
          Seduce
        </span>
        <span className="text-[8px] font-bold uppercase tracking-[0.06em] text-white/45 transition-colors group-hover:text-red-200/65">
          Her Now
        </span>
      </div>
      <div className="h-px w-8 bg-gradient-to-r from-transparent via-red-400/25 to-transparent transition-all group-hover:via-red-400/55" />
    </button>
  )
}

// Mobile "Seduce Her Now" button — horizontal strip
function SeduceHerButtonMobile({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex md:hidden items-center gap-3 w-full mt-2",
        "rounded-xl border border-red-500/20 px-4 py-3",
        "bg-gradient-to-r from-red-500/10 via-rose-500/6 to-pink-500/10",
        "transition-all duration-300",
        "hover:border-red-400/35 hover:shadow-[0_0_24px_3px_rgba(239,68,68,0.15)]",
        "active:scale-[0.98]",
      )}
    >
      <div className="relative">
        <div className="absolute -inset-1 animate-pulse rounded-full bg-red-500/25 blur-md" style={{ animationDuration: "2s" }} />
        <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-red-500 via-rose-600 to-pink-600 shadow-lg shadow-red-500/30 ring-1 ring-red-400/20">
          <Flame className="h-4 w-4 text-white" />
        </div>
      </div>
      <div className="flex flex-col">
        <span className="text-sm font-semibold text-white/80">Seduce Her Now</span>
        <span className="text-[10px] text-white/35">Unlock intimate achievements early</span>
      </div>
      <span className="ml-auto text-white/20 text-lg">&rsaquo;</span>
    </button>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Soft floating Lucide icons — elegant romantic wallpaper
// ═══════════════════════════════════════════════════════════════════════════════

const FLOAT_ICONS = [Heart, Sparkles, Star, Flame, Heart, Sparkles, Heart, Star] as const

function FloatingRomanticIcons() {
  const items = Array.from({ length: 35 }, (_, i) => ({
    Icon: FLOAT_ICONS[i % FLOAT_ICONS.length],
    left: `${(i * 31 + 11) % 100}%`,
    top: `${(i * 47 + 19) % 100}%`,
    size: 12 + (i % 5) * 4,
    opacity: 0.03 + (i % 4) * 0.01,
    rotation: (i * 67) % 360,
    delay: `${(i * 1.9) % 10}s`,
    dur: `${8 + (i % 5) * 3}s`,
    fill: i % 3 === 0,
    color: REGION_COLORS[i % REGION_COLORS.length],
  }))

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {items.map((it, i) => (
        <it.Icon
          key={i}
          className={cn("absolute animate-pulse", it.fill && "fill-current")}
          style={{
            left: it.left,
            top: it.top,
            width: it.size,
            height: it.size,
            opacity: it.opacity,
            transform: `rotate(${it.rotation}deg)`,
            color: `rgba(${it.color[0]},${it.color[1]},${it.color[2]},0.6)`,
            animationDelay: it.delay,
            animationDuration: it.dur,
          }}
        />
      ))}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Fullscreen immersive relationship timeline
// Each region = full viewport. Scroll-based color interpolation.
// ═══════════════════════════════════════════════════════════════════════════════

function RelationshipPanel({ onClose }: { onClose: () => void }) {
  const currentGirlfriendId = useAppStore((s) => s.currentGirlfriendId)

  const { data: relState, isLoading } = useQuery<RelationshipState>({
    queryKey: ["chatState", currentGirlfriendId],
    queryFn: () => getChatState(currentGirlfriendId ?? undefined),
    enabled: !!currentGirlfriendId,
    staleTime: 30_000,
  })

  // Fetch achievement catalog
  const { data: catalogData } = useQuery({
    queryKey: ["achievementsCatalog"],
    queryFn: getAchievementsCatalog,
    staleTime: 60_000 * 10, // catalog rarely changes
  })

  const achievementsByRegion: AchievementsByRegion = catalogData?.achievements_by_region ?? {}
  const milestonesReached = new Set(relState?.milestones_reached ?? [])

  const level = relState?.level ?? 0
  const currentRegion: RegionKey = relState?.region_key ?? "EARLY_CONNECTION"
  const regionTitle = relState?.region_title ?? REGIONS[0].title
  const curIdx = relState?.current_region_index ?? regionIdx(currentRegion)

  // Scroll-based color interpolation
  const scrollRef = useRef<HTMLDivElement>(null)
  const [gradientOverlay, setGradientOverlay] = useState("")

  const handleScroll = useCallback(() => {
    const el = scrollRef.current
    if (!el) return
    const scrollTop = el.scrollTop
    const vh = el.clientHeight
    // Each section is 100vh tall; figure out which two regions we're between
    const rawIdx = scrollTop / vh
    const idx = Math.min(Math.floor(rawIdx), REGIONS.length - 1)
    const nextIdx = Math.min(idx + 1, REGIONS.length - 1)
    const t = rawIdx - idx // 0..1 within current section

    const c = lerpColor(REGION_COLORS[idx], REGION_COLORS[nextIdx], t)
    // Subtle color tint overlay (the solid base color is set separately)
    setGradientOverlay(
      `radial-gradient(ellipse 120% 80% at 50% 40%, rgba(${c[0]},${c[1]},${c[2]},0.14) 0%, rgba(${c[0]},${c[1]},${c[2]},0.04) 50%, transparent 100%)`
    )
  }, [])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    handleScroll() // init
    el.addEventListener("scroll", handleScroll, { passive: true })
    return () => el.removeEventListener("scroll", handleScroll)
  }, [handleScroll])

  // Lock body scroll while panel is open
  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => { document.body.style.overflow = prev }
  }, [])

  if (isLoading) {
    return (
      <div className="fixed inset-0 z-[9999] flex items-center justify-center" style={{ backgroundColor: "#08080c" }}>
        <div className="space-y-4 text-center">
          <div className="mx-auto h-12 w-12 animate-pulse rounded-full bg-pink-500/20" />
          <Skeleton className="mx-auto h-5 w-40" />
        </div>
      </div>
    )
  }

  // Compute total achievements unlocked across all regions
  const totalAchievements = Object.values(achievementsByRegion).reduce((s, arr) => s + arr.length, 0)
  const totalUnlocked = Object.values(achievementsByRegion).reduce(
    (s, arr) => s + arr.filter(a => milestonesReached.has(a.id)).length, 0
  )

  return (
    <div
      className="fixed inset-0 z-[9999] flex flex-col"
      style={{ backgroundColor: "#06060b" }}
    >
      {/* Soft floating romantic icons */}
      <FloatingRomanticIcons />

      {/* Color tint overlay */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{ background: gradientOverlay, transition: "background 300ms ease" }}
      />

      {/* ── Top bar with glass effect ──────────────────────────────────── */}
      <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between px-4 py-3 backdrop-blur-xl bg-black/40 border-b border-white/[0.06]">
        <button
          onClick={onClose}
          className="flex items-center gap-2 rounded-full bg-white/[0.06] pl-3 pr-4 py-2 text-white/70 border border-white/[0.08] transition-all duration-200 hover:bg-white/10 hover:text-white hover:scale-[1.03] active:scale-[0.97]"
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm font-medium">Back</span>
        </button>

        <div className="flex items-center gap-3">
          {/* Level pill */}
          <div className="flex items-center gap-2 rounded-full bg-white/[0.06] px-4 py-2 border border-white/[0.08]">
            <Heart className="h-3.5 w-3.5 text-pink-400 fill-pink-400/60" />
            <span className="text-xs font-bold text-white/90">Lv. {level}</span>
          </div>
          {/* Achievement counter */}
          <div className="flex items-center gap-2 rounded-full bg-white/[0.06] px-4 py-2 border border-white/[0.08]">
            <Trophy className="h-3.5 w-3.5 text-amber-400" />
            <span className="text-xs font-bold text-white/90">{totalUnlocked}</span>
            <span className="text-xs text-white/40">/ {totalAchievements}</span>
          </div>
        </div>
      </div>

      {/* ── Scrollable sections ────────────────────────────────────────── */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto scroll-smooth pt-14">
        <div className="relative">

          {/* ── How it works hero section ──────────────────────────────── */}
          <div className="relative flex flex-col items-center px-6 md:px-12 pt-12 pb-16 md:pt-20 md:pb-24 text-center">
            <div className="pointer-events-none absolute inset-0" style={{
              background: "radial-gradient(ellipse 100% 70% at 50% 30%, rgba(236,72,153,0.08) 0%, transparent 70%)",
            }} />

            <div className="relative z-10 max-w-lg space-y-5">
              {/* Animated icon cluster */}
              <div className="flex items-center justify-center gap-3 mb-2">
                <Heart className="h-5 w-5 text-pink-400/60 fill-pink-400/30 animate-pulse" style={{ animationDuration: "3s" }} />
                <Sparkles className="h-7 w-7 text-pink-300/50 animate-pulse" style={{ animationDuration: "4s", animationDelay: "0.5s" }} />
                <Heart className="h-5 w-5 text-pink-400/60 fill-pink-400/30 animate-pulse" style={{ animationDuration: "3.5s", animationDelay: "1s" }} />
              </div>

              <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white/90">
                Your Relationship Story
              </h1>

              <p className="text-base md:text-lg leading-relaxed text-white/50">
                Every meaningful moment between you and her is remembered.
                Show affection, be vulnerable, earn her trust — and watch your story unfold.
              </p>

              {/* How it works cards */}
              <div className="grid gap-3 pt-3">
                <div className="flex items-start gap-3 rounded-xl bg-white/[0.03] border border-white/[0.06] p-3.5 text-left">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-pink-500/10">
                    <Heart className="h-4 w-4 text-pink-400" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white/70">Emotional milestones</p>
                    <p className="text-xs text-white/35 mt-0.5">Achievements unlock when she detects real emotional signals — compliments, vulnerability, support, commitment. No grinding, no faking it.</p>
                  </div>
                </div>

                <div className="flex items-start gap-3 rounded-xl bg-white/[0.03] border border-white/[0.06] p-3.5 text-left">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-amber-500/10">
                    <Trophy className="h-4 w-4 text-amber-400" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white/70">Independent from your level</p>
                    <p className="text-xs text-white/35 mt-0.5">Achievements and levels are completely separate. Your level doesn't unlock achievements, and achievements don't affect your level. Both grow from how you treat her.</p>
                  </div>
                </div>

                <div className="flex items-start gap-3 rounded-xl bg-white/[0.03] border border-white/[0.06] p-3.5 text-left">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-500/10">
                    <Sparkles className="h-4 w-4 text-violet-400" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white/70">Never miss an achievement</p>
                    <p className="text-xs text-white/35 mt-0.5">Achievements from earlier stages can still unlock later. Keep being genuine and they'll come naturally — some are even hidden secrets.</p>
                  </div>
                </div>
              </div>

              {/* Scroll prompt */}
              <div className="flex flex-col items-center pt-4 animate-bounce" style={{ animationDuration: "2.5s" }}>
                <ChevronDown className="h-5 w-5 text-white/20" />
                <span className="text-[10px] uppercase tracking-widest text-white/20 font-medium mt-1">Scroll to explore</span>
              </div>
            </div>
          </div>

          {REGIONS.map((region, rIdx) => {
            const isCurrent = rIdx === curIdx
            const isPast = rIdx < curIdx
            const isFuture = rIdx > curIdx
            const color = REGION_COLORS[rIdx]
            const regionAchievements: RelationshipAchievement[] = achievementsByRegion[rIdx] ?? []
            const tierUnlocked = regionAchievements.filter(a => milestonesReached.has(a.id)).length
            const tierTotal = regionAchievements.length

            return (
              <section
                key={region.key}
                className="relative flex flex-col items-center px-4 md:px-12 py-16 md:py-24"
              >
                {/* Big dramatic radial glow */}
                <div
                  className="pointer-events-none absolute inset-0"
                  style={{
                    background: `
                      radial-gradient(ellipse 100% 60% at 50% 20%, rgba(${color[0]},${color[1]},${color[2]},${isCurrent ? 0.14 : 0.06}) 0%, transparent 70%),
                      radial-gradient(circle at 50% 80%, rgba(${color[0]},${color[1]},${color[2]},0.03) 0%, transparent 60%)
                    `,
                  }}
                />

                {/* ── Region header card ─────────────────────────────────── */}
                <div
                  className={cn(
                    "relative z-10 w-full max-w-xl rounded-3xl border p-6 md:p-8 mb-6 overflow-hidden transition-all duration-500",
                    isCurrent && "scale-[1.02]",
                    isFuture && "opacity-40",
                  )}
                  style={{
                    backgroundColor: `rgba(${color[0]},${color[1]},${color[2]},${isCurrent ? 0.06 : 0.03})`,
                    borderColor: `rgba(${color[0]},${color[1]},${color[2]},${isCurrent ? 0.25 : 0.10})`,
                    boxShadow: isCurrent
                      ? `0 0 80px 20px rgba(${color[0]},${color[1]},${color[2]},0.08), inset 0 1px 0 rgba(255,255,255,0.04)`
                      : `inset 0 1px 0 rgba(255,255,255,0.02)`,
                  }}
                >
                  {/* Inner glow effect */}
                  <div
                    className="pointer-events-none absolute -top-20 left-1/2 -translate-x-1/2 h-40 w-[120%] rounded-full blur-3xl"
                    style={{
                      backgroundColor: `rgba(${color[0]},${color[1]},${color[2]},${isCurrent ? 0.12 : 0.04})`,
                    }}
                  />

                  <div className="relative flex flex-col items-center text-center">
                    {/* Region icon orb */}
                    <div
                      className="mb-5 flex h-20 w-20 md:h-24 md:w-24 items-center justify-center rounded-full border-2"
                      style={{
                        backgroundColor: `rgba(${color[0]},${color[1]},${color[2]},0.12)`,
                        borderColor: `rgba(${color[0]},${color[1]},${color[2]},${isCurrent ? 0.40 : 0.15})`,
                        boxShadow: isCurrent
                          ? `0 0 60px 15px rgba(${color[0]},${color[1]},${color[2]},0.15), 0 0 20px 5px rgba(${color[0]},${color[1]},${color[2]},0.10)`
                          : `0 0 30px 5px rgba(${color[0]},${color[1]},${color[2]},0.06)`,
                      }}
                    >
                      <div className={cn("scale-[2.2] md:scale-[2.8]", region.accentClass)}>
                        {region.icon}
                      </div>
                    </div>

                    {/* Title */}
                    <h2 className="text-3xl font-extrabold tracking-tight text-white md:text-5xl">
                      {region.title}
                    </h2>

                    {/* Level range + status */}
                    <div className="mt-3 flex items-center gap-3">
                      <span className="text-sm font-medium text-white/30">
                        Levels {region.levelRange}
                      </span>
                      {isCurrent && (
                        <span
                          className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider animate-pulse"
                          style={{
                            backgroundColor: `rgba(${color[0]},${color[1]},${color[2]},0.20)`,
                            color: `rgba(${color[0]},${color[1]},${color[2]},0.95)`,
                            boxShadow: `0 0 20px 4px rgba(${color[0]},${color[1]},${color[2]},0.15)`,
                          }}
                        >
                          You are here
                        </span>
                      )}
                      {isPast && (
                        <span className="px-3 py-1 rounded-full text-xs font-medium bg-white/[0.04] text-white/25">
                          Completed
                        </span>
                      )}
                    </div>

                    {/* Description */}
                    <p className="mt-4 max-w-md text-sm leading-relaxed text-white/40 md:text-base">
                      {region.subtitle}
                    </p>

                    {/* Progress bar */}
                    {tierTotal > 0 && (
                      <div className="mt-5 w-full max-w-xs">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-[11px] font-bold uppercase tracking-wider text-white/30">
                            Achievements
                          </span>
                          <span className="text-[11px] font-bold text-white/50">
                            {tierUnlocked} / {tierTotal}
                          </span>
                        </div>
                        <div className="h-2 w-full rounded-full bg-white/[0.06] overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-700 ease-out"
                            style={{
                              width: `${tierTotal > 0 ? (tierUnlocked / tierTotal) * 100 : 0}%`,
                              background: `linear-gradient(90deg, rgba(${color[0]},${color[1]},${color[2]},0.6), rgba(${color[0]},${color[1]},${color[2]},0.9))`,
                              boxShadow: tierUnlocked > 0 ? `0 0 12px 2px rgba(${color[0]},${color[1]},${color[2]},0.4)` : "none",
                            }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* ── Achievement cards — the star of the show ──────────── */}
                {tierTotal > 0 && (
                  <div className={cn(
                    "relative z-10 w-full max-w-xl space-y-3 transition-opacity duration-500",
                    isFuture && "opacity-30",
                  )}>
                    {regionAchievements.map((a) => {
                      const isUnlocked = milestonesReached.has(a.id)
                      const isSecretLocked = a.is_secret && !isUnlocked

                      // Per-rarity styling
                      const rarityStyles = (() => {
                        const r = a.rarity ?? "COMMON"
                        if (!isUnlocked) return {
                          bg: isSecretLocked ? "bg-amber-500/[0.02] border-dashed" : "bg-white/[0.015]",
                          ring: isSecretLocked ? "ring-amber-400/[0.08]" : "ring-white/[0.04]",
                          iconBg: isSecretLocked ? "bg-amber-500/[0.06]" : "bg-white/[0.03]",
                          icon: isSecretLocked
                            ? <Sparkles className="h-6 w-6 text-amber-400/20" />
                            : <Lock className="h-6 w-6 text-white/12" />,
                          title: isSecretLocked ? "text-amber-200/25" : "text-white/30",
                          sub: isSecretLocked ? "text-amber-200/15" : "text-white/15",
                          badge: isSecretLocked
                            ? <span className="text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400/30 border border-amber-400/10">Secret</span>
                            : null as React.ReactNode,
                          glow: "",
                        }
                        switch (r) {
                          case "LEGENDARY": return {
                            bg: "bg-gradient-to-r from-amber-500/[0.10] via-yellow-500/[0.06] to-amber-500/[0.10]",
                            ring: "ring-amber-400/30",
                            iconBg: "bg-amber-500/15",
                            icon: <Sparkles className="h-6 w-6 text-amber-400" />,
                            title: "text-amber-200",
                            sub: "text-amber-200/40",
                            badge: <span className="text-[10px] font-black uppercase tracking-widest px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-400/20">Legendary</span>,
                            glow: `0 0 30px 8px rgba(245,158,11,0.10)`,
                          }
                          case "EPIC": return {
                            bg: "bg-gradient-to-r from-purple-500/[0.08] via-violet-500/[0.05] to-purple-500/[0.08]",
                            ring: "ring-purple-400/25",
                            iconBg: "bg-purple-500/15",
                            icon: <Star className="h-6 w-6 text-purple-400" />,
                            title: "text-purple-200",
                            sub: "text-purple-200/40",
                            badge: <span className="text-[10px] font-black uppercase tracking-widest px-2.5 py-1 rounded-full bg-purple-500/20 text-purple-300 border border-purple-400/20">Epic</span>,
                            glow: `0 0 24px 6px rgba(168,85,247,0.08)`,
                          }
                          case "RARE": return {
                            bg: "bg-gradient-to-r from-blue-500/[0.07] via-cyan-500/[0.04] to-blue-500/[0.07]",
                            ring: "ring-blue-400/20",
                            iconBg: "bg-blue-500/12",
                            icon: <Trophy className="h-6 w-6 text-blue-400" />,
                            title: "text-blue-200",
                            sub: "text-blue-200/35",
                            badge: <span className="text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full bg-blue-500/15 text-blue-300">Rare</span>,
                            glow: `0 0 20px 4px rgba(59,130,246,0.06)`,
                          }
                          case "UNCOMMON": return {
                            bg: "bg-gradient-to-r from-emerald-500/[0.06] to-teal-500/[0.04]",
                            ring: "ring-emerald-400/15",
                            iconBg: "bg-emerald-500/10",
                            icon: <CheckCircle2 className="h-6 w-6 text-emerald-400" />,
                            title: "text-emerald-200",
                            sub: "text-emerald-200/35",
                            badge: <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/12 text-emerald-300/70">Uncommon</span>,
                            glow: "",
                          }
                          default: return {
                            bg: "bg-white/[0.03]",
                            ring: "ring-white/[0.08]",
                            iconBg: "bg-white/[0.06]",
                            icon: <CheckCircle2 className="h-6 w-6 text-white/50" />,
                            title: "text-white/80",
                            sub: "text-white/35",
                            badge: null as React.ReactNode,
                            glow: "",
                          }
                        }
                      })()

                      return (
                        <div
                          key={a.id}
                          className={cn(
                            "group relative flex items-center gap-4 rounded-2xl p-4 md:p-5 ring-1 transition-all duration-400",
                            rarityStyles.bg,
                            rarityStyles.ring,
                            isUnlocked && "hover:scale-[1.01]",
                          )}
                          style={{
                            boxShadow: isUnlocked ? rarityStyles.glow : "",
                          }}
                        >
                          {/* Icon container */}
                          <div className={cn(
                            "flex h-14 w-14 md:h-16 md:w-16 shrink-0 items-center justify-center rounded-xl transition-all duration-300",
                            rarityStyles.iconBg,
                          )}>
                            {rarityStyles.icon}
                          </div>

                          {/* Text content */}
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <h3 className={cn(
                                "text-base md:text-lg font-bold",
                                rarityStyles.title,
                              )}>
                                {isSecretLocked ? "???" : a.title}
                              </h3>
                              {rarityStyles.badge}
                            </div>
                            <p className={cn(
                              "text-sm mt-1 leading-relaxed",
                              rarityStyles.sub,
                            )}>
                              {isSecretLocked ? "A hidden achievement awaits..." : a.subtitle}
                            </p>
                          </div>

                          {/* Status indicator */}
                          <div className="shrink-0">
                            {isUnlocked ? (
                              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/15 ring-1 ring-emerald-400/20">
                                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                              </div>
                            ) : (
                              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/[0.03] ring-1 ring-white/[0.06]">
                                <Lock className="h-4 w-4 text-white/12" />
                              </div>
                            )}
                          </div>

                          {/* Subtle shimmer on unlocked legendary/epic */}
                          {isUnlocked && (a.rarity === "LEGENDARY" || a.rarity === "EPIC") && (
                            <div className="pointer-events-none absolute inset-0 rounded-2xl overflow-hidden">
                              <div
                                className="absolute -top-8 left-1/2 -translate-x-1/2 h-16 w-[80%] rounded-full blur-2xl opacity-30"
                                style={{
                                  backgroundColor: a.rarity === "LEGENDARY"
                                    ? "rgba(245,158,11,0.15)"
                                    : "rgba(168,85,247,0.12)",
                                }}
                              />
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}

                {/* Scroll hint on first section */}
                {rIdx === 0 && (
                  <div className="mt-8 animate-bounce text-white/15">
                    <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                    </svg>
                  </div>
                )}

                {/* Elegant divider between regions */}
                {rIdx < REGIONS.length - 1 && (() => {
                  const c1 = REGION_COLORS[rIdx]
                  const c2 = REGION_COLORS[rIdx + 1]
                  return (
                    <div className="mt-14 mb-2 flex items-center justify-center gap-4">
                      <div className="h-px w-16 rounded-full" style={{ background: `linear-gradient(90deg, transparent, rgba(${c1[0]},${c1[1]},${c1[2]},0.15))` }} />
                      <Heart
                        className="h-4 w-4 fill-current animate-pulse"
                        style={{
                          color: `rgba(${c1[0]},${c1[1]},${c1[2]},0.15)`,
                          animationDuration: "4s",
                        }}
                      />
                      <Sparkles
                        className="h-3 w-3"
                        style={{ color: `rgba(${c2[0]},${c2[1]},${c2[2]},0.10)` }}
                      />
                      <Heart
                        className="h-4 w-4 fill-current animate-pulse"
                        style={{
                          color: `rgba(${c2[0]},${c2[1]},${c2[2]},0.15)`,
                          animationDuration: "5s",
                        }}
                      />
                      <div className="h-px w-16 rounded-full" style={{ background: `linear-gradient(90deg, rgba(${c2[0]},${c2[1]},${c2[2]},0.15), transparent)` }} />
                    </div>
                  )
                })()}
              </section>
            )
          })}

          {/* Bottom padding */}
          <div className="h-24" />
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Main GirlPage
// ═══════════════════════════════════════════════════════════════════════════════

export default function GirlPage() {
  const [tab, setTab] = useState<Tab>("chat")
  const [showRelationship, setShowRelationship] = useState(false)
  const [showIntimate, setShowIntimate] = useState(false)
  const [showGiftCollection, setShowGiftCollection] = useState(false)
  const [showMysteryBox, setShowMysteryBox] = useState(false)
  const [showSeduceHer, setShowSeduceHer] = useState(false)
  const setMessages = useChatStore((s) => s.setMessages)
  const currentGirlfriendId = useAppStore((s) => s.currentGirlfriendId)
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const [giftBanner, setGiftBanner] = useState(false)

  // Gallery state
  const [selectedImage, setSelectedImage] = useState<GalleryItem | null>(null)
  const [viewerOpen, setViewerOpen] = useState(false)

  // Relationship state is fetched by RelationshipPanel when opened

  // ── Chat data ─────────────────────────────────────────────────────────
  const { data: chatData, isLoading: chatLoading } = useQuery({
    queryKey: ["chatHistory", currentGirlfriendId],
    queryFn: () => getChatHistory(currentGirlfriendId ?? undefined),
    enabled: tab === "chat" && !showRelationship,
  })

  // ── Gallery data ──────────────────────────────────────────────────────
  const { data: galleryData, isLoading: galleryLoading } = useQuery({
    queryKey: ["gallery", currentGirlfriendId],
    queryFn: () => getGallery(currentGirlfriendId ?? undefined),
    enabled: tab === "gallery" && !showRelationship,
  })

  // Handle gift_success return from Stripe
  useEffect(() => {
    if (searchParams.get("gift_success") === "1") {
      setGiftBanner(true)
      searchParams.delete("gift_success")
      setSearchParams(searchParams, { replace: true })
      const timer = setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["chatHistory"] })
        queryClient.invalidateQueries({ queryKey: ["chatState"] })
      }, 3000)
      const hide = setTimeout(() => setGiftBanner(false), 8000)
      return () => { clearTimeout(timer); clearTimeout(hide) }
    }
  }, [searchParams, setSearchParams, queryClient])

  // Handle upgraded=1 return from Stripe checkout
  useEffect(() => {
    if (searchParams.get("upgraded") === "1") {
      searchParams.delete("upgraded")
      setSearchParams(searchParams, { replace: true })
      queryClient.invalidateQueries({ queryKey: ["billingStatus"] })
      queryClient.invalidateQueries({ queryKey: ["girlfriendsList"] })
    }
  }, [searchParams, setSearchParams, queryClient])

  // Sync chat messages to store
  useEffect(() => {
    if (chatData?.messages) setMessages(chatData.messages)
  }, [chatData?.messages, setMessages])

  const handleSelectImage = (item: GalleryItem) => {
    setSelectedImage(item)
    setViewerOpen(true)
  }

  const galleryItems = galleryData?.items ?? []

  // ── Default: Chat/Gallery + relationship button on the right ──────────
  return (
    <div className="flex h-[calc(100vh-8rem)] gap-3">
      {/* Fullscreen relationship timeline — portaled to body to escape layout */}
      {showRelationship && createPortal(
        <RelationshipPanel onClose={() => setShowRelationship(false)} />,
        document.body
      )}
      {/* Fullscreen intimate progression */}
      {showIntimate && createPortal(
        <IntimateProgressionPanel onClose={() => setShowIntimate(false)} />,
        document.body
      )}
      {/* Fullscreen gift collection */}
      {showGiftCollection && createPortal(
        <GiftCollectionPanel onClose={() => setShowGiftCollection(false)} />,
        document.body
      )}
      {/* Fullscreen mystery boxes */}
      {showMysteryBox && createPortal(
        <MysteryBoxPanel onClose={() => setShowMysteryBox(false)} />,
        document.body
      )}
      {/* Fullscreen seduce her (intimate progression → surprise tab) */}
      {showSeduceHer && createPortal(
        <IntimateProgressionPanel onClose={() => setShowSeduceHer(false)} defaultTab="surprise" />,
        document.body
      )}
      {/* Chat / Gallery card */}
      <div className="flex min-w-0 flex-1 flex-col rounded-2xl border border-white/10 bg-card/50 shadow-xl overflow-hidden">
        <ChatHeader />

        {/* Tab bar */}
        <div className="flex items-center border-b border-white/10 px-2">
          <button
            onClick={() => setTab("chat")}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px",
              tab === "chat"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            <MessageCircle className="h-4 w-4" />
            Chat
          </button>
          <button
            onClick={() => setTab("gallery")}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px",
              tab === "gallery"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            <ImageIcon className="h-4 w-4" />
            Gallery
          </button>
        </div>

        {/* Chat tab */}
        {tab === "chat" && (
          <>
            {giftBanner && (
              <div className="flex items-center justify-center gap-2 bg-primary/10 border-b border-primary/20 px-4 py-2.5 text-sm text-primary animate-in fade-in slide-in-from-top duration-300">
                <Gift className="h-4 w-4" />
                <span className="font-medium">Your gift is being delivered...</span>
              </div>
            )}
            {/* Milestone messages + next milestone progress */}
            <MilestoneInbox girlfriendId={currentGirlfriendId ?? undefined} className="px-4 pt-2" />
            {chatLoading ? (
              <div className="flex-1 space-y-3 p-4">
                <Skeleton className="h-12 w-3/4" />
                <Skeleton className="h-12 w-2/3 ml-auto" />
                <Skeleton className="h-12 w-4/5" />
              </div>
            ) : (
              <MessageList className="flex-1" />
            )}
            <Composer />
          </>
        )}

        {/* Gallery tab */}
        {tab === "gallery" && (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {galleryLoading ? (
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <Skeleton key={i} className="aspect-square rounded-xl" />
                ))}
              </div>
            ) : galleryItems.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <ImageIcon className="h-12 w-12 text-muted-foreground/30 mb-3" />
                <p className="text-muted-foreground text-sm">No photos yet</p>
                <p className="text-muted-foreground/60 text-xs mt-1">
                  Photos from your conversations will appear here
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-4 gap-2"
                  onClick={() => setTab("chat")}
                >
                  <ArrowLeft className="h-3.5 w-3.5" />
                  Back to chat
                </Button>
              </div>
            ) : (
              <GalleryGrid items={galleryItems} onSelect={handleSelectImage} />
            )}
            <ImageViewerModal item={selectedImage} open={viewerOpen} onOpenChange={setViewerOpen} />
          </div>
        )}
      </div>

      {/* Side buttons — right side (desktop) */}
      <div className="hidden md:flex flex-col gap-3">
        <RelationshipButton onClick={() => setShowRelationship(true)} />
        <IntimateButton onClick={() => setShowIntimate(true)} />
        <SeduceHerButton onClick={() => setShowSeduceHer(true)} />
        <GiftCollectionButton onClick={() => setShowGiftCollection(true)} />
        <MysteryBoxButton onClick={() => setShowMysteryBox(true)} />
      </div>

      {/* Bottom buttons — mobile */}
      <div className="fixed bottom-16 left-0 right-0 z-40 px-4 md:hidden">
        <RelationshipButtonMobile onClick={() => setShowRelationship(true)} />
        <IntimateButtonMobile onClick={() => setShowIntimate(true)} />
        <SeduceHerButtonMobile onClick={() => setShowSeduceHer(true)} />
        <GiftCollectionButtonMobile onClick={() => setShowGiftCollection(true)} />
        <MysteryBoxButtonMobile onClick={() => setShowMysteryBox(true)} />
      </div>
    </div>
  )
}
