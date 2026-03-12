/**
 * Stream chat from the internal `/api/chat/send` endpoint and parse SSE.
 * Uses the full relationship/behavior pipeline (bond engine, dossier, achievements, etc.).
 * Stream format: event: token / data: {"token":"..."}, plus richer events for gains/achievements.
 * Sending a new message while streaming aborts the current stream and commits partial reply.
 */
import { flushSync } from "react-dom"
import { useChatStore } from "@/lib/store/useChatStore"
import { useAppStore } from "@/lib/store/useAppStore"
import { getChatSendStreamUrl } from "@/lib/api/endpoints"

let currentAbortController: AbortController | null = null

export async function sendChatMessage(message: string): Promise<void> {
  const { appendMessage, setStreamingContent, setIsStreaming } = useChatStore.getState()
  const girlfriendId = useAppStore.getState().currentGirlfriendId

  // Queue non-token events so we can insert them smoothly AFTER the main reply.
  const pendingEvents: Array<{ type: string; data: unknown }> = []

  const flushPendingEvents = () => {
    for (const evt of pendingEvents) {
      const { type, data } = evt

      // Image decision (tease/blurred paywall gating)
      if (type === "image_decision") {
        const d = data as {
          message?: Record<string, string | null>
          decision?: { ui_copy?: string; suggested_prompts?: string[]; reason?: string; blurred_image_url?: string; action?: string }
        }
        const msg = d.message as Record<string, string | null> | undefined
        if (!msg) continue
        const decision = d.decision

        // If the decision is blurred_paywall, render as a blurred preview card
        if (decision?.action === "blurred_paywall") {
          appendMessage({
            id: msg.id || `blurred-${Date.now()}`,
            role: "assistant",
            content: (decision.ui_copy as string) || (msg.content as string) || "She sent you something special... Upgrade to see it.",
            image_url: null,
            event_type: "blurred_preview",
            event_key: (decision.reason as string) || (msg.event_key as string) || "free_plan_upgrade",
            created_at: (msg.created_at as string) || new Date().toISOString(),
            blurred_image_url: (decision.blurred_image_url as string) || undefined,
          } as Parameters<typeof appendMessage>[0])
        } else {
          appendMessage({
            id: msg.id || `decision-${Date.now()}`,
            role: "assistant",
            content: (decision?.ui_copy as string) || (msg.content as string) || "This content requires a deeper connection.",
            image_url: null,
            event_type: "image_decision",
            event_key: (decision?.reason as string) || (msg.event_key as string) || undefined,
            created_at: (msg.created_at as string) || new Date().toISOString(),
            ...(decision ? { decision } : {}),
          } as Parameters<typeof appendMessage>[0])
        }
        continue
      }

      // Relationship gain (trust/intimacy delta)
      if (type === "relationship_gain") {
        const d = data as { gain: Record<string, unknown> }
        const gain = d.gain
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

      // Relationship achievement (region/story achievement)
      if (type === "relationship_achievement") {
        const d = data as { achievement: Record<string, unknown> }
        const ach = d.achievement
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

      // Intimacy achievement / stage unlock
      if (type === "intimacy_achievement") {
        const d = data as { achievement: Record<string, unknown> }
        const ach = d.achievement
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

      // Intimacy photo ready (image reward)
      if (type === "intimacy_photo_ready") {
        const d = data as { photo: Record<string, unknown>; message?: Record<string, string | null> }
        const photo = d.photo
        const msg = d.message as Record<string, string | null> | undefined
        appendMessage({
          id: msg?.id || `intphoto-${Date.now()}`,
          role: "assistant",
          content: msg?.content || `${(photo.icon as string) || "🔥"} *${(photo.title as string) || "Achievement"}* — unlocked`,
          image_url: (photo.image_url as string) || null,
          event_type: "intimacy_photo_ready",
          event_key: (photo.id as string) || "",
          created_at: msg?.created_at || new Date().toISOString(),
          photo,
        } as Parameters<typeof appendMessage>[0])
        continue
      }

      // Blurred preview (proactive surprise)
      if (type === "blurred_preview") {
        const d = data as { message?: Record<string, string | null> }
        const msg = d.message as Record<string, string | null> | undefined
        if (!msg) continue
        appendMessage({
          id: msg.id || `blurred-${Date.now()}`,
          role: "assistant",
          content: (msg.content as string) || "She sent you something special... Upgrade to see it.",
          image_url: null,
          event_type: "blurred_preview",
          event_key: (msg.event_key as string) || "free_plan_upgrade",
          created_at: (msg.created_at as string) || new Date().toISOString(),
          blurred_image_url: (msg.blurred_image_url as string) || undefined,
        } as Parameters<typeof appendMessage>[0])
        continue
      }
    }
    pendingEvents.length = 0
  }
  // Abort any in-flight stream so the new message gets a fresh reply
  if (currentAbortController) {
    currentAbortController.abort()
    currentAbortController = null
  }
  currentAbortController = new AbortController()
  const signal = currentAbortController.signal

  setStreamingContent("")
  setIsStreaming(true)
  let fullContent = ""
  let streamDone = false
  let streamError: string | null = null
  try {
    // Backend already knows full history from persistence; send only this turn.
    const body = {
      message,
      girlfriend_id: girlfriendId,
    }
    const res = await fetch(getChatSendStreamUrl(), {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      signal,
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
    let lastEvent = ""
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
            flushPendingEvents()
            break
          }
          try {
            const data = JSON.parse(payload) as {
              token?: string
              error?: string
              finish_reason?: string
              type?: string
              message?: Record<string, unknown>
              decision?: Record<string, unknown>
              gain?: Record<string, unknown>
              achievement?: Record<string, unknown>
              photo?: Record<string, unknown>
            }
            // Queue image_decision events from the backend
            if ((lastEvent === "image_decision" || data.type === "image_decision") && data.message) {
              pendingEvents.push({ type: "image_decision", data })
              continue
            }
            // Queue relationship_gain events (trust/intimacy changes)
            if ((lastEvent === "relationship_gain" || data.type === "relationship_gain") && (data as Record<string, unknown>).gain) {
              pendingEvents.push({ type: "relationship_gain", data: { gain: (data as Record<string, unknown>).gain as Record<string, unknown> } })
              continue
            }
            // Queue relationship_achievement events (achievement unlocked)
            if ((lastEvent === "relationship_achievement" || data.type === "relationship_achievement") && (data as Record<string, unknown>).achievement) {
              pendingEvents.push({ type: "relationship_achievement", data: { achievement: (data as Record<string, unknown>).achievement as Record<string, unknown> } })
              continue
            }
            // Queue intimacy_achievement events (intimacy achievement unlocked)
            if ((lastEvent === "intimacy_achievement" || data.type === "intimacy_achievement") && (data as Record<string, unknown>).achievement) {
              pendingEvents.push({ type: "intimacy_achievement", data: { achievement: (data as Record<string, unknown>).achievement as Record<string, unknown> } })
              continue
            }
            // Queue intimacy_photo_ready events (photo reward for intimacy achievement)
            if ((lastEvent === "intimacy_photo_ready" || data.type === "intimacy_photo_ready") && (data as Record<string, unknown>).photo) {
              pendingEvents.push({
                type: "intimacy_photo_ready",
                data: {
                  photo: (data as Record<string, unknown>).photo as Record<string, unknown>,
                  message: (data as Record<string, unknown>).message as Record<string, string | null> | undefined,
                },
              })
              continue
            }
            // Queue blurred_preview events (proactive surprise for free users)
            if ((lastEvent === "blurred_preview" || data.type === "blurred_preview") && data.message) {
              pendingEvents.push({ type: "blurred_preview", data })
              continue
            }
            if ((lastEvent === "token" || data.type === "token") && data.token) {
              fullContent += data.token
              flushSync(() => setStreamingContent(fullContent))
            } else if ((lastEvent === "error" || data.type === "error") && data.error) {
              streamError = String(data.error)
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
              flushPendingEvents()
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
    if (streamError) throw new Error(streamError)
  } catch (e) {
    if (e instanceof Error && e.name === "AbortError") {
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
      flushPendingEvents()
    } else {
      throw e
    }
  } finally {
    currentAbortController = null
    useChatStore.getState().setIsStreaming(false)
    useChatStore.getState().setStreamingContent("")
  }
}

export function useSSEChat() {
  return { sendMessage: sendChatMessage }
}
