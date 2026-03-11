import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAppStore } from "@/lib/store/useAppStore"
import { ChevronRight, ChevronLeft, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"
import {
  JOB_VIBES,
  HOBBIES,
  CITY_VIBES,
  isValidName,
  getRandomName,
} from "@/lib/constants/identity"

export default function OnboardingIdentity() {
  const navigate = useNavigate()
  const onboardingIdentity = useAppStore((s) => s.onboardingIdentity)

  const [name, setName] = useState(onboardingIdentity?.girlfriend_name ?? "")
  const [jobVibe, setJobVibe] = useState(onboardingIdentity?.job_vibe ?? "")
  const [hobbies, setHobbies] = useState<string[]>(onboardingIdentity?.hobbies ?? [])
  const [originVibe, setOriginVibe] = useState(onboardingIdentity?.origin_vibe ?? "")
  const [step, setStep] = useState(0) // 0: name, 1: vibe, 2: hobbies, 3: origin

  const nameValid = isValidName(name)
  const canContinue = nameValid && jobVibe && hobbies.length === 3 && originVibe

  const handleSurpriseMe = () => {
    setName(getRandomName())
  }

  const handleToggleHobby = (hobby: string) => {
    setHobbies((prev) => {
      if (prev.includes(hobby)) return prev.filter((h) => h !== hobby)
      if (prev.length >= 3) return prev
      return [...prev, hobby]
    })
  }

  const handleBack = () => {
    if (step > 0) {
      setStep(step - 1)
    } else {
      navigate("/onboarding/preferences", { replace: true })
    }
  }

  const handleNext = () => {
    if (step < 3) {
      setStep(step + 1)
    }
  }

  const handleCreate = () => {
    if (!canContinue) return
    useAppStore.setState({
      onboardingIdentity: {
        girlfriend_name: name.trim(),
        job_vibe: jobVibe,
        hobbies: hobbies,
        origin_vibe: originVibe,
      },
    })
    navigate("/onboarding/generating", { replace: true })
  }

  const stepValid = 
    step === 0 ? nameValid :
    step === 1 ? !!jobVibe :
    step === 2 ? hobbies.length === 3 :
    !!originVibe

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Progress bar */}
      <div className="fixed top-0 inset-x-0 z-50">
        <div className="h-1 bg-muted">
          <div 
            className="h-full bg-primary transition-all duration-500"
            style={{ width: `${75 + (step / 3) * 25}%` }}
          />
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-16">
        <div className="w-full max-w-lg">
          {/* Back button */}
          <button 
            onClick={handleBack}
            className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors mb-8"
          >
            <ChevronLeft className="w-4 h-4" />
            <span className="text-sm">Back</span>
          </button>

          {/* Step 0: Name */}
          {step === 0 && (
            <div className="animate-in fade-in slide-in-from-right-4 duration-300">
              <div className="text-center mb-10">
                <h1 className="text-3xl md:text-4xl font-serif text-foreground mb-3">
                  What's her name?
                </h1>
                <p className="text-muted-foreground">
                  Give her an identity that feels right
                </p>
              </div>

              <div className="space-y-4 mb-10">
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Enter a name..."
                  maxLength={20}
                  className="w-full px-5 py-4 rounded-xl border border-border/50 bg-card/50 text-foreground text-center text-xl font-medium placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary transition-colors"
                />
                
                <button
                  onClick={handleSurpriseMe}
                  className="w-full flex items-center justify-center gap-2 py-3 text-primary hover:text-primary/80 transition-colors"
                >
                  <Sparkles className="w-4 h-4" />
                  <span className="text-sm font-medium">Surprise me</span>
                </button>
              </div>
            </div>
          )}

          {/* Step 1: Job Vibe */}
          {step === 1 && (
            <div className="animate-in fade-in slide-in-from-right-4 duration-300">
              <div className="text-center mb-10">
                <h1 className="text-3xl md:text-4xl font-serif text-foreground mb-3">
                  What's her vibe?
                </h1>
                <p className="text-muted-foreground">
                  Her lifestyle and energy
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 mb-10">
                {JOB_VIBES.map((job) => {
                  const isSelected = jobVibe === job.id
                  return (
                    <button
                      key={job.id}
                      onClick={() => setJobVibe(job.id)}
                      className={cn(
                        "p-4 rounded-xl border text-left transition-all duration-200",
                        isSelected
                          ? "border-primary bg-primary/5"
                          : "border-border/50 hover:border-primary/50"
                      )}
                    >
                      <div className={cn(
                        "font-medium text-sm",
                        isSelected ? "text-primary" : "text-foreground"
                      )}>
                        {job.title}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {job.subtitle}
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {/* Step 2: Hobbies */}
          {step === 2 && (
            <div className="animate-in fade-in slide-in-from-right-4 duration-300">
              <div className="text-center mb-10">
                <h1 className="text-3xl md:text-4xl font-serif text-foreground mb-3">
                  Her interests?
                </h1>
                <p className="text-muted-foreground">
                  Pick 3 hobbies she loves
                </p>
              </div>

              <div className="flex flex-wrap gap-2 justify-center mb-6">
                {HOBBIES.map((hobby) => {
                  const selected = hobbies.includes(hobby)
                  const disabled = !selected && hobbies.length >= 3
                  return (
                    <button
                      key={hobby}
                      onClick={() => handleToggleHobby(hobby)}
                      disabled={disabled}
                      className={cn(
                        "px-4 py-2 rounded-full border text-sm transition-all duration-200",
                        selected
                          ? "border-primary bg-primary/10 text-primary"
                          : disabled
                            ? "border-border/30 text-muted-foreground/40 cursor-not-allowed"
                            : "border-border/50 hover:border-primary/50"
                      )}
                    >
                      {hobby}
                    </button>
                  )
                })}
              </div>

              <p className="text-center text-sm text-muted-foreground mb-10">
                {hobbies.length}/3 selected
              </p>
            </div>
          )}

          {/* Step 3: Origin */}
          {step === 3 && (
            <div className="animate-in fade-in slide-in-from-right-4 duration-300">
              <div className="text-center mb-10">
                <h1 className="text-3xl md:text-4xl font-serif text-foreground mb-3">
                  Where is she from?
                </h1>
                <p className="text-muted-foreground">
                  Her cultural background
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 mb-10">
                {CITY_VIBES.map((city) => {
                  const isSelected = originVibe === city.id
                  return (
                    <button
                      key={city.id}
                      onClick={() => setOriginVibe(city.id)}
                      className={cn(
                        "p-4 rounded-xl border text-center transition-all duration-200",
                        isSelected
                          ? "border-primary bg-primary/5"
                          : "border-border/50 hover:border-primary/50"
                      )}
                    >
                      <span className={cn(
                        "font-medium text-sm",
                        isSelected ? "text-primary" : "text-foreground"
                      )}>
                        {city.title}
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {/* Progress dots */}
          <div className="flex items-center justify-center gap-2 mb-8">
            {[0, 1, 2, 3].map((i) => (
              <button
                key={i}
                onClick={() => setStep(i)}
                className={cn(
                  "w-2 h-2 rounded-full transition-all duration-300",
                  i === step 
                    ? "bg-primary w-6" 
                    : i < step 
                      ? "bg-primary/50" 
                      : "bg-muted"
                )}
              />
            ))}
          </div>

          {/* Continue button */}
          <div className="flex justify-center">
            {step < 3 ? (
              <button
                onClick={handleNext}
                disabled={!stepValid}
                className={cn(
                  "group flex items-center gap-2 px-8 py-4 rounded-full font-medium transition-all duration-300",
                  stepValid
                    ? "bg-primary text-white hover:bg-primary/90 hover:gap-3"
                    : "bg-muted text-muted-foreground cursor-not-allowed"
                )}
              >
                Next
                <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            ) : (
              <button
                onClick={handleCreate}
                disabled={!canContinue}
                className={cn(
                  "group flex items-center gap-2 px-8 py-4 rounded-full font-medium transition-all duration-300",
                  canContinue
                    ? "bg-primary text-white hover:bg-primary/90 hover:gap-3"
                    : "bg-muted text-muted-foreground cursor-not-allowed"
                )}
              >
                Create {name || "Her"}
                <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
