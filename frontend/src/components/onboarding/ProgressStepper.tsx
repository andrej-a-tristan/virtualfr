import { cn } from "@/lib/utils"
import { Check } from "lucide-react"

export interface StepperStep {
  id: string
  label: string
}

interface ProgressStepperProps {
  steps: StepperStep[]
  completedCount: number
  currentIndex: number
  onStepClick?: (index: number) => void
  className?: string
}

export default function ProgressStepper({
  steps,
  completedCount,
  currentIndex,
  onStepClick,
  className,
}: ProgressStepperProps) {
  return (
    <nav className={cn("flex items-center justify-center gap-1", className)} aria-label="Progress">
      {steps.map((step, i) => (
        <div key={step.id} className="flex items-center">
          <button
            type="button"
            onClick={() => onStepClick?.(i)}
            className={cn(
              "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background",
              i < completedCount && "border-primary bg-primary text-primary-foreground",
              i === currentIndex && i >= completedCount && "border-primary bg-primary/20 text-primary",
              i > currentIndex && "border-muted bg-muted/30 text-muted-foreground"
            )}
            aria-current={i === currentIndex ? "step" : undefined}
            aria-label={`Step ${i + 1}: ${step.label}`}
          >
            {i < completedCount ? <Check className="h-4 w-4" /> : i + 1}
          </button>
          {i < steps.length - 1 && (
            <div
              className={cn("mx-0.5 h-0.5 w-4 sm:w-6", i < completedCount ? "bg-primary" : "bg-muted")}
              aria-hidden
            />
          )}
        </div>
      ))}
    </nav>
  )
}
