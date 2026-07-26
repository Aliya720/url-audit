/**
 * Register a Monitor screen — SiteGuard Design Spec
 * Target URL, interval selector pills, webhook endpoint, latency threshold
 */
import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { createMonitor } from '../api/client.js'
import ErrorBanner from '../components/ErrorBanner.jsx'
import './RegisterMonitor.css'

const INTERVAL_OPTIONS = [
  { label: '1 min', value: 60 },
  { label: '5 min', value: 300 },
  { label: '15 min', value: 900 },
  { label: '30 min', value: 1800 },
  { label: '60 min', value: 3600 },
]

function RegisterMonitor() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const [url, setUrl] = useState(searchParams.get('url') || '')
  const [intervalSeconds, setIntervalSeconds] = useState(300)
  const [webhookUrl, setWebhookUrl] = useState('')
  const [latencyThreshold, setLatencyThreshold] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      await createMonitor({
        url: url.trim(),
        interval_seconds: intervalSeconds,
        webhook_url: webhookUrl.trim(),
        latency_threshold_ms: latencyThreshold ? parseInt(latencyThreshold, 10) : null,
      })
      navigate('/monitors')
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="register-monitor-page animate-fade-in" id="register-monitor-page">
      <div className="register-header">
        <button className="btn btn-ghost" onClick={() => navigate('/monitors')} style={{ marginBottom: 16 }}>
          <span className="material-symbols-outlined text-sm">arrow_back</span>
          <span>Back to Monitors</span>
        </button>
        <h1 className="font-display-lg text-on-surface">Watch a website continuously</h1>
        <p className="font-body-base text-on-surface-variant">
          Register a URL for scheduled health checks with webhook alerts on state changes.
        </p>
      </div>

      <div className="register-form-card card">
        <form onSubmit={handleSubmit} className="monitor-form" id="monitor-form">
          {/* Target URL */}
          <div className="input-group">
            <label htmlFor="monitor-url">Target Website URL *</label>
            <div className="input-with-icon">
              <span className="material-symbols-outlined input-prefix">language</span>
              <input
                id="monitor-url"
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com"
                required
                disabled={loading}
              />
            </div>
          </div>

          {/* Check Interval */}
          <div className="input-group">
            <label htmlFor="monitor-interval">Check Frequency *</label>
            <div className="interval-pills">
              {INTERVAL_OPTIONS.map((opt) => (
                <button
                  type="button"
                  key={opt.value}
                  className={`pill-btn ${intervalSeconds === opt.value ? 'pill-active' : ''}`}
                  onClick={() => setIntervalSeconds(opt.value)}
                  disabled={loading}
                >
                  <span className="material-symbols-outlined text-sm">timer</span>
                  <span>{opt.label}</span>
                </button>
              ))}
            </div>
            <span className="input-hint">Minimum interval floor: 1 minute (60s)</span>
          </div>

          {/* Webhook Endpoint */}
          <div className="input-group">
            <label htmlFor="monitor-webhook">Alert Webhook Endpoint URL *</label>
            <div className="input-with-icon">
              <span className="material-symbols-outlined input-prefix">webhook</span>
              <input
                id="monitor-webhook"
                type="url"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                placeholder="https://your-endpoint.example/webhook"
                required
                disabled={loading}
              />
            </div>
            <span className="input-hint">HTTP POST notification dispatched when monitor transitions state</span>
          </div>

          {/* Latency Threshold */}
          <div className="input-group">
            <label htmlFor="monitor-latency">Latency Degradation Threshold (optional)</label>
            <div className="input-with-icon">
              <span className="material-symbols-outlined input-prefix">speed</span>
              <input
                id="monitor-latency"
                type="number"
                value={latencyThreshold}
                onChange={(e) => setLatencyThreshold(e.target.value)}
                placeholder="2000"
                min="1"
                disabled={loading}
              />
              <span className="input-suffix font-mono-data">ms</span>
            </div>
            <span className="input-hint">Mark monitor DEGRADED if response exceeds this threshold</span>
          </div>

          {error && <ErrorBanner error={error} />}

          <button
            type="submit"
            className="btn btn-primary register-submit-btn"
            disabled={loading || !url.trim() || !webhookUrl.trim()}
            id="monitor-submit-btn"
          >
            {loading ? (
              <>
                <span className="spinner" aria-hidden="true"></span>
                <span>Registering Monitor…</span>
              </>
            ) : (
              <>
                <span className="material-symbols-outlined">add_task</span>
                <span>Start Continuous Monitoring</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  )
}

export default RegisterMonitor
