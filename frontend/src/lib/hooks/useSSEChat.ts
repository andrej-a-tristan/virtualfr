/**
 * POST /v1/chat/stream (gateway → internal LLM) and parse SSE.
 * Stream format: event: token / data: {"token":"..."}, event: done / data: {"finish_reason":"stop"}.
 * Use flushSync so each token paints immediately (React 18 would otherwise batch updates).
 */
import { flushSync } from "react-dom"
import { useChatStore } from "@/lib/store/useChatStore"
import { useAppStore } from "@/lib/store/useAppStore"

const CHAT_GATEWAY_KEY = import.meta.env.VITE_CHAT_GATEWAY_KEY ?? "dev-key"

export async function sendChatMessage(message: string): Promise<void> {
  const { messages, appendMessage, setStreamingContent, setIsStreaming } = useChatStore.getState()
  const user = useAppStore.getState().user
  const girlfriendId = useAppStore.getState().currentGirlfriendId
  const sessionId = user?.id ?? "anonymous"

  setStreamingContent("")
  setIsStreaming(true)
  try {
    // history already includes the current user message (Composer appended it before calling sendMessage)
    const history = messages.map((m) => ({ role: m.role, content: (m.content ?? "").trim() }))
    const body = {
      session_id: sessionId,
      model: "mock-1",
      model_version: "local",
      messages: history,
      girlfriend_id: girlfriendId,
    }
    const res = await fetch("/api/chat/stream", {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${CHAT_GATEWAY_KEY}`,
      },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({})) as { error?: string; detail?: string | unknown }
      let msg = err.error
      if (msg == null) {
        if (typeof err.detail === "string") msg = err.detail
        else if (Array.isArray(err.detail)) msg = err.detail.map((d: { msg?: string }) => d?.msg ?? d).join("; ")
        else msg = JSON.stringify(err.detail ?? res.statusText)
      }
      throw new Error(`${res.status}: ${msg}`)
    }
    const reader = res.body?.getReader()
    const decoder = new TextDecoder()
    let buffer = ""
    let fullContent = ""
    let lastEvent = ""
    let streamDone = false
    while (reader && !streamDone) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split("\n")
      buffer = lines.pop() ?? ""
      for (const line of lines) {
        const trimmed = line.trim()
        if (trimmed.startsWith("event:")) {
          lastEvent = trimmed.slice(6).trim()
          continue
        }
        if (trimmed.startsWith("data:")) {
          const payload = trimmed.slice(5).trim()
          if (payload === "[DONE]" || lastEvent === "done") {
            if (fullContent) {
              appendMessage({
                id: `assistant-${Date.now()}`,
                role: "assistant",
                content: fullContent,
                image_url: null,
                event_type: null,
                created_at: new Date().toISOString(),
              })
            }
            setStreamingContent("")
            streamDone = true
            break
          }
          try {
            const data = JSON.parse(payload) as { token?: string; error?: string; finish_reason?: string }
            if (lastEvent === "token" && data.token) {
              fullContent += data.token
              flushSync(() => setStreamingContent(fullContent))
            } else if (lastEvent === "error" && data.error) {
              appendMessage({
                id: `assistant-${Date.now()}`,
                role: "assistant",
                content: `Error: ${data.error}`,
                image_url: null,
                event_type: null,
                created_at: new Date().toISOString(),
              })
              streamDone = true
              break
            } else if (data.finish_reason) {
              if (fullContent) {
                appendMessage({
                  id: `assistant-${Date.now()}`,
                  role: "assistant",
                  content: fullContent,
                  image_url: null,
                  event_type: null,
                  created_at: new Date().toISOString(),
                })
              }
              setStreamingContent("")
              streamDone = true
              break
            }
          } catch (e) {
            if (e instanceof SyntaxError) continue
            throw e
          }
        }
      }
    }
    if (fullContent && !streamDone) {
      appendMessage({
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: fullContent,
        image_url: null,
        event_type: null,
        created_at: new Date().toISOString(),
      })
    }
  } finally {
    useChatStore.getState().setIsStreaming(false)
    useChatStore.getState().setStreamingContent("")
  }
}

export function useSSEChat() {
  return { sendMessage: sendChatMessage }
}
