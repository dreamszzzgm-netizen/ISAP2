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
  | "pmlaQuestionnaire"
  | "documents"
  | "documentDetail"
  | "ai"
  | "directories"
  | "settings"
  | "help"

interface NavStore {
  activePage: PageKey
  documentDetailId: string | null
  setActivePage: (page: PageKey) => void
  openDocumentDetail: (documentId: string) => void
  goBack: () => void
}

export const useNavStore = create<NavStore>((set) => ({
  activePage: "overview",
  documentDetailId: null,
  setActivePage: (page) => set({ activePage: page, documentDetailId: null }),
  openDocumentDetail: (documentId) => set({ activePage: "documentDetail", documentDetailId: documentId }),
  goBack: () => set((state) => {
    if (state.activePage === "documentDetail") return { activePage: "pmla" as PageKey, documentDetailId: null }
    return { activePage: "overview" as PageKey, documentDetailId: null }
  }),
}))
