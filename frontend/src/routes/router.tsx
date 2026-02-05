import { createBrowserRouter, Navigate } from "react-router-dom"
import { RequireAuth, RequireAgeGate, RequireGirlfriend } from "./guards"
import AppShell from "@/components/layout/AppShell"
import Landing from "@/pages/Landing"
import Login from "@/pages/Login"
import Signup from "@/pages/Signup"
import AgeGate from "@/pages/AgeGate"
import OnboardingTraits from "@/pages/OnboardingTraits"
import PersonaPreview from "@/pages/PersonaPreview"
import OnboardingAppearance from "@/pages/OnboardingAppearance"
import OnboardingPreferences from "@/pages/OnboardingPreferences"
import OnboardingGenerating from "@/pages/OnboardingGenerating"
import OnboardingIdentity from "@/pages/OnboardingIdentity"
import Chat from "@/pages/Chat"
import Gallery from "@/pages/Gallery"
import Profile from "@/pages/Profile"
import Settings from "@/pages/Settings"
import Billing from "@/pages/Billing"
import Safety from "@/pages/Safety"

const router = createBrowserRouter([
  { path: "/", element: <Landing /> },
  { path: "/login", element: <Login /> },
  { path: "/signup", element: <Signup /> },
  {
    path: "/age-gate",
    element: (
      <RequireAuth>
        <AgeGate />
      </RequireAuth>
    ),
  },
  {
    path: "/onboarding/traits",
    element: (
      <RequireAuth>
        <RequireAgeGate>
          <OnboardingTraits />
        </RequireAgeGate>
      </RequireAuth>
    ),
  },
  {
    path: "/onboarding/appearance",
    element: (
      <RequireAuth>
        <RequireAgeGate>
          <OnboardingAppearance />
        </RequireAgeGate>
      </RequireAuth>
    ),
  },
  {
    path: "/onboarding/preferences",
    element: (
      <RequireAuth>
        <RequireAgeGate>
          <OnboardingPreferences />
        </RequireAgeGate>
      </RequireAuth>
    ),
  },
  {
    path: "/onboarding/identity",
    element: (
      <RequireAuth>
        <RequireAgeGate>
          <OnboardingIdentity />
        </RequireAgeGate>
      </RequireAuth>
    ),
  },
  {
    path: "/onboarding/generating",
    element: (
      <RequireAuth>
        <RequireAgeGate>
          <OnboardingGenerating />
        </RequireAgeGate>
      </RequireAuth>
    ),
  },
  {
    path: "/onboarding/preview",
    element: (
      <RequireAuth>
        <RequireAgeGate>
          <RequireGirlfriend>
            <PersonaPreview />
          </RequireGirlfriend>
        </RequireAgeGate>
      </RequireAuth>
    ),
  },
  {
    path: "/app",
    element: (
      <RequireAuth>
        <RequireAgeGate>
          <RequireGirlfriend>
            <AppShell />
          </RequireGirlfriend>
        </RequireAgeGate>
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="/app/chat" replace /> },
      { path: "chat", element: <Chat /> },
      { path: "gallery", element: <Gallery /> },
      { path: "profile", element: <Profile /> },
      { path: "settings", element: <Settings /> },
      { path: "billing", element: <Billing /> },
      { path: "safety", element: <Safety /> },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
])

export default router
