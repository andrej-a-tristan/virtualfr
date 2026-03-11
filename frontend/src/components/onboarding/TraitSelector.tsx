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
    <section className={cn("space-y-5", className)} aria-labelledby={`trait-${config.key}`}>
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 border border-primary/20 text-primary">
          <Icon className="h-5 w-5" />
        </div>
        <h2 id={`trait-${config.key}`} className="text-base font-medium text-foreground leading-relaxed pt-2">
          {config.question}
        </h2>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 pl-0 lg:pl-13">
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
