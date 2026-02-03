import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

export interface TraitCardOption {
  value: string
  label: string
  description: string
}

interface TraitCardProps {
  option: TraitCardOption
  selected: boolean
  onClick: () => void
  className?: string
}

export default function TraitCard({ option, selected, onClick, className }: TraitCardProps) {
  return (
    <Card
      role="button"
      tabIndex={0}
      className={cn(
        "cursor-pointer rounded-2xl border-2 p-4 text-left transition-all hover:border-white/25",
        selected
          ? "border-primary bg-primary/15 shadow-[0_0_20px_-5px_rgba(139,92,246,0.3)]"
          : "border-white/10 bg-card/60",
        className
      )}
      onClick={onClick}
      onKeyDown={(e) => e.key === "Enter" && onClick()}
    >
      <CardContent className="p-0">
        <p className="font-medium text-foreground">{option.label}</p>
        <p className="mt-1.5 text-sm text-muted-foreground">{option.description}</p>
      </CardContent>
    </Card>
  )
}
