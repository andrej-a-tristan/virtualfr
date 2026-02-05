import { useState, useRef } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useSSEChat } from "@/lib/hooks/useSSEChat"
import { useChatStore } from "@/lib/store/useChatStore"
import { getBillingStatus } from "@/lib/api/endpoints"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import PaywallInlineCard from "./PaywallInlineCard"
import { Send, ImagePlus } from "lucide-react"

export default function Composer() {
  const [text, setText] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()
  const { sendMessage } = useSSEChat()
  const { isStreaming, appendMessage } = useChatStore()
  const { data: billing } = useQuery({ queryKey: ["billing"], queryFn: getBillingStatus })

  const canSend = text.trim().length > 0 && !isStreaming
  const imageCapReached = billing ? (billing.plan === "free" && false) : false

  const handleSend = async () => {
    const msg = text.trim()
    if (!msg || isStreaming) return
    setText("")
    appendMessage({
      id: `user-${Date.now()}`,
      role: "user",
      content: msg,
      image_url: null,
      event_type: null,
      created_at: new Date().toISOString(),
    })
    try {
      await sendMessage(msg)
      await queryClient.invalidateQueries({ queryKey: ["chatHistory"] })
    } catch {
      // Error handled in hook / store
    }
    inputRef.current?.focus()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="space-y-2 border-t border-white/10 p-4">
      {billing && billing.plan === "free" && <PaywallInlineCard billing={billing} />}
      <div className="flex gap-2">
        <Input
          ref={inputRef}
          placeholder="Type a message…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isStreaming}
          className="flex-1 rounded-xl"
        />
        <Button
          size="icon"
          className="rounded-xl"
          disabled={!canSend}
          onClick={handleSend}
          aria-label="Send"
        >
          <Send className="h-4 w-4" />
        </Button>
        <Button
          size="icon"
          variant="outline"
          className="rounded-xl"
          disabled={imageCapReached || isStreaming}
          aria-label="Request image"
        >
          <ImagePlus className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
