import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getAlerts } from '../api/client.js'
import './AlertsBanner.css'

export default function AlertsBanner({ onAlertsUpdated }) {
  const [alertsData, setAlertsData] = useState({ active_alert_count: 0, alerts: [] })
  const [dismissed, setDismissed] = useState(false)
  const [loading, setLoading] = useState(true)

  const fetchAlerts = async () => {
    try {
      const res = await getAlerts()
      if (res?.data) {
        setAlertsData(res.data)
        if (onAlertsUpdated) {
          onAlertsUpdated(res.data)
        }
      }
    } catch (err) {
      console.warn('Failed to fetch alerts:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAlerts()
    const interval = setInterval(fetchAlerts, 10000)
    return () => clearInterval(interval)
  }, [])

  if (loading || !alertsData || alertsData.active_alert_count === 0 || dismissed) {
    return null
  }

  return (
    <div className="alerts-banner animate-fade-in" role="alert" id="alerts-banner">
      <div className="alerts-banner-header">
        <div className="alerts-banner-title">
          <span className="material-symbols-outlined alerts-banner-icon">notifications_active</span>
          <strong>
            {alertsData.active_alert_count} Active {alertsData.active_alert_count === 1 ? 'Alert' : 'Alerts'} Detected
          </strong>
        </div>
        <button
          className="alerts-banner-dismiss"
          onClick={() => setDismissed(true)}
          aria-label="Dismiss alert banner"
          id="alerts-banner-dismiss-btn"
        >
          <span className="material-symbols-outlined text-sm">close</span>
        </button>
      </div>
      <div className="alerts-banner-list">
        {alertsData.alerts.map((alert) => (
          <div key={alert.monitor_id} className="alerts-banner-item">
            <div className="alerts-banner-item-info">
              <span className={`badge ${alert.state === 'DOWN' ? 'badge-down' : 'badge-degraded'}`}>
                <span className={`state-dot ${alert.state === 'DOWN' ? 'state-dot-down' : 'state-dot-degraded'}`}></span>
                {alert.state}
              </span>
              <span className="alerts-banner-url">{alert.url}</span>
              {alert.error_code && (
                <span className="alerts-banner-reason">({alert.error_code})</span>
              )}
              {alert.response_time_ms && alert.state === 'DEGRADED' && (
                <span className="alerts-banner-reason">({alert.response_time_ms}ms)</span>
              )}
            </div>
            <Link
              to={`/monitors/${alert.monitor_id}`}
              className="btn btn-ghost alerts-banner-link"
              id={`view-alert-monitor-${alert.monitor_id}`}
            >
              <span>View</span>
              <span className="material-symbols-outlined text-sm">arrow_forward</span>
            </Link>
          </div>
        ))}
      </div>
    </div>
  )
}
