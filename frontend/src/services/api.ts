import type { DashboardStats, Alert, PaginatedResponse, ThreatTrendPoint, SeverityDistribution, SampleLogFile, ParseResult, IOCRecord, IOCScanResponse, IOCStats, HashResult, HashAnalyzeResult, HashHistoryItem, Investigation, Report, ClearResultsResponse } from '../types'

const API_BASE = '/api'

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `API error: ${res.status}`)
  }
  return res.json()
}

// Dashboard
export const dashboardAPI = {
  getStats: () => fetchJSON<DashboardStats>('/dashboard/stats'),
  getRecentAlerts: (params?: { severity?: string; status?: string; hours?: number; page?: number; page_size?: number }) => {
    const q = new URLSearchParams()
    if (params?.severity) q.set('severity', params.severity)
    if (params?.status) q.set('status', params.status)
    if (params?.hours) q.set('hours', String(params.hours))
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    return fetchJSON<PaginatedResponse<Alert>>(`/dashboard/recent-alerts?${q}`)
  },
  getTrends: (hours?: number) => fetchJSON<ThreatTrendPoint[]>(`/dashboard/trends?hours=${hours || 24}`),
  getSeverityDistribution: () => fetchJSON<SeverityDistribution[]>('/dashboard/severity-distribution'),
}

// Log Analyzer
export const logsAPI = {
  listSamples: () => fetchJSON<SampleLogFile[]>('/logs/sample'),
  parseSample: (filename: string) => fetchJSON<{ job_id: string; filename: string; status: string; message: string }>(`/logs/parse-sample/${filename}`, { method: 'POST' }),
  getParseResult: (jobId: string) => fetchJSON<ParseResult>(`/logs/parse-result/${jobId}`),
  clearJob: (jobId: string) => fetchJSON<ClearResultsResponse>(`/logs/results/${jobId}`, { method: 'DELETE' }),
  clearAll: () => fetchJSON<ClearResultsResponse>('/logs/results', { method: 'DELETE' }),
  upload: async (file: File) => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${API_BASE}/logs/upload`, { method: 'POST', body: form })
    if (!res.ok) throw new Error('Upload failed')
    return res.json() as Promise<{ job_id: string; filename: string; status: string; message: string }>
  },
}

// IOC Scanner
export const iocAPI = {
  scan: (content: string) => fetchJSON<IOCScanResponse>('/ioc/scan', { method: 'POST', body: JSON.stringify({ content }) }),
  list: (params?: { ioc_type?: string; search?: string; page?: number; page_size?: number }) => {
    const q = new URLSearchParams()
    if (params?.ioc_type) q.set('ioc_type', params.ioc_type)
    if (params?.search) q.set('search', params.search)
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    return fetchJSON<PaginatedResponse<IOCRecord>>(`/ioc/database?${q}`)
  },
  create: (record: Omit<IOCRecord, 'id' | 'created_at' | 'updated_at'>) =>
    fetchJSON<IOCRecord>('/ioc/database', { method: 'POST', body: JSON.stringify(record) }),
  remove: (id: number) => fetchJSON(`/ioc/database/${id}`, { method: 'DELETE' }),
  getStats: () => fetchJSON<IOCStats>('/ioc/stats'),
}

// Hash Analyzer
export const hashAPI = {
  analyze: async (file: File) => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${API_BASE}/hash/analyze`, { method: 'POST', body: form })
    if (!res.ok) throw new Error('Analysis failed')
    return res.json() as Promise<HashResult>
  },
  analyzeHash: (hashValue: string) =>
    fetchJSON<HashAnalyzeResult>('/hash/analyze-hash', { method: 'POST', body: JSON.stringify({ hash_value: hashValue }) }),
  getHistory: () => fetchJSON<HashHistoryItem[]>('/hash/history'),
}

// Investigations
export const investigationsAPI = {
  list: (params?: { status?: string; severity?: string; search?: string; page?: number; page_size?: number }) => {
    const q = new URLSearchParams()
    if (params?.status) q.set('status', params.status)
    if (params?.severity) q.set('severity', params.severity)
    if (params?.search) q.set('search', params.search)
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    return fetchJSON<PaginatedResponse<Investigation>>(`/investigations?${q}`)
  },
  get: (id: number) => fetchJSON<Investigation>(`/investigations/${id}`),
  create: (data: { title: string; description?: string; severity?: string; alert_ids?: number[] }) =>
    fetchJSON<Investigation>('/investigations', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: { title?: string; description?: string; severity?: string; status?: string; assigned_to?: string }) =>
    fetchJSON<Investigation>(`/investigations/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  remove: (id: number) => fetchJSON(`/investigations/${id}`, { method: 'DELETE' }),
  addNote: (id: number, content: string) =>
    fetchJSON(`/investigations/${id}/notes`, { method: 'POST', body: JSON.stringify({ content }) }),
}

// Reports
export const reportsAPI = {
  generate: (data: { investigation_id?: number; alert_id?: number; format: string; title?: string }) =>
    fetchJSON<Report>('/reports/generate', { method: 'POST', body: JSON.stringify(data) }),
  list: (params?: { investigation_id?: number; format?: string; page?: number; page_size?: number }) => {
    const q = new URLSearchParams()
    if (params?.investigation_id) q.set('investigation_id', String(params.investigation_id))
    if (params?.format) q.set('format', params.format)
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    return fetchJSON<PaginatedResponse<Report>>(`/reports?${q}`)
  },
  downloadUrl: (id: number) => `${API_BASE}/reports/${id}/download`,
  remove: (id: number) => fetchJSON(`/reports/${id}`, { method: 'DELETE' }),
}