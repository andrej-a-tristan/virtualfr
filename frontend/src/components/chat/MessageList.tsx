import { useEffect, useRef } from "react"
import { useChatStore } from "@/lib/store/useChatStore"
import MessageBubble from "./MessageBubble"
import ImageMessage from "./ImageMessage"
import TypingIndicator from "./TypingIndicator"
import { cn } from "@/lib/utils"

interface MessageListProps {
  className?: string
}

export default function MessageList({ className }: MessageListProps) {
  const { messages, streamingContent, isStreaming } = useChatStore()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, streamingContent])

  return (
    <div className={cn("flex flex-1 flex-col gap-3 overflow-y-auto p-4", className)}>
      {messages.map((msg) =>
        msg.image_url ? (
          <ImageMessage key={msg.id} message={msg} />
        ) : (
          <MessageBubble key={msg.id} message={msg} />
        )
      )}
      {isStreaming && streamingContent && (
        <div className="flex justify-start">
          <div className="max-w-[85%] rounded-2xl bg-muted/80 px-4 py-2.5 text-sm text-foreground">
            {streamingContent}
            <span className="animate-pulse">▌</span>
          </div>
        </div>
      )}
      {isStreaming && !streamingContent && <TypingIndicator />}
      <div ref={bottomRef} />
    </div>
  )
}
