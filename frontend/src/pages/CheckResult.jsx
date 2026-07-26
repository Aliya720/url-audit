/**
 * Check Result screen — SiteGuard Audit Report Specification
 * Four audit cards (Availability, Performance, SEO, Security), cache status badge,
 * monospaced technical output, and "Monitor this site" CTA
 */
import { useLocation, useNavigate, useParams, Link } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { getAudit } from '../api/client.js'
import ErrorBanner from '../components/ErrorBanner.jsx'
import './CheckResult.css'

function CheckResult() {
  const { auditId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const [data, setData] = useState(location.state?.result?.data || null)
  const [loading, setLoading] = useState(!data)
  const [error, setError] = useState(null)
  const [toastMsg, setToastMsg] = useState(null)

  useEffect(() => {
    if (!data && auditId) {
      setLoading(true)
      getAudit(auditId)
        .then((result) => setData(result.data))
        .catch((err) => setError(err))
        .finally(() => setLoading(false))
    }
  }, [auditId, data])

  const showToast = (msg) => {
    setToastMsg(msg)
    setTimeout(() => setToastMsg(null), 3000)
  }

  const handleExportJson = () => {
    if (!data) return
    const hostname = extractHostname(data.url)
    const jsonStr = JSON.stringify(data, null, 2)
    const blob = new Blob([jsonStr], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `audit-report-${hostname}-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
    showToast('Exported JSON report successfully!')
  }

  const handleCopyMarkdown = () => {
    if (!data) return
    const { url, result, checked_at } = data
    const score = result?.score ?? 0
    const grade = result?.score_grade ?? '—'
    const label = result?.score_label ?? '—'
    const suggestions = result?.fix_suggestions || []

    let md = `# PulseWatch Audit Report for ${url}\n`
    md += `**Date:** ${new Date(checked_at).toLocaleString()}\n`
    md += `**Health Score:** ${score}/100 (Grade ${grade} — ${label})\n\n`

    md += `## 1. Availability\n`
    md += `- **Status Code:** ${result.availability?.status_code}\n`
    md += `- **Reachable:** ${result.availability?.reachable ? 'Yes' : 'No'}\n`
    md += `- **Redirects:** ${result.availability?.redirect_count}\n\n`

    md += `## 2. Performance\n`
    md += `- **Response Time:** ${result.performance?.response_time_ms} ms\n`
    md += `- **TTFB:** ${result.performance?.ttfb_ms} ms\n`
    md += `- **Payload Size:** ${formatBytes(result.performance?.page_size_bytes)}\n\n`

    md += `## 3. Security Headers\n`
    md += `- **HSTS:** ${result.security_headers?.hsts ? 'Enabled' : 'Missing'}\n`
    md += `- **CSP:** ${result.security_headers?.csp ? 'Configured' : 'Missing'}\n`
    md += `- **X-Frame-Options:** ${result.security_headers?.x_frame_options ? 'Protected' : 'Missing'}\n`
    md += `- **X-Content-Type-Options:** ${result.security_headers?.x_content_type_options ? 'nosniff' : 'Missing'}\n\n`

    if (suggestions.length > 0) {
      md += `## 4. Fix Suggestions & Remediation\n`
      suggestions.forEach((item, idx) => {
        md += `${idx + 1}. **[${item.severity}] ${item.title}**\n`
        md += `   - *Problem:* ${item.description}\n`
        md += `   - *Fix:* ${item.recommendation}\n`
      })
    }

    navigator.clipboard.writeText(md).then(() => {
      showToast('Markdown report copied to clipboard!')
    })
  }

  const handlePrintPdf = () => {
    window.print()
  }

  if (loading) {
    return (
      <div className="check-result animate-fade-in" id="check-result-page">
        <div className="result-loading-skeleton">
          <div className="skeleton" style={{ height: 40, width: '40%', marginBottom: 20 }}></div>
          <div className="skeleton" style={{ height: 100, marginBottom: 24 }}></div>
          <div className="result-grid">
            <div className="skeleton" style={{ height: 220 }}></div>
            <div className="skeleton" style={{ height: 220 }}></div>
            <div className="skeleton" style={{ height: 220 }}></div>
            <div className="skeleton" style={{ height: 220 }}></div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="check-result animate-fade-in" id="check-result-page">
        <div className="result-error-container">
          <ErrorBanner error={error} />
          <button className="btn btn-ghost" onClick={() => navigate('/')} style={{ marginTop: 16 }}>
            <span className="material-symbols-outlined text-sm">arrow_back</span>
            Back to Audit Check
          </button>
        </div>
      </div>
    )
  }

  if (!data) return null

  const { result, cache, checked_at, url } = data
  const { availability, performance, seo_signals, security_headers, network_diagnostics, score, score_breakdown, score_grade, score_label, fix_suggestions } = result

  const checkedTime = new Date(checked_at).toLocaleString('en-US', {
    hour: '2-digit', minute: '2-digit', second: '2-digit', timeZoneName: 'short',
  })

  const overallScore = score ?? 0
  const suggestions = fix_suggestions || []

  return (
    <div className="check-result animate-fade-in" id="check-result-page">
      {/* Notification Toast */}
      {toastMsg && (
        <div className="toast-notification animate-fade-in">
          <span className="material-symbols-outlined text-sm">check_circle</span>
          <span>{toastMsg}</span>
        </div>
      )}

      {/* Header bar */}
      <div className="result-top-bar print-hide">
        <button className="btn btn-ghost result-back" onClick={() => navigate('/')} id="result-back-btn">
          <span className="material-symbols-outlined text-sm">arrow_back</span>
          <span>Back</span>
        </button>
        <div className="result-actions">
          <button className="btn btn-secondary" onClick={handleExportJson} title="Download JSON Audit Report">
            <span className="material-symbols-outlined text-sm">download</span>
            <span>JSON</span>
          </button>
          <button className="btn btn-secondary" onClick={handleCopyMarkdown} title="Copy Markdown Report">
            <span className="material-symbols-outlined text-sm">content_copy</span>
            <span>Markdown</span>
          </button>
          <button className="btn btn-secondary" onClick={handlePrintPdf} title="Print or Save PDF">
            <span className="material-symbols-outlined text-sm">print</span>
            <span>Print / PDF</span>
          </button>
          <Link
            to={`/monitors/new?url=${encodeURIComponent(url)}`}
            className="btn btn-primary"
            id="header-monitor-cta-btn"
          >
            <span className="material-symbols-outlined text-sm">add_alarm</span>
            <span>Monitor Site</span>
          </Link>
        </div>
      </div>

      {/* Target Site Overview Banner & Health Score Gauge */}
      <div className="result-banner-card">
        <div className="banner-main-info">
          <div className="banner-url-title">
            <span className="material-symbols-outlined text-primary text-2xl">public</span>
            <h1 className="result-url" id="result-url">{url}</h1>
          </div>
          <div className="banner-meta-pills">
            <span className={`badge ${cache === 'hit' ? 'badge-cache-hit' : 'badge-cache-miss'}`} id="cache-badge">
              <span className="material-symbols-outlined text-xs">memory</span>
              CACHE: {cache?.toUpperCase()}
            </span>
            <span className="result-time-text">
              <span className="material-symbols-outlined text-xs">schedule</span>
              {checkedTime}
            </span>
          </div>
        </div>

        {/* 0-100 Score Badge */}
        <div className="banner-score-pill">
          <span className="font-label-caps text-outline">WEBSITE HEALTH SCORE</span>
          <div className="score-counter">
            <span className={`score-number score-grade-${score_grade || 'C'}`}>{overallScore}</span>
            <span className="font-headline-md text-on-surface-variant">/ 100</span>
          </div>
          <div className="score-label-badge">
            <span className="badge badge-up font-mono-data">GRADE {score_grade} • {score_label}</span>
          </div>
        </div>
      </div>

      {/* Sub-Score Breakdown Cards */}
      {score_breakdown && (
        <div className="score-breakdown-bar">
          <div className="breakdown-item">
            <span className="breakdown-label">Availability</span>
            <span className="breakdown-value">{score_breakdown.availability?.score} / 35</span>
            <div className="progress-bg">
              <div className="progress-fill fill-primary" style={{ width: `${(score_breakdown.availability?.score / 35) * 100}%` }}></div>
            </div>
          </div>
          <div className="breakdown-item">
            <span className="breakdown-label">Performance</span>
            <span className="breakdown-value">{score_breakdown.performance?.score} / 25</span>
            <div className="progress-bg">
              <div className="progress-fill fill-primary" style={{ width: `${(score_breakdown.performance?.score / 25) * 100}%` }}></div>
            </div>
          </div>
          <div className="breakdown-item">
            <span className="breakdown-label">Security Headers</span>
            <span className="breakdown-value">{score_breakdown.security?.score} / 25</span>
            <div className="progress-bg">
              <div className="progress-fill fill-primary" style={{ width: `${(score_breakdown.security?.score / 25) * 100}%` }}></div>
            </div>
          </div>
          <div className="breakdown-item">
            <span className="breakdown-label">SEO Signals</span>
            <span className="breakdown-value">{score_breakdown.seo?.score} / 15</span>
            <div className="progress-bg">
              <div className="progress-fill fill-primary" style={{ width: `${(score_breakdown.seo?.score / 15) * 100}%` }}></div>
            </div>
          </div>
        </div>
      )}

      {/* Diagnostic Fix Suggestions Engine */}
      {suggestions.length > 0 && (
        <div className="card suggestions-card" id="card-suggestions">
          <div className="card-header">
            <div className="card-title-box">
              <span className="material-symbols-outlined text-primary">auto_fix_high</span>
              <h3 className="font-headline-md">Diagnostic & Fix Recommendations</h3>
            </div>
            <span className="badge badge-down">{suggestions.length} Issues Detected</span>
          </div>

          <div className="suggestions-list">
            {suggestions.map((item, idx) => (
              <div key={idx} className={`suggestion-item severity-${item.severity.toLowerCase()}`}>
                <div className="suggestion-top font-headline-sm">
                  <span className={`severity-badge sev-${item.severity.toLowerCase()}`}>{item.severity}</span>
                  <span className="suggestion-category">{item.category}</span>
                  <span className="suggestion-title">{item.title}</span>
                </div>
                <p className="suggestion-desc font-body-sm">{item.description}</p>
                <div className="suggestion-fix font-mono-data">
                  <span className="material-symbols-outlined text-sm">build</span>
                  <span><strong>Fix Action:</strong> {item.recommendation}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Result Cards — 2×2 grid */}
      <div className="result-grid" id="result-cards">
        {/* Availability */}
        <div className="card result-card" id="card-availability">
          <div className="card-header">
            <div className="card-title-box">
              <span className="material-symbols-outlined text-primary">sensors</span>
              <h3 className="font-headline-md">Availability</h3>
            </div>
            <span className={`badge ${availability?.reachable ? 'badge-up' : 'badge-down'}`}>
              <span className={`state-dot ${availability?.reachable ? 'state-dot-up' : 'state-dot-down'}`}></span>
              {availability?.reachable ? 'Reachable' : 'Unreachable'}
            </span>
          </div>

          <div className="card-metrics-list">
            <div className="metric-row">
              <span className="metric-label">HTTP Status</span>
              <span className="metric-value font-mono-data status-code-pill">
                {availability?.status_code || 'N/A'}
              </span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Redirect Count</span>
              <span className="metric-value font-mono-data">{availability?.redirect_count ?? 0}</span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Target Reachable</span>
              <span className="metric-value font-mono-data">
                {availability?.reachable ? 'YES' : 'NO'}
              </span>
            </div>
          </div>
        </div>

        {/* Performance */}
        <div className="card result-card" id="card-performance">
          <div className="card-header">
            <div className="card-title-box">
              <span className="material-symbols-outlined text-primary">speed</span>
              <h3 className="font-headline-md">Performance</h3>
            </div>
            <span className="badge badge-up">
              {performance?.response_time_ms ? `${performance.response_time_ms} ms` : '—'}
            </span>
          </div>

          <div className="card-metrics-list">
            <div className="metric-row">
              <span className="metric-label">Response Time</span>
              <span className="metric-value font-mono-data">{performance?.response_time_ms ?? '—'} ms</span>
            </div>
            <div className="metric-row">
              <span className="metric-label">TTFB (First Byte)</span>
              <span className="metric-value font-mono-data">{performance?.ttfb_ms ?? '—'} ms</span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Page Payload Size</span>
              <span className="metric-value font-mono-data">{formatBytes(performance?.page_size_bytes)}</span>
            </div>
          </div>
        </div>

        {/* SEO Signals */}
        <div className="card result-card" id="card-seo">
          <div className="card-header">
            <div className="card-title-box">
              <span className="material-symbols-outlined text-primary">find_in_page</span>
              <h3 className="font-headline-md">SEO Signals</h3>
            </div>
          </div>

          <div className="card-metrics-list">
            <div className="metric-row">
              <span className="metric-label">Page Title</span>
              <span className={`metric-status ${seo_signals?.title_present ? 'pass' : 'fail'}`}>
                <span className="material-symbols-outlined text-sm">
                  {seo_signals?.title_present ? 'check_circle' : 'cancel'}
                </span>
                <span className="font-body-sm">
                  {seo_signals?.title_present ? `Present (${seo_signals.title_length} chars)` : 'Missing'}
                </span>
              </span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Meta Description</span>
              <span className={`metric-status ${seo_signals?.meta_description_present ? 'pass' : 'fail'}`}>
                <span className="material-symbols-outlined text-sm">
                  {seo_signals?.meta_description_present ? 'check_circle' : 'cancel'}
                </span>
                <span className="font-body-sm">
                  {seo_signals?.meta_description_present ? 'Present' : 'Missing'}
                </span>
              </span>
            </div>
            <div className="metric-row">
              <span className="metric-label">H1 Heading Tags</span>
              <span className="metric-value font-mono-data">{seo_signals?.h1_count ?? 0}</span>
            </div>
          </div>
        </div>

        {/* Security Headers */}
        <div className="card result-card" id="card-security">
          <div className="card-header">
            <div className="card-title-box">
              <span className="material-symbols-outlined text-primary">verified_user</span>
              <h3 className="font-headline-md">Security Headers</h3>
            </div>
          </div>

          <div className="card-metrics-list">
            <div className="metric-row">
              <span className="metric-label">HSTS Strict-Transport</span>
              <span className={`metric-status ${security_headers?.hsts ? 'pass' : 'fail'}`}>
                <span className="material-symbols-outlined text-sm">
                  {security_headers?.hsts ? 'check_circle' : 'cancel'}
                </span>
                <span className="font-body-sm">{security_headers?.hsts ? 'Enabled' : 'Missing'}</span>
              </span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Content Security Policy</span>
              <span className={`metric-status ${security_headers?.csp ? 'pass' : 'fail'}`}>
                <span className="material-symbols-outlined text-sm">
                  {security_headers?.csp ? 'check_circle' : 'cancel'}
                </span>
                <span className="font-body-sm">{security_headers?.csp ? 'Configured' : 'Missing'}</span>
              </span>
            </div>
            <div className="metric-row">
              <span className="metric-label">X-Frame-Options</span>
              <span className={`metric-status ${security_headers?.x_frame_options ? 'pass' : 'fail'}`}>
                <span className="material-symbols-outlined text-sm">
                  {security_headers?.x_frame_options ? 'check_circle' : 'cancel'}
                </span>
                <span className="font-body-sm">{security_headers?.x_frame_options ? 'Protected' : 'Missing'}</span>
              </span>
            </div>
            <div className="metric-row">
              <span className="metric-label">X-Content-Type-Options</span>
              <span className={`metric-status ${security_headers?.x_content_type_options ? 'pass' : 'fail'}`}>
                <span className="material-symbols-outlined text-sm">
                  {security_headers?.x_content_type_options ? 'check_circle' : 'cancel'}
                </span>
                <span className="font-body-sm">{security_headers?.x_content_type_options ? 'nosniff' : 'Missing'}</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Network & Server Diagnostics Card */}
      {network_diagnostics && (
        <div className="card network-card" id="card-network">
          <div className="card-header">
            <div className="card-title-box">
              <span className="material-symbols-outlined text-primary">dns</span>
              <h3 className="font-headline-md">Network & Server Diagnostics</h3>
            </div>
          </div>
          <div className="network-grid">
            <div className="network-item">
              <span className="metric-label">Server Engine</span>
              <span className="metric-value font-mono-data">{network_diagnostics.server || 'Unknown'}</span>
            </div>
            <div className="network-item">
              <span className="metric-label">Content Encoding</span>
              <span className="metric-value font-mono-data">{network_diagnostics.content_encoding?.toUpperCase()}</span>
            </div>
            <div className="network-item">
              <span className="metric-label">Protocol Scheme</span>
              <span className="metric-value font-mono-data">{network_diagnostics.is_https ? 'HTTPS (Secure)' : 'HTTP (Unencrypted)'}</span>
            </div>
            <div className="network-item">
              <span className="metric-label">HTTP Headers Count</span>
              <span className="metric-value font-mono-data">{network_diagnostics.headers_count} headers</span>
            </div>
          </div>
        </div>
      )}

      {/* Monitor CTA Section */}
      <div className="result-cta-card print-hide">
        <div className="cta-content">
          <h3 className="font-headline-md text-primary">Continuous Web Monitoring</h3>
          <p className="font-body-sm text-on-surface-variant">
            Set up 24/7 background checks with webhook notifications to catch downtime and response degradation instantly.
          </p>
        </div>
        <Link
          to={`/monitors/new?url=${encodeURIComponent(url)}`}
          className="btn btn-primary"
          id="monitor-cta-btn"
        >
          <span className="material-symbols-outlined text-sm">add_alarm</span>
          <span>Register Monitor for {extractHostname(url)}</span>
        </Link>
      </div>
    </div>
  )
}

function formatBytes(bytes) {
  if (bytes == null) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function extractHostname(urlStr) {
  try {
    return new URL(urlStr).hostname
  } catch {
    return urlStr
  }
}

export default CheckResult
