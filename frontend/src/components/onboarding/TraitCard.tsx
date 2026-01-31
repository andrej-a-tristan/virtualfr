import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface TraitCardProps {
  title: string
  value: string
  className?: string
}

export default function TraitCard({ title, value, className }: TraitCardProps) {
  return (
    <Card className={cn("rounded-xl border-white/10", className)}>
      <CardContent className="p-3">
        <p className="text-xs text-muted-foreground">{title}</p>
        <p className="font-medium">{value}</p>
      </CardContent>
    </Card>
  )
}
