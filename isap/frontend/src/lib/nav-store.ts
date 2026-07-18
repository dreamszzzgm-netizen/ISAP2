import { create } from "zustand"

export type PageKey =
  | "overview"
  | "tasks"
  | "clients"
  | "contracts"
  | "analytics"
  | "expertise"
  | "opo"
  | "facilityDetail"
  | "pmla"
  | "pmlaQuestionnaire"
  | "documents"
  | "documentDetail"
  | "organizationDetail"
  | "ai"
  | "directories"
  | "settings"
  | "help"

interface NavStore {
  activePage: PageKey
  facilityDetailId: string | null
  documentDetailId: string | null
  pmlaQuestionnaireFacilityId: string | null
  opoPreSelectedOrgId: string | null   // для создания ОПО из карточки организации
  organizationDetailId: string | null   // для карточки организации
  setActivePage: (page: PageKey) => void
  openFacilityDetail: (facilityId: string) => void
  openDocumentDetail: (documentId: string) => void
  openPmlaQuestionnaire: (facilityId?: string) => void
  openOrganizationDetail: (orgId: string) => void
  openOpoForOrganization: (orgId: string) => void  // создать ОПО для организации
  goBack: () => void
}

export const useNavStore = create<NavStore>((set) => ({
  activePage: "overview",
  facilityDetailId: null,
  documentDetailId: null,
  pmlaQuestionnaireFacilityId: null,
  opoPreSelectedOrgId: null,
  organizationDetailId: null,
  setActivePage: (page) => set({ activePage: page, facilityDetailId: null, documentDetailId: null, pmlaQuestionnaireFacilityId: null, opoPreSelectedOrgId: null, organizationDetailId: null }),
  openFacilityDetail: (facilityId) => set({ activePage: "facilityDetail", facilityDetailId: facilityId, documentDetailId: null }),
  openDocumentDetail: (documentId) => set({ activePage: "documentDetail", documentDetailId: documentId }),
  openPmlaQuestionnaire: (facilityId) => set({ activePage: "pmlaQuestionnaire", pmlaQuestionnaireFacilityId: facilityId || null }),
  openOrganizationDetail: (orgId) => set({ activePage: "organizationDetail", organizationDetailId: orgId, facilityDetailId: null, documentDetailId: null, pmlaQuestionnaireFacilityId: null, opoPreSelectedOrgId: null }),
  openOpoForOrganization: (orgId) => set({ activePage: "opo", opoPreSelectedOrgId: orgId, facilityDetailId: null, documentDetailId: null }),
  goBack: () => set((state) => {
    if (state.activePage === "documentDetail") return { activePage: "pmla" as PageKey, documentDetailId: null }
    if (state.activePage === "pmlaQuestionnaire" && state.pmlaQuestionnaireFacilityId) return { activePage: "facilityDetail" as PageKey, facilityDetailId: state.pmlaQuestionnaireFacilityId, pmlaQuestionnaireFacilityId: null }
    if (state.activePage === "facilityDetail") return { activePage: "opo" as PageKey, facilityDetailId: null }
    if (state.activePage === "organizationDetail") return { activePage: "clients" as PageKey, organizationDetailId: null }
    return { activePage: "overview" as PageKey, facilityDetailId: null, documentDetailId: null }
  }),
}))
