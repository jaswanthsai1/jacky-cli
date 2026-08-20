"""Tests for tools/passive_recon_tool.py."""

import json
import socket
from unittest.mock import MagicMock, patch

import pytest

from tools.passive_recon_tool import (
    _looks_like_hostname,
    _parse_crtsh_loose,
    _passive_recon_handler,
    check_dnspython_available,
    check_passive_recon_available,
    passive_recon,
    query_crtsh,
    resolve_a_aaaa,
    resolve_extended_records,
)


# ---------------------------------------------------------------------------
# Hostname validation
# ---------------------------------------------------------------------------


class TestLooksLikeHostname:
    def test_valid_hostname(self):
        assert _looks_like_hostname("api.example.com") is True

    def test_valid_deep_subdomain(self):
        assert _looks_like_hostname("a.b.c.example.com") is True

    def test_bare_word_rejected(self):
        assert _looks_like_hostname("localhost") is False

    def test_empty_string_rejected(self):
        assert _looks_like_hostname("") is False

    def test_wildcard_prefix_rejected(self):
        assert _looks_like_hostname("*.example.com") is False

    def test_leading_hyphen_label_rejected(self):
        assert _looks_like_hostname("-bad.example.com") is False


# ---------------------------------------------------------------------------
# crt.sh loose-JSON recovery
# ---------------------------------------------------------------------------


class TestParseCrtshLoose:
    def test_recovers_concatenated_objects(self):
        text = '{"name_value": "a.example.com"}\n{"name_value": "b.example.com"}'
        data = _parse_crtsh_loose(text)
        assert len(data) == 2
        assert {d["name_value"] for d in data} == {"a.example.com", "b.example.com"}

    def test_empty_text_returns_empty_list(self):
        assert _parse_crtsh_loose("") == []

    def test_unrecoverable_garbage_returns_empty_list(self):
        assert _parse_crtsh_loose("not json at all {{{") == []


# ---------------------------------------------------------------------------
# query_crtsh — mocked network, never hits the real crt.sh in tests
# ---------------------------------------------------------------------------


def _mock_urlopen_response(body_bytes):
    mock_resp = MagicMock()
    mock_resp.read.return_value = body_bytes
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestQueryCrtsh:
    def test_parses_and_dedupes_names(self):
        body = json.dumps(
            [
                {"name_value": "api.example.com\nwww.example.com"},
                {"name_value": "www.example.com"},
                {"name_value": "*.staging.example.com"},
            ]
        ).encode()
        with patch("tools.passive_recon_tool.urllib.request.urlopen", return_value=_mock_urlopen_response(body)) as mock_urlopen:
            result = query_crtsh("example.com")
        assert result == ["api.example.com", "staging.example.com", "www.example.com"]
        sent_req = mock_urlopen.call_args[0][0]
        assert "crt.sh" in sent_req.full_url
        assert "example.com" in sent_req.full_url

    def test_filters_out_names_not_ending_in_domain(self):
        body = json.dumps([{"name_value": "api.example.com\nevil.com"}]).encode()
        with patch("tools.passive_recon_tool.urllib.request.urlopen", return_value=_mock_urlopen_response(body)):
            result = query_crtsh("example.com")
        assert result == ["api.example.com"]

    def test_apex_domain_itself_included(self):
        body = json.dumps([{"name_value": "example.com"}]).encode()
        with patch("tools.passive_recon_tool.urllib.request.urlopen", return_value=_mock_urlopen_response(body)):
            result = query_crtsh("example.com")
        assert result == ["example.com"]

    def test_empty_domain_raises_value_error(self):
        with pytest.raises(ValueError):
            query_crtsh("")

    def test_non_list_response_returns_empty(self):
        body = json.dumps({"error": "something"}).encode()
        with patch("tools.passive_recon_tool.urllib.request.urlopen", return_value=_mock_urlopen_response(body)):
            result = query_crtsh("example.com")
        assert result == []

    def test_malformed_json_recovers_via_loose_parse(self):
        body = b'{"name_value": "a.example.com"}\n{"name_value": "b.example.com"}'
        with patch("tools.passive_recon_tool.urllib.request.urlopen", return_value=_mock_urlopen_response(body)):
            result = query_crtsh("example.com")
        assert result == ["a.example.com", "b.example.com"]

    def test_network_error_propagates_for_caller_to_handle(self):
        with patch("tools.passive_recon_tool.urllib.request.urlopen", side_effect=ConnectionError("no route")):
            with pytest.raises(ConnectionError):
                query_crtsh("example.com")

    def test_uses_custom_endpoint(self):
        body = json.dumps([]).encode()
        with patch("tools.passive_recon_tool.urllib.request.urlopen", return_value=_mock_urlopen_response(body)) as mock_urlopen:
            query_crtsh("example.com", endpoint="https://mirror.internal/crt")
        sent_req = mock_urlopen.call_args[0][0]
        assert sent_req.full_url.startswith("https://mirror.internal/crt")


# ---------------------------------------------------------------------------
# DNS resolution — mocked socket / dnspython
# ---------------------------------------------------------------------------


class TestResolveAAaaa:
    def test_resolves_ipv4_and_ipv6(self):
        infos = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.2.3.4", 0)),
            (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", 0, 0, 0)),
        ]
        with patch("tools.passive_recon_tool.socket.getaddrinfo", return_value=infos):
            result = resolve_a_aaaa("api.example.com")
        assert result["A"] == ["1.2.3.4"]
        assert result["AAAA"] == ["::1"]

    def test_dedupes_addresses(self):
        infos = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.2.3.4", 0)),
            (socket.AF_INET, socket.SOCK_DGRAM, 17, "", ("1.2.3.4", 0)),
        ]
        with patch("tools.passive_recon_tool.socket.getaddrinfo", return_value=infos):
            result = resolve_a_aaaa("api.example.com")
        assert result["A"] == ["1.2.3.4"]

    def test_resolution_failure_returns_empty_not_raises(self):
        with patch("tools.passive_recon_tool.socket.getaddrinfo", side_effect=socket.gaierror("nxdomain")):
            result = resolve_a_aaaa("nonexistent.example.com")
        assert result == {"A": [], "AAAA": []}

    def test_timeout_returns_empty_not_raises(self):
        with patch("tools.passive_recon_tool.socket.getaddrinfo", side_effect=socket.timeout("timed out")):
            result = resolve_a_aaaa("slow.example.com")
        assert result == {"A": [], "AAAA": []}


class TestCheckDnspythonAvailable:
    def test_reports_false_when_not_importable(self):
        with patch.dict("sys.modules", {"dns.resolver": None, "dns": None}):
            with patch("builtins.__import__", side_effect=ImportError):
                assert check_dnspython_available() is False


class TestResolveExtendedRecords:
    def test_returns_none_per_type_when_dnspython_missing(self):
        with patch("builtins.__import__", side_effect=ImportError):
            result = resolve_extended_records("example.com", ["MX", "TXT"])
        assert result == {"MX": None, "TXT": None}


# ---------------------------------------------------------------------------
# passive_recon() top-level entry point
# ---------------------------------------------------------------------------


class TestPassiveReconTopLevel:
    def test_missing_domain_error(self):
        result = passive_recon("")
        assert result["success"] is False
        assert "required" in result["error"]

    def test_crtsh_failure_is_reported_not_raised(self):
        with patch("tools.passive_recon_tool.query_crtsh", side_effect=ConnectionError("simulated outage")):
            result = passive_recon("example.com")
        assert result["success"] is False
        assert "crt.sh unreachable" in result["error"]
        assert result["subdomains"] == []

    def test_subdomains_found_without_dns_resolution(self):
        with patch("tools.passive_recon_tool.query_crtsh", return_value=["a.example.com", "b.example.com"]):
            result = passive_recon("example.com", resolve_dns=False)
        assert result["success"] is True
        assert result["subdomains"] == ["a.example.com", "b.example.com"]
        assert result["subdomains_found"] == 2
        assert result["dns"] == {}

    def test_resolves_dns_for_each_subdomain(self):
        with patch("tools.passive_recon_tool.query_crtsh", return_value=["a.example.com"]), \
             patch("tools.passive_recon_tool.resolve_a_aaaa", return_value={"A": ["1.2.3.4"], "AAAA": []}):
            result = passive_recon("example.com", resolve_dns=True)
        assert result["dns"]["a.example.com"]["A"] == ["1.2.3.4"]

    def test_truncates_at_max_subdomains(self):
        subs = [f"h{i}.example.com" for i in range(10)]
        with patch("tools.passive_recon_tool.query_crtsh", return_value=subs), \
             patch("tools.passive_recon_tool.resolve_a_aaaa", return_value={"A": [], "AAAA": []}):
            result = passive_recon("example.com", max_subdomains=3)
        assert len(result["subdomains"]) == 3
        assert result["truncated"] is True
        assert result["subdomains_found"] == 10

    def test_extended_record_types_requested(self):
        with patch("tools.passive_recon_tool.query_crtsh", return_value=["a.example.com"]), \
             patch("tools.passive_recon_tool.resolve_a_aaaa", return_value={"A": ["1.2.3.4"], "AAAA": []}), \
             patch("tools.passive_recon_tool.resolve_extended_records", return_value={"MX": ["mail.example.com"]}) as mock_ext:
            result = passive_recon("example.com", resolve_dns=True, record_types=["A", "MX"])
        mock_ext.assert_called_once()
        assert result["dns"]["a.example.com"]["MX"] == ["mail.example.com"]
        assert "AAAA" not in result["dns"]["a.example.com"]

    def test_no_subdomains_found_skips_dns(self):
        with patch("tools.passive_recon_tool.query_crtsh", return_value=[]):
            result = passive_recon("example.com")
        assert result["success"] is True
        assert result["dns"] == {}

    def test_dnspython_available_flag_present(self):
        with patch("tools.passive_recon_tool.query_crtsh", return_value=[]):
            result = passive_recon("example.com")
        assert isinstance(result["dnspython_available"], bool)

    def test_invalid_max_subdomains_falls_back_to_default(self):
        with patch("tools.passive_recon_tool.query_crtsh", return_value=["a.example.com"]), \
             patch("tools.passive_recon_tool.resolve_a_aaaa", return_value={"A": [], "AAAA": []}):
            result = passive_recon("example.com", max_subdomains="not-a-number")
        assert result["success"] is True
        assert result["truncated"] is False


# ---------------------------------------------------------------------------
# Registry handler + availability
# ---------------------------------------------------------------------------


class TestPassiveReconHandler:
    def test_missing_domain_returns_error(self):
        response = _passive_recon_handler({})
        assert "error" in json.loads(response)

    def test_valid_domain_returns_json_result(self):
        with patch("tools.passive_recon_tool.query_crtsh", return_value=["a.example.com"]), \
             patch("tools.passive_recon_tool.resolve_a_aaaa", return_value={"A": [], "AAAA": []}):
            response = _passive_recon_handler({"domain": "example.com"})
        data = json.loads(response)
        assert data["success"] is True
        assert data["subdomains"] == ["a.example.com"]

    def test_resolve_dns_false_skips_resolution(self):
        with patch("tools.passive_recon_tool.query_crtsh", return_value=["a.example.com"]) as mock_query:
            response = _passive_recon_handler({"domain": "example.com", "resolve_dns": False})
        data = json.loads(response)
        assert data["dns"] == {}
        mock_query.assert_called_once()


class TestCheckPassiveReconAvailable:
    def test_always_true(self):
        assert check_passive_recon_available() is True


class TestToolRegistration:
    def test_registered_in_registry(self):
        from tools.registry import registry
        assert registry.get_entry("passive_recon") is not None
        assert registry.get_entry("passive_recon").toolset == "passive_recon"
