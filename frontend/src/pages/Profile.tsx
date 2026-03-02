import { useState, useMemo } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { getProfileGirls, switchGirlfriend, getBillingStatus } from "@/lib/api/endpoints"
import { useAuth } from "@/lib/hooks/useAuth"
import { useAppStore } from "@/lib/store/useAppStore"
import { useChatStore } from "@/lib/store/useChatStore"
import type { GirlProfileStats, ProfileGirlsResponse } from "@/lib/api/types"
import { cn, formatRelativeTime } from "@/lib/utils"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import AvatarCircle from "@/components/ui/AvatarCircle"
import {
  Heart,
  Sparkles,
  MessageCircle,
  Image,
  Gift,
  Flame,
  Crown,
  ArrowRightLeft,
  MessageSquare,
  LayoutGrid,
  Users,
  Trophy,
  ChevronDown,
} from "lucide-react"

// ── Sort options ──────────────────────────────────────────────────────────────

type SortKey = "recent" | "intimacy" | "streak" | "photos"

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: "recent", label: "Most active" },
  { key: "intimacy", label: "Highest intimacy" },
  { key: "streak", label: "Longest streak" },
  { key: "photos", label: "Most photos" },
]

function sortGirls(girls: GirlProfileStats[], key: SortKey): GirlProfileStats[] {
  const sorted = [...girls]
  switch (key) {
    case "recent":
      return sorted.sort((a, b) => {
        const ta = a.activity.last_interaction_at ?? ""
        const tb = b.activity.last_interaction_at ?? ""
        return tb.localeCompare(ta)
      })
    case "intimacy":
      return sorted.sort(
        (a, b) => b.relationship.intimacy_visible - a.relationship.intimacy_visible
      )
    case "streak":
      return sorted.sort(
        (a, b) => b.activity.streak_current_days - a.activity.streak_current_days
      )
    case "photos":
      return sorted.sort((a, b) => b.collections.photos - a.collections.photos)
    default:
      return sorted
  }
}

// ── Level badge color mapping ─────────────────────────────────────────────────

const LEVEL_COLORS: Record<string, string> = {
  STRANGER: "bg-slate-600/60 text-slate-200",
  FAMILIAR: "bg-blue-600/60 text-blue-200",
  CLOSE: "bg-violet-600/60 text-violet-200",
  INTIMATE: "bg-pink-600/60 text-pink-200",
  EXCLUSIVE: "bg-amber-500/60 text-amber-100",
}

// ── Plan badge ────────────────────────────────────────────────────────────────

function PlanBadge({ plan }: { plan: string }) {
  if (plan === "premium")
    return (
      <Badge className="bg-gradient-to-r from-amber-500 to-yellow-400 text-black text-[10px] px-1.5 py-0 h-4">
        <Crown className="h-2.5 w-2.5 mr-0.5" /> Premium
      </Badge>
    )
  if (plan === "plus")
    return (
      <Badge className="bg-gradient-to-r from-primary to-primary/70 text-white text-[10px] px-1.5 py-0 h-4">
        Plus
      </Badge>
    )
  return (
    <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">
      Free
    </Badge>
  )
}

// ── Compact meter ─────────────────────────────────────────────────────────────

function MiniMeter({
  value,
  cap,
  color,
  label,
  icon,
}: {
  value: number
  cap: number
  color: string
  label: string
  icon: React.ReactNode
}) {
  const pct = cap > 0 ? Math.min(100, (value / cap) * 100) : 0
  return (
    <div className="flex items-center gap-1.5 text-[11px]">
      {icon}
      <span className="text-muted-foreground w-9 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 rounded-full bg-white/10 overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-muted-foreground tabular-nums w-7 text-right text-[10px]">
        {value}
      </span>
    </div>
  )
}

// ── Girl Card ─────────────────────────────────────────────────────────────────

function GirlCard({
  girl,
  isCurrent,
  onSwitch,
  onOpenChat,
  onOpenGallery,
}: {
  girl: GirlProfileStats
  isCurrent: boolean
  onSwitch: () => void
  onOpenChat: () => void
  onOpenGallery: () => void
}) {
  const { relationship: rel, activity: act, collections: col } = girl

  return (
    <Card
      className={cn(
        "rounded-2xl border-white/10 overflow-hidden transition-all hover:border-white/20",
        isCurrent && "ring-1 ring-primary/50 border-primary/30"
      )}
    >
      <CardContent className="p-4 space-y-3">
        {/* ── Header ──────────────────────────────────────────────────── */}
        <div className="flex items-start gap-3">
          <AvatarCircle name={girl.name} avatarUrl={girl.avatar_url} size="lg" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold truncate">{girl.name}</h3>
              {isCurrent && (
                <Badge variant="outline" className="text-[9px] px-1 py-0 h-3.5 border-primary/40 text-primary shrink-0">
                  Active
                </Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground truncate mt-0.5">{girl.vibe_line}</p>
            <div className="flex items-center gap-1.5 mt-1.5">
              <Badge
                className={cn(
                  "text-[10px] px-1.5 py-0 h-4 font-medium",
                  LEVEL_COLORS[rel.level_label] ?? LEVEL_COLORS.STRANGER
                )}
              >
                {rel.level_label}
              </Badge>
              {rel.region_title && (
                <span className="text-[10px] text-muted-foreground">
                  Region {rel.current_region_index} &middot; {rel.region_title}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* ── Trust & Intimacy meters ─────────────────────────────────── */}
        <div className="space-y-1">
          <MiniMeter
            value={rel.trust_visible}
            cap={rel.trust_cap}
            color="bg-rose-500"
            label="Trust"
            icon={<Heart className="h-3 w-3 text-rose-400" />}
          />
          <MiniMeter
            value={rel.intimacy_visible}
            cap={rel.intimacy_cap}
            color="bg-violet-500"
            label="Intim."
            icon={<Sparkles className="h-3 w-3 text-violet-400" />}
          />
        </div>

        {/* ── Activity row ────────────────────────────────────────────── */}
        <div className="flex items-center justify-between text-[11px] text-muted-foreground">
          <span className="flex items-center gap-1">
            <MessageCircle className="h-3 w-3" />
            {act.message_count} msgs
          </span>
          <span>
            Last: {formatRelativeTime(act.last_interaction_at)}
          </span>
        </div>

        {/* ── Streak row ──────────────────────────────────────────────── */}
        {act.streak_current_days > 0 ? (
          <div
            className={cn(
              "relative rounded-xl px-3 py-2 flex items-center gap-2.5 overflow-hidden transition-all",
              act.streak_active_today
                ? "bg-gradient-to-r from-orange-500/15 via-amber-500/10 to-red-500/15 border border-orange-500/25"
                : "bg-white/[0.03] border border-white/5"
            )}
            style={act.streak_active_today ? { animation: "flame-glow-pulse 2.5s ease-in-out infinite" } : undefined}
          >
            {/* Flame icon with flicker */}
            <div className="relative shrink-0">
              <Flame
                className={cn(
                  "h-5 w-5",
                  act.streak_active_today
                    ? "text-orange-400"
                    : "text-muted-foreground/30"
                )}
                style={act.streak_active_today ? {
                  animation: "flame-flicker 1.5s ease-in-out infinite",
                  filter: "drop-shadow(0 0 6px rgba(251,146,60,0.6)) drop-shadow(0 0 12px rgba(251,146,60,0.3))",
                } : undefined}
              />
              {/* Floating embers when active */}
              {act.streak_active_today && (
                <>
                  <span className="absolute -top-0.5 left-1 text-[6px]" style={{ animation: "ember-float 2s ease-out infinite" }}>
                    ✦
                  </span>
                  <span className="absolute -top-0.5 right-0 text-[5px] text-orange-300" style={{ animation: "ember-float 2.3s ease-out infinite 0.5s" }}>
                    ✦
                  </span>
                </>
              )}
            </div>

            {/* Streak count — big and bold */}
            <div className="flex items-baseline gap-1">
              <span
                className={cn(
                  "text-lg font-extrabold tabular-nums leading-none",
                  act.streak_active_today
                    ? "bg-gradient-to-b from-orange-300 via-amber-400 to-orange-500 bg-clip-text text-transparent"
                    : "text-muted-foreground/60"
                )}
                style={act.streak_active_today ? { animation: "streak-count-pop 3s ease-in-out infinite" } : undefined}
              >
                {act.streak_current_days}
              </span>
              <span className={cn(
                "text-[11px] font-semibold",
                act.streak_active_today ? "text-orange-300/80" : "text-muted-foreground/40"
              )}>
                day{act.streak_current_days !== 1 ? "s" : ""}
              </span>
            </div>

            {/* Streak label + best */}
            <div className="flex-1 text-right">
              {act.streak_active_today ? (
                <span className="text-[10px] font-medium text-orange-300/70">
                  on fire today
                </span>
              ) : (
                <span className="text-[10px] text-muted-foreground/40">
                  talk to keep it
                </span>
              )}
              {act.streak_best_days > act.streak_current_days && (
                <div className="text-[9px] text-muted-foreground/30 mt-0.5">
                  Best: {act.streak_best_days}d
                </div>
              )}
            </div>

            {/* Milestone badge for big streaks */}
            {act.streak_current_days >= 7 && act.streak_active_today && (
              <div className="shrink-0 flex items-center gap-0.5 rounded-full bg-gradient-to-r from-orange-500/20 to-amber-500/20 border border-orange-400/20 px-1.5 py-0.5">
                <span className="text-[10px]">
                  {act.streak_current_days >= 30 ? "💎" : act.streak_current_days >= 14 ? "⚡" : "🔥"}
                </span>
                <span className="text-[9px] font-bold text-orange-300">
                  {act.streak_current_days >= 30 ? "Legend" : act.streak_current_days >= 14 ? "Hot" : "Lit"}
                </span>
              </div>
            )}
          </div>
        ) : (
          <div className="rounded-xl px-3 py-2 flex items-center gap-2.5 bg-white/[0.02] border border-dashed border-white/5">
            <Flame className="h-4 w-4 text-muted-foreground/20" />
            <span className="text-[11px] text-muted-foreground/30">
              No streak — send a message to start one
            </span>
          </div>
        )}

        {/* ── Collections ─────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
          <span className="flex items-center gap-1">
            <Image className="h-3 w-3" /> Photos {col.photos}
          </span>
          <span className="flex items-center gap-1">
            <Gift className="h-3 w-3" /> Gifts {col.gifts_owned}/{col.gifts_total}
          </span>
          <span className="flex items-center gap-1">
            <Trophy className="h-3 w-3" /> Relat. {col.relationship_achievements_unlocked}/{col.relationship_achievements_total}
          </span>
          <span className="flex items-center gap-1">
            <Sparkles className="h-3 w-3" /> Intim. {col.intimacy_achievements_unlocked}/{col.intimacy_achievements_total}
          </span>
        </div>

        {/* ── Quick actions ───────────────────────────────────────────── */}
        <div className="h-px bg-white/5" />
        <div className="flex gap-2">
          {!isCurrent && (
            <Button
              variant="outline"
              size="sm"
              className="flex-1 rounded-lg text-xs gap-1 h-8"
              onClick={onSwitch}
            >
              <ArrowRightLeft className="h-3 w-3" /> Switch
            </Button>
          )}
          <Button
            variant={isCurrent ? "default" : "outline"}
            size="sm"
            className="flex-1 rounded-lg text-xs gap-1 h-8"
            onClick={onOpenChat}
          >
            <MessageSquare className="h-3 w-3" /> Chat
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="flex-1 rounded-lg text-xs gap-1 h-8"
            onClick={onOpenGallery}
          >
            <LayoutGrid className="h-3 w-3" /> Gallery
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

// ── Skeleton card ─────────────────────────────────────────────────────────────

function GirlCardSkeleton() {
  return (
    <Card className="rounded-2xl border-white/10">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-start gap-3">
          <Skeleton className="h-12 w-12 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-3 w-36" />
          </div>
        </div>
        <Skeleton className="h-1.5 w-full rounded" />
        <Skeleton className="h-1.5 w-full rounded" />
        <Skeleton className="h-3 w-32" />
        <Skeleton className="h-3 w-28" />
        <div className="grid grid-cols-2 gap-2">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-3 w-20" />
        </div>
        <div className="flex gap-2 pt-1">
          <Skeleton className="h-8 flex-1 rounded-lg" />
          <Skeleton className="h-8 flex-1 rounded-lg" />
        </div>
      </CardContent>
    </Card>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function Profile() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [sortKey, setSortKey] = useState<SortKey>("recent")
  const [sortOpen, setSortOpen] = useState(false)
  const [switching, setSwitching] = useState<string | null>(null)

  const { data, isLoading } = useQuery<ProfileGirlsResponse>({
    queryKey: ["profile-girls"],
    queryFn: getProfileGirls,
  })

  const { data: billing } = useQuery({
    queryKey: ["billing-status"],
    queryFn: getBillingStatus,
  })

  const setGirlfriends = useAppStore((s) => s.setGirlfriends)
  const setCurrentGirlfriend = useAppStore((s) => s.setCurrentGirlfriend)
  const setGirlfriend = useAppStore((s) => s.setGirlfriend)
  const currentGirlfriendId = useAppStore((s) => s.currentGirlfriendId)
  const resetChat = useChatStore((s) => s.reset)

  const currentGfId = currentGirlfriendId ?? user?.current_girlfriend_id ?? null
  const plan = billing?.plan ?? "free"

  const sortedGirls = useMemo(
    () => (data ? sortGirls(data.girls, sortKey) : []),
    [data, sortKey]
  )

  const _doSwitch = async (gfId: string) => {
    const res = await switchGirlfriend(gfId)
    // Update Zustand store so the whole app reflects the switch immediately
    setGirlfriends(res.girlfriends, res.current_girlfriend_id)
    setCurrentGirlfriend(gfId)
    const selected = res.girlfriends.find((g) => g.id === gfId)
    if (selected) setGirlfriend(selected)
    resetChat()
    // Invalidate all relevant queries
    queryClient.invalidateQueries({ queryKey: ["profile-girls"] })
    queryClient.invalidateQueries({ queryKey: ["girlfriend"] })
    queryClient.invalidateQueries({ queryKey: ["chatHistory"] })
    queryClient.invalidateQueries({ queryKey: ["chatState"] })
    queryClient.invalidateQueries({ queryKey: ["girlfriendsList"] })
    queryClient.invalidateQueries({ queryKey: ["gallery"] })
  }

  const handleSwitch = async (gfId: string) => {
    if (gfId === currentGfId) {
      navigate("/app/girl")
      return
    }
    setSwitching(gfId)
    try {
      await _doSwitch(gfId)
      navigate("/app/girl")
    } catch (err) {
      console.error("Switch failed:", err)
    } finally {
      setSwitching(null)
    }
  }

  const handleOpenChat = async (gfId: string) => {
    if (gfId !== currentGfId) {
      setSwitching(gfId)
      try {
        await _doSwitch(gfId)
      } catch (err) {
        console.error("Switch failed:", err)
      } finally {
        setSwitching(null)
      }
    }
    navigate("/app/girl")
  }

  const handleOpenGallery = async (gfId: string) => {
    if (gfId !== currentGfId) {
      setSwitching(gfId)
      try {
        await _doSwitch(gfId)
      } catch (err) {
        console.error("Switch failed:", err)
      } finally {
        setSwitching(null)
      }
    }
    navigate("/app/girl?tab=gallery")
  }

  return (
    <div className="space-y-6 pb-8">
      <h1 className="text-2xl font-bold tracking-tight">Profile</h1>

      {/* ── Account Overview Card ────────────────────────────────────── */}
      <Card className="rounded-2xl border-white/10">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              Overview
            </h2>
            <PlanBadge plan={plan} />
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex gap-6">
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-10 w-16" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-4 gap-3 text-center">
              <div>
                <div className="text-xl font-bold">{data?.totals.girls ?? 0}</div>
                <div className="text-[10px] text-muted-foreground flex items-center justify-center gap-0.5">
                  <Users className="h-2.5 w-2.5" /> Girls
                </div>
              </div>
              <div>
                <div className="text-xl font-bold">{data?.totals.messages ?? 0}</div>
                <div className="text-[10px] text-muted-foreground flex items-center justify-center gap-0.5">
                  <MessageCircle className="h-2.5 w-2.5" /> Messages
                </div>
              </div>
              <div>
                <div className="text-xl font-bold">{data?.totals.photos ?? 0}</div>
                <div className="text-[10px] text-muted-foreground flex items-center justify-center gap-0.5">
                  <Image className="h-2.5 w-2.5" /> Photos
                </div>
              </div>
              <div>
                <div className="text-xl font-bold">{data?.totals.gifts_owned ?? 0}</div>
                <div className="text-[10px] text-muted-foreground flex items-center justify-center gap-0.5">
                  <Gift className="h-2.5 w-2.5" /> Gifts
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Sort + Grid Header ───────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Your Girls</h2>
        <div className="relative">
          <Button
            variant="outline"
            size="sm"
            className="rounded-lg text-xs gap-1 h-7"
            onClick={() => setSortOpen((v) => !v)}
          >
            Sort: {SORT_OPTIONS.find((o) => o.key === sortKey)?.label}
            <ChevronDown className="h-3 w-3" />
          </Button>
          {sortOpen && (
            <div className="absolute right-0 top-full mt-1 z-50 rounded-lg border border-white/10 bg-popover shadow-lg py-1 min-w-[140px]">
              {SORT_OPTIONS.map((opt) => (
                <button
                  key={opt.key}
                  className={cn(
                    "w-full text-left px-3 py-1.5 text-xs hover:bg-white/5 transition-colors",
                    sortKey === opt.key && "text-primary font-medium"
                  )}
                  onClick={() => {
                    setSortKey(opt.key)
                    setSortOpen(false)
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Girl Cards Grid ──────────────────────────────────────────── */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {[1, 2].map((i) => (
            <GirlCardSkeleton key={i} />
          ))}
        </div>
      ) : sortedGirls.length === 0 ? (
        <Card className="rounded-2xl border-white/10">
          <CardContent className="py-12 text-center">
            <Users className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
            <p className="text-muted-foreground text-sm">
              No companions yet. Start by creating one!
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {sortedGirls.map((girl) => (
            <GirlCard
              key={girl.girlfriend_id}
              girl={girl}
              isCurrent={girl.girlfriend_id === currentGfId}
              onSwitch={() => handleSwitch(girl.girlfriend_id)}
              onOpenChat={() => handleOpenChat(girl.girlfriend_id)}
              onOpenGallery={() => handleOpenGallery(girl.girlfriend_id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
