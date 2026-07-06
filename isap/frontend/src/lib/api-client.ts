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

export const isapApi = {
  health: () => apiRequest<{ status: string }>("/health"),
  organizations: () => apiRequest<unknown[]>("/api/v1/organizations/"),
  facilities: () => apiRequest<unknown[]>("/api/v1/facilities/"),
  pmlaDocuments: () => apiRequest<unknown[]>("/api/v1/pmla/"),
  pmlaExpiring: (days = 30) => apiRequest<unknown[]>(`/api/v1/pmla/expiring?days=${days}`),
  aiConfig: () => apiRequest<Record<string, unknown>>("/api/v1/ai/config"),
  aiHealth: () => apiRequest<Record<string, unknown>>("/api/v1/ai/health"),
  embeddingsHealth: () => apiRequest<Record<string, unknown>>("/api/v1/ai/embeddings/health"),
}
