/**
 * Monitor Detail + History screen — SiteGuard Monitor Detail Spec
 * Current state card, check frequency metadata, check history table, and delete monitor action
 */
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getMonitor, getMonitorHistory, deleteMonitor } from '../api/client.js'
import ErrorBanner from '../components/ErrorBanner.jsx'
import './MonitorDetail.css'

const STATE_CONFIG = {
  UP: { dot: 'state-dot-up', badge: 'badge-up', label: 'UP' },
  DOWN: { dot: 'state-dot-down', badge: 'badge-down', label: 'DOWN' },
  DEGRADED: { dot: 'state-dot-degraded', badge: 'badge-degraded', label: 'DEGRADED' },
  PENDING_FIRST_CHECK: { dot: 'state-dot-pending', badge: 'badge-pending', label: 'PENDING' },
}

function MonitorDetail() {
  const { monitorId } = useParams()
  const navigate = useNavigate()
  const [monitor, setMonitor] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    loadData(true)
    const interval = setInterval(() => {
      loadData(false)
    }, 10000)
    return () => clearInterval(interval)
  }, [monitorId])

  const loadData = async (showLoading = false) => {
    if (showLoading) setLoading(true)
    setError(null)
    try {
      const [monitorRes, historyRes] = await Promise.all([
        getMonitor(monitorId),
        getMonitorHistory(monitorId),
      ])
      setMonitor(monitorRes.data)
      setHistory(historyRes.data?.checks || [])
    } catch (err) {
      if (showLoading) setError(err)
    } finally {
      if (showLoading) setLoading(false)
    }
  }

  const handleDelete = async () => {
    const hostname = extractHostname(monitor?.url)
    if (!window.confirm(`Stop monitoring ${hostname}? This action cannot be undone.`)) return

    setDeleting(true)
    try {
      await deleteMonitor(monitorId)
      navigate('/monitors')
    } catch (err) {
      setError(err)
      setDeleting(false)
    }
  }

  const formatInterval = (seconds) => {
    if (seconds < 60) return `${seconds}s`
    if (seconds < 3600) return `${Math.round(seconds / 60)} min`
    return `${Math.round(seconds / 3600)}h`
  }

  const formatTime = (dateStr) => {
    if (!dateStr) return '—'
    return new Date(dateStr).toLocaleString('en-US', {
      hour: '2-digit', minute: '2-digit', second: '2-digit', timeZoneName: 'short',
    })
  }

  if (loading) {
    return (
      <div className="monitor-detail-page animate-fade-in" id="monitor-detail-page">
        <div className="skeleton" style={{ height: 40, width: '30%', marginBottom: 20 }}></div>
        <div className="skeleton" style={{ height: 160, marginBottom: 24 }}></div>
        <div className="skeleton" style={{ height: 300 }}></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="monitor-detail-page animate-fade-in" id="monitor-detail-page">
        <ErrorBanner error={error} />
        <button className="btn btn-ghost" onClick={() => navigate('/monitors')} style={{ marginTop: 16 }}>
          <span className="material-symbols-outlined text-sm">arrow_back</span>
          <span>Back to My Monitors</span>
        </button>
      </div>
    )
  }

  if (!monitor) return null

  const cfg = STATE_CONFIG[monitor.state] || STATE_CONFIG.PENDING_FIRST_CHECK
  const hostname = extractHostname(monitor.url)

  return (
    <div className="monitor-detail-page animate-fade-in" id="monitor-detail-page">
      {/* Back Button */}
      <div className="detail-top-nav">
        <button className="btn btn-ghost" onClick={() => navigate('/monitors')} id="detail-back-btn">
          <span className="material-symbols-outlined text-sm">arrow_back</span>
          <span>My Monitors</span>
        </button>
      </div>

      {/* Main Target Header Card */}
      <div className="detail-header-card card">
        <div className="detail-header-left">
          <div className="domain-title-row">
            <span className="material-symbols-outlined text-primary text-2xl">public</span>
            <h1 className="detail-hostname" id="detail-hostname">{hostname}</h1>
          </div>
          <div className="detail-full-url font-mono-data">{monitor.url}</div>

          <div className="detail-meta-list font-body-sm text-on-surface-variant">
            <span>
              <span className="material-symbols-outlined text-xs">timer</span>
              Every {formatInterval(monitor.interval_seconds)}
            </span>
            <span>•</span>
            <span>
              <span className="material-symbols-outlined text-xs">schedule</span>
              Last check: {formatTime(monitor.last_checked_at)}
            </span>
            {monitor.webhook_url && (
              <>
                <span>•</span>
                <span className="font-mono-data text-xs" title={`Webhook: ${monitor.webhook_url}`}>
                  <span className="material-symbols-outlined text-xs">webhook</span> Webhook Active
                </span>
              </>
            )}
          </div>
        </div>

        <div className="detail-header-right">
          <span className={`badge ${cfg.badge} detail-state-badge`} id="detail-state-badge">
            <span className={`state-dot ${cfg.dot}`}></span>
            {cfg.label}
          </span>
          <button
            className="btn btn-danger"
            onClick={handleDelete}
            disabled={deleting}
            id="delete-monitor-btn"
          >
            <span className="material-symbols-outlined text-sm">delete</span>
            <span>{deleting ? 'Deleting…' : 'Delete Monitor'}</span>
          </button>
        </div>
      </div>

      {/* Check History Logs Table */}
      <div className="detail-history-card card">
        <div className="history-header">
          <h2 className="font-headline-md text-on-surface">Check History Log</h2>
          <span className="font-body-sm text-on-surface-variant">Showing latest checks</span>
        </div>

        {history.length === 0 ? (
          <div className="history-empty text-center py-8 text-on-surface-variant">
            <span className="material-symbols-outlined text-3xl mb-2">hourglass_top</span>
            <p>No checks recorded yet — initial check scheduled to run shortly.</p>
          </div>
        ) : (
          <div className="history-table-wrapper" id="history-list">
            <div className="history-table-header">
              <span>CHECK TIMESTAMP</span>
              <span>STATE</span>
              <span>HTTP STATUS</span>
              <span>RESPONSE SPEED</span>
              <span>DIAGNOSTIC CODE</span>
            </div>

            {history.map((check, idx) => {
              const checkCfg = STATE_CONFIG[check.state] || STATE_CONFIG.PENDING_FIRST_CHECK
              return (
                <div key={idx} className="history-table-row">
                  <div className="history-time font-mono-data">{formatTime(check.checked_at)}</div>
                  <div>
                    <span className={`badge ${checkCfg.badge}`}>
                      <span className={`state-dot ${checkCfg.dot}`}></span>
                      {checkCfg.label}
                    </span>
                  </div>
                  <div className="font-mono-data">
                    {check.status_code ? (
                      <span className="status-code-tag">{check.status_code}</span>
                    ) : (
                      '—'
                    )}
                  </div>
                  <div className="font-mono-data">
                    {check.response_time_ms != null ? `${check.response_time_ms} ms` : '—'}
                  </div>
                  <div className="font-mono-data text-error font-body-sm">
                    {check.error_code || '—'}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
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

export default MonitorDetail
