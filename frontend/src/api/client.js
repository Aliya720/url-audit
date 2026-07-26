/**
 * API Client — App Flow §0.1
 * Handles X-Client-Key generation/storage and all API calls.
 */

const CLIENT_KEY_STORAGE = 'pulsewatch_client_key'
const API_BASE = '/url-audit-project'

/**
 * Generate and store a client key on first visit (App Flow §0.1).
 * Uses crypto.randomUUID() for UUID generation.
 */
export function ensureClientKey() {
  let key = localStorage.getItem(CLIENT_KEY_STORAGE)
  if (!key) {
    key = crypto.randomUUID()
    localStorage.setItem(CLIENT_KEY_STORAGE, key)
  }
  return key
}

function getClientKey() {
  return localStorage.getItem(CLIENT_KEY_STORAGE) || ensureClientKey()
}

/**
 * Base API fetch wrapper.
 * Adds X-Client-Key header to every request (App Flow §0.1).
 */
async function apiFetch(url, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    'X-Client-Key': getClientKey(),
    ...(options.headers || {}),
  }

  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers,
  })

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    const error = new Error(data?.error?.message || 'An unexpected error occurred.')
    error.code = data?.error?.code || 'INTERNAL_ERROR'
    error.status = response.status
    error.retryAfter = response.headers.get('Retry-After')
    error.requestId = data?.request_id
    throw error
  }

  return data
}

// ---- Audit API (TRD §4.1, §4.2) ----

export async function runAudit(url) {
  return apiFetch('/api/audits', {
    method: 'POST',
    body: JSON.stringify({ url }),
  })
}

export async function getAudit(auditId) {
  return apiFetch(`/api/audits/${auditId}`)
}

// ---- Monitor API (TRD §4.4–§4.7) ----

export async function createMonitor({ url, interval_seconds, webhook_url, latency_threshold_ms }) {
  return apiFetch('/api/monitors', {
    method: 'POST',
    body: JSON.stringify({ url, interval_seconds, webhook_url, latency_threshold_ms }),
  })
}

export async function listMonitors() {
  return apiFetch('/api/monitors')
}

export async function getAlerts() {
  return apiFetch('/api/monitors/alerts')
}

export async function getMonitor(monitorId) {
  return apiFetch(`/api/monitors/${monitorId}`)
}

export async function getMonitorHistory(monitorId, limit = 50) {
  return apiFetch(`/api/monitors/${monitorId}/history?limit=${limit}`)
}

export async function deleteMonitor(monitorId) {
  const headers = {
    'X-Client-Key': getClientKey(),
  }
  const response = await fetch(`${API_BASE}/api/monitors/${monitorId}`, {
    method: 'DELETE',
    headers,
  })

  if (!response.ok && response.status !== 204) {
    const data = await response.json().catch(() => null)
    const error = new Error(data?.error?.message || 'Failed to delete monitor.')
    error.code = data?.error?.code || 'INTERNAL_ERROR'
    error.status = response.status
    throw error
  }

  return true
}

// ---- Health API (TRD §4.3) ----

export async function getHealth() {
  return apiFetch('/api/health')
}
