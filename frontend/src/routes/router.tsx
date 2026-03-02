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
import AppearanceAge from "@/pages/appearance/AppearanceAge"
import AppearanceEthnicity from "@/pages/appearance/AppearanceEthnicity"
import AppearanceBodyDetails from "@/pages/appearance/AppearanceBodyDetails"
import AppearanceHairEyes from "@/pages/appearance/AppearanceHairEyes"
import OnboardingPreferences from "@/pages/OnboardingPreferences"
import OnboardingGenerating from "@/pages/OnboardingGenerating"
import OnboardingIdentity from "@/pages/OnboardingIdentity"
import GirlfriendReveal from "@/pages/GirlfriendReveal"
import SubscriptionPlan from "@/pages/SubscriptionPlan"
import RevealSuccess from "@/pages/RevealSuccess"
import GirlPage from "@/pages/GirlPage"
import Profile from "@/pages/Profile"
import Settings from "@/pages/Settings"
import Billing from "@/pages/Billing"
import PaymentOptions from "@/pages/PaymentOptions"
import Safety from "@/pages/Safety"
import RelationshipPage from "@/pages/Relationship"

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
  /* Onboarding pages — no auth guards needed; Landing creates a guest session */
  { path: "/onboarding/traits", element: <OnboardingTraits /> },
  { path: "/onboarding/appearance", element: <OnboardingAppearance /> },
  { path: "/onboarding/appearance/age", element: <AppearanceAge /> },
  { path: "/onboarding/appearance/ethnicity", element: <AppearanceEthnicity /> },
  { path: "/onboarding/appearance/body", element: <AppearanceBodyDetails /> },
  { path: "/onboarding/appearance/hair-eyes", element: <AppearanceHairEyes /> },
  { path: "/onboarding/preferences", element: <OnboardingPreferences /> },
  { path: "/onboarding/identity", element: <OnboardingIdentity /> },
  { path: "/onboarding/generating", element: <OnboardingGenerating /> },
  {
    path: "/onboarding/reveal",
    element: <GirlfriendReveal />,
  },
  {
    path: "/onboarding/subscribe",
    element: <SubscriptionPlan />,
  },
  {
    path: "/onboarding/reveal-success",
    element: <RevealSuccess />,
  },
  { path: "/onboarding/preview", element: <PersonaPreview /> },
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
      { index: true, element: <Navigate to="/app/girl" replace /> },
      { path: "girl", element: <GirlPage /> },
      /* Girlfriend-specific relationship page */
      { path: "girls/:girlId/relationship", element: <RelationshipPage /> },
      /* Legacy redirects so old bookmarks / return URLs still work */
      { path: "chat", element: <Navigate to="/app/girl" replace /> },
      { path: "gallery", element: <Navigate to="/app/girl" replace /> },
      { path: "relationship", element: <Navigate to="/app/girl" replace /> },
      { path: "profile", element: <Profile /> },
      { path: "settings", element: <Settings /> },
      { path: "billing", element: <Billing /> },
      { path: "payment-options", element: <PaymentOptions /> },
      { path: "safety", element: <Safety /> },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
])

export default router
