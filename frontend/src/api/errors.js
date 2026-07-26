/**
 * Error copy mapping — UI/UX Brief §8
 * One canonical message per error code, reused everywhere.
 */

const ERROR_MESSAGES = {
  INVALID_URL: {
    message: "That doesn't look like a valid URL. Check the format and try again.",
    retryable: false,
  },
  URL_NOT_ALLOWED: {
    message: "This URL can't be checked — it points to a private or internal address.",
    retryable: false,
  },
  INTERVAL_TOO_SHORT: {
    message: "The check interval is too short. Please choose a longer interval.",
    retryable: false,
  },
  CLIENT_KEY_REQUIRED: {
    message: "Session error. Please refresh the page.",
    retryable: false,
  },
  AUDIT_NOT_FOUND: {
    message: "We couldn't find that — it may have been removed.",
    retryable: false,
  },
  MONITOR_NOT_FOUND: {
    message: "We couldn't find that — it may have been removed.",
    retryable: false,
  },
  RATE_LIMITED: {
    message: "You're checking sites a bit fast — try again in a few seconds.",
    retryable: true,
  },
  TARGET_UNREACHABLE: {
    message: "We couldn't reach that site. It may be down or blocking automated requests.",
    retryable: true,
  },
  TARGET_TIMEOUT: {
    message: "That site took too long to respond.",
    retryable: true,
  },
  SERVICE_BUSY: {
    message: "PulseWatch is handling a lot of checks right now — try again in a moment.",
    retryable: true,
  },
  INTERNAL_ERROR: {
    message: "Something went wrong on our end. Try again, or come back shortly.",
    retryable: true,
  },
  DUPLICATE_MONITOR: {
    message: "You're already monitoring this URL.",
    retryable: false,
  },
}

/**
 * Get the user-facing error info for a given error code.
 */
export function getErrorInfo(code) {
  return ERROR_MESSAGES[code] || ERROR_MESSAGES.INTERNAL_ERROR
}
