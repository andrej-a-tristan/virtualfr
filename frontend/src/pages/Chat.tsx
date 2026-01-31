import { useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { getChatHistory } from "@/lib/api/endpoints"
import { useChatStore } from "@/lib/store/useChatStore"
import ChatHeader from "@/components/chat/ChatHeader"
import MessageList from "@/components/chat/MessageList"
import Composer from "@/components/chat/Composer"
import { Skeleton } from "@/components/ui/skeleton"

export default function Chat() {
  const setMessages = useChatStore((s) => s.setMessages)
  const { data, isLoading } = useQuery({
    queryKey: ["chatHistory"],
    queryFn: getChatHistory,
  })

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
      <MessageList className="flex-1" />
      <Composer />
    </div>
  )
}
