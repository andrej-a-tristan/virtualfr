/**
 * Habit inference from message history: preferred hours, typical gap.
 * Used by initiation engine. Parity with backend habits.py.
 */

export interface UserHabitProfile {
  preferredHours?: number[]
  typicalGapHours?: number
  updatedAt?: string
}

const DEFAULT_LAST_N = 50
const MIN_OCCURRENCES = 2
const TOP_HOURS = 3
const GAP_CAP_MIN = 4
const GAP_CAP_MAX = 72

/**
 * From last N user message timestamps, return top 3 hours (0-23) that appear at least twice.
 */
export function inferPreferredHours(
  messageTimestamps: string[],
  lastN: number = DEFAULT_LAST_N
): number[] {
  const recent = messageTimestamps.slice(-lastN)
  const hourCounts: Record<number, number> = {}
  for (const ts of recent) {
    const hour = new Date(ts).getUTCHours()
    hourCounts[hour] = (hourCounts[hour] ?? 0) + 1
  }
  const candidates = Object.entries(hourCounts)
    .filter(([, count]) => count >= MIN_OCCURRENCES)
    .map(([h, count]) => ({ hour: parseInt(h, 10), count }))
    .sort((a, b) => b.count - a.count)
  return candidates.slice(0, TOP_HOURS).map((c) => c.hour)
}

/**
 * Median gap in hours between consecutive user messages. Capped to [4, 72].
 */
export function inferTypicalGapHours(messageTimestamps: string[]): number | undefined {
  if (messageTimestamps.length < 2) return undefined
  const sorted = [...messageTimestamps].sort(
    (a, b) => new Date(a).getTime() - new Date(b).getTime()
  )
  const gaps: number[] = []
  for (let i = 1; i < sorted.length; i++) {
    const ms = new Date(sorted[i]).getTime() - new Date(sorted[i - 1]).getTime()
    const hours = ms / (1000 * 60 * 60)
    gaps.push(Math.max(GAP_CAP_MIN, Math.min(GAP_CAP_MAX, Math.round(hours))))
  }
  gaps.sort((a, b) => a - b)
  const mid = Math.floor(gaps.length / 2)
  const median = gaps.length % 2 ? gaps[mid] : (gaps[mid - 1] + gaps[mid]) / 2
  return Math.round(median)
}

export function buildHabitProfile(userMessageTimestamps: string[]): UserHabitProfile {
  return {
    preferredHours: inferPreferredHours(userMessageTimestamps).length
      ? inferPreferredHours(userMessageTimestamps)
      : undefined,
    typicalGapHours: inferTypicalGapHours(userMessageTimestamps),
    updatedAt: new Date().toISOString(),
  }
}
