import type { GalleryItem } from "@/lib/api/types"
import { cn } from "@/lib/utils"

interface GalleryGridProps {
  items: GalleryItem[]
  onSelect: (item: GalleryItem) => void
  className?: string
}

export default function GalleryGrid({ items, onSelect, className }: GalleryGridProps) {
  if (items.length === 0) {
    return (
      <div className={cn("flex flex-col items-center justify-center rounded-2xl border border-dashed border-white/20 bg-card/30 py-16 text-center", className)}>
        <p className="text-muted-foreground">No images yet.</p>
        <p className="mt-1 text-sm text-muted-foreground">Request images in Chat to see them here.</p>
      </div>
    )
  }

  return (
    <div className={cn("grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4", className)}>
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          className="aspect-square overflow-hidden rounded-xl border border-white/10 bg-muted/50 transition hover:border-primary/30 focus:outline-none focus:ring-2 focus:ring-primary"
          onClick={() => onSelect(item)}
        >
          <img src={item.url} alt={item.caption ?? "Gallery"} className="h-full w-full object-cover" />
        </button>
      ))}
    </div>
  )
}
