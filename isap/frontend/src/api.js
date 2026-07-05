const API_BASE = import.meta.env.VITE_API_URL || '';

function getApiKey() {
  return localStorage.getItem('isap_api_key') || '';
}

function authHeaders(extra = {}) {
  const apiKey = getApiKey();
  return {
    ...extra,
    ...(apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {}),
  };
}

async function request(url, options = {}) {
  const { headers: customHeaders, body, ...restOptions } = options;
  const isFormData = body instanceof FormData;
  const defaultHeaders = isFormData ? {} : { 'Content-Type': 'application/json' };
  const response = await fetch(`${API_BASE}${url}`, {
    ...restOptions,
    body,
    headers: authHeaders({ ...defaultHeaders, ...customHeaders }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(err.detail || `HTTP ${response.status}`);
  }
  if (response.status === 204) return null;
  return response.json();
}

async function requestBlob(url, options = {}) {
  const { headers: customHeaders, body, ...restOptions } = options;
  const response = await fetch(`${API_BASE}${url}`, {
    ...restOptions,
    body,
    headers: authHeaders({ ...customHeaders }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(err.detail || `HTTP ${response.status}`);
  }
  return response.blob();
}

// ===== Organizations =====
export const organizationsApi = {
  list: (skip = 0, limit = 100) => request(`/api/v1/organizations/?skip=${skip}&limit=${limit}`),
  get: (id) => request(`/api/v1/organizations/${id}`),
  create: (data) => request('/api/v1/organizations/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/api/v1/organizations/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id) => request(`/api/v1/organizations/${id}`, { method: 'DELETE' }),
};

// ===== Facilities =====
export const facilitiesApi = {
  list: (organizationId = null, skip = 0, limit = 100) => {
    const params = new URLSearchParams({ skip, limit });
    if (organizationId) params.append('organization_id', organizationId);
    return request(`/api/v1/facilities/?${params}`);
  },
  get: (id) => request(`/api/v1/facilities/${id}`),
  getFull: (id) => request(`/api/v1/facilities/${id}/full`),
  create: (data) => request('/api/v1/facilities/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/api/v1/facilities/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id) => request(`/api/v1/facilities/${id}`, { method: 'DELETE' }),
};

export const facilityTypesApi = {
  list: () => request('/api/v1/facility-types/'),
};

export const facilitiesWordApi = {
  importWord: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return request('/api/v1/facilities/import-word', { method: 'POST', body: formData });
  },
};

// ===== OPO Details =====
export const opoDetailsApi = {
  get: (facilityId) => request(`/api/v1/facilities/${facilityId}/details`),
  save: (facilityId, data) => request(`/api/v1/facilities/${facilityId}/details`, { method: 'POST', body: JSON.stringify({ form_data: data }) }),
  exportDocx: (facilityId) => requestBlob(`/api/v1/facilities/${facilityId}/export/docx`),
  exportPdf: (facilityId) => requestBlob(`/api/v1/facilities/${facilityId}/export/pdf`),
};

// ===== Equipment =====
export const equipmentApi = {
  list: (facilityId = null, skip = 0, limit = 100) => {
    const params = new URLSearchParams({ skip, limit });
    if (facilityId) params.append('hazardous_facility_id', facilityId);
    return request(`/api/v1/equipment/?${params}`);
  },
  get: (id) => request(`/api/v1/equipment/${id}`),
  create: (data) => request('/api/v1/equipment/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/api/v1/equipment/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id) => request(`/api/v1/equipment/${id}`, { method: 'DELETE' }),
};

// ===== Substances =====
export const substancesApi = {
  list: (facilityId = null, skip = 0, limit = 100) => {
    const params = new URLSearchParams({ skip, limit });
    if (facilityId) params.append('hazardous_facility_id', facilityId);
    return request(`/api/v1/substances/?${params}`);
  },
  get: (id) => request(`/api/v1/substances/${id}`),
  create: (data) => request('/api/v1/substances/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/api/v1/substances/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id) => request(`/api/v1/substances/${id}`, { method: 'DELETE' }),
};

// ===== Persons =====
export const personsApi = {
  list: (organizationId = null, skip = 0, limit = 100) => {
    const params = new URLSearchParams({ skip, limit });
    if (organizationId) params.append('organization_id', organizationId);
    return request(`/api/v1/persons/?${params}`);
  },
  get: (id) => request(`/api/v1/persons/${id}`),
  create: (data) => request('/api/v1/persons/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/api/v1/persons/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id) => request(`/api/v1/persons/${id}`, { method: 'DELETE' }),
};

// ===== PMLA =====
export const pmlaApi = {
  list: () => request('/api/v1/pmla/'),

  generate: (facilityId, context = null, regenerateSections = null) => {
    const body = { facility_id: facilityId };
    if (context) body.context = context;
    if (regenerateSections) body.regenerate_sections = regenerateSections;
    return request('/api/v1/pmla/generate', { method: 'POST', body: JSON.stringify(body) });
  },

  getStatus: (documentId) => request(`/api/v1/pmla/${documentId}/status`),

  review: (documentId, reviewerId, decision, comments = []) =>
    request(`/api/v1/pmla/${documentId}/review`, {
      method: 'POST',
      body: JSON.stringify({ reviewer_id: reviewerId, decision, comments }),
    }),

  download: (documentId) => requestBlob(`/api/v1/pmla/${documentId}/download`),
  downloadPdf: (documentId) => requestBlob(`/api/v1/pmla/${documentId}/download/pdf`),
  preview: (documentId) => request(`/api/v1/pmla/${documentId}/preview`),

  regenerate: (documentId, sections) =>
    request(`/api/v1/pmla/${documentId}/regenerate`, {
      method: 'POST',
      body: JSON.stringify({ sections }),
    }),

  restoreVersion: (documentId, versionId) =>
    request(`/api/v1/pmla/${documentId}/restore/${versionId}`, { method: 'POST' }),

  aiReview: (documentId) => request(`/api/v1/pmla/${documentId}/ai-review`),
  versions: (documentId) => request(`/api/v1/pmla/${documentId}/versions`),
  listMethods: () => request('/api/v1/pmla/methods/list'),
  expiring: (days = 90) => request(`/api/v1/pmla/expiring?days=${days}`),
  overdue: () => request('/api/v1/pmla/overdue'),
};

// ===== Regulatory =====
export const regulatoryApi = {
  list: (category = null, status = null) => {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (status) params.append('status', status);
    return request(`/api/v1/regulatory/?${params}`);
  },
  get: (id) => request(`/api/v1/regulatory/${id}`),
  create: (data) => request('/api/v1/regulatory/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/api/v1/regulatory/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id) => request(`/api/v1/regulatory/${id}`, { method: 'DELETE' }),
};

// ===== PMLA Samples =====
export const pmlaSamplesApi = {
  list: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.facility_type) params.append('facility_type', filters.facility_type);
    if (filters.hazard_class) params.append('hazard_class', filters.hazard_class);
    const qs = params.toString();
    return request(`/api/v1/pmla-samples/${qs ? '?' + qs : ''}`);
  },
  get: (id) => request(`/api/v1/pmla-samples/${id}`),
  preview: (id) => request(`/api/v1/pmla-samples/${id}/preview`),
  upload: (formData) => request('/api/v1/pmla-samples/upload', { method: 'POST', body: formData }),
  download: (id) => requestBlob(`/api/v1/pmla-samples/${id}/download`),
  verify: (id, isVerified = true) => request(`/api/v1/pmla-samples/${id}/verify?is_verified=${isVerified}`, { method: 'PUT' }),
  delete: (id) => request(`/api/v1/pmla-samples/${id}`, { method: 'DELETE' }),
};
