import { create } from "zustand"
import type {
  AppearancePrefs,
  ContentPrefs,
  Girlfriend,
  Traits,
  User,
} from "@/lib/api/types"

interface AppState {
  user: User | null
  girlfriend: Girlfriend | null
  onboardingTraits?: Traits
  onboardingAppearance?: AppearancePrefs
  onboardingContentPrefs?: ContentPrefs
  setUser: (u: User | null) => void
  setGirlfriend: (g: Girlfriend | null) => void
  setOnboardingTraits: (traits: Traits | undefined) => void
  setOnboardingAppearance: (prefs: AppearancePrefs | undefined) => void
  setOnboardingContentPrefs: (prefs: ContentPrefs | undefined) => void
  clearOnboarding: () => void
  reset: () => void
}

export const useAppStore = create<AppState>((set) => ({
  user: null,
  girlfriend: null,
  onboardingTraits: undefined,
  onboardingAppearance: undefined,
  onboardingContentPrefs: undefined,
  setUser: (user) => set({ user }),
  setGirlfriend: (girlfriend) => set({ girlfriend }),
  setOnboardingTraits: (onboardingTraits) => set({ onboardingTraits }),
  setOnboardingAppearance: (onboardingAppearance) => set({ onboardingAppearance }),
  setOnboardingContentPrefs: (onboardingContentPrefs) => set({ onboardingContentPrefs }),
  clearOnboarding: () =>
    set({
      onboardingTraits: undefined,
      onboardingAppearance: undefined,
      onboardingContentPrefs: undefined,
    }),
  reset: () =>
    set({
      user: null,
      girlfriend: null,
      onboardingTraits: undefined,
      onboardingAppearance: undefined,
      onboardingContentPrefs: undefined,
    }),
}))
