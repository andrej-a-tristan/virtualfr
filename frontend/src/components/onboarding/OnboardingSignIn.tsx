import { Link } from "react-router-dom"
import { LogIn } from "lucide-react"
import { useAppStore } from "@/lib/store/useAppStore"

/**
 * Persistent "Sign in" button shown in the top-right corner
 * throughout the first-time onboarding flow only.
 * Hidden when creating additional girls (user is already signed in).
 */
export default function OnboardingSignIn() {
  const onboardingMode = useAppStore((s) => s.onboardingMode)

  // Don't show "Sign in" when the user is already logged in and adding more girls
  if (onboardingMode === "additional") return null

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
