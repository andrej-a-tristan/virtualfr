import { cn } from "@/lib/utils"
import { Check } from "lucide-react"

interface Step {
  id: string
  label: string
}

interface ProgressStepperProps {
  steps: Step[]
  currentStep: number
  className?: string
}

export default function ProgressStepper({ steps, currentStep, className }: ProgressStepperProps) {
  return (
    <nav className={cn("flex items-center justify-center gap-2", className)} aria-label="Progress">
      {steps.map((step, i) => (
        <div key={step.id} className="flex items-center">
          <div
            className={cn(
              "flex h-8 w-8 items-center justify-center rounded-full border-2 text-sm font-medium transition-colors",
              i < currentStep && "border-primary bg-primary text-primary-foreground",
              i === currentStep && "border-primary bg-primary/20 text-primary",
              i > currentStep && "border-muted text-muted-foreground"
            )}
          >
            {i < currentStep ? <Check className="h-4 w-4" /> : i + 1}
          </div>
          {i < steps.length - 1 && (
            <div className={cn("mx-1 h-0.5 w-6", i < currentStep ? "bg-primary" : "bg-muted")} />
          )}
        </div>
      ))}
    </nav>
  )
}
