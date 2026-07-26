# Check Engine — TRD §3 steps 4-6, §4.1
# Orchestrates the outbound fetch and computes availability/performance/SEO/security results
# Shared by both on-demand Check and scheduled Monitor (FR-12 — no duplicated logic)

import logging
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from django.conf import settings

from .exceptions import TargetTimeout, TargetUnreachable, URLNotAllowed
from .utils.url_validation import check_ssrf

logger = logging.getLogger("checks")

# Custom User-Agent — PRD §4.5 legal/ethical note
USER_AGENT = "PulseWatch/1.0 (URL Health Checker; +https://github.com/pulsewatch)"


def fetch_url(url: str, request_id: str) -> dict:
    """
    Fetch a URL with timeout, manual redirect handling, and SSRF re-validation.

    TRD §3 step 6:
    - requests session with allow_redirects=False
    - Manual redirect following with per-hop SSRF re-validation (TRD §6 step 4)
    - Max redirect hops capped (TRD §6 step 5)
    - Custom User-Agent (PRD §4.5 ethical note)

    Returns raw fetch result dict with timing and response data.
    Raises TargetTimeout, TargetUnreachable on failure.
    """
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    timeout = settings.FETCH_TIMEOUT_SECONDS
    max_redirects = settings.MAX_REDIRECT_HOPS
    redirect_count = 0
    current_url = url

    start_time = time.monotonic()
    ttfb_ms = None
    final_response = None

    try:
        while redirect_count <= max_redirects:
            try:
                response = session.get(
                    current_url,
                    timeout=timeout,
                    allow_redirects=False,
                    stream=True,
                )

                # Capture TTFB on first response
                if ttfb_ms is None:
                    ttfb_ms = round((time.monotonic() - start_time) * 1000, 2)

                # Check if this is a redirect
                if response.is_redirect and response.headers.get("Location"):
                    redirect_count += 1
                    if redirect_count > max_redirects:
                        logger.warning(
                            "max_redirects_exceeded",
                            extra={
                                "request_id": request_id,
                                "url": url,
                                "redirect_count": redirect_count,
                            },
                        )
                        break

                    # Get next URL
                    next_url = response.headers["Location"]
                    # Handle relative redirects
                    if not next_url.startswith(("http://", "https://")):
                        parsed_current = urlparse(current_url)
                        next_url = f"{parsed_current.scheme}://{parsed_current.netloc}{next_url}"

                    # SSRF re-validation on each hop (TRD §6 step 4)
                    parsed_next = urlparse(next_url)
                    if parsed_next.hostname:
                        check_ssrf(parsed_next.hostname)

                    current_url = next_url
                    continue

                # Not a redirect — we have our final response
                # Read the full body
                content = response.content
                final_response = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "content": content,
                    "content_length": len(content),
                    "redirect_count": redirect_count,
                    "final_url": current_url,
                }
                break

            except requests.exceptions.Timeout:
                raise TargetTimeout(f"Target site timed out after {timeout}s.")
            except requests.exceptions.ConnectionError as e:
                raise TargetUnreachable(f"Unable to reach the target site: {str(e)[:200]}")
            except (requests.exceptions.TooManyRedirects, requests.exceptions.RequestException) as e:
                raise TargetUnreachable(f"Error fetching target site: {str(e)[:200]}")
            except URLNotAllowed:
                # Re-raise SSRF errors from redirect validation
                raise

    finally:
        session.close()

    total_time_ms = round((time.monotonic() - start_time) * 1000, 2)

    if final_response is None:
        raise TargetUnreachable("No valid response received after following redirects.")

    final_response["response_time_ms"] = total_time_ms
    final_response["ttfb_ms"] = ttfb_ms

    return final_response


def analyze_seo_signals(content: bytes, headers: dict) -> dict:
    """
    Analyze SEO signals from page content — TRD §4.1 result.seo_signals.

    Checks: title present/length, meta description present, h1 count.
    """
    signals = {
        "title_present": False,
        "title_length": 0,
        "meta_description_present": False,
        "h1_count": 0,
    }

    try:
        content_type = headers.get("Content-Type", "")
        if "text/html" not in content_type.lower():
            return signals

        soup = BeautifulSoup(content, "html.parser")

        # Title
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            title_text = title_tag.string.strip()
            signals["title_present"] = bool(title_text)
            signals["title_length"] = len(title_text)

        # Meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            signals["meta_description_present"] = True

        # H1 count
        h1_tags = soup.find_all("h1")
        signals["h1_count"] = len(h1_tags)

    except Exception as e:
        logger.warning(
            "seo_analysis_error",
            extra={"error": str(e)[:200]},
        )

    return signals


def analyze_security_headers(headers: dict) -> dict:
    """
    Analyze security headers — TRD §4.1 result.security_headers.

    Checks: HSTS, CSP, X-Frame-Options, X-Content-Type-Options.
    """
    # Case-insensitive header lookup
    lower_headers = {k.lower(): v for k, v in headers.items()}

    return {
        "hsts": "strict-transport-security" in lower_headers,
        "csp": "content-security-policy" in lower_headers,
        "x_frame_options": "x-frame-options" in lower_headers,
        "x_content_type_options": "x-content-type-options" in lower_headers,
    }


def extract_network_diagnostics(headers: dict, final_url: str) -> dict:
    """
    Extract network and server environment diagnostics.
    """
    lower_headers = {k.lower(): v for k, v in headers.items()}
    return {
        "server": headers.get("Server") or headers.get("server") or "Unknown",
        "content_encoding": lower_headers.get("content-encoding", "identity"),
        "content_type": lower_headers.get("content-type", "Unknown"),
        "headers_count": len(headers),
        "is_https": final_url.lower().startswith("https://"),
    }


def calculate_health_score(availability: dict, performance: dict, seo_signals: dict, security_headers: dict) -> dict:
    """
    Compute 0-100 overall site health score and category sub-scores.
    Weights: Availability (35), Performance (25), Security Headers (25), SEO (15).
    """
    # 1. Availability Score (max 35)
    avail_score = 0
    if availability.get("reachable"):
        status = availability.get("status_code", 0)
        if 200 <= status < 300:
            avail_score = 35
        elif 300 <= status < 400:
            avail_score = 25
        else:
            avail_score = 10

    # 2. Performance Score (max 25)
    perf_score = 0
    rt = performance.get("response_time_ms")
    if rt is not None:
        if rt < 300:
            perf_score = 25
        elif rt < 800:
            perf_score = 20
        elif rt < 1500:
            perf_score = 12
        else:
            perf_score = 5

    # 3. Security Headers Score (max 25)
    sec_score = 0
    if security_headers.get("hsts"):
        sec_score += 7
    if security_headers.get("csp"):
        sec_score += 8
    if security_headers.get("x_frame_options"):
        sec_score += 5
    if security_headers.get("x_content_type_options"):
        sec_score += 5

    # 4. SEO Signals Score (max 15)
    seo_score = 0
    if seo_signals.get("title_present"):
        seo_score += 5
        length = seo_signals.get("title_length", 0)
        if 30 <= length <= 60:
            seo_score += 3
        else:
            seo_score += 1
    if seo_signals.get("meta_description_present"):
        seo_score += 4
    h1 = seo_signals.get("h1_count", 0)
    if h1 == 1:
        seo_score += 3
    elif h1 > 1:
        seo_score += 1

    total = avail_score + perf_score + sec_score + seo_score

    if total >= 90:
        grade, label = "A", "Excellent"
    elif total >= 75:
        grade, label = "B", "Good"
    elif total >= 60:
        grade, label = "C", "Fair"
    elif total >= 40:
        grade, label = "D", "Needs Improvement"
    else:
        grade, label = "F", "Critical Issues"

    return {
        "overall_score": total,
        "grade": grade,
        "label": label,
        "breakdown": {
            "availability": {"score": avail_score, "max": 35},
            "performance": {"score": perf_score, "max": 25},
            "security": {"score": sec_score, "max": 25},
            "seo": {"score": seo_score, "max": 15},
        },
    }


def generate_fix_suggestions(
    availability: dict,
    performance: dict,
    seo_signals: dict,
    security_headers: dict,
    network_diagnostics: dict,
) -> list[dict]:
    """
    Generate actionable fix suggestions and recommendations based on audit findings.
    """
    suggestions = []

    # Security
    if not security_headers.get("hsts"):
        suggestions.append(
            {
                "id": "SEC_HSTS_MISSING",
                "severity": "CRITICAL",
                "category": "Security",
                "title": "Enable HTTP Strict Transport Security (HSTS)",
                "description": (
                    "HSTS header is missing. Without HSTS, connection upgrades"
                    " to HTTPS can be stripped by attackers."
                ),
                "recommendation": (
                    "Configure your server to return"
                    " 'Strict-Transport-Security: max-age=31536000; includeSubDomains'."
                ),
            }
        )

    if not security_headers.get("csp"):
        suggestions.append(
            {
                "id": "SEC_CSP_MISSING",
                "severity": "CRITICAL",
                "category": "Security",
                "title": "Configure Content Security Policy (CSP)",
                "description": (
                    "Content-Security-Policy header is missing, exposing"
                    " the site to Cross-Site Scripting (XSS) attacks."
                ),
                "recommendation": "Define a CSP header restricting allowed script, style, and frame sources.",
            }
        )

    if not security_headers.get("x_frame_options"):
        suggestions.append(
            {
                "id": "SEC_XFRAME_MISSING",
                "severity": "WARNING",
                "category": "Security",
                "title": "Add X-Frame-Options Header",
                "description": "X-Frame-Options header is missing, allowing potential clickjacking attacks in frames.",
                "recommendation": "Set 'X-Frame-Options: SAMEORIGIN' or 'DENY' in web server response headers.",
            }
        )

    if not security_headers.get("x_content_type_options"):
        suggestions.append(
            {
                "id": "SEC_XCTO_MISSING",
                "severity": "WARNING",
                "category": "Security",
                "title": "Add X-Content-Type-Options Header",
                "description": "X-Content-Type-Options header is missing, allowing browser MIME-sniffing.",
                "recommendation": "Set 'X-Content-Type-Options: nosniff' header.",
            }
        )

    # Performance
    rt = performance.get("response_time_ms", 0)
    if rt > 1000:
        suggestions.append(
            {
                "id": "PERF_HIGH_LATENCY",
                "severity": "WARNING",
                "category": "Performance",
                "title": "High Response Latency",
                "description": f"Server response time was {rt}ms (recommended benchmark is under 500ms).",
                "recommendation": "Optimize backend queries, enable page/object caching, or place assets behind a CDN.",
            }
        )

    encoding = network_diagnostics.get("content_encoding", "identity").lower()
    if encoding == "identity" or not encoding:
        suggestions.append(
            {
                "id": "PERF_NO_COMPRESSION",
                "severity": "INFO",
                "category": "Performance",
                "title": "Enable HTTP Compression (Gzip / Brotli)",
                "description": "Response content was delivered uncompressed.",
                "recommendation": "Enable Gzip or Brotli compression on your origin server/reverse proxy.",
            }
        )

    # SEO
    if not seo_signals.get("title_present"):
        suggestions.append(
            {
                "id": "SEO_TITLE_MISSING",
                "severity": "CRITICAL",
                "category": "SEO",
                "title": "Add HTML Title Tag",
                "description": "The page lacks a <title> tag, preventing proper indexing by search engines.",
                "recommendation": "Add a descriptive <title> tag inside the <head> element.",
            }
        )
    else:
        title_len = seo_signals.get("title_length", 0)
        if title_len < 30 or title_len > 60:
            suggestions.append(
                {
                    "id": "SEO_TITLE_LENGTH",
                    "severity": "INFO",
                    "category": "SEO",
                    "title": "Optimize Title Tag Length",
                    "description": (
                        f"Title tag length is {title_len} characters." " Recommended target is 30 to 60 characters."
                    ),
                    "recommendation": (
                        "Adjust page title text to fit standard search" " snippet displays (30–60 characters)."
                    ),
                }
            )

    if not seo_signals.get("meta_description_present"):
        suggestions.append(
            {
                "id": "SEO_META_DESC_MISSING",
                "severity": "WARNING",
                "category": "SEO",
                "title": "Add Meta Description Tag",
                "description": "Meta description is missing.",
                "recommendation": "Add <meta name='description' content='...'> providing a summary of page content.",
            }
        )

    h1_cnt = seo_signals.get("h1_count", 0)
    if h1_cnt == 0:
        suggestions.append(
            {
                "id": "SEO_H1_MISSING",
                "severity": "WARNING",
                "category": "SEO",
                "title": "Add Primary Heading (H1)",
                "description": "No <h1> heading tags were found.",
                "recommendation": "Include a single <h1> tag containing the principal page topic.",
            }
        )
    elif h1_cnt > 1:
        suggestions.append(
            {
                "id": "SEO_H1_MULTIPLE",
                "severity": "INFO",
                "category": "SEO",
                "title": "Multiple H1 Headings Detected",
                "description": f"Found {h1_cnt} <h1> tags on the page.",
                "recommendation": "Use a single <h1> for the page title and structural <h2>–<h6> tags for subheadings.",
            }
        )

    return suggestions


def run_check(url: str, request_id: str) -> dict:
    """
    Run the complete check engine — TRD §3 steps 4-6.

    This is the shared code path used by both:
    - POST /api/audits (on-demand check)
    - run_monitor_check Celery task (scheduled check)

    Returns the full result dict matching TRD §4.1 response shape.
    """
    # Fetch the URL (includes timeout, redirect handling, SSRF re-validation)
    fetch_result = fetch_url(url, request_id)

    # Compute availability
    status_code = fetch_result["status_code"]
    availability = {
        "reachable": 200 <= status_code < 400,
        "status_code": status_code,
        "redirect_count": fetch_result["redirect_count"],
    }

    # Compute performance
    performance = {
        "response_time_ms": fetch_result["response_time_ms"],
        "ttfb_ms": fetch_result["ttfb_ms"],
        "page_size_bytes": fetch_result["content_length"],
    }

    # Analyze SEO signals
    seo_signals = analyze_seo_signals(fetch_result["content"], fetch_result["headers"])

    # Analyze security headers
    security_headers = analyze_security_headers(fetch_result["headers"])

    # Network diagnostics
    network_diagnostics = extract_network_diagnostics(fetch_result["headers"], fetch_result["final_url"])

    # Health score
    score_data = calculate_health_score(availability, performance, seo_signals, security_headers)

    # Fix suggestions
    fix_suggestions = generate_fix_suggestions(
        availability, performance, seo_signals, security_headers, network_diagnostics
    )

    result = {
        "availability": availability,
        "performance": performance,
        "seo_signals": seo_signals,
        "security_headers": security_headers,
        "network_diagnostics": network_diagnostics,
        "score": score_data["overall_score"],
        "score_breakdown": score_data["breakdown"],
        "score_grade": score_data["grade"],
        "score_label": score_data["label"],
        "fix_suggestions": fix_suggestions,
    }

    logger.info(
        "check_completed",
        extra={
            "request_id": request_id,
            "url": url,
            "status_code": status_code,
            "response_time_ms": fetch_result["response_time_ms"],
            "reachable": availability["reachable"],
            "score": score_data["overall_score"],
        },
    )

    return result
