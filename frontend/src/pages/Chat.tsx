import { useEffect, useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useSearchParams } from "react-router-dom"
import { getChatHistory } from "@/lib/api/endpoints"
import { useChatStore } from "@/lib/store/useChatStore"
import ChatHeader from "@/components/chat/ChatHeader"
import MessageList from "@/components/chat/MessageList"
import Composer from "@/components/chat/Composer"
import { Skeleton } from "@/components/ui/skeleton"
import { Gift } from "lucide-react"

export default function Chat() {
  const setMessages = useChatStore((s) => s.setMessages)
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const [giftBanner, setGiftBanner] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ["chatHistory"],
    queryFn: getChatHistory,
  })

  // Handle gift_success return from Stripe
  useEffect(() => {
    if (searchParams.get("gift_success") === "1") {
      setGiftBanner(true)
      // Clean up URL
      searchParams.delete("gift_success")
      setSearchParams(searchParams, { replace: true })
      // Refetch chat history after a short delay (webhook needs time)
      const timer = setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["chatHistory"] })
        queryClient.invalidateQueries({ queryKey: ["chatState"] })
      }, 3000)
      // Hide banner after 8s
      const hide = setTimeout(() => setGiftBanner(false), 8000)
      return () => { clearTimeout(timer); clearTimeout(hide) }
    }
  }, [searchParams, setSearchParams, queryClient])

  useEffect(() => {
    if (data?.messages) setMessages(data.messages)
  }, [data?.messages, setMessages])

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
          <span className="font-medium">Your gift is being delivered… ✨</span>
        </div>
      )}
      <MessageList className="flex-1" />
      <Composer />
    </div>
  )
}
