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
        "cursor-pointer rounded-xl border p-4 text-left transition-all duration-200",
        selected
          ? "border-primary bg-primary/10 ring-1 ring-primary/30"
          : "border-border/50 bg-card/40 hover:border-primary/50",
        className
      )}
      onClick={onClick}
      onKeyDown={(e) => e.key === "Enter" && onClick()}
    >
      <CardContent className="p-0">
        <p className={cn(
          "font-medium",
          selected ? "text-primary" : "text-foreground"
        )}>
          {option.label}
        </p>
        <p className="mt-1.5 text-sm text-muted-foreground leading-relaxed">{option.description}</p>
      </CardContent>
    </Card>
  )
}
