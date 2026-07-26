import { useState, useEffect } from 'react'
import { NavLink, Link } from 'react-router-dom'
import { getAlerts } from '../api/client.js'
import './Header.css'

function Header() {
  const [alertCount, setAlertCount] = useState(0)

  useEffect(() => {
    const checkAlerts = async () => {
      try {
        const res = await getAlerts()
        if (res?.data?.active_alert_count !== undefined) {
          setAlertCount(res.data.active_alert_count)
        }
      } catch (err) {
        // Silent catch for header polling
      }
    }
    checkAlerts()
    const interval = setInterval(checkAlerts, 10000)
    return () => clearInterval(interval)
  }, [])

  return (
    <header className="site-header" id="header">
      <div className="header-container">
        <div className="header-left">
          <NavLink to="/" className="header-logo" id="header-logo">
            <span className="material-symbols-outlined logo-icon">verified_user</span>
            <span className="logo-text">PulseWatch</span>
          </NavLink>

          <nav className="header-nav" id="header-nav" aria-label="Main navigation">
            <NavLink
              to="/"
              className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
              end
              id="nav-check"
            >
              <span className="material-symbols-outlined nav-icon">travel_explore</span>
              Check Site
            </NavLink>
            <NavLink
              to="/monitors"
              className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''} header-monitors-link`}
              id="nav-monitors"
            >
              <span className="material-symbols-outlined nav-icon">speed</span>
              Dashboard & Monitors
              {alertCount > 0 && (
                <span className="header-alert-badge" id="header-alert-count" title={`${alertCount} active monitor alert(s)`}>
                  {alertCount}
                </span>
              )}
            </NavLink>
          </nav>
        </div>

        <div className="header-right">
          <Link to="/monitors/new" className="btn btn-primary header-cta" id="header-add-btn">
            <span className="material-symbols-outlined text-sm">add</span>
            <span>Add Monitor</span>
          </Link>
        </div>
      </div>
    </header>
  )
}

export default Header
