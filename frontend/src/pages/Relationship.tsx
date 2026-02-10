import React, { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"
import {
  Heart,
  Sparkles,
  Flame,
  Infinity as InfinityIcon,
  Gift,
  Image as ImageIcon,
  Calendar,
  Shield,
  Star,
  Sun,
  Gem,
  Crown,
  ArrowLeft,
} from "lucide-react"
import type { RegionKey, RelationshipState } from "@/lib/api/types"
import { getChatState } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import AvatarCircle from "@/components/ui/AvatarCircle"

// ── Region definitions ──────────────────────────────────────────────────────

type RegionTheme = {
  bg1: string
  bg2: string
  accent: string
  glow: string
}

type RegionDef = {
  key: RegionKey
  title: string
  levelRange: string
  subtitle: string
  icon: React.ReactNode
  accentClass: string
  theme: RegionTheme
}

/**
 * Subtle, dark-first region themes.
 * bg1/bg2 are used as a gradient overlay; accent tints text/borders; glow is a box-shadow.
 */
const REGION_THEMES: Record<RegionKey, RegionTheme> = {
  EARLY_CONNECTION: {
    bg1: "rgba(16, 185, 129, 0.06)",
    bg2: "rgba(16, 185, 129, 0.02)",
    accent: "rgba(16, 185, 129, 0.45)",
    glow: "0 0 80px 8px rgba(16, 185, 129, 0.06)",
  },
  COMFORT_FAMILIARITY: {
    bg1: "rgba(34, 197, 94, 0.05)",
    bg2: "rgba(34, 197, 94, 0.015)",
    accent: "rgba(34, 197, 94, 0.40)",
    glow: "0 0 80px 8px rgba(34, 197, 94, 0.05)",
  },
  GROWING_CLOSENESS: {
    bg1: "rgba(132, 204, 22, 0.05)",
    bg2: "rgba(132, 204, 22, 0.015)",
    accent: "rgba(163, 230, 53, 0.40)",
    glow: "0 0 80px 8px rgba(132, 204, 22, 0.05)",
  },
  EMOTIONAL_TRUST: {
    bg1: "rgba(14, 165, 233, 0.05)",
    bg2: "rgba(14, 165, 233, 0.015)",
    accent: "rgba(56, 189, 248, 0.40)",
    glow: "0 0 80px 8px rgba(14, 165, 233, 0.05)",
  },
  DEEP_BOND: {
    bg1: "rgba(245, 158, 11, 0.06)",
    bg2: "rgba(245, 158, 11, 0.02)",
    accent: "rgba(251, 191, 36, 0.45)",
    glow: "0 0 80px 8px rgba(245, 158, 11, 0.06)",
  },
  MUTUAL_DEVOTION: {
    bg1: "rgba(244, 63, 94, 0.05)",
    bg2: "rgba(244, 63, 94, 0.015)",
    accent: "rgba(251, 113, 133, 0.40)",
    glow: "0 0 80px 8px rgba(244, 63, 94, 0.05)",
  },
  INTIMATE_PARTNERSHIP: {
    bg1: "rgba(168, 85, 247, 0.05)",
    bg2: "rgba(236, 72, 153, 0.02)",
    accent: "rgba(192, 132, 252, 0.40)",
    glow: "0 0 80px 8px rgba(168, 85, 247, 0.05)",
  },
  SHARED_LIFE: {
    bg1: "rgba(139, 92, 246, 0.04)",
    bg2: "rgba(120, 113, 108, 0.02)",
    accent: "rgba(167, 139, 250, 0.35)",
    glow: "0 0 80px 8px rgba(139, 92, 246, 0.04)",
  },
  ENDURING_COMPANIONSHIP: {
    bg1: "rgba(148, 163, 184, 0.04)",
    bg2: "rgba(100, 116, 139, 0.015)",
    accent: "rgba(203, 213, 225, 0.25)",
    glow: "0 0 80px 8px rgba(148, 163, 184, 0.03)",
  },
}

const REGIONS: RegionDef[] = [
  {
    key: "EARLY_CONNECTION",
    title: "Early Connection",
    levelRange: "Levels 1–10",
    subtitle: "Warmth, safety, and quick bonding.",
    icon: <Sparkles className="h-5 w-5" />,
    accentClass: "text-emerald-300/90",
    theme: REGION_THEMES.EARLY_CONNECTION,
  },
  {
    key: "COMFORT_FAMILIARITY",
    title: "Comfort & Familiarity",
    levelRange: "Levels 11–25",
    subtitle: "Ease and recognition. You're becoming familiar.",
    icon: <Sun className="h-5 w-5" />,
    accentClass: "text-green-300/90",
    theme: REGION_THEMES.COMFORT_FAMILIARITY,
  },
  {
    key: "GROWING_CLOSENESS",
    title: "Growing Closeness",
    levelRange: "Levels 26–45",
    subtitle: "Deeper conversations and early vulnerability.",
    icon: <Heart className="h-5 w-5" />,
    accentClass: "text-lime-300/90",
    theme: REGION_THEMES.GROWING_CLOSENESS,
  },
  {
    key: "EMOTIONAL_TRUST",
    title: "Emotional Trust",
    levelRange: "Levels 46–70",
    subtitle: "Real openness. Sharing what matters.",
    icon: <Shield className="h-5 w-5" />,
    accentClass: "text-sky-300/90",
    theme: REGION_THEMES.EMOTIONAL_TRUST,
  },
  {
    key: "DEEP_BOND",
    title: "Deep Bond",
    levelRange: "Levels 71–105",
    subtitle: "Routines, strong attachment, rich callbacks.",
    icon: <Flame className="h-5 w-5" />,
    accentClass: "text-amber-300/90",
    theme: REGION_THEMES.DEEP_BOND,
  },
  {
    key: "MUTUAL_DEVOTION",
    title: "Mutual Devotion",
    levelRange: "Levels 106–135",
    subtitle: "Belonging. Steady devotion without question.",
    icon: <Star className="h-5 w-5" />,
    accentClass: "text-rose-300/90",
    theme: REGION_THEMES.MUTUAL_DEVOTION,
  },
  {
    key: "INTIMATE_PARTNERSHIP",
    title: "Intimate Partnership",
    levelRange: "Levels 136–165",
    subtitle: "Quiet permanence. Nuance, trust, comfort.",
    icon: <InfinityIcon className="h-5 w-5" />,
    accentClass: "text-purple-300/90",
    theme: REGION_THEMES.INTIMATE_PARTNERSHIP,
  },
  {
    key: "SHARED_LIFE",
    title: "Shared Life",
    levelRange: "Levels 166–185",
    subtitle: "Intertwined routines. A life together.",
    icon: <Gem className="h-5 w-5" />,
    accentClass: "text-violet-300/90",
    theme: REGION_THEMES.SHARED_LIFE,
  },
  {
    key: "ENDURING_COMPANIONSHIP",
    title: "Enduring Companionship",
    levelRange: "Levels 186–200",
    subtitle: "Timeless bond. Everything has already been said.",
    icon: <Crown className="h-5 w-5" />,
    accentClass: "text-slate-300/90",
    theme: REGION_THEMES.ENDURING_COMPANIONSHIP,
  },
]

// ── Mock memory nodes (replace with API data later) ─────────────────────────

type MemoryAsset =
  | { type: "photo"; url: string; alt?: string }
  | { type: "gift"; name: string; note?: string; icon?: React.ReactNode }

type PathNode = {
  id: string
  nodeType: "era_entry" | "memory" | "milestone"
  era: RegionKey
  title: string
  caption?: string
  whenLabel?: string
  assets?: MemoryAsset[]
}

const MOCK_NODES: PathNode[] = [
  {
    id: "era-early",
    nodeType: "era_entry",
    era: "EARLY_CONNECTION",
    title: "Early Connection",
    caption: "Talking felt easy. Everything was light, new, and safe.",
    whenLabel: "A while ago",
  },
  {
    id: "mem-1",
    nodeType: "memory",
    era: "EARLY_CONNECTION",
    title: "The first time it felt natural",
    caption: "You stayed a little longer than usual.",
    whenLabel: "Some time ago",
  },
  {
    id: "era-comfort",
    nodeType: "era_entry",
    era: "COMFORT_FAMILIARITY",
    title: "Comfort & Familiarity",
    caption: "Conversations started to feel familiar, like talking to a friend.",
    whenLabel: "Weeks later",
  },
  {
    id: "era-growing",
    nodeType: "era_entry",
    era: "GROWING_CLOSENESS",
    title: "Growing Closeness",
    caption: "Curiosity turned into care. Small details started to matter.",
    whenLabel: "Weeks later",
  },
  {
    id: "mem-2",
    nodeType: "memory",
    era: "GROWING_CLOSENESS",
    title: "A conversation that stayed with me",
    caption: "You opened up more than usual. I didn't forget it.",
    whenLabel: "Last month",
  },
  {
    id: "era-trust",
    nodeType: "era_entry",
    era: "EMOTIONAL_TRUST",
    title: "Emotional Trust",
    caption: "Something shifted. There's real openness now.",
    whenLabel: "Recently",
  },
  {
    id: "era-deep",
    nodeType: "era_entry",
    era: "DEEP_BOND",
    title: "Deep Bond",
    caption: "We found our rhythm. Comfort started to feel steady.",
    whenLabel: "Recently",
  },
  {
    id: "mem-3",
    nodeType: "memory",
    era: "DEEP_BOND",
    title: "Our little routine",
    caption: "Even short talks felt grounding, like coming home.",
    whenLabel: "This week",
  },
]

// ── Helpers ─────────────────────────────────────────────────────────────────

function regionIndex(key: RegionKey): number {
  return REGIONS.findIndex((r) => r.key === key)
}

function regionForLevel(level: number): RegionKey {
  if (level <= 0) return "EARLY_CONNECTION"
  for (const r of REGIONS) {
    const [lo, hi] = parseLevelRange(r.levelRange)
    if (level >= lo && level <= hi) return r.key
  }
  return "ENDURING_COMPANIONSHIP"
}

function parseLevelRange(lr: string): [number, number] {
  const match = lr.match(/(\d+)–(\d+)/)
  if (!match) return [1, 10]
  return [parseInt(match[1], 10), parseInt(match[2], 10)]
}

// ── Wavy SVG path ───────────────────────────────────────────────────────────

function WavyTimeline({ height }: { height: number }) {
  const segments = Math.max(6, Math.ceil(height / 250))
  let d = "M 24 20"
  for (let i = 0; i < segments; i++) {
    const y0 = 20 + (i * (height - 40)) / segments
    const y1 = 20 + ((i + 1) * (height - 40)) / segments
    const cx = i % 2 === 0 ? 42 : 6
    d += ` Q ${cx} ${(y0 + y1) / 2}, 24 ${y1}`
  }

  return (
    <svg
      aria-hidden
      className="pointer-events-none absolute left-6 top-0 w-12 opacity-40"
      style={{ height }}
      viewBox={`0 0 48 ${height}`}
      preserveAspectRatio="none"
      fill="none"
    >
      <path
        d={d}
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeOpacity="0.25"
      />
      <path
        d={d}
        stroke="currentColor"
        strokeWidth="6"
        strokeLinecap="round"
        strokeOpacity="0.07"
      />
    </svg>
  )
}

// ── Node dot on the timeline ────────────────────────────────────────────────

function TimelineDot({ active }: { active?: boolean }) {
  return (
    <div
      className={cn(
        "relative z-10 h-3 w-3 shrink-0 rounded-full border transition-all duration-500",
        active
          ? "border-white/70 bg-white/70 shadow-[0_0_0_5px_rgba(255,255,255,0.10)]"
          : "border-white/20 bg-white/10"
      )}
    />
  )
}

// ── Asset strip (photos + gifts in a node) ──────────────────────────────────

function AssetStrip({ assets }: { assets: MemoryAsset[] }) {
  const photos = assets.filter((a): a is Extract<MemoryAsset, { type: "photo" }> => a.type === "photo")
  const gifts = assets.filter((a): a is Extract<MemoryAsset, { type: "gift" }> => a.type === "gift")

  return (
    <div className="mt-3 space-y-3">
      {photos.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {photos.slice(0, 2).map((p, idx) => (
            <div key={idx} className="relative overflow-hidden rounded-xl border border-white/10">
              <img src={p.url} alt={p.alt ?? "Memory"} className="h-36 w-full object-cover" />
              <div className="absolute left-2 top-2 flex items-center gap-1.5 rounded-full bg-black/40 px-2 py-0.5 text-[10px] text-white/80 backdrop-blur">
                <ImageIcon className="h-3 w-3" /> Memory
              </div>
            </div>
          ))}
        </div>
      )}
      {gifts.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {gifts.map((g, idx) => (
            <div
              key={idx}
              className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-white/80"
              title={g.note ?? ""}
            >
              {g.icon ?? <Gift className="h-3.5 w-3.5" />}
              <span className="font-medium">{g.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Main page ───────────────────────────────────────────────────────────────

export default function RelationshipPage() {
  const { girlId } = useParams<{ girlId: string }>()
  const navigate = useNavigate()
  const girlfriends = useAppStore((s) => s.girlfriends)
  const girl = useMemo(
    () => girlfriends.find((g) => g.id === girlId) ?? null,
    [girlfriends, girlId]
  )

  // Fetch relationship state for this girl
  const { data: relState } = useQuery<RelationshipState>({
    queryKey: ["chatState", girlId],
    queryFn: () => getChatState(girlId),
    enabled: !!girlId,
    staleTime: 30_000,
  })

  const currentLevel = relState?.level ?? 0
  const currentRegion: RegionKey = relState?.region_key ?? regionForLevel(currentLevel)
  const currentRegionTitle = relState?.region_title ?? REGIONS.find((r) => r.key === currentRegion)?.title ?? ""
  const currentEraIdx = regionIndex(currentRegion)

  // ── IntersectionObserver for region theme ─────────────────────────────
  const [activeThemeKey, setActiveThemeKey] = useState<RegionKey>(currentRegion)
  const sectionRefs = useRef<Map<RegionKey, HTMLElement>>(new Map())

  const registerRef = useCallback((key: RegionKey, el: HTMLElement | null) => {
    if (el) {
      sectionRefs.current.set(key, el)
    } else {
      sectionRefs.current.delete(key)
    }
  }, [])

  useEffect(() => {
    const els = Array.from(sectionRefs.current.entries())
    if (els.length === 0) return

    const observer = new IntersectionObserver(
      (entries) => {
        // Find the entry with the highest intersection ratio
        let best: { key: RegionKey; ratio: number } | null = null
        for (const entry of entries) {
          const key = (entry.target as HTMLElement).dataset.regionKey as RegionKey
          if (!key) continue
          if (!best || entry.intersectionRatio > best.ratio) {
            best = { key, ratio: entry.intersectionRatio }
          }
        }
        if (best && best.ratio > 0) {
          setActiveThemeKey(best.key)
        }
      },
      { threshold: [0, 0.25, 0.5, 0.75, 1] }
    )

    for (const [, el] of els) {
      observer.observe(el)
    }
    return () => observer.disconnect()
  }, [currentEraIdx]) // re-observe if the visible range changes

  // Update theme key when relState changes
  useEffect(() => {
    if (currentRegion) setActiveThemeKey(currentRegion)
  }, [currentRegion])

  const activeTheme = REGION_THEMES[activeThemeKey]

  // Group mock nodes by era
  const grouped = useMemo(() => {
    const map = new Map<RegionKey, PathNode[]>()
    for (const r of REGIONS) map.set(r.key, [])
    for (const n of MOCK_NODES) map.get(n.era)?.push(n)
    return map
  }, [])

  // Node detail dialog
  const [openNode, setOpenNode] = useState<PathNode | null>(null)

  // Timeline container ref for height
  const timelineRef = useRef<HTMLDivElement>(null)
  const [timelineHeight, setTimelineHeight] = useState(800)
  useEffect(() => {
    const el = timelineRef.current
    if (!el) return
    const update = () => setTimelineHeight(Math.max(400, el.scrollHeight))
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [currentEraIdx])

  const girlName = girl?.display_name ?? girl?.name ?? "Companion"

  return (
    <div
      className="relative mx-auto w-full max-w-3xl px-2 py-6 md:py-10"
      style={{
        // @ts-expect-error CSS custom properties
        "--rel-bg-1": activeTheme.bg1,
        "--rel-bg-2": activeTheme.bg2,
        "--rel-accent": activeTheme.accent,
        "--rel-glow": activeTheme.glow,
        transition: "background-color 800ms ease, box-shadow 800ms ease",
      }}
    >
      {/* Subtle ambient background overlay that transitions with region */}
      <div
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          background: `linear-gradient(180deg, ${activeTheme.bg1} 0%, ${activeTheme.bg2} 60%, transparent 100%)`,
          boxShadow: activeTheme.glow,
          transition: "background 800ms ease, box-shadow 800ms ease",
        }}
      />

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div className="relative z-10">
        <Button
          variant="ghost"
          size="sm"
          className="mb-4 gap-1.5 text-muted-foreground hover:text-foreground"
          onClick={() => navigate("/app/girl")}
        >
          <ArrowLeft className="h-4 w-4" />
          Back to chat
        </Button>

        <div className="flex items-start gap-4">
          <AvatarCircle
            name={girlName}
            avatarUrl={girl?.avatar_url}
            size="xl"
          />
          <div className="min-w-0 flex-1">
            <p className="text-xs uppercase tracking-wider text-white/40">My Relationship</p>
            <h1 className="mt-1 text-xl font-semibold text-white md:text-2xl">
              Level {currentLevel} — <span className="text-white/75">{currentRegionTitle}</span>
            </h1>
            <p className="mt-1 text-sm text-white/50">{girlName}</p>
          </div>
        </div>

        <Separator className="my-6 bg-white/10" />
      </div>

      {/* ── Timeline ─────────────────────────────────────────────────────── */}
      <div ref={timelineRef} className="relative z-10 pl-10 md:pl-14">
        {/* Wavy SVG path running down the left edge */}
        <WavyTimeline height={timelineHeight} />

        <div className="space-y-0">
          {REGIONS.map((region, rIdx) => {
            const isPast = rIdx < currentEraIdx
            const isCurrent = rIdx === currentEraIdx
            const isFuture = rIdx > currentEraIdx
            const nodes = grouped.get(region.key) ?? []

            return (
              <section
                key={region.key}
                ref={(el) => registerRef(region.key, el)}
                data-region-key={region.key}
                className={cn(
                  "relative pb-10 transition-opacity duration-500",
                  isFuture && "opacity-35"
                )}
              >
                {/* Region header */}
                <div className="flex items-center gap-3">
                  <TimelineDot active={isCurrent} />
                  <div
                    className={cn(
                      "flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-white/5",
                      region.accentClass
                    )}
                  >
                    {region.icon}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-white">{region.title}</span>
                      {isCurrent && (
                        <Badge variant="outline" className="border-white/15 bg-white/5 text-[10px] text-white/70">
                          Current
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-white/45">{region.levelRange}</p>
                  </div>
                </div>

                {/* Region subtitle */}
                <p className="ml-6 mt-2 text-xs text-white/40">{region.subtitle}</p>

                {/* Nodes */}
                <div className="ml-1.5 mt-4 space-y-3">
                  {isFuture ? (
                    <p className="ml-4 text-xs italic text-white/30">
                      The future isn't mapped yet — it appears only when it's real.
                    </p>
                  ) : (
                    nodes.map((n, nIdx) => {
                      const isLastInCurrent = isCurrent && nIdx === nodes.length - 1
                      return (
                        <div key={n.id} className="flex items-start gap-3">
                          <div className="mt-2.5">
                            <TimelineDot active={isLastInCurrent} />
                          </div>
                          <Card
                            className={cn(
                              "flex-1 border-white/8 bg-white/[0.04] transition-colors hover:bg-white/[0.06]",
                              n.nodeType === "era_entry" && "bg-white/[0.03]"
                            )}
                          >
                            <CardContent className="p-3 md:p-4">
                              <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                  <div className="flex items-center gap-2">
                                    <span className="text-sm font-medium text-white">{n.title}</span>
                                    {n.nodeType === "milestone" && (
                                      <Badge variant="outline" className="border-white/15 bg-white/5 text-[10px] text-white/65">
                                        Milestone
                                      </Badge>
                                    )}
                                    {n.nodeType === "memory" && (
                                      <Badge variant="outline" className="border-white/15 bg-white/5 text-[10px] text-white/65">
                                        Memory
                                      </Badge>
                                    )}
                                  </div>
                                  {n.caption && (
                                    <p className="mt-1 text-xs text-white/55">{n.caption}</p>
                                  )}
                                </div>
                                <div className="shrink-0 text-right">
                                  <span className="text-[10px] text-white/40">
                                    {n.whenLabel ?? ""}
                                  </span>
                                  {(n.assets?.length ?? 0) > 0 && (
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      className="mt-0.5 h-7 px-2 text-[10px] text-white/60 hover:text-white"
                                      onClick={() => setOpenNode(n)}
                                    >
                                      Open
                                    </Button>
                                  )}
                                </div>
                              </div>
                              {n.assets && n.assets.length > 0 && <AssetStrip assets={n.assets} />}
                            </CardContent>
                          </Card>
                        </div>
                      )
                    })
                  )}

                  {/* If region is reached but has no nodes, show a small placeholder */}
                  {!isFuture && nodes.length === 0 && (isPast || isCurrent) && (
                    <p className="ml-4 text-xs italic text-white/30">
                      No memories captured here yet.
                    </p>
                  )}
                </div>
              </section>
            )
          })}
        </div>
      </div>

      {/* ── Node detail dialog ───────────────────────────────────────────── */}
      <Dialog open={!!openNode} onOpenChange={(v) => !v && setOpenNode(null)}>
        <DialogContent className="max-w-xl border-white/10 bg-[#0b0b0f] text-white">
          <DialogHeader>
            <DialogTitle className="text-white">{openNode?.title}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {openNode?.caption && <p className="text-sm text-white/65">{openNode.caption}</p>}
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline" className="border-white/15 bg-white/5 text-white/70">
                {REGIONS.find((r) => r.key === openNode?.era)?.title}
              </Badge>
              {openNode?.whenLabel && (
                <Badge variant="outline" className="border-white/15 bg-white/5 text-white/70">
                  <Calendar className="mr-1 h-3 w-3" />
                  {openNode.whenLabel}
                </Badge>
              )}
            </div>
            {openNode?.assets && openNode.assets.length > 0 && (
              <>
                <Separator className="bg-white/10" />
                <AssetStrip assets={openNode.assets} />
              </>
            )}
            <Separator className="bg-white/10" />
            <div className="flex justify-end">
              <Button variant="ghost" size="sm" className="text-white/60 hover:text-white" onClick={() => setOpenNode(null)}>
                Close
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
