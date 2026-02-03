import type { LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import TraitCard, { type TraitCardOption } from "./TraitCard"
import type { TraitSelection } from "@/lib/api/types"

export type TraitSelectorKey = keyof TraitSelection

export interface TraitSelectorConfig {
  key: TraitSelectorKey
  question: string
  options: TraitCardOption[]
  icon: LucideIcon
}

interface TraitSelectorProps {
  config: TraitSelectorConfig
  value: string
  onChange: (key: TraitSelectorKey, value: string) => void
  className?: string
}

export default function TraitSelector({ config, value, onChange, className }: TraitSelectorProps) {
  const Icon = config.icon
  return (
    <section className={cn("space-y-4", className)} aria-labelledby={`trait-${config.key}`}>
      <div className="flex items-center gap-2">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/15 text-primary">
          <Icon className="h-4 w-4" />
        </div>
        <h2 id={`trait-${config.key}`} className="text-base font-semibold text-foreground">
          {config.question}
        </h2>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {config.options.map((opt) => (
          <TraitCard
            key={opt.value}
            option={opt}
            selected={value === opt.value}
            onClick={() => onChange(config.key, opt.value)}
          />
        ))}
      </div>
    </section>
  )
}
