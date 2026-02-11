/**
 * Route guards: RequireAuth, RequireAgeGate, RequireGirlfriend.
 * Wrap protected routes and redirect when conditions fail.
 */
import { Navigate, useLocation } from "react-router-dom"
import { useAuth } from "@/lib/hooks/useAuth"

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, user } = useAuth()
  const location = useLocation()
  if (isLoading) return <div className="flex min-h-screen items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" /></div>
  // Accept either server-confirmed auth OR Zustand user (guest sessions set user before navigating)
  if (!isAuthenticated && !user) return <Navigate to="/login" state={{ from: location }} replace />
  return <>{children}</>
}

export function RequireAgeGate({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return <div className="flex min-h-screen items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" /></div>
  if (!user?.age_gate_passed) return <Navigate to="/" replace />
  return <>{children}</>
}

export function RequireGirlfriend({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return <div className="flex min-h-screen items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" /></div>
  if (!user?.has_girlfriend) return <Navigate to="/" replace />
  return <>{children}</>
}
