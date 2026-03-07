/**
 * Route guards: RequireAuth, RequireAgeGate, RequireGirlfriend, RequireSubscription.
 * Wrap protected routes and redirect when conditions fail.
 */
import { Navigate, useLocation } from "react-router-dom"
import { useAuth } from "@/lib/hooks/useAuth"
import { useQuery } from "@tanstack/react-query"
import { getBillingStatus } from "@/lib/api/endpoints"

const Spinner = () => (
  <div className="flex min-h-screen items-center justify-center">
    <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
  </div>
)

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()
  if (isLoading) return <Spinner />
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />
  return <>{children}</>
}

export function RequireAgeGate({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return <Spinner />
  if (!user?.age_gate_passed) return <Navigate to="/" replace />
  return <>{children}</>
}

export function RequireGirlfriend({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return <Spinner />
  if (!user?.has_girlfriend) return <Navigate to="/" replace />
  return <>{children}</>
}

export function RequireSubscription({ children }: { children: React.ReactNode }) {
  const { data: billing, isLoading } = useQuery({
    queryKey: ["billingStatus"],
    queryFn: getBillingStatus,
    retry: false,
    staleTime: 30_000,
  })
  if (isLoading) return <Spinner />
  if (!billing?.has_card_on_file) return <Navigate to="/onboarding/subscribe" replace />
  return <>{children}</>
}
