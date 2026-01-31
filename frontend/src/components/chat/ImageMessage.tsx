import type { ChatMessage } from "@/lib/api/types"
import { cn } from "@/lib/utils"

interface ImageMessageProps {
  message: ChatMessage
  className?: string
}

export default function ImageMessage({ message, className }: ImageMessageProps) {
  if (!message.image_url) return null
  return (
    <div className={cn("flex justify-start", className)}>
      <div className="max-w-[280px] overflow-hidden rounded-2xl border border-white/10 bg-muted/50">
        <img
          src={message.image_url}
          alt="Shared"
          className="h-auto w-full object-cover"
        />
        {message.content && (
          <p className="px-3 py-2 text-sm text-muted-foreground">{message.content}</p>
        )}
      </div>
    </div>
  )
}
