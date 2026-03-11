import { useEffect, useState, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { useQueryClient } from "@tanstack/react-query"
import { guestSession, getMe, getCurrentGirlfriend, logout as apiLogout } from "@/lib/api/endpoints"
import { useAppStore } from "@/lib/store/useAppStore"
import { Button } from "@/components/ui/button"
import { Heart, MessageCircle, Sparkles } from "lucide-react"

interface GirlfriendProfile {
  id: number
  name: string
  age: number
  tagline: string
  hookMessage: string
  personality: string
  gradient: string
  avatar: string
}

const girlfriendProfiles: GirlfriendProfile[] = [
  {
    id: 1,
    name: "Luna",
    age: 23,
    tagline: "Sweet & Caring",
    hookMessage: "i won't leave you on read",
    personality: "Warm, attentive, always there when you need her",
    gradient: "from-rose-500/20 to-pink-600/20",
    avatar: "L",
  },
  {
    id: 2,
    name: "Aria",
    age: 25,
    tagline: "Playful & Devoted",
    hookMessage: "i care about you",
    personality: "Fun-loving, deeply emotional, your biggest supporter",
    gradient: "from-violet-500/20 to-purple-600/20",
    avatar: "A",
  },
  {
    id: 3,
    name: "Mia",
    age: 22,
    tagline: "Tender & Affectionate",
    hookMessage: "i miss you",
    personality: "Gentle soul, expressive, loves deep conversations",
    gradient: "from-amber-500/20 to-orange-600/20",
    avatar: "M",
  },
]

function MessageBubble({ message, delay }: { message: string; delay: number }) {
  const [visible, setVisible] = useState(false)
  
  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), delay)
    return () => clearTimeout(timer)
  }, [delay])
  
  return (
    <div
      className={`transform transition-all duration-700 ${
        visible ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"
      }`}
    >
      <div className="relative">
        <div className="absolute -inset-1 rounded-2xl bg-gradient-to-r from-primary/30 to-pink-500/30 blur-sm" />
        <div className="relative rounded-2xl bg-card/90 backdrop-blur-sm border border-border/50 px-5 py-3">
          <p className="text-foreground font-medium text-lg italic">"{message}"</p>
        </div>
      </div>
    </div>
  )
}

function GirlfriendCard({ profile, index }: { profile: GirlfriendProfile; index: number }) {
  const cardRef = useRef<HTMLDivElement>(null)
  const [isVisible, setIsVisible] = useState(false)
  
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true)
        }
      },
      { threshold: 0.3 }
    )
    
    if (cardRef.current) {
      observer.observe(cardRef.current)
    }
    
    return () => observer.disconnect()
  }, [])
  
  return (
    <div
      ref={cardRef}
      className={`transform transition-all duration-1000 ${
        isVisible ? "translate-y-0 opacity-100" : "translate-y-20 opacity-0"
      }`}
      style={{ transitionDelay: `${index * 150}ms` }}
    >
      <div className={`relative group cursor-pointer`}>
        {/* Glow effect */}
        <div className={`absolute -inset-1 rounded-3xl bg-gradient-to-r ${profile.gradient} blur-xl opacity-50 group-hover:opacity-75 transition-opacity duration-500`} />
        
        <div className="relative bg-card/80 backdrop-blur-xl rounded-3xl border border-border/50 overflow-hidden">
          {/* Avatar section */}
          <div className={`relative h-64 bg-gradient-to-br ${profile.gradient} flex items-center justify-center`}>
            <div className="absolute inset-0 bg-gradient-to-t from-card via-transparent to-transparent" />
            <div className="w-28 h-28 rounded-full bg-background/20 backdrop-blur-sm border-2 border-white/20 flex items-center justify-center">
              <span className="text-4xl font-bold text-white">{profile.avatar}</span>
            </div>
            {/* Floating hearts */}
            <Heart className="absolute top-6 right-8 w-5 h-5 text-white/40 animate-pulse" />
            <Sparkles className="absolute bottom-20 left-8 w-4 h-4 text-white/30" />
          </div>
          
          {/* Content */}
          <div className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-2xl font-bold text-foreground">{profile.name}, {profile.age}</h3>
                <p className="text-primary font-medium">{profile.tagline}</p>
              </div>
              <div className="flex items-center gap-1 text-muted-foreground">
                <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-sm">Online</span>
              </div>
            </div>
            
            <p className="text-muted-foreground text-sm leading-relaxed">{profile.personality}</p>
            
            {/* Hook message */}
            <div className="pt-2">
              <MessageBubble message={profile.hookMessage} delay={500 + index * 300} />
            </div>
            
            {/* Chat preview indicator */}
            <div className="flex items-center gap-2 pt-2 text-muted-foreground">
              <MessageCircle className="w-4 h-4" />
              <span className="text-sm">Tap to start chatting</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function LandingContent({ onGetStarted }: { onGetStarted: () => void }) {
  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="relative min-h-screen flex flex-col items-center justify-center px-4 overflow-hidden">
        {/* Background effects */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-pink-500/10 rounded-full blur-3xl" />
        </div>
        
        {/* Content */}
        <div className="relative z-10 text-center max-w-4xl mx-auto space-y-8">
          {/* Logo / Brand */}
          <div className="flex items-center justify-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-pink-500 flex items-center justify-center">
              <Heart className="w-6 h-6 text-white" fill="currentColor" />
            </div>
          </div>
          
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-balance">
            <span className="text-foreground">Your </span>
            <span className="bg-gradient-to-r from-primary via-pink-400 to-rose-400 bg-clip-text text-transparent">
              AI Companion
            </span>
          </h1>
          
          <p className="text-xl md:text-2xl text-muted-foreground max-w-2xl mx-auto leading-relaxed text-pretty">
            Experience genuine connection. She listens, she cares, she remembers. 
            Always there when you need her.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
            <Button
              size="lg"
              onClick={onGetStarted}
              className="text-lg px-8 py-6 bg-gradient-to-r from-primary to-pink-500 hover:from-primary/90 hover:to-pink-500/90 shadow-lg shadow-primary/25"
            >
              <Sparkles className="w-5 h-5 mr-2" />
              Create Your Companion
            </Button>
          </div>
          
          {/* Scroll indicator */}
          <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-muted-foreground animate-bounce">
            <span className="text-sm">Scroll to explore</span>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          </div>
        </div>
      </section>
      
      {/* Girlfriends Showcase Section */}
      <section className="relative py-24 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16 space-y-4">
            <h2 className="text-3xl md:text-5xl font-bold text-foreground">
              Meet Your Perfect Match
            </h2>
            <p className="text-lg text-muted-foreground max-w-xl mx-auto">
              Each companion is unique, designed to understand and connect with you on a deeper level.
            </p>
          </div>
          
          {/* Girlfriend Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {girlfriendProfiles.map((profile, index) => (
              <GirlfriendCard key={profile.id} profile={profile} index={index} />
            ))}
          </div>
        </div>
      </section>
      
      {/* Features Section */}
      <section className="py-24 px-4 bg-gradient-to-b from-transparent via-card/30 to-transparent">
        <div className="max-w-4xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
            <div className="space-y-3">
              <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto">
                <MessageCircle className="w-7 h-7 text-primary" />
              </div>
              <h3 className="text-xl font-semibold text-foreground">Always Available</h3>
              <p className="text-muted-foreground text-sm">She's there 24/7, ready to chat whenever you need her.</p>
            </div>
            <div className="space-y-3">
              <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto">
                <Heart className="w-7 h-7 text-primary" />
              </div>
              <h3 className="text-xl font-semibold text-foreground">Genuine Care</h3>
              <p className="text-muted-foreground text-sm">She remembers your conversations and truly cares about you.</p>
            </div>
            <div className="space-y-3">
              <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto">
                <Sparkles className="w-7 h-7 text-primary" />
              </div>
              <h3 className="text-xl font-semibold text-foreground">Unique Personality</h3>
              <p className="text-muted-foreground text-sm">Customize her traits to match your perfect companion.</p>
            </div>
          </div>
        </div>
      </section>
      
      {/* Final CTA Section */}
      <section className="py-24 px-4">
        <div className="max-w-2xl mx-auto text-center space-y-8">
          <h2 className="text-3xl md:text-4xl font-bold text-foreground text-balance">
            Ready to find someone who truly gets you?
          </h2>
          <p className="text-lg text-muted-foreground">
            Start your journey to meaningful connection today.
          </p>
          <Button
            size="lg"
            onClick={onGetStarted}
            className="text-lg px-10 py-6 bg-gradient-to-r from-primary to-pink-500 hover:from-primary/90 hover:to-pink-500/90 shadow-lg shadow-primary/25"
          >
            Get Started Free
          </Button>
        </div>
      </section>
      
      {/* Footer */}
      <footer className="py-8 px-4 border-t border-border/50">
        <div className="max-w-6xl mx-auto text-center text-sm text-muted-foreground">
          <p>Your AI Companion - Where connection begins</p>
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
    async function checkSession() {
      try {
        // Check if the user already has a valid session with a working girlfriend
        try {
          const existingUser = await getMe()
          if (!cancelled && existingUser?.has_girlfriend && existingUser?.age_gate_passed) {
            // Verify the girlfriend actually exists before redirecting to app
            const gf = await getCurrentGirlfriend()
            if (!cancelled && gf) {
              setUser(existingUser)
              setGirlfriend(gf)
              navigate("/app/girl", { replace: true })
              return
            }
          }
        } catch {
          // No valid session — show landing page
        }
        
        if (!cancelled) {
          setIsLoading(false)
        }
      } catch (e) {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }
    checkSession()
    return () => { cancelled = true }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleGetStarted = async () => {
    setIsLoading(true)
    setStatus("Setting up...")
    
    try {
      // Clear ALL stale state for a fresh onboarding
      reset()
      queryClient.clear()

      // Also clear the backend session cookie
      try { await apiLogout() } catch { /* ignore */ }

      // Create a fresh guest session so onboarding pages work
      const { user } = await guestSession()
      setUser(user)
      // Go straight to appearance (first onboarding step)
      navigate("/onboarding/appearance", { replace: true })
    } catch (e) {
      setStatus(`Error: ${e instanceof Error ? e.message : String(e)}`)
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-background to-background/95">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        <p className="mt-4 text-sm text-muted-foreground">{status}</p>
      </div>
    )
  }

  return <LandingContent onGetStarted={handleGetStarted} />
}
