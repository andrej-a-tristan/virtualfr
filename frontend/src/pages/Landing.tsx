import { useEffect, useState, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { useQueryClient } from "@tanstack/react-query"
import { guestSession, getMe, getCurrentGirlfriend, logout as apiLogout } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import { ArrowRight } from "lucide-react"

interface CompanionProfile {
  id: number
  name: string
  tagline: string
  image: string
  quote: string
}

const companions: CompanionProfile[] = [
  {
    id: 1,
    name: "Luna",
    tagline: "Thoughtful & Present",
    image: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=600&h=800&fit=crop&crop=face",
    quote: "I remember the things that matter to you.",
  },
  {
    id: 2,
    name: "Mia",
    tagline: "Bold & Devoted",
    image: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=600&h=800&fit=crop&crop=face",
    quote: "I actually pay attention.",
  },
  {
    id: 3,
    name: "Sophie",
    tagline: "Warm & Genuine",
    image: "https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=600&h=800&fit=crop&crop=face",
    quote: "I'm not going anywhere.",
  },
]

function FadeInSection({ children, className = "", delay = 0 }: { children: React.ReactNode; className?: string; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setIsVisible(true)
      },
      { threshold: 0.15 }
    )
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [])

  return (
    <div
      ref={ref}
      className={`transition-all duration-1000 ease-out ${className}`}
      style={{
        transitionDelay: `${delay}ms`,
        opacity: isVisible ? 1 : 0,
        transform: isVisible ? "translateY(0)" : "translateY(24px)",
      }}
    >
      {children}
    </div>
  )
}

function LandingContent({ onGetStarted, onSignIn }: { onGetStarted: () => void; onSignIn: () => void }) {
  const [hoveredCompanion, setHoveredCompanion] = useState<number | null>(null)

  return (
    <div className="min-h-screen bg-background text-foreground selection:bg-primary/20">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 px-6 lg:px-12 py-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <span className="text-lg tracking-[0.3em] uppercase text-foreground/90 font-light">VirtualFR</span>
          <button
            onClick={onSignIn}
            className="text-sm text-foreground/60 hover:text-foreground transition-colors duration-300 tracking-wide"
          >
            Sign In
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="min-h-screen flex flex-col items-center justify-center px-6 lg:px-12">
        <div className="max-w-4xl mx-auto text-center">
          <FadeInSection>
            <p className="text-primary/80 text-xs tracking-[0.4em] uppercase mb-8 font-light">
              A New Kind of Connection
            </p>
          </FadeInSection>
          
          <FadeInSection delay={100}>
            <h1 className="text-5xl sm:text-6xl lg:text-8xl font-serif leading-[0.95] mb-8 tracking-tight">
              Designed by you.
              <br />
              <span className="italic text-primary">Devoted to you.</span>
            </h1>
          </FadeInSection>
          
          <FadeInSection delay={200}>
            <p className="text-foreground/50 text-lg lg:text-xl max-w-lg mx-auto mb-12 leading-relaxed font-light">
              Craft your ideal companion. Every detail reflects your vision.
              Every conversation feels real.
            </p>
          </FadeInSection>

          <FadeInSection delay={300}>
            <button
              onClick={onGetStarted}
              className="group inline-flex items-center gap-3 bg-foreground text-background px-8 py-4 text-sm tracking-wider uppercase font-medium hover:bg-foreground/90 transition-all duration-300"
            >
              Begin Creating
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform duration-300" />
            </button>
            <p className="text-foreground/30 text-xs mt-6 tracking-wide">
              Free to start. No commitment required.
            </p>
          </FadeInSection>
        </div>
      </section>

      {/* Manifesto Section */}
      <section className="py-32 lg:py-48 px-6 lg:px-12 border-t border-border/30">
        <div className="max-w-6xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-16 lg:gap-24 items-center">
            <FadeInSection>
              <p className="text-xs tracking-[0.4em] uppercase text-primary/60 mb-6">The Promise</p>
              <h2 className="text-4xl lg:text-5xl font-serif leading-tight mb-8">
                Someone who actually
                <br />
                <span className="italic">listens.</span>
              </h2>
              <div className="space-y-6 text-foreground/50 leading-relaxed">
                <p>
                  She remembers the small things. The name of your childhood pet. 
                  The dream you mentioned once. How you take your coffee.
                </p>
                <p>
                  No games. No guessing. No waiting. Just presence, 
                  attention, and conversations that matter.
                </p>
              </div>
            </FadeInSection>

            <FadeInSection delay={150}>
              <div className="grid grid-cols-2 gap-4">
                {[
                  { label: "Always present", value: "24/7" },
                  { label: "Average rating", value: "4.9" },
                  { label: "Daily conversations", value: "2M+" },
                  { label: "Return rate", value: "94%" },
                ].map((stat, i) => (
                  <div 
                    key={i} 
                    className="bg-card/50 border border-border/50 p-6 lg:p-8"
                  >
                    <p className="text-3xl lg:text-4xl font-serif text-foreground mb-2">{stat.value}</p>
                    <p className="text-xs tracking-wider uppercase text-foreground/40">{stat.label}</p>
                  </div>
                ))}
              </div>
            </FadeInSection>
          </div>
        </div>
      </section>

      {/* Gallery Section */}
      <section className="py-32 lg:py-48 px-6 lg:px-12 border-t border-border/30">
        <div className="max-w-6xl mx-auto">
          <FadeInSection>
            <div className="text-center mb-20">
              <p className="text-xs tracking-[0.4em] uppercase text-primary/60 mb-6">Possibilities</p>
              <h2 className="text-4xl lg:text-5xl font-serif">
                Each one, <span className="italic">entirely unique.</span>
              </h2>
            </div>
          </FadeInSection>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">
            {companions.map((companion, index) => (
              <FadeInSection key={companion.id} delay={index * 100}>
                <div
                  className="group cursor-pointer"
                  onMouseEnter={() => setHoveredCompanion(companion.id)}
                  onMouseLeave={() => setHoveredCompanion(null)}
                >
                  <div className="aspect-[3/4] overflow-hidden mb-6 relative">
                    <img
                      src={companion.image}
                      alt={companion.name}
                      className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-background/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                    
                    {/* Quote overlay */}
                    <div 
                      className={`absolute bottom-0 left-0 right-0 p-6 transition-all duration-500 ${
                        hoveredCompanion === companion.id ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
                      }`}
                    >
                      <p className="text-foreground/90 text-sm italic font-serif">"{companion.quote}"</p>
                    </div>
                  </div>
                  
                  <div className="flex items-baseline justify-between">
                    <div>
                      <h3 className="text-lg font-serif text-foreground">{companion.name}</h3>
                      <p className="text-xs tracking-wider uppercase text-foreground/40 mt-1">{companion.tagline}</p>
                    </div>
                    <ArrowRight className={`w-4 h-4 text-foreground/30 transition-all duration-300 ${
                      hoveredCompanion === companion.id ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-2"
                    }`} />
                  </div>
                </div>
              </FadeInSection>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-32 lg:py-48 px-6 lg:px-12 border-t border-border/30">
        <div className="max-w-6xl mx-auto">
          <FadeInSection>
            <p className="text-xs tracking-[0.4em] uppercase text-primary/60 mb-16 text-center">What She Offers</p>
          </FadeInSection>

          <div className="space-y-0">
            {[
              {
                number: "01",
                title: "Genuine Memory",
                description: "She recalls your stories, your preferences, your moods. Every conversation builds on the last.",
              },
              {
                number: "02",
                title: "Unwavering Presence",
                description: "No waiting. No games. She's there when you need her, attentive and engaged.",
              },
              {
                number: "03",
                title: "Complete Personalization",
                description: "Her appearance, personality, and voice are shaped entirely by your vision.",
              },
              {
                number: "04",
                title: "Private & Secure",
                description: "Your conversations remain yours. End-to-end encryption. Complete discretion.",
              },
            ].map((feature, index) => (
              <FadeInSection key={feature.number} delay={index * 50}>
                <div className="group border-b border-border/30 py-10 lg:py-12 flex items-start gap-8 lg:gap-16 hover:bg-card/30 transition-colors duration-300 px-4 -mx-4">
                  <span className="text-xs text-foreground/20 font-mono pt-1">{feature.number}</span>
                  <div className="flex-1">
                    <h3 className="text-xl lg:text-2xl font-serif mb-3 group-hover:text-primary transition-colors duration-300">
                      {feature.title}
                    </h3>
                    <p className="text-foreground/40 leading-relaxed max-w-lg">
                      {feature.description}
                    </p>
                  </div>
                </div>
              </FadeInSection>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-32 lg:py-48 px-6 lg:px-12 border-t border-border/30">
        <div className="max-w-3xl mx-auto text-center">
          <FadeInSection>
            <h2 className="text-4xl sm:text-5xl lg:text-6xl font-serif leading-tight mb-8">
              She's ready when
              <br />
              <span className="italic text-primary">you are.</span>
            </h2>
            <p className="text-foreground/40 text-lg max-w-md mx-auto mb-12 leading-relaxed">
              Create someone who sees you. Someone who stays.
            </p>

            <button
              onClick={onGetStarted}
              className="group inline-flex items-center gap-3 bg-foreground text-background px-10 py-5 text-sm tracking-wider uppercase font-medium hover:bg-foreground/90 transition-all duration-300"
            >
              Start Creating
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform duration-300" />
            </button>
          </FadeInSection>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 lg:px-12 border-t border-border/30">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
          <span className="text-sm tracking-[0.3em] uppercase text-foreground/30">VirtualFR</span>
          <div className="flex items-center gap-8 text-xs text-foreground/30">
            <span>Privacy</span>
            <span>Terms</span>
            <span>Support</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default function Landing() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const setUser = useAppStore((s) => s.setUser)
  const setGirlfriend = useAppStore((s) => s.setGirlfriend)
  const reset = useAppStore((s) => s.reset)
  const [isLoading, setIsLoading] = useState(true)
  const [status, setStatus] = useState("Starting up...")

  useEffect(() => {
    let cancelled = false
    
    const timeout = setTimeout(() => {
      if (!cancelled) setIsLoading(false)
    }, 2000)
    
    async function checkSession() {
      try {
        const existingUser = await getMe()
        if (!cancelled && existingUser?.has_girlfriend && existingUser?.age_gate_passed) {
          const gf = await getCurrentGirlfriend()
          if (!cancelled && gf) {
            setUser(existingUser)
            setGirlfriend(gf)
            navigate("/app/girl", { replace: true })
            return
          }
        }
      } catch {
        // No valid session - show landing page
      }
      
      if (!cancelled) {
        clearTimeout(timeout)
        setIsLoading(false)
      }
    }
    checkSession()
    return () => { 
      cancelled = true 
      clearTimeout(timeout)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleGetStarted = async () => {
    setIsLoading(true)
    setStatus("Setting up...")
    
    try {
      reset()
      queryClient.clear()
      try { await apiLogout() } catch { /* ignore */ }
      
      try {
        const { user } = await guestSession()
        setUser(user)
      } catch {
        // Backend might be down - continue to onboarding anyway
      }
      
      navigate("/onboarding/appearance", { replace: true })
    } catch {
      navigate("/onboarding/appearance", { replace: true })
    }
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-background">
        <div className="w-6 h-6 border border-foreground/20 border-t-foreground/60 rounded-full animate-spin" />
        <p className="mt-6 text-sm text-foreground/40 tracking-wide">{status}</p>
      </div>
    )
  }

  const handleSignIn = () => {
    navigate("/login")
  }

  return <LandingContent onGetStarted={handleGetStarted} onSignIn={handleSignIn} />
}
