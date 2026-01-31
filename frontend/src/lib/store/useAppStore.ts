import { create } from "zustand"
import type { User, Girlfriend } from "@/lib/api/types"

interface AppState {
  user: User | null
  girlfriend: Girlfriend | null
  setUser: (u: User | null) => void
  setGirlfriend: (g: Girlfriend | null) => void
  reset: () => void
}

export const useAppStore = create<AppState>((set) => ({
  user: null,
  girlfriend: null,
  setUser: (user) => set({ user }),
  setGirlfriend: (girlfriend) => set({ girlfriend }),
  reset: () => set({ user: null, girlfriend: null }),
}))
