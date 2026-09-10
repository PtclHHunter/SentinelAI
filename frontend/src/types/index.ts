export type SeverityLevel = 'low' | 'medium' | 'high' | 'critical'
export type AlertStatus = 'new' | 'investigating' | 'resolved'
export type InvestigationStatus = 'open' | 'in_progress' | 'closed'
export type IOCType = 'ipv4' | 'domain' | 'url' | 'md5' | 'sha1' | 'sha256' | 'sha512'

export interface DashboardStats {
  total_events: number
  total_alerts: number
  critical_alerts: number
  total_investigations: number
  severity_breakdown: Record<SeverityLevel, number>
  recent_alerts_count: number
}

export interface ThreatTrendPoint {
  timestamp: string
  severity: string
  count: number
}

export interface SeverityDistribution {
  severity: string
  count: number
}

export interface IOCStats {
  total: number
  active: number
  by_type: Record<string, number>
}

export interface Alert {
  id: number
  event_id?: number
  rule_id: string
  title: string
  severity: SeverityLevel
  confidence: number
  evidence: string[]
  source_file: string
  source_event_id?: string
  timestamp: string
  recommendation: string
  status: AlertStatus
  metadata?: Record<string, unknown>
  created_at?: string
  updated_at?: string
}

export interface Event {
  id?: number
  source_file: string
  source_line?: number
  timestamp: string
  event_type: string
  severity: SeverityLevel
  message?: string
  raw_data?: Record<string, unknown>
  normalized_data?: Record<string, unknown>
}

export interface IOCRecord {
  id?: number
  ioc_type: IOCType
  value: string
  description?: string
  source?: string
  tags?: string[]
  is_active?: boolean
  created_at?: string
  updated_at?: string
}

export interface Investigation {
  id: number
  title: string
  description?: string
  severity: SeverityLevel
  status: InvestigationStatus
  created_at: string
  updated_at: string
  closed_at?: string
  created_by?: string
  assigned_to?: string
  alert_count: number
  evidence_count: number
  alerts?: Alert[]
  evidence?: Evidence[]
  timeline?: TimelineEntry[]
  notes?: Note[]
}

export interface Evidence {
  id: number
  investigation_id: number
  title: string
  description?: string
  evidence_type: string
  content?: Record<string, unknown>
  file_path?: string
  created_at: string
}

export interface TimelineEntry {
  id: number
  investigation_id: number
  timestamp: string
  event_type: string
  title: string
  description?: string
  metadata?: Record<string, unknown>
}

export interface Note {
  id: number
  investigation_id: number
  content: string
  created_by?: string
  created_at: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface HashResult {
  filename: string
  file_size: number
  md5: string
  sha1: string
  sha256: string
  sha512: string
  ioc_matches: IOCMatch[]
  scan_time_ms: number
}

export interface HashAnalyzeResult {
  input_hash: string
  detected_type: IOCType
  detected_algorithm: string
  ioc_matches: IOCMatch[]
  in_database: boolean
  scan_time_ms: number
}

export interface HashHistoryItem {
  id: number
  filename: string
  file_size: number
  sha256: string
  created_at: string
  ioc_matches_count: number
}

export interface ClearResultsResponse {
  message: string
  deleted_jobs?: number
  deleted_events: number
  deleted_alerts: number
}

export interface IOCMatch {
  ioc_type: IOCType
  value: string
  matched_ioc: IOCRecord
  context: string
}

export interface IOCScanResponse {
  extracted_iocs: Record<IOCType, string[]>
  matches: IOCMatch[]
  scan_time_ms: number
}

export interface Report {
  id: number
  investigation_id?: number
  alert_id?: number
  title: string
  format: 'pdf' | 'json' | 'csv'
  file_path: string
  file_size?: number
  generated_by?: string
  created_at: string
}

export interface SampleLogFile {
  filename: string
  size: number
  modified: string
  description?: string
}

export interface ParseResult {
  job_id: string
  filename: string
  total_lines: number
  parsed_events: number
  alerts_generated: number
  parse_errors: number
  events: Event[]
  alerts: Alert[]
}