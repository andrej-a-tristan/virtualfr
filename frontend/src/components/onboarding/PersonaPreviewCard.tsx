import { Card, CardContent, CardHeader } from "@/components/ui/card"
import type { TraitsInput } from "@/lib/api/zod"
import { cn } from "@/lib/utils"

interface PersonaPreviewCardProps {
  traits: Partial<TraitsInput>
  className?: string
}

const LABELS: Record<keyof TraitsInput, string> = {
  emotional_style: "Emotional style",
  attachment_style: "Attachment",
  jealousy_level: "Jealousy",
  communication_tone: "Tone",
  intimacy_pace: "Intimacy pace",
  cultural_personality: "Personality",
}

export default function PersonaPreviewCard({ traits, className }: PersonaPreviewCardProps) {
  const entries = Object.entries(traits).filter(([, v]) => v) as [keyof TraitsInput, string][]
  return (
    <Card className={cn("rounded-2xl border-white/10 bg-card/80", className)}>
      <CardHeader className="pb-2">
        <h3 className="text-lg font-semibold">Persona preview</h3>
        <p className="text-sm text-muted-foreground">Your companion will reflect these traits.</p>
      </CardHeader>
      <CardContent className="space-y-2">
        {entries.length ? (
          entries.map(([key, value]) => (
            <div key={key} className="flex justify-between text-sm">
              <span className="text-muted-foreground">{LABELS[key]}</span>
              <span className="font-medium capitalize">{value.replace(/_/g, " ")}</span>
            </div>
          ))
        ) : (
          <p className="text-sm text-muted-foreground">Select traits above to see a preview.</p>
        )}
      </CardContent>
    </Card>
  )
}
