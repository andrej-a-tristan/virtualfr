import { useEffect, useRef, useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useSearchParams } from "react-router-dom"
import { getChatHistory, postChatAppOpen, getCurrentGirlfriend } from "@/lib/api/endpoints"
import { useChatStore } from "@/lib/store/useChatStore"
import { useAppStore } from "@/lib/store/useAppStore"
import ChatHeader from "@/components/chat/ChatHeader"
import MessageList from "@/components/chat/MessageList"
import Composer from "@/components/chat/Composer"
import { Skeleton } from "@/components/ui/skeleton"
import { Gift } from "lucide-react"

export default function Chat() {
  const setMessages = useChatStore((s) => s.setMessages)
  const isStreaming = useChatStore((s) => s.isStreaming)
  const currentGirlfriendId = useAppStore((s) => s.currentGirlfriendId)
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const [giftBanner, setGiftBanner] = useState(false)
  const hasMergedRef = useRef(false)

  const { data: gf } = useQuery({ queryKey: ["girlfriend"], queryFn: getCurrentGirlfriend })
  const { data: appOpenData } = useQuery({
    queryKey: ["chatAppOpen", gf?.id],
    queryFn: () => postChatAppOpen(gf!.id),
    enabled: !!gf?.id,
    staleTime: 60_000,
  })
  const { data: historyData, isLoading } = useQuery({
    queryKey: ["chatHistory", currentGirlfriendId],
    queryFn: () => getChatHistory(currentGirlfriendId ?? undefined),
  })

  // Handle gift_success return from Stripe
  useEffect(() => {
    if (searchParams.get("gift_success") === "1") {
      setGiftBanner(true)
      searchParams.delete("gift_success")
      setSearchParams(searchParams, { replace: true })
      const timer = setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["chatHistory"] })
        queryClient.invalidateQueries({ queryKey: ["chatState"] })
      }, 3000)
      const hide = setTimeout(() => setGiftBanner(false), 8000)
      return () => { clearTimeout(timer); clearTimeout(hide) }
    }
  }, [searchParams, setSearchParams, queryClient])

  // Handle upgraded=1 return from Stripe checkout (Premium upgrade)
  useEffect(() => {
    if (searchParams.get("upgraded") === "1") {
      searchParams.delete("upgraded")
      setSearchParams(searchParams, { replace: true })
      // Refetch billing status so the UI picks up the new plan
      queryClient.invalidateQueries({ queryKey: ["billingStatus"] })
      queryClient.invalidateQueries({ queryKey: ["girlfriendsList"] })
    }
  }, [searchParams, setSearchParams, queryClient])

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
      {giftBanner && (
        <div className="flex items-center justify-center gap-2 bg-primary/10 border-b border-primary/20 px-4 py-2.5 text-sm text-primary animate-in fade-in slide-in-from-top duration-300">
          <Gift className="h-4 w-4" />
          <span className="font-medium">Your gift is being delivered... </span>
        </div>
      )}
      <MessageList className="flex-1" />
      <Composer />
    </div>
  )
}
