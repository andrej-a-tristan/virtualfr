import { cn } from "@/lib/utils"
import { Card } from "@/components/ui/card"
import type { TraitsInput } from "@/lib/api/zod"

export interface TraitOption {
  value: string
  label: string
  description: string
}

interface TraitSelectorProps {
  traitKey: keyof TraitsInput
  label: string
  options: TraitOption[]
  value: string
  onChange: (key: keyof TraitsInput, value: string) => void
}

export default function TraitSelector({ traitKey, label, options, value, onChange }: TraitSelectorProps) {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-foreground">{label}</h3>
      <div className="grid gap-2 sm:grid-cols-2">
        {options.map((opt) => (
          <Card
            key={opt.value}
            className={cn(
              "cursor-pointer rounded-xl border-2 p-4 transition-colors",
              value === opt.value ? "border-primary bg-primary/10" : "border-white/10 hover:border-white/20"
            )}
            onClick={() => onChange(traitKey, opt.value)}
          >
            <p className="font-medium">{opt.label}</p>
            <p className="mt-1 text-xs text-muted-foreground">{opt.description}</p>
          </Card>
        ))}
      </div>
    </div>
  )
}
