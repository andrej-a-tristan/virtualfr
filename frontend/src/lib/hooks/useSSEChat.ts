/**
 * POST /api/chat/send and parse SSE stream.
 * Appends streaming tokens to a draft assistant message; on "message" event finalizes in store.
 */
import type { ChatMessage } from "@/lib/api/types"
import { useChatStore } from "@/lib/store/useChatStore"

export async function sendChatMessage(message: string): Promise<void> {
  const { appendMessage, setStreamingContent, setIsStreaming } = useChatStore.getState()
  setStreamingContent("")
  setIsStreaming(true)
  try {
    const res = await fetch("/api/chat/send", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error((err as { error?: string }).error || "Send failed")
    }
    const reader = res.body?.getReader()
    if (!reader) {
      useChatStore.getState().appendMessage({
        id: `err-${Date.now()}`,
        role: "assistant",
        content: "[Error: No response body from server]",
        image_url: null,
        event_type: null,
        event_key: null,
        created_at: new Date().toISOString(),
      })
      return
    }
    const decoder = new TextDecoder()
    let buffer = ""
    let fullContent = ""
    while (reader) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split("\n")
      buffer = lines.pop() ?? ""
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6)) as { type: string; token?: string; message?: ChatMessage; error?: string }
            if (data.type === "token" && data.token) {
              fullContent += data.token
              setStreamingContent(fullContent)
            } else if (data.type === "message" && data.message) {
              appendMessage(data.message)
              setStreamingContent("")
            } else if (data.type === "error" && data.error) {
              appendMessage({
                id: `err-${Date.now()}`,
                role: "assistant",
                content: `[Error: ${data.error}]`,
                image_url: null,
                event_type: null,
                event_key: null,
                created_at: new Date().toISOString(),
              })
              setStreamingContent("")
            } else if (data.type === "done") {
              setStreamingContent("")
            }
          } catch {
            // skip invalid json
          }
        }
      }
    }
  } finally {
    useChatStore.getState().setIsStreaming(false)
    useChatStore.getState().setStreamingContent("")
  }
}

export function useSSEChat() {
  return { sendMessage: sendChatMessage }
}
