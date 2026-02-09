import { cn } from "@/lib/utils"

interface AvatarCircleProps {
  name?: string | null
  avatarUrl?: string | null
  size?: "xs" | "sm" | "md" | "lg" | "xl"
  className?: string
}

const SIZES = {
  xs: "h-6 w-6 text-[10px]",
  sm: "h-7 w-7 text-xs",
  md: "h-10 w-10 text-sm",
  lg: "h-12 w-12 text-base",
  xl: "h-16 w-16 text-lg",
} as const

/**
 * Displays an avatar image if available, otherwise a gradient circle with the first letter.
 * Use this everywhere instead of hardcoded companion-avatar.png references.
 */
export default function AvatarCircle({
  name,
  avatarUrl,
  size = "md",
  className,
}: AvatarCircleProps) {
  const initial = (name ?? "?")[0]?.toUpperCase() ?? "?"

  // If we have a real avatar URL (not the old placeholder), show it
  if (avatarUrl && !avatarUrl.includes("companion-avatar")) {
    return (
      <img
        src={avatarUrl}
        alt={name ?? "Companion"}
        className={cn(
          "shrink-0 rounded-full object-cover",
          SIZES[size],
          className,
        )}
      />
    )
  }

  // Gradient initial fallback
  return (
    <div
      className={cn(
        "shrink-0 rounded-full flex items-center justify-center font-bold text-white bg-gradient-to-br from-primary to-primary/60",
        SIZES[size],
        className,
      )}
      aria-label={name ?? "Companion"}
    >
      {initial}
    </div>
  )
}
