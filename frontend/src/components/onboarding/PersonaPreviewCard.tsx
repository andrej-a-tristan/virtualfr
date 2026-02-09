import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { getVibeSummary, getHowSheTreatsYou } from "@/lib/onboarding/vibe"
import type { TraitSelection } from "@/lib/api/types"
import { cn } from "@/lib/utils"
import AvatarCircle from "@/components/ui/AvatarCircle"

interface PersonaPreviewCardProps {
  displayName: string
  traits: Partial<TraitSelection>
  compact?: boolean
  className?: string
}

export default function PersonaPreviewCard({
  displayName,
  traits,
  compact = false,
  className,
}: PersonaPreviewCardProps) {
  const vibe = getVibeSummary(traits)
  const bullets = getHowSheTreatsYou(traits)
  const hasAny = Object.values(traits).some(Boolean)

  return (
    <Card className={cn("rounded-2xl border-white/10 bg-card/80 shadow-xl", className)}>
      <CardHeader className={cn("space-y-1", compact ? "p-4 pb-2" : "p-6 pb-2")}>
        <div className="flex items-center gap-3">
          <AvatarCircle name={displayName} size="lg" />
          <div>
            <h3 className="text-lg font-semibold text-foreground">
              {displayName || "My Girl"}
            </h3>
            <p className="text-xs text-muted-foreground">
              All choices still care — only the style changes.
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className={cn("space-y-4", compact ? "p-4 pt-0" : "p-6 pt-0")}>
        {hasAny ? (
          <>
            <p className="text-sm leading-relaxed text-muted-foreground">{vibe}</p>
            {bullets.length > 0 && (
              <>
                <Separator className="bg-white/10" />
                <div>
                  <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    How she’ll treat you
                  </p>
                  <ul className="space-y-1.5 text-sm text-foreground">
                    {bullets.map((b, i) => (
                      <li key={i} className="flex gap-2">
                        <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                        <span>{b}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            )}
          </>
        ) : (
          <p className="text-sm text-muted-foreground">
            Select options above to see a live preview. Her personality stays consistent, but she opens up more as you get closer.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
