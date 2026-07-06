import { create } from "zustand"

export type PageKey =
  | "overview"
  | "tasks"
  | "clients"
  | "contracts"
  | "analytics"
  | "expertise"
  | "opo"
  | "pmla"
  | "documents"
  | "ai"
  | "directories"
  | "settings"
  | "help"

interface NavStore {
  activePage: PageKey
  setActivePage: (page: PageKey) => void
}

export const useNavStore = create<NavStore>((set) => ({
  activePage: "overview",
  setActivePage: (page) => set({ activePage: page }),
}))