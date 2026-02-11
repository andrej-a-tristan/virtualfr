import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format an ISO date string as a relative time label.
 * Returns "Just now", "2m ago", "3h ago", "5d ago", etc.
 */
export function formatRelativeTime(isoString: string | null | undefined): string {
  if (!isoString) return "Never"
  const date = new Date(isoString)
  if (isNaN(date.getTime())) return "Never"

  const now = Date.now()
  const diffMs = now - date.getTime()
  if (diffMs < 0) return "Just now"

  const seconds = Math.floor(diffMs / 1000)
  if (seconds < 60) return "Just now"

  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`

  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}d ago`

  const months = Math.floor(days / 30)
  if (months < 12) return `${months}mo ago`

  const years = Math.floor(months / 12)
  return `${years}y ago`
}
