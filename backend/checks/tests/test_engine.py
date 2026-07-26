# Tests for the Check Engine — TRD §3 steps 4-6
# Verifies SEO signal and security header analysis

import pytest

from checks.engine import (
    analyze_security_headers,
    analyze_seo_signals,
    calculate_health_score,
    extract_network_diagnostics,
    generate_fix_suggestions,
)


class TestSEOSignals:
    """Tests for SEO signal analysis — TRD §4.1 result.seo_signals."""

    def test_detects_title(self):
        html = b"<html><head><title>Test Title</title></head><body></body></html>"
        result = analyze_seo_signals(html, {"Content-Type": "text/html"})
        assert result["title_present"] is True
        assert result["title_length"] == 10

    def test_detects_missing_title(self):
        html = b"<html><head></head><body></body></html>"
        result = analyze_seo_signals(html, {"Content-Type": "text/html"})
        assert result["title_present"] is False
        assert result["title_length"] == 0

    def test_detects_meta_description(self):
        html = b'<html><head><meta name="description" content="Test desc"></head><body></body></html>'
        result = analyze_seo_signals(html, {"Content-Type": "text/html"})
        assert result["meta_description_present"] is True

    def test_detects_missing_meta_description(self):
        html = b"<html><head></head><body></body></html>"
        result = analyze_seo_signals(html, {"Content-Type": "text/html"})
        assert result["meta_description_present"] is False

    def test_counts_h1_tags(self):
        html = b"<html><body><h1>One</h1><h1>Two</h1></body></html>"
        result = analyze_seo_signals(html, {"Content-Type": "text/html"})
        assert result["h1_count"] == 2

    def test_non_html_returns_defaults(self):
        result = analyze_seo_signals(b'{"key": "value"}', {"Content-Type": "application/json"})
        assert result["title_present"] is False
        assert result["h1_count"] == 0


class TestSecurityHeaders:
    """Tests for security header analysis — TRD §4.1 result.security_headers."""

    def test_detects_all_headers_present(self):
        headers = {
            "Strict-Transport-Security": "max-age=31536000",
            "Content-Security-Policy": "default-src 'self'",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
        }
        result = analyze_security_headers(headers)
        assert result["hsts"] is True
        assert result["csp"] is True
        assert result["x_frame_options"] is True
        assert result["x_content_type_options"] is True

    def test_detects_all_headers_missing(self):
        result = analyze_security_headers({})
        assert result["hsts"] is False
        assert result["csp"] is False
        assert result["x_frame_options"] is False
        assert result["x_content_type_options"] is False

    def test_case_insensitive_header_detection(self):
        headers = {"strict-transport-security": "max-age=31536000"}
        result = analyze_security_headers(headers)
        assert result["hsts"] is True

    def test_partial_headers(self):
        headers = {"X-Frame-Options": "SAMEORIGIN"}
        result = analyze_security_headers(headers)
        assert result["x_frame_options"] is True
        assert result["hsts"] is False
        assert result["csp"] is False


class TestHealthScore:
    """Tests for 0-100 Health Score calculation engine."""

    def test_perfect_score(self):
        avail = {"reachable": True, "status_code": 200}
        perf = {"response_time_ms": 150}
        seo = {"title_present": True, "title_length": 45, "meta_description_present": True, "h1_count": 1}
        sec = {"hsts": True, "csp": True, "x_frame_options": True, "x_content_type_options": True}

        score = calculate_health_score(avail, perf, seo, sec)
        assert score["overall_score"] == 100
        assert score["grade"] == "A"
        assert score["label"] == "Excellent"

    def test_unreachable_site_low_score(self):
        avail = {"reachable": False, "status_code": 500}
        perf = {"response_time_ms": 2500}
        seo = {"title_present": False, "meta_description_present": False, "h1_count": 0}
        sec = {"hsts": False, "csp": False, "x_frame_options": False, "x_content_type_options": False}

        score = calculate_health_score(avail, perf, seo, sec)
        assert score["overall_score"] == 5
        assert score["grade"] == "F"
        assert score["label"] == "Critical Issues"


class TestFixSuggestions:
    """Tests for diagnostic fix suggestion engine."""

    def test_generates_security_fix_suggestions(self):
        avail = {"reachable": True, "status_code": 200}
        perf = {"response_time_ms": 200}
        seo = {"title_present": True, "title_length": 45, "meta_description_present": True, "h1_count": 1}
        sec = {"hsts": False, "csp": False, "x_frame_options": True, "x_content_type_options": True}
        net = {"content_encoding": "gzip"}

        suggestions = generate_fix_suggestions(avail, perf, seo, sec, net)
        rule_ids = [s["id"] for s in suggestions]
        assert "SEC_HSTS_MISSING" in rule_ids
        assert "SEC_CSP_MISSING" in rule_ids
        assert "SEC_XFRAME_MISSING" not in rule_ids

    def test_generates_performance_and_seo_suggestions(self):
        avail = {"reachable": True, "status_code": 200}
        perf = {"response_time_ms": 1200}
        seo = {"title_present": False, "title_length": 0, "meta_description_present": False, "h1_count": 0}
        sec = {"hsts": True, "csp": True, "x_frame_options": True, "x_content_type_options": True}
        net = {"content_encoding": "identity"}

        suggestions = generate_fix_suggestions(avail, perf, seo, sec, net)
        rule_ids = [s["id"] for s in suggestions]
        assert "PERF_HIGH_LATENCY" in rule_ids
        assert "PERF_NO_COMPRESSION" in rule_ids
        assert "SEO_TITLE_MISSING" in rule_ids
        assert "SEO_META_DESC_MISSING" in rule_ids
        assert "SEO_H1_MISSING" in rule_ids


class TestNetworkDiagnostics:
    """Tests for Network & Server diagnostics extractor."""

    def test_extracts_headers_and_server(self):
        headers = {"Server": "nginx/1.24.0", "Content-Encoding": "br", "Content-Type": "text/html"}
        diag = extract_network_diagnostics(headers, "https://example.com/test")
        assert diag["server"] == "nginx/1.24.0"
        assert diag["content_encoding"] == "br"
        assert diag["is_https"] is True
        assert diag["headers_count"] == 3

