import { useState, useEffect } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useSearchParams } from "react-router-dom"
import { getChatHistory, getGallery } from "@/lib/api/endpoints"
import { useChatStore } from "@/lib/store/useChatStore"
import { useAppStore } from "@/lib/store/useAppStore"
import ChatHeader from "@/components/chat/ChatHeader"
import MessageList from "@/components/chat/MessageList"
import Composer from "@/components/chat/Composer"
import GalleryGrid from "@/components/gallery/GalleryGrid"
import ImageViewerModal from "@/components/gallery/ImageViewerModal"
import type { GalleryItem } from "@/lib/api/types"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { MessageCircle, Image as ImageIcon, Gift, ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"

type Tab = "chat" | "gallery"

export default function GirlPage() {
  const [tab, setTab] = useState<Tab>("chat")
  const setMessages = useChatStore((s) => s.setMessages)
  const currentGirlfriendId = useAppStore((s) => s.currentGirlfriendId)
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const [giftBanner, setGiftBanner] = useState(false)

  // Gallery state
  const [selectedImage, setSelectedImage] = useState<GalleryItem | null>(null)
  const [viewerOpen, setViewerOpen] = useState(false)

  // ── Chat data ─────────────────────────────────────────────────────────
  const { data: chatData, isLoading: chatLoading } = useQuery({
    queryKey: ["chatHistory", currentGirlfriendId],
    queryFn: () => getChatHistory(currentGirlfriendId ?? undefined),
    enabled: tab === "chat",
  })

  // ── Gallery data ──────────────────────────────────────────────────────
  const { data: galleryData, isLoading: galleryLoading } = useQuery({
    queryKey: ["gallery", currentGirlfriendId],
    queryFn: () => getGallery(currentGirlfriendId ?? undefined),
    enabled: tab === "gallery",
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

  // Handle upgraded=1 return from Stripe checkout
  useEffect(() => {
    if (searchParams.get("upgraded") === "1") {
      searchParams.delete("upgraded")
      setSearchParams(searchParams, { replace: true })
      queryClient.invalidateQueries({ queryKey: ["billingStatus"] })
      queryClient.invalidateQueries({ queryKey: ["girlfriendsList"] })
    }
  }, [searchParams, setSearchParams, queryClient])

  // Sync chat messages to store
  useEffect(() => {
    if (chatData?.messages) setMessages(chatData.messages)
  }, [chatData?.messages, setMessages])

  const handleSelectImage = (item: GalleryItem) => {
    setSelectedImage(item)
    setViewerOpen(true)
  }

  const galleryItems = galleryData?.items ?? []

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col rounded-2xl border border-white/10 bg-card/50 shadow-xl overflow-hidden">
      {/* Header — always visible */}
      <ChatHeader />

      {/* Tab bar below the header */}
      <div className="flex items-center border-b border-white/10 px-2">
        <button
          onClick={() => setTab("chat")}
          className={cn(
            "flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px",
            tab === "chat"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          <MessageCircle className="h-4 w-4" />
          Chat
        </button>
        <button
          onClick={() => setTab("gallery")}
          className={cn(
            "flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px",
            tab === "gallery"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          <ImageIcon className="h-4 w-4" />
          Gallery
        </button>
      </div>

      {/* ── Chat tab ───────────────────────────────────────────────────── */}
      {tab === "chat" && (
        <>
          {giftBanner && (
            <div className="flex items-center justify-center gap-2 bg-primary/10 border-b border-primary/20 px-4 py-2.5 text-sm text-primary animate-in fade-in slide-in-from-top duration-300">
              <Gift className="h-4 w-4" />
              <span className="font-medium">Your gift is being delivered...</span>
            </div>
          )}
          {chatLoading ? (
            <div className="flex-1 space-y-3 p-4">
              <Skeleton className="h-12 w-3/4" />
              <Skeleton className="h-12 w-2/3 ml-auto" />
              <Skeleton className="h-12 w-4/5" />
            </div>
          ) : (
            <MessageList className="flex-1" />
          )}
          <Composer />
        </>
      )}

      {/* ── Gallery tab ────────────────────────────────────────────────── */}
      {tab === "gallery" && (
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {galleryLoading ? (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <Skeleton key={i} className="aspect-square rounded-xl" />
              ))}
            </div>
          ) : galleryItems.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <ImageIcon className="h-12 w-12 text-muted-foreground/30 mb-3" />
              <p className="text-muted-foreground text-sm">No photos yet</p>
              <p className="text-muted-foreground/60 text-xs mt-1">
                Photos from your conversations will appear here
              </p>
              <Button
                variant="outline"
                size="sm"
                className="mt-4 gap-2"
                onClick={() => setTab("chat")}
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Back to chat
              </Button>
            </div>
          ) : (
            <GalleryGrid items={galleryItems} onSelect={handleSelectImage} />
          )}
          <ImageViewerModal item={selectedImage} open={viewerOpen} onOpenChange={setViewerOpen} />
        </div>
      )}
    </div>
  )
}
