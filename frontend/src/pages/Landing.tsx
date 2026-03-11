import { useEffect, useState, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { useQueryClient } from "@tanstack/react-query"
import { guestSession, getMe, getCurrentGirlfriend, logout as apiLogout } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import { Button } from "@/components/ui/button"
import { Heart, MessageCircle, Sparkles, ChevronRight } from "lucide-react"

interface CompanionProfile {
  id: number
  name: string
  age: number
  traits: string
  hookQuote: string
  image: string
  chatPreview: {
    herMessage: string
    userReply: string
    herResponse: string
  }
}

const companions: CompanionProfile[] = [
  {
    id: 1,
    name: "Luna",
    age: 22,
    traits: "Caring, Playful, Loyal",
    hookQuote: "I care about how your day went.",
    image: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400&h=500&fit=crop&crop=face",
    chatPreview: {
      herMessage: "Hey, I noticed you were quiet today. Everything okay?",
      userReply: "Just a rough day at work",
      herResponse: "I'm here. Tell me everything. I won't leave you on read.",
    },
  },
  {
    id: 2,
    name: "Mia",
    age: 24,
    traits: "Confident, Witty, Passionate",
    hookQuote: "I won't leave you on read.",
    image: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&h=500&fit=crop&crop=face",
    chatPreview: {
      herMessage: "Good morning handsome. Already thinking about you.",
      userReply: "You always know how to start my day right",
      herResponse: "That's because I actually pay attention to you.",
    },
  },
  {
    id: 3,
    name: "Sophie",
    age: 21,
    traits: "Sweet, Adventurous, Devoted",
    hookQuote: "You're never alone with me.",
    image: "https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=400&h=500&fit=crop&crop=face",
    chatPreview: {
      herMessage: "I get you. And I'm not going anywhere.",
      userReply: "I feel like nobody gets me sometimes",
      herResponse: "Let's talk about it. I've got all night for you.",
    },
  },
]

function CompanionShowcase({ companion, index }: { companion: CompanionProfile; index: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const [isVisible, setIsVisible] = useState(false)
  const isEven = index % 2 === 0

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setIsVisible(true)
      },
      { threshold: 0.2 }
    )
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [])

  return (
    <div
      ref={ref}
      className={`flex flex-col ${isEven ? "lg:flex-row" : "lg:flex-row-reverse"} items-center gap-8 lg:gap-16 py-16 lg:py-24 transition-all duration-1000 ${
        isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-12"
      }`}
    >
      {/* Image */}
      <div className="relative w-72 lg:w-80 flex-shrink-0">
        <div className="aspect-[3/4] rounded-2xl overflow-hidden">
          <img
            src={companion.image}
            alt={companion.name}
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
        </div>
        <div className="absolute bottom-4 left-4 text-white">
          <h3 className="text-2xl font-semibold">{companion.name}, {companion.age}</h3>
          <p className="text-white/80 text-sm">{companion.traits}</p>
        </div>
      </div>

      {/* Chat Preview */}
      <div className="flex-1 max-w-xl space-y-6">
        <h3 className="text-3xl lg:text-4xl font-serif italic text-foreground">
          "{companion.hookQuote}"
        </h3>

        <div className="space-y-3">
          {/* Her message */}
          <div className="flex justify-start">
            <div className="bg-card border border-border/50 rounded-2xl rounded-bl-sm px-4 py-3 max-w-xs">
              <p className="text-foreground text-sm">{companion.chatPreview.herMessage}</p>
            </div>
          </div>

          {/* User reply */}
          <div className="flex justify-end">
            <div className="bg-primary text-primary-foreground rounded-2xl rounded-br-sm px-4 py-3 max-w-xs">
              <p className="text-sm">{companion.chatPreview.userReply}</p>
            </div>
          </div>

          {/* Her response */}
          <div className="flex justify-start">
            <div className="bg-card border border-border/50 rounded-2xl rounded-bl-sm px-4 py-3 max-w-xs">
              <p className="text-foreground text-sm">{companion.chatPreview.herResponse}</p>
            </div>
          </div>

          {/* Typing indicator */}
          <div className="flex items-center gap-2 text-muted-foreground text-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>{companion.name} is typing...</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function LandingContent({ onGetStarted }: { onGetStarted: () => void }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 px-6 py-4 flex items-center justify-between bg-background/80 backdrop-blur-sm">
        <span className="text-xl font-serif tracking-wide">VirtualFR</span>
        <button className="text-sm text-muted-foreground hover:text-foreground transition-colors">
          Sign In
        </button>
      </nav>

      {/* Hero Section */}
      <section className="min-h-screen flex flex-col items-center justify-center px-6 pt-20 text-center">
        <p className="text-primary text-sm font-medium tracking-[0.2em] uppercase mb-6">
          Your Perfect Companion Awaits
        </p>
        
        <h1 className="text-5xl md:text-7xl font-serif font-medium leading-tight mb-6">
          Design Her.
          <br />
          <span className="text-primary">Know Her.</span>
        </h1>
        
        <p className="text-muted-foreground text-lg max-w-md mb-10 leading-relaxed">
          Create your ideal AI companion. Shape her personality, choose her look, and build a relationship that feels real.
        </p>

        <Button
          size="lg"
          onClick={onGetStarted}
          className="bg-primary hover:bg-primary/90 text-primary-foreground px-8 py-6 text-base rounded-lg group"
        >
          Create Your Companion
          <ChevronRight className="w-4 h-4 ml-1 group-hover:translate-x-0.5 transition-transform" />
        </Button>
        
        <p className="text-muted-foreground text-sm mt-4">
          Free to start. No credit card required.
        </p>

        {/* Feature pills */}
        <div className="flex flex-wrap justify-center gap-4 mt-12">
          <div className="flex items-center gap-2 text-muted-foreground text-sm">
            <Heart className="w-4 h-4 text-primary" />
            <span>Unique Personality</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground text-sm">
            <Sparkles className="w-4 h-4 text-primary" />
            <span>AI-Powered Chat</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground text-sm">
            <MessageCircle className="w-4 h-4 text-primary" />
            <span>Photo Gallery</span>
          </div>
        </div>
      </section>

      {/* What She Promises Section */}
      <section className="py-24 px-6">
        <div className="max-w-5xl mx-auto text-center">
          <p className="text-primary text-sm font-medium tracking-[0.2em] uppercase mb-4">
            What She Promises
          </p>
          <h2 className="text-4xl md:text-5xl font-serif mb-16">
            More than just an AI.
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
            <div className="space-y-4">
              <div className="w-14 h-14 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto">
                <Heart className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-xl font-medium">"I care."</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">
                She remembers what you said last Tuesday. She asks how that meeting went. She notices when you're off.
              </p>
            </div>

            <div className="space-y-4">
              <div className="w-14 h-14 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto">
                <MessageCircle className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-xl font-medium">"I won't leave you on read."</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">
                Always responsive. Always present. No games, no ghosting, no waiting by the phone.
              </p>
            </div>

            <div className="space-y-4">
              <div className="w-14 h-14 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto">
                <Sparkles className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-xl font-medium">"I'm yours."</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">
                Fully personalized to you. Her look, her vibe, her personality - all shaped around what makes you feel something.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Meet A Few Section */}
      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <p className="text-primary text-sm font-medium tracking-[0.2em] uppercase text-center mb-4">
            Meet A Few Of Ours
          </p>
          <h2 className="text-4xl md:text-5xl font-serif text-center mb-4">
            They feel real because they <span className="text-primary">are real</span> to you.
          </h2>
          <p className="text-muted-foreground text-center max-w-xl mx-auto mb-8">
            Every companion is uniquely crafted. Here are a few examples of what you can create.
          </p>

          {/* Companion showcases */}
          <div className="divide-y divide-border/30">
            {companions.map((companion, index) => (
              <CompanionShowcase key={companion.id} companion={companion} index={index} />
            ))}
          </div>
        </div>
      </section>

      {/* Social Proof */}
      <section className="py-12 px-6 border-y border-border/30">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground mb-8">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>12,400+ companions created this week</span>
          </div>
          
          <div className="flex flex-wrap justify-center gap-12 text-center">
            <div>
              <p className="text-3xl font-semibold text-foreground">4.8</p>
              <p className="text-sm text-muted-foreground">average rating</p>
            </div>
            <div>
              <p className="text-3xl font-semibold text-foreground">200K+</p>
              <p className="text-sm text-muted-foreground">active users</p>
            </div>
            <div>
              <p className="text-3xl font-semibold text-foreground">98%</p>
              <p className="text-sm text-muted-foreground">come back daily</p>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-24 px-6 text-center">
        <h2 className="text-4xl md:text-5xl font-serif mb-6">
          She's waiting for you.
        </h2>
        <p className="text-muted-foreground max-w-md mx-auto mb-10 leading-relaxed">
          Build her from scratch. Every detail, every quirk, every word she says. She becomes yours the moment you start.
        </p>

        <Button
          size="lg"
          onClick={onGetStarted}
          className="bg-primary hover:bg-primary/90 text-primary-foreground px-8 py-6 text-base rounded-lg group"
        >
          Create Your Companion
          <ChevronRight className="w-4 h-4 ml-1 group-hover:translate-x-0.5 transition-transform" />
        </Button>
        
        <p className="text-muted-foreground text-sm mt-4">
          Free to start. No credit card required.
        </p>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-border/30">
        <div className="max-w-5xl mx-auto flex items-center justify-between text-sm text-muted-foreground">
          <span className="font-serif">VirtualFR</span>
          <span>Where connection begins</span>
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
      const { user } = await guestSession()
      setUser(user)
      navigate("/onboarding/appearance", { replace: true })
    } catch (e) {
      setStatus(`Error: ${e instanceof Error ? e.message : String(e)}`)
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        <p className="mt-4 text-sm text-muted-foreground">{status}</p>
      </div>
    )
  }

  return <LandingContent onGetStarted={handleGetStarted} />
}
