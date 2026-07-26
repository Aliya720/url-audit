/**
 * Home / Check screen — UI/UX Brief §2 & PulseWatch Design Spec
 * Instant URL health check form + Bento Grid feature highlights + Dashboard preview
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { runAudit } from '../api/client.js'
import ErrorBanner from '../components/ErrorBanner.jsx'
import './Home.css'

function Home() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!url.trim()) return

    setLoading(true)
    setError(null)

    try {
      const result = await runAudit(url.trim())
      navigate(`/result/${result.data.audit_id}`, { state: { result } })
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  const handleRetry = () => {
    setError(null)
    handleSubmit(new Event('submit'))
  }

  return (
    <div className="home-page animate-fade-in" id="home-page">
      {/* Hero Section */}
      <section className="home-hero">
        <div className="hero-eyebrow font-label-caps">
          <span className="material-symbols-outlined text-sm">radar</span>
          REAL-TIME WEB INTELLIGENCE
        </div>
        <h1 className="hero-title font-display-lg" id="home-title">
          Your Website's Health, <br className="hidden-mobile" />Monitored 24/7
        </h1>
        <p className="hero-subtitle font-body-base">
          Precision diagnostic tools for IT professionals and site administrators. Get deep scan audits, uptime alerts, and technical performance metrics in one unified dashboard.
        </p>

        {/* Free Audit Input Form */}
        <form onSubmit={handleSubmit} className="audit-form-card" id="check-form">
          <div className="audit-input-wrapper">
            <span className="material-symbols-outlined input-icon">language</span>
            <input
              id="url-input"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://your-website.com"
              disabled={loading}
              autoFocus
              required
              aria-label="Website URL to check"
              className="audit-input"
            />
          </div>
          <button
            type="submit"
            className="btn btn-primary audit-submit-btn"
            disabled={loading || !url.trim()}
            id="check-submit-btn"
          >
            {loading ? (
              <>
                <span className="spinner" aria-hidden="true"></span>
                <span>Analyzing…</span>
              </>
            ) : (
              <>
                <span>Run Free Audit</span>
                <span className="material-symbols-outlined text-sm">arrow_forward</span>
              </>
            )}
          </button>
        </form>

        {loading && (
          <p className="home-loading-hint font-body-sm" aria-live="polite">
            <span className="material-symbols-outlined text-sm animate-spin">hourglass_empty</span>
            Fetching response metrics & security headers — this takes ~2 seconds…
          </p>
        )}

        {error && (
          <div className="home-error-container" aria-live="polite">
            <ErrorBanner error={error} onRetry={handleRetry} />
          </div>
        )}

        <div className="hero-social-proof">
          <div className="avatar-group">
            <div className="avatar-circle">DEV</div>
            <div className="avatar-circle avatar-sec">OPS</div>
            <div className="avatar-circle avatar-tri">SEO</div>
          </div>
          <p className="font-body-sm text-on-surface-variant">
            Trusted by 12,000+ developers & webmasters
          </p>
        </div>
      </section>

      {/* Corporate Partners Bar */}
      <section className="social-proof-bar">
        <p className="font-label-caps text-outline proof-title">POWERING GLOBAL INFRASTRUCTURE FOR</p>
        <div className="proof-logos">
          <span>TechFlow</span>
          <span>DataNexus</span>
          <span>WebScale</span>
          <span>CloudOps</span>
          <span>SecureNet</span>
        </div>
      </section>

      {/* Features Bento Grid */}
      <section className="bento-section" id="features">
        <div className="section-header text-center">
          <h2 className="font-display-lg">Enterprise-Grade Performance</h2>
          <p className="font-body-base text-on-surface-variant">Deploy our comprehensive monitoring suite to identify bottlenecks before they affect your users.</p>
        </div>

        <div className="bento-grid">
          {/* Card 1 */}
          <div className="glass-card bento-card">
            <div className="card-icon-box bg-secondary">
              <span className="material-symbols-outlined">analytics</span>
            </div>
            <div>
              <h3 className="font-headline-md mb-2">Deep Scan Audits</h3>
              <p className="font-body-sm text-on-surface-variant">Automated technical analysis covering response latency, accessibility, and SEO compliance across 100+ checkpoints.</p>
            </div>
            <div className="bento-footer">
              <span className="bento-link">Learn more <span className="material-symbols-outlined text-sm">chevron_right</span></span>
            </div>
          </div>

          {/* Card 2 */}
          <div className="glass-card bento-card">
            <div className="card-icon-box bg-primary">
              <span className="material-symbols-outlined">speed</span>
            </div>
            <div>
              <h3 className="font-headline-md mb-2">Uptime & Performance</h3>
              <p className="font-body-sm text-on-surface-variant">Global edge monitoring with configurable check intervals and detailed response time graphing for all target endpoints.</p>
            </div>
            <div className="bento-footer">
              <span className="bento-link">Learn more <span className="material-symbols-outlined text-sm">chevron_right</span></span>
            </div>
          </div>

          {/* Card 3 */}
          <div className="glass-card bento-card">
            <div className="card-icon-box bg-tertiary">
              <span className="material-symbols-outlined">notifications_active</span>
            </div>
            <div>
              <h3 className="font-headline-md mb-2">Instant Alert System</h3>
              <p className="font-body-sm text-on-surface-variant">Instant webhook notifications the second your target website experiences high latency or HTTP errors.</p>
            </div>
            <div className="bento-footer">
              <span className="bento-link">Learn more <span className="material-symbols-outlined text-sm">chevron_right</span></span>
            </div>
          </div>
        </div>
      </section>

      {/* Stats & Dashboard Preview Section */}
      <section className="dashboard-preview-section">
        <div className="preview-grid">
          <div className="preview-info">
            <h2 className="font-display-lg mb-4">Actionable insights, <br />not just raw data.</h2>
            <div className="preview-points">
              <div className="point-item">
                <span className="material-symbols-outlined text-primary fill-1">check_circle</span>
                <div>
                  <h4 className="font-bold font-body-base">Priority Issue Detection</h4>
                  <p className="font-body-sm text-on-surface-variant">Highlight missing security headers, missing meta titles, and slow TTFB metrics instantly.</p>
                </div>
              </div>
              <div className="point-item">
                <span className="material-symbols-outlined text-primary fill-1">check_circle</span>
                <div>
                  <h4 className="font-bold font-body-base">Automated Continuous Monitors</h4>
                  <p className="font-body-sm text-on-surface-variant">Schedule background checks down to 1-minute intervals with browser-persistent monitoring keys.</p>
                </div>
              </div>
            </div>
          </div>

          {/* Live Preview Card */}
          <div className="preview-card-mockup">
            <div className="mockup-header">
              <span className="font-bold text-primary">MONITOR PREVIEW</span>
              <span className="badge badge-up">All Systems Optimal</span>
            </div>
            <div className="mockup-stats-grid">
              <div className="stat-box">
                <span className="font-label-caps text-outline block mb-1">HEALTH SCORE</span>
                <span className="font-display-lg text-primary">98/100</span>
              </div>
              <div className="stat-box">
                <span className="font-label-caps text-outline block mb-1">UPTIME</span>
                <span className="font-display-lg text-primary">99.99%</span>
              </div>
            </div>
            <div className="mockup-progress">
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: '92%' }}></div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

export default Home
