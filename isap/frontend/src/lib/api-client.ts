export type ApiErrorPayload = {
  detail?: string
  message?: string
  error?: string
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || ""

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`
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
  const response = await fetch(`${API_BASE_URL}${path}`, {
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
  document_id: string
  questionnaire_id: string
  facility_id: string
  status: string
  version?: number
  source?: string
  context_quality?: Record<string, unknown>
  quality_review?: PmlaQualityReview | null
  debug_artifacts?: Record<string, string> | null
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

export type ImportPreviewResult = {
  job?: { id: string; status: string; error_rows?: number; warning_rows?: number; created_rows?: number }
  rows?: Array<Record<string, unknown>>
  header_mapping?: Record<string, string>
}

export const isapApi = {
  health: () => apiRequest<{ status: string }>("/health"),
  organizations: () => apiRequest<unknown[]>("/api/v1/organizations/"),
  facilities: () => apiRequest<unknown[]>("/api/v1/facilities/"),
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
  generatePmlaFromQuestionnaire: (
    questionnaireId: string,
    options: { regenerate_sections?: string[] | null; save_debug_artifacts?: boolean } = {},
  ) =>
    apiRequest<PmlaGenerationResult>(`/api/v1/pmla-questionnaires/${questionnaireId}/generate`, {
      method: "POST",
      body: JSON.stringify({ regenerate_sections: null, save_debug_artifacts: true, ...options }),
    }),
  previewPmlaQuestionnaireImport: (file: File) =>
    apiUpload<ImportPreviewResult>("/api/v1/imports/pmla_questionnaire/preview", file),
  confirmImportJob: (jobId: string) =>
    apiRequest<Record<string, unknown>>(`/api/v1/imports/jobs/${jobId}/confirm`, { method: "POST" }),
  downloadPmlaDocument: (documentId: string): string =>
    `${API_BASE_URL}/api/v1/pmla/${documentId}/download${API_KEY ? `?api_key=${API_KEY}` : ""}`,
  downloadPmlaDocumentBlob: async (documentId: string): Promise<Blob> => {
    const url = `${API_BASE_URL}/api/v1/pmla/${documentId}/download`
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
    apiRequest<unknown[]>(`/api/v1/pmla/${documentId}/versions`),
  reviewPmlaDocument: (documentId: string, action: "approve" | "reject", comment?: string) =>
    apiRequest<Record<string, unknown>>(`/api/v1/pmla/${documentId}/review`, {
      method: "POST",
      body: JSON.stringify({ action, reviewer_id: "ui-user", comment: comment || "" }),
    }),
  getAiReview: (documentId: string) =>
    apiRequest<Record<string, unknown>>(`/api/v1/pmla/${documentId}/ai-review`),
  runAiReview: (documentId: string) =>
    apiRequest<Record<string, unknown>>(`/api/v1/pmla/${documentId}/ai-review`, { method: "POST" }),
  getQuestionnaireDocuments: (questionnaireId: string) =>
    apiRequest<PmlaDocumentListItem[]>(`/api/v1/pmla-questionnaires/${questionnaireId}/documents`),

  // Directories: ПАСФ
  getPasfUnits: (search?: string) =>
    apiRequest<unknown[]>(`/api/v1/directories/pasf${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  createPasfUnit: (data: Record<string, unknown>) =>
    apiRequest<Record<string, unknown>>("/api/v1/directories/pasf", { method: "POST", body: JSON.stringify(data) }),
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
    return apiRequest<unknown[]>(`/api/v1/directories/emergency-services${qs ? `?${qs}` : ""}`)
  },
  createEmergencyService: (data: Record<string, unknown>) =>
    apiRequest<Record<string, unknown>>("/api/v1/directories/emergency-services", { method: "POST", body: JSON.stringify(data) }),
  updateEmergencyService: (id: string, data: Record<string, unknown>) =>
    apiRequest<Record<string, unknown>>(`/api/v1/directories/emergency-services/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteEmergencyService: (id: string) =>
    apiRequest<Record<string, unknown>>(`/api/v1/directories/emergency-services/${id}`, { method: "DELETE" }),
}
