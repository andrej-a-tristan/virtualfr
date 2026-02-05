import { create } from "zustand"
import type {
  AppearancePrefs,
  ContentPrefs,
  Girlfriend,
  IdentityPrefs,
  Traits,
  User,
} from "@/lib/api/types"

interface AppState {
  user: User | null
  girlfriend: Girlfriend | null
  onboardingTraits?: Traits
  onboardingAppearance?: AppearancePrefs
  onboardingContentPrefs?: ContentPrefs
  onboardingIdentity?: IdentityPrefs
  setUser: (u: User | null) => void
  setGirlfriend: (g: Girlfriend | null) => void
  setOnboardingTraits: (traits: Traits | undefined) => void
  setOnboardingAppearance: (prefs: AppearancePrefs | undefined) => void
  setOnboardingContentPrefs: (prefs: ContentPrefs | undefined) => void
  setGirlfriendName: (name: string) => void
  setJobVibe: (vibe: string) => void
  toggleHobby: (hobby: string) => void
  setOriginVibe: (vibe: string) => void
  clearOnboarding: () => void
  reset: () => void
}

export const useAppStore = create<AppState>((set, get) => ({
  user: null,
  girlfriend: null,
  onboardingTraits: undefined,
  onboardingAppearance: undefined,
  onboardingContentPrefs: undefined,
  onboardingIdentity: undefined,
  setUser: (user) => set({ user }),
  setGirlfriend: (girlfriend) => set({ girlfriend }),
  setOnboardingTraits: (onboardingTraits) => set({ onboardingTraits }),
  setOnboardingAppearance: (onboardingAppearance) => set({ onboardingAppearance }),
  setOnboardingContentPrefs: (onboardingContentPrefs) => set({ onboardingContentPrefs }),
  setGirlfriendName: (name) =>
    set((state) => ({
      onboardingIdentity: { ...state.onboardingIdentity, girlfriend_name: name, hobbies: state.onboardingIdentity?.hobbies ?? [] },
    })),
  setJobVibe: (vibe) =>
    set((state) => ({
      onboardingIdentity: { ...state.onboardingIdentity, girlfriend_name: state.onboardingIdentity?.girlfriend_name ?? "", job_vibe: vibe, hobbies: state.onboardingIdentity?.hobbies ?? [] },
    })),
  toggleHobby: (hobby) =>
    set((state) => {
      const current = state.onboardingIdentity?.hobbies ?? []
      const hobbies = current.includes(hobby)
        ? current.filter((h) => h !== hobby)
        : [...current, hobby]
      return {
        onboardingIdentity: { ...state.onboardingIdentity, girlfriend_name: state.onboardingIdentity?.girlfriend_name ?? "", hobbies },
      }
    }),
  setOriginVibe: (vibe) =>
    set((state) => ({
      onboardingIdentity: { ...state.onboardingIdentity, girlfriend_name: state.onboardingIdentity?.girlfriend_name ?? "", origin_vibe: vibe, hobbies: state.onboardingIdentity?.hobbies ?? [] },
    })),
  clearOnboarding: () =>
    set({
      onboardingTraits: undefined,
      onboardingAppearance: undefined,
      onboardingContentPrefs: undefined,
      onboardingIdentity: undefined,
    }),
  reset: () =>
    set({
      user: null,
      girlfriend: null,
      onboardingTraits: undefined,
      onboardingAppearance: undefined,
      onboardingContentPrefs: undefined,
      onboardingIdentity: undefined,
    }),
}))
