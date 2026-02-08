import type { ChatMessage } from "@/lib/api/types"
import { cn } from "@/lib/utils"

interface MessageBubbleProps {
  message: ChatMessage
  className?: string
}

export default function MessageBubble({ message, className }: MessageBubbleProps) {
  const isUser = message.role === "user"
  const isMilestone = message.event_type === "milestone"
  return (
    <div
      className={cn(
        "flex w-full",
        isUser ? "justify-end" : "justify-start",
        className
      )}
    >
      <div className={cn("flex items-end gap-2", isUser ? "flex-row-reverse" : "flex-row")}>
        {!isUser && (
          <img
            src="/assets/companion-avatar.png"
            alt="Companion"
            className="h-7 w-7 shrink-0 rounded-full object-cover"
          />
        )}
        <div
          className={cn(
            "max-w-[85%] rounded-2xl px-4 py-2.5 text-sm",
            isUser
              ? "bg-primary text-primary-foreground"
              : isMilestone
                ? "bg-primary/20 text-primary border border-primary/30"
                : "bg-muted/80 text-foreground"
          )}
        >
          {message.content && <p className="whitespace-pre-wrap">{message.content}</p>}
        </div>
      </div>
    </div>
  )
}
