/**
 * MilestoneInbox — polls for unread milestone messages and renders them as cards.
 *
 * Designed to be embedded in the chat view or as a sidebar panel.
 * Uses react-query polling to detect new milestones in real-time.
 */
import { useQuery } from "@tanstack/react-query"
import { getProgressionMessages, getProgressionSummary } from "@/lib/api/endpoints"
import type { MilestoneMessage, ProgressionSummary } from "@/lib/api/types"
import MilestoneCard from "./MilestoneCard"
import { Flame, Target, TrendingUp } from "lucide-react"

interface Props {
  girlfriendId?: string
  className?: string
}

export default function MilestoneInbox({ girlfriendId, className = "" }: Props) {
  // Poll for unread messages every 30 seconds
  const { data: messagesData } = useQuery({
    queryKey: ["progressionMessages", girlfriendId],
    queryFn: () => getProgressionMessages(girlfriendId),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })

  // Fetch progression summary for the progress bar
  const { data: summary } = useQuery({
    queryKey: ["progressionSummary", girlfriendId],
    queryFn: () => getProgressionSummary(girlfriendId),
    staleTime: 60_000,
  })

  const messages = messagesData?.messages ?? []
  const unreadCount = messagesData?.unread_count ?? 0

  if (messages.length === 0 && !summary?.next_milestone) {
    return null
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Progress mini-bar */}
      {summary?.next_milestone && (
        <NextMilestoneBar summary={summary} />
      )}

      {/* Streak indicator */}
      {summary && summary.streak_days > 0 && (
        <div className="flex items-center gap-2 rounded-lg border border-orange-500/20 bg-orange-500/5 px-3 py-2 text-xs text-orange-300">
          <Flame className="h-3.5 w-3.5" />
          <span>{summary.streak_days}-day streak</span>
          {summary.streak_days >= 7 && <span className="ml-auto text-orange-400/70">Keep it going!</span>}
        </div>
      )}

      {/* Unread milestone messages */}
      {messages.map((msg: MilestoneMessage) => (
        <MilestoneCard key={msg.id} message={msg} />
      ))}
    </div>
  )
}

function NextMilestoneBar({ summary }: { summary: ProgressionSummary }) {
  const next = summary.next_milestone
  if (!next) return null

  return (
    <div className="rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2.5">
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <Target className="h-3 w-3" />
          <span>Next: {next.title}</span>
        </div>
        <span className="text-muted-foreground/60">{Math.round(next.progress_pct)}%</span>
      </div>
      <div className="mt-1.5 h-1.5 rounded-full bg-white/5 overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-primary/60 to-primary transition-all duration-500"
          style={{ width: `${Math.min(next.progress_pct, 100)}%` }}
        />
      </div>
      {/* Level + region context */}
      <div className="mt-1.5 flex items-center justify-between text-[10px] text-muted-foreground/40">
        <span>Lvl {summary.level} — {summary.region_key.replace(/_/g, " ").toLowerCase()}</span>
        <div className="flex items-center gap-1">
          <TrendingUp className="h-2.5 w-2.5" />
          <span>{summary.message_count} msgs</span>
        </div>
      </div>
    </div>
  )
}
