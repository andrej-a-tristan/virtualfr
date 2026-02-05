import { useEffect, useRef } from "react"
import { useQuery } from "@tanstack/react-query"
import { getChatHistory, postChatAppOpen } from "@/lib/api/endpoints"
import { getCurrentGirlfriend } from "@/lib/api/endpoints"
import { useChatStore } from "@/lib/store/useChatStore"
import ChatHeader from "@/components/chat/ChatHeader"
import MessageList from "@/components/chat/MessageList"
import Composer from "@/components/chat/Composer"
import { Skeleton } from "@/components/ui/skeleton"

export default function Chat() {
  const setMessages = useChatStore((s) => s.setMessages)
  const isStreaming = useChatStore((s) => s.isStreaming)
  const hasMergedRef = useRef(false)

  const { data: gf } = useQuery({ queryKey: ["girlfriend"], queryFn: getCurrentGirlfriend })
  const { data: appOpenData } = useQuery({
    queryKey: ["chatAppOpen", gf?.id],
    queryFn: () => postChatAppOpen(gf!.id),
    enabled: !!gf?.id,
    staleTime: 60_000,
  })
  const { data: historyData, isLoading } = useQuery({
    queryKey: ["chatHistory"],
    queryFn: getChatHistory,
  })

  useEffect(() => {
    hasMergedRef.current = false
  }, [gf?.id])

  // Merge app_open messages (top) with history when data is ready. Don't overwrite if we're
  // streaming or have more messages locally (e.g. just received a streamed reply).
  useEffect(() => {
    if (historyData == null) return
    const history = historyData.messages ?? []
    const initiated = appOpenData?.messages ?? []
    const next = initiated.length > 0 ? [...initiated, ...history] : history

    setMessages((prev) => {
      if (isStreaming) return prev
      if (hasMergedRef.current && next.length <= prev.length) return prev
      hasMergedRef.current = true
      return next
    })
  }, [historyData, appOpenData?.messages, isStreaming, setMessages])

  if (isLoading) {
    return (
      <div className="flex h-[calc(100vh-8rem)] flex-col rounded-2xl border border-white/10 bg-card/50">
        <Skeleton className="h-16 w-full rounded-t-2xl" />
        <div className="flex-1 space-y-3 p-4">
          <Skeleton className="h-12 w-3/4" />
          <Skeleton className="h-12 w-2/3 ml-auto" />
          <Skeleton className="h-12 w-4/5" />
        </div>
        <Skeleton className="h-14 w-full rounded-b-2xl" />
      </div>
    )
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col rounded-2xl border border-white/10 bg-card/50 shadow-xl">
      <ChatHeader />
      <MessageList className="flex-1" />
      <Composer />
    </div>
  )
}
