/**
 * POST /api/chat/send — full engine pipeline (bond engine, behavior engine,
 * prompt builder, memory, personality, OpenAI streaming).
 *
 * Stream format: event: token / data: {"type":"token","token":"..."},
 *                event: done  / data: {"type":"done"}
 * Use flushSync so each token paints immediately (React 18 would otherwise batch updates).
 */
import { flushSync } from "react-dom"
import { useChatStore } from "@/lib/store/useChatStore"
import { useAppStore } from "@/lib/store/useAppStore"

export async function sendChatMessage(message: string): Promise<void> {
  const { appendMessage, setStreamingContent, setIsStreaming } = useChatStore.getState()
  const girlfriendId = useAppStore.getState().currentGirlfriendId

  setStreamingContent("")
  setIsStreaming(true)
  try {
    const res = await fetch("/api/chat/send", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        girlfriend_id: girlfriendId ?? undefined,
      }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({})) as { error?: string; message?: string; detail?: string | unknown }
      // Friendly message for daily limit
      if (res.status === 429 && err.error === "daily_limit_reached") {
        throw new Error(err.message || "You've used all your free messages today. Upgrade to Plus for unlimited messaging!")
      }
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
          if (payload === "[DONE]" || lastEvent === "done" || (payload.includes('"type":"done"') || payload.includes('"type": "done"'))) {
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
            const data = JSON.parse(payload) as { token?: string; error?: string; finish_reason?: string; type?: string; message?: Record<string, unknown>; decision?: Record<string, unknown> }
            // Handle image_decision events from the backend
            if ((lastEvent === "image_decision" || data.type === "image_decision") && data.message) {
              const msg = data.message as Record<string, string | null>
              appendMessage({
                id: msg.id || `decision-${Date.now()}`,
                role: "assistant",
                content: (msg.content as string) || "",
                image_url: null,
                event_type: "image_decision",
                created_at: (msg.created_at as string) || new Date().toISOString(),
                ...(data.decision ? { decision: data.decision } : {}),
              } as Parameters<typeof appendMessage>[0])
              continue
            }
            // Handle relationship_gain events (trust/intimacy changes)
            if ((lastEvent === "relationship_gain" || data.type === "relationship_gain") && (data as Record<string, unknown>).gain) {
              const gain = (data as Record<string, unknown>).gain as Record<string, unknown>
              appendMessage({
                id: `gain-${Date.now()}`,
                role: "assistant",
                content: "",
                image_url: null,
                event_type: "relationship_gain",
                event_key: (gain.reason as string) || "conversation",
                created_at: new Date().toISOString(),
                gain_data: gain,
              } as Parameters<typeof appendMessage>[0])
              continue
            }
            // Handle relationship_achievement events (achievement unlocked)
            if ((lastEvent === "relationship_achievement" || data.type === "relationship_achievement") && (data as Record<string, unknown>).achievement) {
              const ach = (data as Record<string, unknown>).achievement as Record<string, unknown>
              appendMessage({
                id: `ach-${Date.now()}`,
                role: "assistant",
                content: "",
                image_url: null,
                event_type: "relationship_achievement",
                event_key: (ach.id as string) || "",
                created_at: new Date().toISOString(),
                achievement: ach,
              } as Parameters<typeof appendMessage>[0])
              continue
            }
            // Handle intimacy_achievement events (intimacy achievement unlocked)
            if ((lastEvent === "intimacy_achievement" || data.type === "intimacy_achievement") && (data as Record<string, unknown>).achievement) {
              const ach = (data as Record<string, unknown>).achievement as Record<string, unknown>
              appendMessage({
                id: `intach-${Date.now()}`,
                role: "assistant",
                content: `${(ach.icon as string) || "🔥"} **${(ach.title as string) || "Achievement"}** unlocked — ${(ach.subtitle as string) || ""}`,
                image_url: null,
                event_type: "intimacy_achievement",
                event_key: (ach.id as string) || "",
                created_at: new Date().toISOString(),
                achievement: ach,
              } as Parameters<typeof appendMessage>[0])
              continue
            }
            // Handle intimacy_photo_ready events (photo reward for intimacy achievement)
            if ((lastEvent === "intimacy_photo_ready" || data.type === "intimacy_photo_ready") && (data as Record<string, unknown>).photo) {
              const photo = (data as Record<string, unknown>).photo as Record<string, unknown>
              const msg = (data as Record<string, unknown>).message as Record<string, string | null> | undefined
              appendMessage({
                id: msg?.id || `intphoto-${Date.now()}`,
                role: "assistant",
                content: msg?.content || `${(photo.icon as string) || "🔥"} *${(photo.title as string) || "Achievement"}* — unlocked`,
                image_url: (photo.image_url as string) || null,
                event_type: "intimacy_photo_ready",
                event_key: (photo.id as string) || "",
                created_at: msg?.created_at || new Date().toISOString(),
              } as Parameters<typeof appendMessage>[0])
              continue
            }
            // Handle blurred_preview events (proactive surprise for free users)
            if ((lastEvent === "blurred_preview" || data.type === "blurred_preview") && data.message) {
              const msg = data.message as Record<string, string | null>
              appendMessage({
                id: msg.id || `blurred-${Date.now()}`,
                role: "assistant",
                content: (msg.content as string) || "",
                image_url: null,
                event_type: "blurred_preview",
                event_key: (msg.event_key as string) || "free_plan_upgrade",
                created_at: (msg.created_at as string) || new Date().toISOString(),
                blurred_image_url: (msg.blurred_image_url as string) || undefined,
              } as Parameters<typeof appendMessage>[0])
              continue
            }
            // Handle 'message' event: the server-saved assistant message (has proper DB id)
            if ((lastEvent === "message" || data.type === "message") && data.message) {
              const msg = data.message as Record<string, string | null>
              appendMessage({
                id: msg.id || `assistant-${Date.now()}`,
                role: "assistant",
                content: (msg.content as string) || fullContent,
                image_url: (msg.image_url as string) || null,
                event_type: (msg.event_type as string) || null,
                created_at: (msg.created_at as string) || new Date().toISOString(),
              })
              setStreamingContent("")
              fullContent = "" // Clear so 'done' doesn't duplicate
              continue
            }
            if ((lastEvent === "token" || data.type === "token") && data.token) {
              fullContent += data.token
              flushSync(() => setStreamingContent(fullContent))
            } else if ((lastEvent === "error" || data.type === "error") && data.error) {
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
            } else if (data.finish_reason || data.type === "done") {
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
