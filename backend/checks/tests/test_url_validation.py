# Unit Tests — URL Validation, Normalization, SSRF Protection
# TRD §12: "write tests for SSRF before wiring it into a view"
# FR-9: at least one test per error code

import pytest

from checks.utils.url_validation import (
    check_ssrf,
    normalize_url,
    validate_and_normalize,
    validate_url,
)
from checks.exceptions import InvalidURL, URLNotAllowed


class TestValidateURL:
    """Tests for URL format validation — FR-1."""

    def test_valid_https_url(self):
        parsed = validate_url("https://example.com")
        assert parsed.scheme == "https"
        assert parsed.hostname == "example.com"

    def test_valid_http_url(self):
        parsed = validate_url("http://example.com/path")
        assert parsed.scheme == "http"
        assert parsed.hostname == "example.com"

    def test_url_with_port(self):
        parsed = validate_url("https://example.com:8080/test")
        assert parsed.port == 8080

    def test_url_with_query(self):
        parsed = validate_url("https://example.com?foo=bar&baz=1")
        assert parsed.query == "foo=bar&baz=1"

    def test_rejects_empty_string(self):
        with pytest.raises(InvalidURL):
            validate_url("")

    def test_rejects_none(self):
        with pytest.raises(InvalidURL):
            validate_url(None)

    def test_rejects_ftp_scheme(self):
        with pytest.raises(InvalidURL):
            validate_url("ftp://example.com")

    def test_rejects_javascript_scheme(self):
        with pytest.raises(InvalidURL):
            validate_url("javascript:alert(1)")

    def test_rejects_file_scheme(self):
        with pytest.raises(InvalidURL):
            validate_url("file:///etc/passwd")

    def test_rejects_no_scheme(self):
        with pytest.raises(InvalidURL):
            validate_url("example.com")

    def test_rejects_no_hostname(self):
        with pytest.raises(InvalidURL):
            validate_url("https://")


class TestNormalizeURL:
    """Tests for URL normalization — Backend Schema §2."""

    def test_lowercase_host(self):
        parsed = validate_url("https://EXAMPLE.COM/path")
        assert "example.com" in normalize_url(parsed)

    def test_strips_default_https_port(self):
        parsed = validate_url("https://example.com:443/path")
        normalized = normalize_url(parsed)
        assert ":443" not in normalized

    def test_strips_default_http_port(self):
        parsed = validate_url("http://example.com:80/path")
        normalized = normalize_url(parsed)
        assert ":80" not in normalized

    def test_keeps_nondefault_port(self):
        parsed = validate_url("https://example.com:8080/path")
        normalized = normalize_url(parsed)
        assert ":8080" in normalized

    def test_sorts_query_params(self):
        parsed = validate_url("https://example.com?z=1&a=2")
        normalized = normalize_url(parsed)
        assert "a=2" in normalized
        # a should come before z
        a_pos = normalized.index("a=2")
        z_pos = normalized.index("z=1")
        assert a_pos < z_pos

    def test_trailing_slash_on_bare_domain(self):
        parsed = validate_url("https://example.com")
        normalized = normalize_url(parsed)
        assert normalized.endswith("/")

    def test_consistent_normalization(self):
        """Same URL with different casing/port produces same key."""
        _, norm1 = validate_and_normalize("https://EXAMPLE.COM:443/")
        _, norm2 = validate_and_normalize("https://example.com/")
        assert norm1 == norm2


class TestSSRFProtection:
    """Tests for SSRF check — TRD §6 / FR-1.

    This is the single highest-stakes piece of logic in the whole build.
    """

    def test_rejects_localhost_127(self):
        with pytest.raises(URLNotAllowed):
            check_ssrf("127.0.0.1")

    def test_rejects_localhost_name(self):
        with pytest.raises(URLNotAllowed):
            check_ssrf("localhost")

    def test_rejects_10_network(self):
        """RFC1918 10.0.0.0/8."""
        with pytest.raises(URLNotAllowed):
            check_ssrf("10.0.0.1")

    def test_rejects_172_16_network(self):
        """RFC1918 172.16.0.0/12."""
        with pytest.raises(URLNotAllowed):
            check_ssrf("172.16.0.1")

    def test_rejects_192_168_network(self):
        """RFC1918 192.168.0.0/16."""
        with pytest.raises(URLNotAllowed):
            check_ssrf("192.168.1.1")

    def test_rejects_metadata_ip(self):
        """Cloud metadata 169.254.169.254."""
        with pytest.raises(URLNotAllowed):
            check_ssrf("169.254.169.254")

    def test_rejects_link_local(self):
        """169.254.0.0/16 link-local."""
        with pytest.raises(URLNotAllowed):
            check_ssrf("169.254.1.1")

    def test_allows_public_ip(self):
        """A known public IP should be allowed."""
        # 8.8.8.8 (Google DNS) is a stable public IP
        result = check_ssrf("8.8.8.8")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_rejects_unresolvable_host(self):
        with pytest.raises(URLNotAllowed):
            check_ssrf("this-domain-does-not-exist-pulsewatch-test.invalid")

    def test_allows_real_public_domain(self):
        """A real public domain should pass."""
        result = check_ssrf("example.com")
        assert isinstance(result, list)
        assert len(result) > 0
