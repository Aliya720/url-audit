# URL Validation, Normalization, and SSRF Protection — TRD §6
# This is the single highest-stakes logic module (FR-1, SSRF prevention)

import ipaddress
import logging
import socket
from urllib.parse import (
    ParseResult,
    parse_qs,
    urlencode,
    urlparse,
    urlunparse,
)

from ..exceptions import InvalidURL, URLNotAllowed

logger = logging.getLogger("checks")

# Allowed schemes — TRD §6 step 1
ALLOWED_SCHEMES = {"http", "https"}

# Default ports to strip during normalization — Backend Schema §2
DEFAULT_PORTS = {"http": 80, "https": 443}


def validate_url(raw_url: str) -> ParseResult:
    """
    Validate URL format and scheme — TRD §6 step 1 / FR-1.

    Returns parsed URL if valid.
    Raises InvalidURL if malformed or uses an unsupported scheme.
    """
    if not raw_url or not isinstance(raw_url, str):
        raise InvalidURL("URL is required and must be a string.")

    raw_url = raw_url.strip()

    try:
        parsed = urlparse(raw_url)
    except Exception:
        raise InvalidURL("Unable to parse the provided URL.")

    if not parsed.scheme:
        raise InvalidURL("URL must include a scheme (http:// or https://).")

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise InvalidURL(f"Unsupported scheme '{parsed.scheme}'. Only HTTP and HTTPS are allowed.")

    if not parsed.hostname:
        raise InvalidURL("URL must include a valid hostname.")

    # Reject obviously malformed netlocs
    if parsed.hostname.startswith(".") or parsed.hostname.endswith("."):
        raise InvalidURL("Invalid hostname in URL.")

    return parsed


def normalize_url(parsed: ParseResult) -> str:
    """
    Normalize a URL for cache key generation — Backend Schema §2.

    - Lowercase host
    - Strip default port (80 for http, 443 for https)
    - Sort query params
    - Ensure trailing slash on bare domains
    """
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname.lower()

    # Strip default port
    port = parsed.port
    if port and port == DEFAULT_PORTS.get(scheme):
        port = None

    # Reconstruct netloc
    netloc = hostname
    if port:
        netloc = f"{hostname}:{port}"
    if parsed.username:
        user_info = parsed.username
        if parsed.password:
            user_info = f"{user_info}:{parsed.password}"
        netloc = f"{user_info}@{netloc}"

    # Normalize path — ensure trailing slash on bare domain
    path = parsed.path or "/"

    # Sort query parameters for consistent cache keys
    query = parsed.query
    if query:
        params = parse_qs(query, keep_blank_values=True)
        sorted_params = sorted(params.items())
        query = urlencode(sorted_params, doseq=True)

    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def check_ssrf(hostname: str) -> list:
    """
    SSRF protection — TRD §6 steps 2-3.

    Resolves hostname via socket.getaddrinfo() BEFORE connecting.
    Rejects if any resolved IP is private/loopback/link-local/metadata.

    Returns list of resolved addresses if all are safe.
    Raises URLNotAllowed if any resolved IP is unsafe.
    """
    try:
        results = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        raise URLNotAllowed(f"Unable to resolve hostname '{hostname}'. DNS lookup failed.")

    if not results:
        raise URLNotAllowed(f"No addresses found for hostname '{hostname}'.")

    resolved_ips = []
    for family, socktype, proto, canonname, sockaddr in results:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise URLNotAllowed(f"Invalid IP address resolved: {ip_str}")

        # Check against private/reserved ranges — TRD §6 step 3
        # Covers 127.0.0.0/8, RFC1918, 169.254.0.0/16 (cloud metadata),
        # IPv6 ::1, fc00::/7, fe80::/10
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            logger.warning(
                "ssrf_blocked",
                extra={
                    "hostname": hostname,
                    "resolved_ip": ip_str,
                    "reason": "private/loopback/link-local/reserved",
                },
            )
            raise URLNotAllowed("This URL resolves to a private or internal address and cannot be checked.")

        # Explicit check for cloud metadata endpoint
        if ip_str in ("169.254.169.254", "fd00::1"):
            logger.warning(
                "ssrf_blocked",
                extra={
                    "hostname": hostname,
                    "resolved_ip": ip_str,
                    "reason": "cloud_metadata_endpoint",
                },
            )
            raise URLNotAllowed("This URL resolves to a cloud metadata endpoint and cannot be checked.")

        resolved_ips.append(ip_str)

    return resolved_ips


def validate_and_normalize(raw_url: str) -> tuple[ParseResult, str]:
    """
    Full validation pipeline — validate format, check SSRF, normalize.

    Returns (parsed_url, normalized_url).
    Raises InvalidURL or URLNotAllowed on failure.
    """
    parsed = validate_url(raw_url)
    check_ssrf(parsed.hostname)
    normalized = normalize_url(parsed)
    return parsed, normalized
