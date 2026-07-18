import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

// ── Mock api-client module ──
const mockGetOrganizationDetail = vi.fn()
const mockUpdateOrganization = vi.fn()
const mockListBankAccounts = vi.fn()
const mockCreateBankAccount = vi.fn()
const mockListOkvedCodes = vi.fn()
const mockCreateOkvedCode = vi.fn()
const mockListLicenses = vi.fn()

vi.mock("@/lib/api-client", () => ({
  isapApi: {
    getOrganizationDetail: (...args: unknown[]) => mockGetOrganizationDetail(...args),
    updateOrganization: (...args: unknown[]) => mockUpdateOrganization(...args),
    listBankAccounts: (...args: unknown[]) => mockListBankAccounts(...args),
    createBankAccount: (...args: unknown[]) => mockCreateBankAccount(...args),
    updateBankAccount: vi.fn(),
    deleteBankAccount: vi.fn(),
    listOkvedCodes: (...args: unknown[]) => mockListOkvedCodes(...args),
    createOkvedCode: (...args: unknown[]) => mockCreateOkvedCode(...args),
    updateOkvedCode: vi.fn(),
    deleteOkvedCode: vi.fn(),
    listLicenses: (...args: unknown[]) => mockListLicenses(...args),
    createLicense: vi.fn(),
    updateLicense: vi.fn(),
    deleteLicense: vi.fn(),
    uploadLicenseFile: vi.fn(),
    deleteLicenseFile: vi.fn(),
    getLicenseDownloadUrl: vi.fn(() => "/download-url"),
  },
}))

// ── Mock nav-store ──
const mockSetActivePage = vi.fn()
vi.mock("@/lib/nav-store", () => ({
  useNavStore: () => ({
    organizationDetailId: "test-org-id",
    setActivePage: mockSetActivePage,
    openOpoForOrganization: vi.fn(),
  }),
}))

// ── Mock sonner toast ──
const mockToastSuccess = vi.fn()
const mockToastError = vi.fn()
vi.mock("sonner", () => ({
  toast: {
    success: (...args: unknown[]) => mockToastSuccess(...args),
    error: (...args: unknown[]) => mockToastError(...args),
  },
}))

import { OrganizationPage } from "../organization-page"

const mockOrgBase = {
  id: "test-org-id",
  name: 'ООО "Тестовая Организация"',
  inn: "7712345678",
  ogrn: "1027700123456",
  address: "г. Москва, ул. Тестовая, д. 1",
  phone: "+7 (495) 123-45-67",
  email: "info@test.ru",
  org_type: "legal",
  full_name: 'Общество с ограниченной ответственностью "Тестовая Организация"',
  short_name: 'ООО "Тестовая Организация"',
  legal_address: "г. Москва, ул. Тестовая, д. 1",
  actual_address: null,
  postal_address: null,
  phone_additional: null,
  phone_mobile: null,
  fax: null,
  website: null,
  kpp: "771234567",
  ogrnip: null,
  okpo: "12345678",
  director_full_name: "Иванов Иван Иванович",
  director_position: "Генеральный директор",
  director_phone: "+7 (495) 111-11-11",
  director_email: "ivanov@test.ru",
  ip_last_name: null,
  ip_first_name: null,
  ip_middle_name: null,
}

const mockDetail = {
  ...mockOrgBase,
  bank_accounts: [
    {
      id: "ba-1",
      organization_id: "test-org-id",
      account_number: "40702810123450000001",
      bank_name: "ПАО Сбербанк",
      bank_bik: "044525225",
      bank_corr_account: "30101810400000000225",
      is_primary: true,
      notes: 'ООО "Тест"',
    },
  ],
  okved_codes: [
    { id: "ok-1", organization_id: "test-org-id", code: "35.22", is_primary: true },
    { id: "ok-2", organization_id: "test-org-id", code: "35.23", is_primary: false },
  ],
  licenses: [
    {
      id: "lic-1",
      organization_id: "test-org-id",
      activity_type: "Эксплуатация",
      license_number: "Л014-00101-77/123456",
      issue_date: "2024-01-15",
      status: "active",
      file_name: "license.pdf",
      file_size: 102400,
      mime_type: "application/pdf",
      checksum_sha256: "abc123",
      has_file: true,
    },
    {
      id: "lic-2",
      organization_id: "test-org-id",
      activity_type: "Транспортировка",
      license_number: "Л014-00101-77/654321",
      issue_date: null,
      status: "expired",
      file_name: null,
      file_size: null,
      mime_type: null,
      checksum_sha256: null,
      has_file: false,
    },
  ],
}

beforeEach(() => {
  vi.clearAllMocks()
  mockGetOrganizationDetail.mockResolvedValue(mockDetail)
  mockUpdateOrganization.mockResolvedValue(mockOrgBase)
  mockListBankAccounts.mockResolvedValue(mockDetail.bank_accounts)
  mockListOkvedCodes.mockResolvedValue(mockDetail.okved_codes)
  mockListLicenses.mockResolvedValue(mockDetail.licenses)
})

// ── Test 1: загрузка и отображение данных ──
describe("OrganizationPage — загрузка и отображение", () => {
  it("загружает организацию и отображает название", async () => {
    render(<OrganizationPage />)

    await waitFor(() => {
      expect(screen.getByText('ООО "Тестовая Организация"')).toBeInTheDocument()
    })

    expect(mockGetOrganizationDetail).toHaveBeenCalledWith("test-org-id")
  })

  it("отображает тип организации — юридическое лицо", async () => {
    render(<OrganizationPage />)

    await waitFor(() => {
      // "Юридическое лицо" appears both in subtitle and tab; use getAllByText
      const elements = screen.getAllByText(/Юридическое лицо/)
      expect(elements.length).toBeGreaterThanOrEqual(2)
    })
  })

  it("отображает ИНН организации", async () => {
    render(<OrganizationPage />)

    await waitFor(() => {
      expect(screen.getByText(/7712345678/)).toBeInTheDocument()
    })
  })

  it("отображает полное наименование в поле ввода", async () => {
    render(<OrganizationPage />)

    await waitFor(() => {
      const input = screen.getByDisplayValue(/Общество с ограниченной ответственностью/)
      expect(input).toBeInTheDocument()
    })
  })

  it("отображает данные руководителя", async () => {
    render(<OrganizationPage />)

    await waitFor(() => {
      expect(screen.getByDisplayValue("Иванов Иван Иванович")).toBeInTheDocument()
      expect(screen.getByDisplayValue("Генеральный директор")).toBeInTheDocument()
      expect(screen.getByDisplayValue("+7 (495) 111-11-11")).toBeInTheDocument()
      expect(screen.getByDisplayValue("ivanov@test.ru")).toBeInTheDocument()
    })
  })

  it("отображает банковские счета", async () => {
    render(<OrganizationPage />)

    await waitFor(() => {
      expect(screen.getByText("40702810123450000001")).toBeInTheDocument()
      expect(screen.getByText("ПАО Сбербанк")).toBeInTheDocument()
    })
  })

  it("отображает коды ОКВЭД", async () => {
    render(<OrganizationPage />)

    await waitFor(() => {
      expect(screen.getByText("35.22")).toBeInTheDocument()
      expect(screen.getByText("35.23")).toBeInTheDocument()
    })
  })

  it("отображает лицензии во вкладке Лицензии", async () => {
    const user = userEvent.setup()
    render(<OrganizationPage />)

    // Wait for load, then click the "Лицензии" tab
    await waitFor(() => {
      expect(screen.getByText('ООО "Тестовая Организация"')).toBeInTheDocument()
    })

    // Find the Лицензии tab trigger and click it
    const licensesTab = screen.getByRole("tab", { name: /Лицензии/ })
    await user.click(licensesTab)

    await waitFor(() => {
      expect(screen.getByText("Эксплуатация")).toBeInTheDocument()
      expect(screen.getByText("Л014-00101-77/123456")).toBeInTheDocument()
    })
  })
})

// ── Test 2: отправка сохранения ──
describe("OrganizationPage — сохранение", () => {
  it("вызывает updateOrganization при нажатии Сохранить", async () => {
    const user = userEvent.setup()
    render(<OrganizationPage />)

    await waitFor(() => {
      expect(screen.getByText('ООО "Тестовая Организация"')).toBeInTheDocument()
    })

    const saveButton = screen.getByRole("button", { name: /Сохранить/ })
    await user.click(saveButton)

    await waitFor(() => {
      expect(mockUpdateOrganization).toHaveBeenCalledWith("test-org-id", expect.objectContaining({
        org_type: "legal",
        name: expect.any(String),
        inn: "7712345678",
        director_full_name: "Иванов Иван Иванович",
        director_phone: "+7 (495) 111-11-11",
      }))
    })
  })
})

// ── Test 3: 409 Conflict ──
describe("OrganizationPage — 409 Conflict", () => {
  it("обрабатывает 409 при создании второго основного счёта (вызов API)", async () => {
    mockCreateBankAccount.mockRejectedValue(new Error("У организации уже есть основной банковский счёт"))

    const user = userEvent.setup()
    render(<OrganizationPage />)

    await waitFor(() => {
      expect(screen.getByText('ООО "Тестовая Организация"')).toBeInTheDocument()
    })

    // Open bank dialog
    const addBankButton = screen.getByRole("button", { name: /Добавить счёт/ })
    await user.click(addBankButton)

    // Fill fields - use placeholder text
    await waitFor(() => {
      expect(screen.getByPlaceholderText("40702810123450000001")).toBeInTheDocument()
    })

    await user.type(screen.getByPlaceholderText("40702810123450000001"), "99")
    await user.type(screen.getByPlaceholderText("ПАО Сбербанк"), "Тест Банк")

    // Click save directly (simulate 409 without checkbox interaction)
    const saveBtns = screen.getAllByRole("button", { name: /Сохранить/ })
    const dialogSaveBtn = saveBtns[saveBtns.length - 1]
    await user.click(dialogSaveBtn)

    await waitFor(() => {
      expect(mockCreateBankAccount).toHaveBeenCalled()
    })
  })

  it("обрабатывает 409 при создании второго основного ОКВЭД (вызов API)", async () => {
    mockCreateOkvedCode.mockRejectedValue(new Error("У организации уже есть основной код ОКВЭД"))

    const user = userEvent.setup()
    render(<OrganizationPage />)

    await waitFor(() => {
      expect(screen.getByText('ООО "Тестовая Организация"')).toBeInTheDocument()
    })

    // Open OKVED dialog
    const addOkvedButton = screen.getByRole("button", { name: /Добавить ОКВЭД/ })
    await user.click(addOkvedButton)

    await waitFor(() => {
      expect(screen.getByPlaceholderText("35.22")).toBeInTheDocument()
    })

    await user.type(screen.getByPlaceholderText("35.22"), "01.11")

    // Save
    const saveBtns = screen.getAllByRole("button", { name: /Сохранить/ })
    const dialogSaveBtn = saveBtns[saveBtns.length - 1]
    await user.click(dialogSaveBtn)

    await waitFor(() => {
      expect(mockCreateOkvedCode).toHaveBeenCalled()
    })
  })
})

// ── Test 4: переключение юрлицо/ИП ──
describe("OrganizationPage — переключение юрлицо/ИП", () => {
  it("отображает поля руководителя для юрлица", async () => {
    render(<OrganizationPage />)

    await waitFor(() => {
      expect(screen.getByText("Руководитель")).toBeInTheDocument()
      expect(screen.getByText("ФИО руководителя")).toBeInTheDocument()
      expect(screen.getByText("Должность")).toBeInTheDocument()
      expect(screen.getByText("Телефон руководителя")).toBeInTheDocument()
      expect(screen.getByText("Email руководителя")).toBeInTheDocument()
    })
  })

  it("переключает секции при выборе ИП", async () => {
    const user = userEvent.setup()

    mockGetOrganizationDetail.mockResolvedValue({
      ...mockDetail,
      org_type: "individual",
      full_name: "Иванов Иван Иванович",
      short_name: "ИП Иванов И.И.",
      ogrnip: "304123456789012",
      ip_last_name: "Иванов",
      ip_first_name: "Иван",
      ip_middle_name: "Иванович",
      kpp: null,
      ogrn: null,
      director_full_name: null,
      director_position: null,
    })

    render(<OrganizationPage />)

    await waitFor(() => {
      const elements = screen.getAllByText("Индивидуальный предприниматель")
      expect(elements.length).toBeGreaterThanOrEqual(1)
    })

    // Click IP tab
    const ipTab = screen.getByRole("tab", { name: /Индивидуальный предприниматель/ })
    await user.click(ipTab)

    await waitFor(() => {
      expect(screen.getByText("Фамилия")).toBeInTheDocument()
      expect(screen.getByText("Имя")).toBeInTheDocument()
      expect(screen.getByText("Отчество")).toBeInTheDocument()
      expect(screen.getByText("ОГРНИП")).toBeInTheDocument()
    })

    // Legal-only sections should be absent
    expect(screen.queryByText("Руководитель")).not.toBeInTheDocument()
    expect(screen.queryByText("КПП")).not.toBeInTheDocument()
    expect(screen.queryByText("ОГРН")).not.toBeInTheDocument()
  })
})

// ── Test 5: отображение ошибки загрузки ──
describe("OrganizationPage — ошибка загрузки", () => {
  it("отображает сообщение об ошибке при неудачной загрузке", async () => {
    mockGetOrganizationDetail.mockRejectedValue(new Error("Организация не найдена"))

    render(<OrganizationPage />)

    await waitFor(() => {
      expect(screen.getByText("Организация не найдена")).toBeInTheDocument()
    })
  })
})
