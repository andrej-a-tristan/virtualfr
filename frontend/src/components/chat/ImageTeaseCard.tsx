import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Heart, Lock, Sparkles } from "lucide-react"
import { useChatStore } from "@/lib/store/useChatStore"
import { useSSEChat } from "@/lib/hooks/useSSEChat"

interface ImageTeaseCardProps {
  uiCopy: string
  suggestedPrompts?: string[]
  reason?: string
}

export default function ImageTeaseCard({ uiCopy, suggestedPrompts = [], reason }: ImageTeaseCardProps) {
  const appendMessage = useChatStore((s) => s.appendMessage)
  const { sendMessage } = useSSEChat()

  const handlePromptClick = (prompt: string) => {
    // Append user message and send
    appendMessage({
      id: `user-${Date.now()}`,
      role: "user",
      content: prompt,
      image_url: null,
      event_type: null,
      created_at: new Date().toISOString(),
    })
    sendMessage(prompt)
  }

  return (
    <div className="flex w-full justify-center py-2">
      <Card className="w-full max-w-sm rounded-2xl border-pink-500/20 bg-gradient-to-b from-pink-500/10 to-pink-500/5">
        <CardContent className="p-4 space-y-3">
          {/* Header */}
          <div className="flex items-center justify-center gap-2">
            <Lock className="h-4 w-4 text-pink-400" />
            <span className="text-xs font-semibold uppercase tracking-wider text-pink-300/80">
              {reason === "intimacy_locked" ? "Intimacy Required" : "Locked"}
            </span>
          </div>

          {/* Message */}
          <p className="text-center text-sm text-muted-foreground leading-relaxed">
            {uiCopy}
          </p>

          {/* Hint */}
          <div className="flex items-center justify-center gap-1.5 text-xs text-pink-400/60">
            <Heart className="h-3 w-3" />
            <span>Grow closer through milestones & gifts</span>
          </div>

          {/* Suggested prompts */}
          {suggestedPrompts.length > 0 && (
            <div className="space-y-1.5 pt-1">
              <p className="text-center text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">
                Try instead
              </p>
              <div className="flex flex-col gap-1.5">
                {suggestedPrompts.map((prompt, i) => (
                  <Button
                    key={i}
                    variant="outline"
                    size="sm"
                    className="h-auto py-2 px-3 text-xs text-left justify-start gap-2 border-pink-500/15 hover:border-pink-500/30 hover:bg-pink-500/5"
                    onClick={() => handlePromptClick(prompt)}
                  >
                    <Sparkles className="h-3 w-3 shrink-0 text-pink-400" />
                    {prompt}
                  </Button>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
