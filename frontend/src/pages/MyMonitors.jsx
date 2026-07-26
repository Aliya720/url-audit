/**
 * My Monitors / Admin Dashboard — SiteGuard Design Spec
 * Summary counters, search filter, domain list with state badges & response times
 */
import { useState, useEffect, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listMonitors } from '../api/client.js'
import ErrorBanner from '../components/ErrorBanner.jsx'
import './MyMonitors.css'

const STATE_CONFIG = {
  UP: { dot: 'state-dot-up', badge: 'badge-up', label: 'UP' },
  DOWN: { dot: 'state-dot-down', badge: 'badge-down', label: 'DOWN' },
  DEGRADED: { dot: 'state-dot-degraded', badge: 'badge-degraded', label: 'DEGRADED' },
  PENDING_FIRST_CHECK: { dot: 'state-dot-pending', badge: 'badge-pending', label: 'PENDING' },
}

function MyMonitors() {
  const [monitors, setMonitors] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    loadMonitors(true)
    const interval = setInterval(() => {
      loadMonitors(false)
    }, 10000)
    return () => clearInterval(interval)
  }, [])

  const loadMonitors = async (showLoading = false) => {
    if (showLoading) setLoading(true)
    setError(null)
    try {
      const result = await listMonitors()
      setMonitors(result.data || [])
    } catch (err) {
      if (showLoading) setError(err)
    } finally {
      if (showLoading) setLoading(false)
    }
  }

  const formatLastChecked = (dateStr) => {
    if (!dateStr) return 'never'
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now - date
    const diffMin = Math.floor(diffMs / 60000)
    if (diffMin < 1) return 'just now'
    if (diffMin < 60) return `${diffMin} min ago`
    const diffHr = Math.floor(diffMin / 60)
    if (diffHr < 24) return `${diffHr}h ago`
    return `${Math.floor(diffHr / 24)}d ago`
  }

  const filteredMonitors = useMemo(() => {
    if (!searchQuery.trim()) return monitors
    const query = searchQuery.toLowerCase()
    return monitors.filter((m) => m.url.toLowerCase().includes(query))
  }, [monitors, searchQuery])

  // Summary Metrics
  const upCount = monitors.filter((m) => m.state === 'UP').length
  const alertCount = monitors.filter((m) => m.state === 'DOWN' || m.state === 'DEGRADED').length

  if (loading) {
    return (
      <div className="monitors-page animate-fade-in" id="monitors-page">
        <div className="monitors-header">
          <div>
            <h1 className="font-display-lg">Dashboard Overview</h1>
            <p className="font-body-sm text-on-surface-variant">Loading real-time monitors…</p>
          </div>
        </div>
        <div className="summary-grid">
          <div className="skeleton" style={{ height: 110 }}></div>
          <div className="skeleton" style={{ height: 110 }}></div>
          <div className="skeleton" style={{ height: 110 }}></div>
        </div>
        <div className="monitors-list-container" style={{ marginTop: 24 }}>
          <div className="skeleton" style={{ height: 60, marginBottom: 12 }}></div>
          <div className="skeleton" style={{ height: 60, marginBottom: 12 }}></div>
          <div className="skeleton" style={{ height: 60 }}></div>
        </div>
      </div>
    )
  }

  return (
    <div className="monitors-page animate-fade-in" id="monitors-page">
      {/* Top Header Section */}
      <div className="monitors-header">
        <div>
          <h1 className="font-display-lg text-on-surface">Dashboard Overview</h1>
          <p className="font-body-base text-on-surface-variant">
            Monitoring {monitors.length} {monitors.length === 1 ? 'domain' : 'domains'} in real-time.
          </p>
        </div>
        <div className="header-actions">
          <Link to="/monitors/new" className="btn btn-primary" id="add-monitor-btn">
            <span className="material-symbols-outlined text-sm">add</span>
            <span>Add New Monitor</span>
          </Link>
        </div>
      </div>

      {error && <ErrorBanner error={error} />}

      {/* Top Row Summary Cards */}
      <div className="summary-grid">
        <div className="summary-card glass-card">
          <div className="summary-card-header">
            <span className="font-label-caps text-outline">TOTAL MONITORS</span>
            <span className="material-symbols-outlined text-primary">language</span>
          </div>
          <div className="summary-card-body">
            <span className="font-display-lg text-on-surface">{monitors.length}</span>
            <span className="font-body-sm text-secondary font-bold">Active checks</span>
          </div>
        </div>

        <div className="summary-card glass-card">
          <div className="summary-card-header">
            <span className="font-label-caps text-outline">SYSTEM HEALTH</span>
            <span className="material-symbols-outlined text-primary">health_and_safety</span>
          </div>
          <div className="summary-card-body">
            <span className="font-display-lg text-on-surface">
              {monitors.length > 0 ? `${Math.round((upCount / monitors.length) * 100)}%` : '100%'}
            </span>
            <span className="font-body-sm text-on-surface-variant">UP status</span>
          </div>
        </div>

        <div className="summary-card glass-card">
          <div className="summary-card-header">
            <span className="font-label-caps text-outline font-bold">ACTIVE ALERTS</span>
            <span className={`material-symbols-outlined ${alertCount > 0 ? 'text-error' : 'text-primary'}`}>
              notifications_active
            </span>
          </div>
          <div className="summary-card-body">
            <span className={`font-display-lg ${alertCount > 0 ? 'text-error' : 'text-on-surface'}`}>
              {alertCount}
            </span>
            <span className="font-body-sm text-on-surface-variant">Requires review</span>
          </div>
        </div>
      </div>

      {monitors.length === 0 ? (
        <div className="empty-state-card" id="monitors-empty">
          <div className="empty-icon-box">
            <span className="material-symbols-outlined text-primary">speed</span>
          </div>
          <h2 className="font-headline-md mb-2">No monitors registered yet</h2>
          <p className="font-body-sm text-on-surface-variant mb-6" style={{ maxWidth: 460 }}>
            Monitors are saved locally to this browser session. Clear browser data will remove saved monitor references.
          </p>
          <Link to="/monitors/new" className="btn btn-primary" id="first-monitor-btn">
            <span className="material-symbols-outlined text-sm">add</span>
            <span>Register your first monitor</span>
          </Link>
        </div>
      ) : (
        <div className="monitors-list-section">
          {/* Search & Filter bar */}
          <div className="monitors-filter-bar">
            <div className="search-input-wrapper">
              <span className="material-symbols-outlined text-outline">search</span>
              <input
                type="text"
                placeholder="Search domain or URL…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="search-input"
              />
            </div>
            <span className="font-body-sm text-on-surface-variant">
              Showing {filteredMonitors.length} of {monitors.length}
            </span>
          </div>

          {/* Monitors Table / Row List */}
          <div className="monitors-table-card" id="monitors-list">
            <div className="table-header-row">
              <span>TARGET DOMAIN / URL</span>
              <span>STATUS</span>
              <span>CHECK INTERVAL</span>
              <span>LAST CHECKED</span>
              <span>ACTION</span>
            </div>

            {filteredMonitors.map((monitor) => {
              const cfg = STATE_CONFIG[monitor.state] || STATE_CONFIG.PENDING_FIRST_CHECK
              const hostname = extractHostname(monitor.url)

              return (
                <div
                  key={monitor.monitor_id}
                  className="table-data-row"
                  onClick={() => navigate(`/monitors/${monitor.monitor_id}`)}
                  id={`monitor-${monitor.monitor_id}`}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && navigate(`/monitors/${monitor.monitor_id}`)}
                >
                  <div className="row-domain-cell">
                    <span className="material-symbols-outlined domain-icon">public</span>
                    <div>
                      <div className="domain-hostname">{hostname}</div>
                      <div className="domain-full-url font-mono-data">{monitor.url}</div>
                    </div>
                  </div>

                  <div className="row-status-cell">
                    <span className={`badge ${cfg.badge}`}>
                      <span className={`state-dot ${cfg.dot}`}></span>
                      {cfg.label}
                    </span>
                  </div>

                  <div className="row-interval-cell font-body-sm text-on-surface-variant">
                    {formatInterval(monitor.interval_seconds)}
                  </div>

                  <div className="row-time-cell font-mono-data">
                    {formatLastChecked(monitor.last_checked_at)}
                  </div>

                  <div className="row-action-cell">
                    <span className="btn btn-ghost btn-sm">
                      <span>View</span>
                      <span className="material-symbols-outlined text-sm">chevron_right</span>
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

function extractHostname(url) {
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

function formatInterval(seconds) {
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`
  return `${Math.round(seconds / 3600)}h`
}

export default MyMonitors
