import { Link } from "react-router-dom"
import { LogIn } from "lucide-react"

/**
 * Persistent "Sign in" button shown in the top-right corner
 * throughout the entire onboarding flow.
 */
export default function OnboardingSignIn() {
  return (
    <Link
      to="/login"
      className="fixed right-4 top-4 z-50 flex items-center gap-2 rounded-full border border-white/15 bg-white/5 backdrop-blur-sm px-4 py-2 text-sm font-medium text-white/80 transition-all hover:text-white hover:bg-white/10 hover:border-white/25 shadow-lg"
    >
      <LogIn className="h-4 w-4" />
      Sign in
    </Link>
  )
}
