export type ApiErrorPayload = {
  detail?: string
  message?: string
  error?: string
}

const API_KEY = process.env.NEXT_PUBLIC_API_KEY || ""

function toApiUrl(path: string): string {
  if (path.startsWith("http")) {
    return path
  }
  return path
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = toApiUrl(path)
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(API_KEY ? { Authorization: `Bearer ${API_KEY}`, "X-API-Key": API_KEY } : {}),
      ...(options.headers || {}),
    },
    cache: "no-store",
  })

  if (!response.ok) {
    let payload: ApiErrorPayload | null = null
    try {
      payload = await response.json()
    } catch {
      payload = null
    }
    const message = payload?.detail || payload?.message || payload?.error || `HTTP ${response.status}`
    throw new Error(message)
  }

  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}

export async function apiUpload<T>(path: string, file: File): Promise<T> {
  const form = new FormData()
  form.append("file", file)
  const response = await fetch(toApiUrl(path), {
    method: "POST",
    headers: {
      ...(API_KEY ? { Authorization: `Bearer ${API_KEY}`, "X-API-Key": API_KEY } : {}),
    },
    body: form,
    cache: "no-store",
  })

  if (!response.ok) {
    let payload: ApiErrorPayload | null = null
    try {
      payload = await response.json()
    } catch {
      payload = null
    }
    const message = payload?.detail || payload?.message || payload?.error || `HTTP ${response.status}`
    throw new Error(message)
  }

  return response.json() as Promise<T>
}

export type PmlaQuestionnaire = {
  id: string
  organization_id?: string | null
  facility_id?: string | null
  title: string
  data: Record<string, unknown>
  created_at?: string | null
  updated_at?: string | null
}

export type PmlaQualityCheck = {
  code: string
  title: string
  status: "ok" | "warning" | "critical"
  message: string
  details?: Record<string, unknown>
}

export type PmlaQualityReview = {
  overall_status: "ok" | "warning" | "critical"
  score: number
  checks: PmlaQualityCheck[]
  missing_required_data: string[]
  manual_review_required: string[]
  recommendations: string[]
}

export type PmlaGenerationResult = {
  // Успешная генерация (status: pending_review)
  document_id?: string
  questionnaire_id?: string
  facility_id?: string
  status: string
  version?: number
  source?: string
  context_quality?: Record<string, unknown>
  quality_review?: PmlaQualityReview | null
  debug_artifacts?: Record<string, string> | null
  // Заблокировано preflight (status: "blocked")
  reason?: string
  preflight?: Record<string, unknown>
  provenance?: Record<string, unknown>
}

export type PmlaPreflightResult = {
  questionnaire_id: string
  facility_id: string
  generation_mode: "draft" | "final"
  generation_blocked: boolean
  preflight: {
    status?: string
    issues?: Array<{ code?: string; message?: string; severity?: string }>
    missing_fields?: string[]
    has_blockers?: boolean
  }
}

export type PmlaDocumentListItem = {
  document_id: string
  version?: number
  status: string
  created_at?: string
  quality_score?: number
  quality_status?: "ok" | "warning" | "critical"
  download_available?: boolean
}

// Review Workflow (ручная проверка) — shape returned by /api/v1/pmla/{id}/review.
export type DocumentReviewWorkflow = {
  document_id: string
  review_status: string
  review_status_label: string
  review_comment?: string | null
  reviewed_by?: string | null
  reviewed_at?: string | null
  issued_at?: string | null
  allowed_transitions: string[]
}

export type ImportPreviewResult = {
  job?: { id: string; status: string; error_rows?: number; warning_rows?: number; created_rows?: number }
  rows?: Array<Record<string, unknown>>
  header_mapping?: Record<string, string>
}

// ── Organization types ──────────────────────────────────────────────────────

export type OrgType = "legal" | "individual";

export type Organization = {
  id: string;
  name: string;
  inn: string;
  ogrn: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  org_type: OrgType | null;
  full_name: string | null;
  short_name: string | null;
  legal_address: string | null;
  actual_address: string | null;
  postal_address: string | null;
  phone_additional: string | null;
  phone_mobile: string | null;
  fax: string | null;
  website: string | null;
  kpp: string | null;
  ogrnip: string | null;
  okpo: string | null;
  director_full_name: string | null;
  director_position: string | null;
  director_phone: string | null;
  director_email: string | null;
  ip_last_name: string | null;
  ip_first_name: string | null;
  ip_middle_name: string | null;
};

export type BankAccount = {
  id: string;
  organization_id: string;
  account_number: string;
  bank_name: string | null;
  bank_bik: string | null;
  bank_corr_account: string | null;
  is_primary: boolean;
  notes: string | null;
};

export type OkvedCode = {
  id: string;
  organization_id: string;
  code: string;
  is_primary: boolean;
};

export type License = {
  id: string;
  organization_id: string;
  activity_type: string;
  license_number: string;
  issue_date: string | null;
  status: string;
  file_name: string | null;
  file_size: number | null;
  mime_type: string | null;
  checksum_sha256: string | null;
  has_file: boolean;
};

export type OrganizationDetail = Organization & {
  bank_accounts: BankAccount[];
  okved_codes: OkvedCode[];
  licenses: License[];
};

/** PMLA template version selector */
export type PmlaTemplateVersion = "v1" | "v2";

export const isapApi = {
  health: () => apiRequest<{ status: string }>("/health"),

  // ── Organizations ──
  organizations: () => apiRequest<Organization[]>("/api/v1/organizations/"),
  createOrganization: (data: Record<string, unknown>) =>
    apiRequest<Organization>("/api/v1/organizations/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getOrganization: (id: string) =>
    apiRequest<Organization>(`/api/v1/organizations/${id}`),
  updateOrganization: (id: string, data: Record<string, unknown>) =>
    apiRequest<Organization>(`/api/v1/organizations/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteOrganization: (id: string) =>
    apiRequest<void>(`/api/v1/organizations/${id}`, { method: "DELETE" }),
  getOrganizationDetail: (id: string) =>
    apiRequest<OrganizationDetail>(`/api/v1/organizations/${id}/detail`),

  // ── Bank accounts ──
  listBankAccounts: (orgId: string) =>
    apiRequest<BankAccount[]>(`/api/v1/organizations/${orgId}/bank-accounts`),
  createBankAccount: (orgId: string, data: Record<string, unknown>) =>
    apiRequest<BankAccount>(`/api/v1/organizations/${orgId}/bank-accounts`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateBankAccount: (orgId: string, accountId: string, data: Record<string, unknown>) =>
    apiRequest<BankAccount>(`/api/v1/organizations/${orgId}/bank-accounts/${accountId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteBankAccount: (orgId: string, accountId: string) =>
    apiRequest<void>(`/api/v1/organizations/${orgId}/bank-accounts/${accountId}`, { method: "DELETE" }),

  // ── OKVED codes ──
  listOkvedCodes: (orgId: string) =>
    apiRequest<OkvedCode[]>(`/api/v1/organizations/${orgId}/okved-codes`),
  createOkvedCode: (orgId: string, data: Record<string, unknown>) =>
    apiRequest<OkvedCode>(`/api/v1/organizations/${orgId}/okved-codes`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateOkvedCode: (orgId: string, codeId: string, data: Record<string, unknown>) =>
    apiRequest<OkvedCode>(`/api/v1/organizations/${orgId}/okved-codes/${codeId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteOkvedCode: (orgId: string, codeId: string) =>
    apiRequest<void>(`/api/v1/organizations/${orgId}/okved-codes/${codeId}`, { method: "DELETE" }),

  // ── Licenses ──
  listLicenses: (orgId: string) =>
    apiRequest<License[]>(`/api/v1/organizations/${orgId}/licenses`),
  getLicense: (orgId: string, licenseId: string) =>
    apiRequest<License>(`/api/v1/organizations/${orgId}/licenses/${licenseId}`),
  createLicense: (orgId: string, data: Record<string, unknown>) =>
    apiRequest<License>(`/api/v1/organizations/${orgId}/licenses`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateLicense: (orgId: string, licenseId: string, data: Record<string, unknown>) =>
    apiRequest<License>(`/api/v1/organizations/${orgId}/licenses/${licenseId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteLicense: (orgId: string, licenseId: string) =>
    apiRequest<void>(`/api/v1/organizations/${orgId}/licenses/${licenseId}`, { method: "DELETE" }),
  uploadLicenseFile: (orgId: string, licenseId: string, file: File) =>
    apiUpload<License>(`/api/v1/organizations/${orgId}/licenses/${licenseId}/file`, file),
  deleteLicenseFile: (orgId: string, licenseId: string) =>
    apiRequest<License>(`/api/v1/organizations/${orgId}/licenses/${licenseId}/file`, { method: "DELETE" }),
  getLicenseDownloadUrl: (orgId: string, licenseId: string): string => {
    const path = `/api/v1/organizations/${orgId}/licenses/${licenseId}/download`;
    const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";
    return `${path}${API_KEY ? `?api_key=${API_KEY}` : ""}`;
  },

  // ── Facilities / ОПО ──
  facilities: () => apiRequest<Record<string, unknown>[]>("/api/v1/facilities/"),
  createFacility: (data: Record<string, unknown>) =>
    apiRequest<Record<string, unknown>>("/api/v1/facilities/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateFacility: (id: string, data: Record<string, unknown>) =>
    apiRequest<Record<string, unknown>>(`/api/v1/facilities/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteFacility: (id: string) =>
    apiRequest<unknown>(`/api/v1/facilities/${id}`, { method: "DELETE" }),
  getFacility: (id: string) =>
    apiRequest<Record<string, unknown>>(`/api/v1/facilities/${id}`),
  getFacilityFull: (id: string) =>
    apiRequest<Record<string, unknown>>(`/api/v1/facilities/${id}/full`),

  // ── Equipment / Оборудование ОПО ──
  equipment: (facilityId: string) =>
    apiRequest<Record<string, unknown>[]>(`/api/v1/equipment/?hazardous_facility_id=${facilityId}`),
  createEquipment: (data: Record<string, unknown>) =>
    apiRequest<Record<string, unknown>>("/api/v1/equipment/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateEquipment: (id: string, data: Record<string, unknown>) =>
    apiRequest<Record<string, unknown>>(`/api/v1/equipment/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteEquipment: (id: string) =>
    apiRequest<unknown>(`/api/v1/equipment/${id}`, { method: "DELETE" }),

  // ── Substances / Опасные вещества ОПО ──
  substances: (facilityId: string) =>
    apiRequest<Record<string, unknown>[]>(`/api/v1/substances/?hazardous_facility_id=${facilityId}`),
  createSubstance: (data: Record<string, unknown>) =>
    apiRequest<Record<string, unknown>>("/api/v1/substances/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateSubstance: (id: string, data: Record<string, unknown>) =>
    apiRequest<Record<string, unknown>>(`/api/v1/substances/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteSubstance: (id: string) =>
    apiRequest<unknown>(`/api/v1/substances/${id}`, { method: "DELETE" }),
  pmlaDocuments: () => apiRequest<unknown[]>("/api/v1/pmla/"),
  pmlaExpiring: (days = 30) => apiRequest<unknown[]>(`/api/v1/pmla/expiring?days=${days}`),
  aiConfig: () => apiRequest<Record<string, unknown>>("/api/v1/ai/config"),
  aiHealth: () => apiRequest<Record<string, unknown>>("/api/v1/ai/health"),
  embeddingsHealth: () => apiRequest<Record<string, unknown>>("/api/v1/ai/embeddings/health"),
  getPmlaQuestionnaireByFacility: (facilityId: string) =>
    apiRequest<PmlaQuestionnaire>(`/api/v1/pmla-questionnaires/facility/${facilityId}`),
  createPmlaQuestionnaire: (facilityId: string) =>
    apiRequest<PmlaQuestionnaire>(`/api/v1/pmla-questionnaires/facility/${facilityId}`, { method: "POST" }),
  getPmlaQuestionnaire: (questionnaireId: string) =>
    apiRequest<PmlaQuestionnaire>(`/api/v1/pmla-questionnaires/${questionnaireId}`),
  updatePmlaQuestionnaireBlock: (questionnaireId: string, blockName: string, data: unknown) =>
    apiRequest<PmlaQuestionnaire>(`/api/v1/pmla-questionnaires/${questionnaireId}/blocks/${blockName}`, {
      method: "PATCH",
      body: JSON.stringify({ data }),
    }),
  addCustomScenario: (questionnaireId: string, scenario: Record<string, unknown>) =>
    apiRequest<PmlaQuestionnaire>(`/api/v1/pmla-questionnaires/${questionnaireId}/custom-scenarios`, {
      method: "POST",
      body: JSON.stringify(scenario),
    }),
  deleteCustomScenario: (questionnaireId: string, index: number) =>
    apiRequest<PmlaQuestionnaire>(`/api/v1/pmla-questionnaires/${questionnaireId}/custom-scenarios/${index}`, {
      method: "DELETE",
    }),
  getPmlaQuestionnaireContext: (questionnaireId: string) =>
    apiRequest<Record<string, unknown>>(`/api/v1/pmla-questionnaires/${questionnaireId}/context`),
  preflightPmlaQuestionnaire: (questionnaireId: string) =>
    apiRequest<PmlaPreflightResult>(`/api/v1/pmla-questionnaires/${questionnaireId}/preflight?generation_mode=final`, {
      method: "POST",
    }),
  generatePmlaFromQuestionnaire: (
    questionnaireId: string,
    options: { template_version?: PmlaTemplateVersion; regenerate_sections?: string[] | null; save_debug_artifacts?: boolean } = {},
  ) =>
    apiRequest<PmlaGenerationResult>(`/api/v1/pmla-questionnaires/${questionnaireId}/generate`, {
      method: "POST",
      body: JSON.stringify({ template_version: "v1", regenerate_sections: null, save_debug_artifacts: true, ...options }),
    }),
  previewPmlaQuestionnaireImport: (file: File) =>
    apiUpload<ImportPreviewResult>("/api/v1/imports/pmla_questionnaire/preview", file),
  confirmImportJob: (jobId: string) =>
    apiRequest<Record<string, unknown>>(`/api/v1/imports/jobs/${jobId}/confirm`, { method: "POST" }),
  downloadPmlaDocument: (documentId: string): string =>
    `${toApiUrl(`/api/v1/pmla/${documentId}/download`)}${API_KEY ? `?api_key=${API_KEY}` : ""}`,
  downloadPmlaDocumentBlob: async (documentId: string): Promise<Blob> => {
    const url = toApiUrl(`/api/v1/pmla/${documentId}/download`)
    const response = await fetch(url, {
      headers: {
        ...(API_KEY ? { Authorization: `Bearer ${API_KEY}`, "X-API-Key": API_KEY } : {}),
      },
      cache: "no-store",
    })
    if (!response.ok) {
      let payload: ApiErrorPayload | null = null
      try { payload = await response.json() } catch { payload = null }
      throw new Error(payload?.detail || `Ошибка скачивания: ${response.status}`)
    }
    return response.blob()
  },
  getPmlaDocumentStatus: (documentId: string) =>
    apiRequest<Record<string, unknown>>(`/api/v1/pmla/${documentId}/status`),
  getPmlaDocumentPreview: (documentId: string) =>
    apiRequest<{ sections: Array<{ title: string; content: string }> }>(`/api/v1/pmla/${documentId}/preview`),
  getPmlaDocumentVersions: (documentId: string) =>
    apiRequest<Record<string, unknown>[]>(`/api/v1/pmla/${documentId}/versions`),
  reviewPmlaDocument: (documentId: string, action: "approve" | "reject", comment?: string) =>
    apiRequest<Record<string, unknown>>(`/api/v1/pmla/${documentId}/review`, {
      method: "POST",
      body: JSON.stringify({
        decision: action === "approve" ? "approved" : "rejected",
        reviewer_id: "ui-user",
        comments: comment ? [{ text: comment }] : [],
      }),
    }),

  // Review Workflow (ручная проверка)
  getDocumentReview: (documentId: string) =>
    apiRequest<DocumentReviewWorkflow>(`/api/v1/pmla/${documentId}/review`),
  updateDocumentReview: (documentId: string, data: { review_status: string; review_comment?: string; reviewed_by?: string }) =>
    apiRequest<DocumentReviewWorkflow>(`/api/v1/pmla/${documentId}/review`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  getAiReview: (documentId: string) =>
    apiRequest<Record<string, unknown>>(`/api/v1/pmla/${documentId}/ai-review`),
  runAiReview: (documentId: string) =>
    apiRequest<Record<string, unknown>>(`/api/v1/pmla/${documentId}/ai-review`, { method: "POST" }),
  getQuestionnaireDocuments: (questionnaireId: string) =>
    apiRequest<PmlaDocumentListItem[]>(`/api/v1/pmla-questionnaires/${questionnaireId}/documents`),

  // Directories: ПАСФ
  getPasfUnits: (search?: string) =>
    apiRequest<Record<string, unknown>[]>(`/api/v1/directories/pasf/${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  createPasfUnit: (data: Record<string, unknown>) =>
    apiRequest<Record<string, unknown>>("/api/v1/directories/pasf/", { method: "POST", body: JSON.stringify(data) }),
  updatePasfUnit: (id: string, data: Record<string, unknown>) =>
    apiRequest<Record<string, unknown>>(`/api/v1/directories/pasf/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deletePasfUnit: (id: string) =>
    apiRequest<Record<string, unknown>>(`/api/v1/directories/pasf/${id}`, { method: "DELETE" }),

  // Directories: Emergency services
  getEmergencyServices: (params?: { search?: string; service_type?: string }) => {
    const q = new URLSearchParams()
    if (params?.search) q.set("search", params.search)
    if (params?.service_type) q.set("service_type", params.service_type)
    const qs = q.toString()
    return apiRequest<Record<string, unknown>[]>(`/api/v1/directories/emergency-services/${qs ? `?${qs}` : ""}`)
  },
  createEmergencyService: (data: Record<string, unknown>) =>
    apiRequest<Record<string, unknown>>("/api/v1/directories/emergency-services/", { method: "POST", body: JSON.stringify(data) }),
  updateEmergencyService: (id: string, data: Record<string, unknown>) =>
    apiRequest<Record<string, unknown>>(`/api/v1/directories/emergency-services/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteEmergencyService: (id: string) =>
    apiRequest<Record<string, unknown>>(`/api/v1/directories/emergency-services/${id}`, { method: "DELETE" }),

  // Import
  previewImport: (importType: string, file: File) =>
    apiUpload<{ job: { id: string; status: string; error_rows?: number; created_rows?: number; updated_rows?: number }; rows: Array<Record<string, unknown>> }>(
      `/api/v1/imports/${importType}/preview`,
      file
    ),
}
