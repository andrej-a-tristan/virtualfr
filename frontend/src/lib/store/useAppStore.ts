import { create } from "zustand"
import { persist } from "zustand/middleware"
import type { User, Girlfriend, TraitSelection } from "@/lib/api/types"

// language_pref from /api/me (e.g. "en" | "sk"); TODO: use for Slovak prompts

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
  onboardingDraft: OnboardingDraft
  setUser: (u: User | null) => void
  setGirlfriend: (g: Girlfriend | null) => void
  setOnboardingDraft: (d: OnboardingDraft | ((prev: OnboardingDraft) => OnboardingDraft)) => void
  updateTrait: <K extends keyof TraitSelection>(key: K, value: TraitSelection[K]) => void
  setDisplayName: (name: string) => void
  clearOnboardingDraft: () => void
  reset: () => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      user: null,
      girlfriend: null,
      onboardingDraft: defaultDraft,
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
      reset: () =>
        set({
          user: null,
          girlfriend: null,
          onboardingDraft: defaultDraft,
        }),
    }),
    {
      name: ONBOARDING_STORAGE_KEY,
      partialize: (s) => ({ onboardingDraft: s.onboardingDraft }),
    }
  )
)
