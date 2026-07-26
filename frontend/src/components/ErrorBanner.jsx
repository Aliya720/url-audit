/**
 * ErrorBanner component — UI/UX Brief §8
 * Displays error messages with retry button when applicable.
 */
import { getErrorInfo } from '../api/errors.js'
import './ErrorBanner.css'

function ErrorBanner({ error, onRetry }) {
  if (!error) return null

  const errorInfo = getErrorInfo(error.code)
  const message = error.message || errorInfo.message
  const canRetry = errorInfo.retryable && onRetry

  return (
    <div className="error-banner" role="alert" id="error-banner">
      <span className="error-icon" aria-hidden="true">⚠</span>
      <div className="error-content">
        <p className="error-message">{message}</p>
        {canRetry && (
          <button
            className="btn btn-ghost error-retry-btn"
            onClick={onRetry}
            id="error-retry-btn"
          >
            Try again
          </button>
        )}
      </div>
    </div>
  )
}

export default ErrorBanner
