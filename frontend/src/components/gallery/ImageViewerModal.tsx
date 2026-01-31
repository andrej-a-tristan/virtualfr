import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import type { GalleryItem } from "@/lib/api/types"

interface ImageViewerModalProps {
  item: GalleryItem | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function ImageViewerModal({ item, open, onOpenChange }: ImageViewerModalProps) {
  if (!item) return null
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent showClose className="max-w-2xl p-0 overflow-hidden">
        <DialogHeader className="p-4 pb-0">
          <DialogTitle className="sr-only">Image</DialogTitle>
        </DialogHeader>
        <div className="relative">
          <img
            src={item.url}
            alt={item.caption ?? "Gallery image"}
            className="w-full max-h-[80vh] object-contain"
          />
          {item.caption && (
            <p className="p-4 text-sm text-muted-foreground">{item.caption}</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
