import { create } from "zustand"
import type { ChatMessage } from "@/lib/api/types"

interface ChatState {
  messages: ChatMessage[]
  streamingContent: string
  isStreaming: boolean
  setMessages: (m: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) => void
  appendMessage: (m: ChatMessage) => void
  /** Insert system-initiated messages at the start (e.g. from app_open). */
  prependMessages: (m: ChatMessage[]) => void
  setStreamingContent: (s: string) => void
  setIsStreaming: (b: boolean) => void
  reset: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  streamingContent: "",
  isStreaming: false,
  setMessages: (m) =>
    set((s) => ({
      messages: typeof m === "function" ? m(s.messages) : m,
    })),
  appendMessage: (m) => set((s) => ({ messages: [...s.messages, m] })),
  prependMessages: (m) => set((s) => ({ messages: [...m, ...s.messages] })),
  setStreamingContent: (s) => set({ streamingContent: s }),
  setIsStreaming: (b) => set({ isStreaming: b }),
  reset: () => set({ messages: [], streamingContent: "", isStreaming: false }),
}))
