import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { getGallery } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import GalleryGrid from "@/components/gallery/GalleryGrid"
import ImageViewerModal from "@/components/gallery/ImageViewerModal"
import type { GalleryItem } from "@/lib/api/types"
import { Skeleton } from "@/components/ui/skeleton"

export default function Gallery() {
  const [selected, setSelected] = useState<GalleryItem | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const currentGirlfriendId = useAppStore((s) => s.currentGirlfriendId)
  const { data, isLoading } = useQuery({
    queryKey: ["gallery", currentGirlfriendId],
    queryFn: () => getGallery(currentGirlfriendId ?? undefined),
  })

  const handleSelect = (item: GalleryItem) => {
    setSelected(item)
    setModalOpen(true)
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">Gallery</h1>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="aspect-square rounded-xl" />
          ))}
        </div>
      </div>
    )
  }

  const items = data?.items ?? []

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Gallery</h1>
      <GalleryGrid items={items} onSelect={handleSelect} />
      <ImageViewerModal item={selected} open={modalOpen} onOpenChange={setModalOpen} />
    </div>
  )
}
