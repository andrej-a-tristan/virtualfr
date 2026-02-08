import { create } from "zustand"
import { persist } from "zustand/middleware"
import type {
  AppearancePrefs,
  ContentPrefs,
  Girlfriend,
  IdentityPrefs,
  TraitSelection,
  Traits,
  User,
} from "@/lib/api/types"

const ONBOARDING_STORAGE_KEY = "companion-onboarding-draft"

export interface OnboardingDraft {
  displayName: string
  traits: Partial<TraitSelection>
}

const defaultDraft: OnboardingDraft = {
  displayName: "My Girl",
  traits: {},
}

interface AppState {
  user: User | null
  girlfriend: Girlfriend | null
  // Legacy onboarding draft (personality engine)
  onboardingDraft: OnboardingDraft
  // Extended onboarding state (LLM chatbot flow)
  onboardingTraits?: Traits
  onboardingAppearance?: AppearancePrefs
  onboardingContentPrefs?: ContentPrefs
  onboardingIdentity?: IdentityPrefs
  // Actions
  setUser: (u: User | null) => void
  setGirlfriend: (g: Girlfriend | null) => void
  setOnboardingDraft: (d: OnboardingDraft | ((prev: OnboardingDraft) => OnboardingDraft)) => void
  updateTrait: <K extends keyof TraitSelection>(key: K, value: TraitSelection[K]) => void
  setDisplayName: (name: string) => void
  clearOnboardingDraft: () => void
  // Extended onboarding actions
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

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      user: null,
      girlfriend: null,
      onboardingDraft: defaultDraft,
      onboardingTraits: undefined,
      onboardingAppearance: undefined,
      onboardingContentPrefs: undefined,
      onboardingIdentity: undefined,
      setUser: (user) => set({ user }),
      setGirlfriend: (girlfriend) => set({ girlfriend }),
      setOnboardingDraft: (d) =>
        set((s) => ({
          onboardingDraft: typeof d === "function" ? d(s.onboardingDraft) : d,
        })),
      updateTrait: (key, value) =>
        set((s) => ({
          onboardingDraft: {
            ...s.onboardingDraft,
            traits: { ...s.onboardingDraft.traits, [key]: value },
          },
        })),
      setDisplayName: (displayName) =>
        set((s) => ({
          onboardingDraft: { ...s.onboardingDraft, displayName },
        })),
      clearOnboardingDraft: () => set({ onboardingDraft: defaultDraft }),
      // Extended onboarding actions
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
          onboardingDraft: defaultDraft,
          onboardingTraits: undefined,
          onboardingAppearance: undefined,
          onboardingContentPrefs: undefined,
          onboardingIdentity: undefined,
        }),
      reset: () =>
        set({
          user: null,
          girlfriend: null,
          onboardingDraft: defaultDraft,
          onboardingTraits: undefined,
          onboardingAppearance: undefined,
          onboardingContentPrefs: undefined,
          onboardingIdentity: undefined,
        }),
    }),
    {
      name: ONBOARDING_STORAGE_KEY,
      partialize: (s) => ({
        onboardingDraft: s.onboardingDraft,
        onboardingTraits: s.onboardingTraits,
        onboardingAppearance: s.onboardingAppearance,
        onboardingContentPrefs: s.onboardingContentPrefs,
        onboardingIdentity: s.onboardingIdentity,
      }),
    }
  )
)
