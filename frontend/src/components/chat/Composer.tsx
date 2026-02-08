import { useState, useRef } from "react"
import { useSSEChat } from "@/lib/hooks/useSSEChat"
import { useChatStore } from "@/lib/store/useChatStore"
import { useAppStore } from "@/lib/store/useAppStore"
import { useQuery } from "@tanstack/react-query"
import { getBillingStatus } from "@/lib/api/endpoints"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import PaywallInlineCard from "./PaywallInlineCard"
import GiftModal from "./GiftModal"
import { Send, ImagePlus, Gift } from "lucide-react"

export default function Composer() {
  const [text, setText] = useState("")
  const [showGifts, setShowGifts] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const { sendMessage } = useSSEChat()
  const { isStreaming, appendMessage } = useChatStore()
  const girlfriend = useAppStore((s) => s.girlfriend)
  const { data: billing } = useQuery({ queryKey: ["billingStatus"], queryFn: getBillingStatus })

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
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : String(e)
      appendMessage({
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: `Error: ${errMsg}`,
        image_url: null,
        event_type: null,
        created_at: new Date().toISOString(),
      })
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
        <Button
          size="icon"
          variant="outline"
          className="rounded-xl text-primary border-primary/30 hover:bg-primary/10"
          onClick={() => setShowGifts(true)}
          aria-label="Buy her something"
        >
          <Gift className="h-4 w-4" />
        </Button>
      </div>

      <GiftModal
        open={showGifts}
        onClose={() => setShowGifts(false)}
        girlfriendName={girlfriend?.display_name || girlfriend?.name}
      />
    </div>
  )
}
