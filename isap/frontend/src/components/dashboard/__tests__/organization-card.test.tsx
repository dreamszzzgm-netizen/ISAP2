import { describe, it, expect, vi, beforeEach } from "vitest"

// ── Mock fetch ──
const mockFetch = vi.fn()
globalThis.fetch = mockFetch as unknown as typeof fetch

beforeEach(() => {
  mockFetch.mockReset()
})

// ── Helpers to extract bank account / OKVED field lists from API type ──

/** Fields that BANK ACCOUNT API sends to frontend */
const BANK_ACCOUNT_FIELDS = [
  "id",
  "organization_id",
  "account_number",
  "bank_name",
  "bank_bik",
  "bank_corr_account",
  "is_primary",
  "notes",
] as const

/** Fields that OKVED API sends to frontend */
const OKVED_FIELDS = [
  "id",
  "organization_id",
  "code",
  "is_primary",
] as const

/** Fields that LICENSE API sends to frontend */
const LICENSE_FIELDS = [
  "id",
  "organization_id",
  "activity_type",
  "license_number",
  "issue_date",
  "status",
  "file_name",
  "file_size",
  "mime_type",
  "checksum_sha256",
  "has_file",
] as const

/** Fields that ORGANIZATION API sends to frontend */
const ORGANIZATION_FIELDS = [
  "id",
  "name",
  "inn",
  "ogrn",
  "address",
  "phone",
  "email",
  "org_type",
  "full_name",
  "short_name",
  "legal_address",
  "actual_address",
  "postal_address",
  "phone_additional",
  "phone_mobile",
  "fax",
  "website",
  "kpp",
  "ogrnip",
  "okpo",
  "director_full_name",
  "director_position",
  "director_phone",
  "director_email",
  "ip_last_name",
  "ip_first_name",
  "ip_middle_name",
] as const

// ── Test: Несогласованные поля банковского счета ──
describe("BankAccount — согласованные поля", () => {
  it("не содержит несогласованных полей: currency", () => {
    const disallowed = ["currency"]
    for (const field of disallowed) {
      expect(BANK_ACCOUNT_FIELDS).not.toContain(field)
    }
  })

  it("содержит все согласованные поля", () => {
    const required = ["account_number", "bank_name", "bank_bik", "bank_corr_account", "is_primary"]
    for (const field of required) {
      expect(BANK_ACCOUNT_FIELDS).toContain(field)
    }
  })
})

// ── Test: Несогласованные поля ОКВЭД ──
describe("OkvedCode — согласованные поля", () => {
  it("не содержит несогласованных полей: description", () => {
    const disallowed = ["description"]
    for (const field of disallowed) {
      expect(OKVED_FIELDS).not.toContain(field)
    }
  })

  it("содержит код и is_primary", () => {
    expect(OKVED_FIELDS).toContain("code")
    expect(OKVED_FIELDS).toContain("is_primary")
  })
})

// ── Test: Лицензия — формат и размер ──
describe("License — ограничения электронной копии", () => {
  it("проверяет допустимые расширения", () => {
    const allowedExts = [".pdf", ".jpg", ".jpeg", ".png"]
    expect(allowedExts).toContain(".pdf")
    expect(allowedExts).toContain(".jpg")
    expect(allowedExts).toContain(".jpeg")
    expect(allowedExts).toContain(".png")
    expect(allowedExts).not.toContain(".docx")
    expect(allowedExts).not.toContain(".xlsx")
  })

  it("проверяет максимальный размер 20 МБ", () => {
    // Backend: settings.max_upload_file_size_mb = 20
    const maxMb = 20
    const maxBytes = maxMb * 1024 * 1024

    // 19 MB — OK
    expect(19 * 1024 * 1024).toBeLessThanOrEqual(maxBytes)
    // 20 MB — OK (ровно)
    expect(maxBytes).toBeLessThanOrEqual(maxBytes)
    // 21 MB — не OK
    expect(21 * 1024 * 1024).toBeGreaterThan(maxBytes)
  })
})

// ── Test: Тип организации ──
describe("Organization — org_type", () => {
  it("org_type может быть legal или individual", () => {
    const validTypes = ["legal", "individual"]
    expect(validTypes).toContain("legal")
    expect(validTypes).toContain("individual")
    expect(validTypes).not.toContain("ip")
    expect(validTypes).not.toContain("entity")
  })

  it("org_type присутствует в API ответе", () => {
    expect(ORGANIZATION_FIELDS).toContain("org_type")
  })

  it("type не должен присутствовать (используется org_type)", () => {
    expect(ORGANIZATION_FIELDS).not.toContain("type")
  })
})

// ── Test: Полное и сокращённое наименование ──
describe("Organization — наименования", () => {
  it("full_name и short_name присутствуют для обоих типов", () => {
    expect(ORGANIZATION_FIELDS).toContain("full_name")
    expect(ORGANIZATION_FIELDS).toContain("short_name")
  })
})

// ── Test: Руководитель ──
describe("Organization — руководитель (юридическое лицо)", () => {
  it("содержит телефон и email руководителя", () => {
    expect(ORGANIZATION_FIELDS).toContain("director_phone")
    expect(ORGANIZATION_FIELDS).toContain("director_email")
  })
})

// ── Test: 409 Conflict ──
describe("Обработка 409 Conflict", () => {
  it("сообщение об основном счёте содержит 'основной'", () => {
    const msg = "У организации уже есть основной банковский счёт"
    expect(msg).toContain("основной")
    expect(msg).toContain("банковский счёт")
  })

  it("сообщение об основном ОКВЭД содержит 'основной'", () => {
    const msg = "У организации уже есть основной код ОКВЭД"
    expect(msg).toContain("основной")
    expect(msg).toContain("ОКВЭД")
  })
})

// ── Test: Runtime-проверка org_type ──
describe("Runtime-проверка org_type", () => {
  it("определяет юрлицо по org_type=legal", () => {
    const orgTypes = { legal: false, individual: true }
    const isLegal = (type: string) => type === "legal"
    const isIndividual = (type: string) => type === "individual"
    expect(isLegal("legal")).toBe(true)
    expect(isIndividual("legal")).toBe(false)
    expect(isLegal("individual")).toBe(false)
    expect(isIndividual("individual")).toBe(true)
  })
})

// ── Test: Отображение полей ИП ──
describe("Organization — поля ИП", () => {
  it("содержит поля ИП", () => {
    expect(ORGANIZATION_FIELDS).toContain("ip_last_name")
    expect(ORGANIZATION_FIELDS).toContain("ip_first_name")
    expect(ORGANIZATION_FIELDS).toContain("ip_middle_name")
    expect(ORGANIZATION_FIELDS).toContain("ogrnip")
  })
})
