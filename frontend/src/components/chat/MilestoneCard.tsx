/**
 * MilestoneCard — renders a progression milestone message with structured content blocks.
 *
 * Displays: celebration headline, meaning narrative, interactive choices, and reward info.
 * Supports: mark as read, choice clicks, dismiss.
 */
import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { markProgressionMessagesRead, recordProgressionAction, dismissProgressionMessage } from "@/lib/api/endpoints"
import type { MilestoneMessage } from "@/lib/api/types"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  BookOpen,
  Sparkles,
  Heart,
  Eye,
  Bookmark,
  PartyPopper,
  Flame,
  Rewind,
  ArrowRight,
  Gift,
  Sun,
  Lock,
  Camera,
  MessageCircle,
  Star,
  Search,
  Smile,
  Mail,
  PenLine,
  X,
} from "lucide-react"

const ICON_MAP: Record<string, React.ElementType> = {
  book: BookOpen,
  "book-open": BookOpen,
  sparkles: Sparkles,
  heart: Heart,
  eye: Eye,
  bookmark: Bookmark,
  party: PartyPopper,
  flame: Flame,
  rewind: Rewind,
  "arrow-right": ArrowRight,
  gift: Gift,
  sun: Sun,
  lock: Lock,
  camera: Camera,
  "message-circle": MessageCircle,
  star: Star,
  search: Search,
  smile: Smile,
  mail: Mail,
  pen: PenLine,
  cool: Smile,
}

interface Props {
  message: MilestoneMessage
  onDismiss?: () => void
}

type MilestoneContent = {
  celebration?: string
  meaning?: string
  choices: {
    action: string
    label: string
    icon?: string
  }[]
  reward?: {
    type?: "story_beat" | "memory_card" | "bonus_points" | "unlock" | string
  }
}

export default function MilestoneCard({ message, onDismiss }: Props) {
  const queryClient = useQueryClient()
  const [selectedAction, setSelectedAction] = useState<string | null>(null)
  const content = (message.content as MilestoneContent) ?? { choices: [] }

  const markReadMutation = useMutation({
    mutationFn: () => markProgressionMessagesRead([message.id]),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["progressionMessages"] }),
  })

  const actionMutation = useMutation({
    mutationFn: (action: string) => recordProgressionAction(message.id, action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["progressionMessages"] })
      // Also mark as read when a choice is selected
      if (!message.read_at) {
        markReadMutation.mutate()
      }
    },
  })

  const dismissMutation = useMutation({
    mutationFn: () => dismissProgressionMessage(message.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["progressionMessages"] })
      onDismiss?.()
    },
  })

  const handleChoice = (action: string) => {
    setSelectedAction(action)
    actionMutation.mutate(action)
  }

  // Event type badge color
  const badgeColor = {
    "relationship.level_achieved": "bg-pink-500/20 text-pink-300 border-pink-500/30",
    "intimacy.level_unlocked": "bg-purple-500/20 text-purple-300 border-purple-500/30",
    "streak.milestone": "bg-orange-500/20 text-orange-300 border-orange-500/30",
    "engagement.milestone": "bg-blue-500/20 text-blue-300 border-blue-500/30",
  }[message.event_type] ?? "bg-primary/20 text-primary border-primary/30"

  const badgeLabel = {
    "relationship.level_achieved": "Relationship",
    "intimacy.level_unlocked": "Trust",
    "streak.milestone": "Streak",
    "engagement.milestone": "Engagement",
  }[message.event_type] ?? "Milestone"

  return (
    <Card className="relative overflow-hidden border-white/10 bg-gradient-to-br from-background via-background to-primary/5 shadow-lg">
      {/* Dismiss button */}
      <button
        onClick={() => dismissMutation.mutate()}
        className="absolute right-2 top-2 rounded-full p-1 text-muted-foreground/50 hover:bg-white/5 hover:text-muted-foreground transition-colors"
        aria-label="Dismiss"
      >
        <X className="h-4 w-4" />
      </button>

      <CardContent className="space-y-4 pt-5 pb-4">
        {/* Badge */}
        <span className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-medium ${badgeColor}`}>
          {badgeLabel}
        </span>

        {/* Celebration headline */}
        {content.celebration && (
          <h3
            className="text-lg font-bold leading-tight"
            dangerouslySetInnerHTML={{ __html: content.celebration.replace(/\*\*(.*?)\*\*/g, '<strong class="text-primary">$1</strong>') }}
          />
        )}

        {/* Meaning narrative */}
        {content.meaning && (
          <p className="text-sm text-muted-foreground leading-relaxed">
            {content.meaning}
          </p>
        )}

        {/* Choices */}
        {content.choices.length > 0 && (
          <div className="space-y-2 pt-1">
            {content.choices.map((choice, i) => {
              const IconComponent = ICON_MAP[choice.icon ?? ""] ?? Sparkles
              const isSelected = selectedAction === choice.action
              return (
                <Button
                  key={i}
                  variant={isSelected ? "default" : "outline"}
                  size="sm"
                  className={`w-full justify-start gap-2 text-left transition-all ${
                    isSelected ? "ring-2 ring-primary/50" : "hover:bg-white/5"
                  }`}
                  onClick={() => handleChoice(choice.action)}
                  disabled={actionMutation.isPending || !!selectedAction}
                >
                  <IconComponent className="h-4 w-4 shrink-0" />
                  <span className="truncate">{choice.label}</span>
                </Button>
              )
            })}
          </div>
        )}

        {/* Reward indicator */}
        {content.reward?.type && (
          <div className="flex items-center gap-1.5 pt-1 text-xs text-muted-foreground/60">
            <Gift className="h-3 w-3" />
            <span>
              {content.reward.type === "story_beat" && "Story scene unlocked"}
              {content.reward.type === "memory_card" && "Memory card earned"}
              {content.reward.type === "bonus_points" && "Bonus points awarded"}
              {content.reward.type === "unlock" && "New feature unlocked"}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
