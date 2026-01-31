import { cn } from "@/lib/utils"

export default function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex gap-1 rounded-2xl bg-muted/80 px-4 py-3">
        <span className={cn("h-2 w-2 rounded-full bg-muted-foreground/60 animate-bounce")} style={{ animationDelay: "0ms" }} />
        <span className={cn("h-2 w-2 rounded-full bg-muted-foreground/60 animate-bounce")} style={{ animationDelay: "150ms" }} />
        <span className={cn("h-2 w-2 rounded-full bg-muted-foreground/60 animate-bounce")} style={{ animationDelay: "300ms" }} />
      </div>
    </div>
  )
}
