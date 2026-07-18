import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import "@testing-library/jest-dom"

const mockFetch = vi.fn()
globalThis.fetch = mockFetch as unknown as typeof fetch

beforeEach(() => { mockFetch.mockReset() })

vi.mock("@/lib/nav-store", () => ({
  useNavStore: () => ({
    facilityDetailId: "test-facility-id",
    goBack: vi.fn(),
    openPmlaQuestionnaire: vi.fn(),
    openDocumentDetail: vi.fn(),
  }),
}))

vi.mock("@/lib/api-client", () => ({
  isapApi: {
    getFacilityFull: vi.fn(),
    getFacilityComposition: vi.fn(),
    getPmlaQuestionnaireByFacility: vi.fn(),
    getQuestionnaireDocuments: vi.fn(),
    createPmlaQuestionnaire: vi.fn(),
    generatePmlaFromQuestionnaire: vi.fn(),
  },
}))

import { CLASSIFICATION_LABELS, WORK_PROCESS_LABELS } from "../facility-detail-page"
import { isapApi } from "@/lib/api-client"

const mockGetFacilityFull = vi.mocked(isapApi.getFacilityFull)
const mockGetFacilityComposition = vi.mocked(isapApi.getFacilityComposition)
const mockGetPmlaQuestionnaireByFacility = vi.mocked(isapApi.getPmlaQuestionnaireByFacility)
const mockGetQuestionnaireDocuments = vi.mocked(isapApi.getQuestionnaireDocuments)

const FACILITY_DATA = {
  id: "test-facility-id",
  name: "Сеть газопотребления",
  opo_full_name: "Сеть газопотребления ООО ТестГазпром",
  reg_number: "ОО-77-00001",
  hazard_class: "3",
  facility_type: "Сеть газопотребления",
  address: "г. Москва, ул. Газовая, д. 10",
  organization_name: "ООО ТестГазпром",
  classification: ["4.1", "4.5", "4.12"],
  work_processes: { "2.1": "транспорт", "2.3": "хранение" },
  licensed_activities: [{ license_id: "lic-1", activity: "газоснабжение" }],
  composition_structures: [{ type: "building", name: "ГРПШ-1", area_sqm: 45.5 }],
  nearby_hazardous: [{ name: "Котельная", distance_m: 350 }],
  properties: { okved: "46.71", oktmo: "45338000", owner: "ООО Тест", owner_basis: "собственник" },
  commissioning_date: "2018-06-15",
}

const COMPOSITION_DATA = {
  facility_id: "test-facility-id",
  structures: [{ type: "building", name: "ГРПШ-1" }],
  equipment: [{ id: "eq-1", name: "ГРПШ-1", equipment_type: "ГРПШ", serial_number: "SN-001", manufacturer: "Завод", manufacture_year: 2019 }],
  substances: [{ id: "sub-1", name: "Природный газ", cas_number: "74-82-8", quantity_kg: 500 }],
  total_equipment: 1, total_substances: 1, total_structures: 1,
}

// Helper to render and wait for data
async function renderAndWait() {
  const { render: r, ...rest } = await import("@testing-library/react")
  // @ts-ignore
  const result = r((await import("../facility-detail-page")).FacilityDetailPage)
  await waitFor(() => {
    expect(screen.getAllByText("Сеть газопотребления ООО ТестГазпром").length).toBeGreaterThan(0)
  })
  return { ...result, ...rest }
}

describe("FacilityDetailPage", () => {
  beforeEach(() => {
    mockGetFacilityFull.mockResolvedValue(FACILITY_DATA as any)
    mockGetFacilityComposition.mockResolvedValue(COMPOSITION_DATA as any)
    mockGetPmlaQuestionnaireByFacility.mockRejectedValue(new Error("not found"))
    mockGetQuestionnaireDocuments.mockResolvedValue([] as any)
  })

  // ── 1. opo_full_name priority ──
  it("shows opo_full_name in header when set", async () => {
    const { FacilityDetailPage } = await import("../facility-detail-page")
    render(<FacilityDetailPage />)
    await waitFor(() => {
      expect(screen.getAllByText("Сеть газопотребления ООО ТестГазпром").length).toBeGreaterThan(0)
    })
  })

  it("falls back to name when opo_full_name is empty", async () => {
    mockGetFacilityFull.mockResolvedValue({ ...FACILITY_DATA, opo_full_name: "" } as any)
    const { FacilityDetailPage } = await import("../facility-detail-page")
    render(<FacilityDetailPage />)
    await waitFor(() => {
      expect(screen.getAllByText("Сеть газопотребления").length).toBeGreaterThan(0)
    })
  })

  // ── 2. facility_type NOT shown ──
  it("does not display facility_type", async () => {
    const { FacilityDetailPage } = await import("../facility-detail-page")
    render(<FacilityDetailPage />)
    await waitFor(() => {
      expect(screen.getAllByText("Сеть газопотребления ООО ТестГазпром").length).toBeGreaterThan(0)
    })
    expect(screen.queryByText("Тип объекта")).not.toBeInTheDocument()
  })

  // ── 3. Only 4 fields in basic tab ──
  it("shows only 4 fields in Основные сведения", async () => {
    const { FacilityDetailPage } = await import("../facility-detail-page")
    render(<FacilityDetailPage />)
    await waitFor(() => {
      expect(screen.getAllByText("Сеть газопотребления ООО ТестГазпром").length).toBeGreaterThan(0)
    })
    expect(screen.getByText("ОО-77-00001")).toBeInTheDocument()
    expect(screen.getByText("3")).toBeInTheDocument()
    expect(screen.getByText(/г\. Москва/)).toBeInTheDocument()
    expect(screen.queryByText("ОКВЭД")).not.toBeInTheDocument()
  })

  // ── 4. Classification labels ──
  it("has correct classification labels", () => {
    expect(CLASSIFICATION_LABELS["4.1"]).toBe("взрывопожароопасные")
    expect(CLASSIFICATION_LABELS["4.12"]).toBe("опасные производственные объекты транспорта")
  })

  // ── 5. Work process labels ──
  it("has correct work process labels", () => {
    expect(WORK_PROCESS_LABELS["2.1"]).toBe("транспортирование")
    expect(WORK_PROCESS_LABELS["2.6"]).toBe("использование")
  })

  // ── 6. Data is loaded and tabs exist ──
  it("renders all three tabs", async () => {
    const { FacilityDetailPage } = await import("../facility-detail-page")
    render(<FacilityDetailPage />)
    await waitFor(() => {
      expect(screen.getAllByText("Сеть газопотребления ООО ТестГазпром").length).toBeGreaterThan(0)
    })
    expect(screen.getByRole("tab", { name: /Основные сведения/ })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /Сведения, характеризующие ОПО/ })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /ПМЛА/ })).toBeInTheDocument()
  })

  // ── 7. API error handling ──
  it("shows error when facility load fails", async () => {
    mockGetFacilityFull.mockRejectedValue(new Error("Network error"))
    const { FacilityDetailPage } = await import("../facility-detail-page")
    render(<FacilityDetailPage />)
    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument()
    })
  })

  // ── 8. No facility ID shows fallback ──
  it("shows 'ОПО не выбрано' when no facility ID", async () => {
    // Override the mock for this test only
    const navModule = await import("@/lib/nav-store")
    const original = navModule.useNavStore
    ;(navModule as any).useNavStore = () => ({
      facilityDetailId: null,
      goBack: vi.fn(),
      openPmlaQuestionnaire: vi.fn(),
      openDocumentDetail: vi.fn(),
    })
    const { FacilityDetailPage } = await import("../facility-detail-page")
    render(<FacilityDetailPage />)
    expect(screen.getByText("ОПО не выбрано")).toBeInTheDocument()
    ;(navModule as any).useNavStore = original
  })
})
