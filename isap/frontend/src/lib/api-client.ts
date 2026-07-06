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

export type PmlaGenerationResult = {
  document_id: string
  questionnaire_id: string
  facility_id: string
  status: string
  version: number
  context_quality: Record<string, unknown>
  debug_artifacts?: Record<string, string> | null
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
}
