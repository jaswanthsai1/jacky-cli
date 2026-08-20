"""Tests for tools/http_client_tool.py."""

import json

import httpx
import pytest

from tools import http_client_tool
from tools.http_client_tool import (
    _http_client_dispatch,
    build_curl_command,
    http_request,
    tls_cert_info,
)


def _install_mock_transport(monkeypatch, handler):
    """Route every httpx.AsyncClient() created by the tool through a MockTransport."""
    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def _factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(http_client_tool.httpx, "AsyncClient", _factory)


def _allow_all_urls(monkeypatch):
    async def _allow(url):
        return True

    monkeypatch.setattr(http_client_tool, "async_is_safe_url", _allow)


def _block_all_urls(monkeypatch):
    async def _block(url):
        return False

    monkeypatch.setattr(http_client_tool, "async_is_safe_url", _block)


class TestHttpRequest:
    @pytest.mark.asyncio
    async def test_basic_get_request(self, monkeypatch):
        _allow_all_urls(monkeypatch)

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "GET"
            return httpx.Response(200, json={"ok": True}, headers={"X-Test": "1"})

        _install_mock_transport(monkeypatch, handler)

        result = json.loads(await http_request("https://example.com/api"))
        assert result["success"] is True
        assert result["status_code"] == 200
        assert json.loads(result["body"]) == {"ok": True}
        assert result["headers"]["x-test"] == "1" or result["headers"].get("X-Test") == "1"

    @pytest.mark.asyncio
    async def test_post_with_json_body(self, monkeypatch):
        _allow_all_urls(monkeypatch)
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = request.content
            captured["content_type"] = request.headers.get("content-type")
            return httpx.Response(201, text="created")

        _install_mock_transport(monkeypatch, handler)

        result = json.loads(
            await http_request(
                "https://example.com/api",
                method="POST",
                body={"name": "jacky"},
            )
        )
        assert result["success"] is True
        assert result["status_code"] == 201
        assert b"jacky" in captured["body"]
        assert "application/json" in captured["content_type"]

    @pytest.mark.asyncio
    async def test_custom_headers_and_params_sent(self, monkeypatch):
        _allow_all_urls(monkeypatch)
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["headers"] = request.headers
            captured["url"] = str(request.url)
            return httpx.Response(200, text="ok")

        _install_mock_transport(monkeypatch, handler)

        await http_request(
            "https://example.com/api",
            headers={"X-Custom": "abc"},
            params={"q": "test"},
        )
        assert captured["headers"]["x-custom"] == "abc"
        assert "q=test" in captured["url"]

    @pytest.mark.asyncio
    async def test_ssrf_blocked(self, monkeypatch):
        _block_all_urls(monkeypatch)

        result = json.loads(await http_request("http://169.254.169.254/latest/meta-data/"))
        assert result["success"] is False
        assert "private or internal" in result["error"]

    @pytest.mark.asyncio
    async def test_url_with_embedded_secret_rejected(self, monkeypatch):
        _allow_all_urls(monkeypatch)
        result = json.loads(
            await http_request("https://example.com/api?key=sk-abcdefghijklmnopqrstuvwx")
        )
        assert result["success"] is False
        assert "credential-like" in result["error"] or "API key" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_method_rejected(self, monkeypatch):
        _allow_all_urls(monkeypatch)
        result = json.loads(await http_request("https://example.com/api", method="TRACE-BOGUS"))
        assert result["success"] is False
        assert "Unsupported method" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_url(self):
        result = json.loads(await http_request(""))
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_large_body_truncated(self, monkeypatch):
        _allow_all_urls(monkeypatch)

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="x" * 50_000)

        _install_mock_transport(monkeypatch, handler)

        result = json.loads(await http_request("https://example.com/big", body_char_limit=1000))
        assert result["success"] is True
        assert result["truncated"] is True
        assert "truncated" in result["body"]

    @pytest.mark.asyncio
    async def test_timeout_reported(self, monkeypatch):
        _allow_all_urls(monkeypatch)

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("boom", request=request)

        _install_mock_transport(monkeypatch, handler)

        result = json.loads(await http_request("https://example.com/slow", timeout=1))
        assert result["success"] is False
        assert "timed out" in result["error"]

    @pytest.mark.asyncio
    async def test_secret_response_header_redacted(self, monkeypatch):
        _allow_all_urls(monkeypatch)

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                text="hi",
                headers={"X-Echo-Auth": "Bearer sk-liveSecretValue1234567890"},
            )

        _install_mock_transport(monkeypatch, handler)

        result = json.loads(await http_request("https://example.com/echo"))
        headers_str = json.dumps(result["headers"])
        assert "sk-liveSecretValue1234567890" not in headers_str


class TestTlsCertInfo:
    @pytest.mark.asyncio
    async def test_ssrf_blocked(self, monkeypatch):
        _block_all_urls(monkeypatch)
        result = json.loads(await tls_cert_info("169.254.169.254"))
        assert result["success"] is False
        assert "private or internal" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_host(self):
        result = json.loads(await tls_cert_info(""))
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_connection_error_reported(self, monkeypatch):
        _allow_all_urls(monkeypatch)
        # Port 1 on localhost should refuse a connection immediately/fast.
        result = json.loads(await tls_cert_info("127.0.0.1", port=1, timeout=2))
        assert result["success"] is False
        assert result["error"]

    @pytest.mark.asyncio
    async def test_url_form_host_extracted(self, monkeypatch):
        _allow_all_urls(monkeypatch)
        captured = {}

        def fake_sync(host, port, timeout):
            captured["host"] = host
            captured["port"] = port
            return json.dumps({"success": True, "subject": {}, "issuer": {}})

        monkeypatch.setattr(http_client_tool, "_tls_cert_info_sync", fake_sync)
        await tls_cert_info("https://example.com:8443/some/path")
        assert captured["host"] == "example.com"
        assert captured["port"] == 8443


class TestBuildCurlCommand:
    def test_basic_get(self):
        result = json.loads(build_curl_command("https://example.com/api"))
        assert result["success"] is True
        assert result["command"] == "curl -sS https://example.com/api"

    def test_post_with_json_body_and_headers(self):
        result = json.loads(
            build_curl_command(
                "https://example.com/api",
                method="POST",
                headers={"X-Custom": "abc"},
                body={"name": "jacky"},
            )
        )
        cmd = result["command"]
        assert "-X POST" in cmd
        assert "-H 'X-Custom: abc'" in cmd
        assert "Content-Type: application/json" in cmd
        assert "--data" in cmd
        assert "jacky" in cmd

    def test_params_appended_to_url(self):
        result = json.loads(build_curl_command("https://example.com/api", params={"q": "hello world"}))
        assert "q=hello" in result["command"]

    def test_cookies_included(self):
        result = json.loads(build_curl_command("https://example.com/api", cookies={"session": "abc123"}))
        assert "-b" in result["command"]
        assert "session=abc123" in result["command"]

    def test_shell_metacharacters_quoted(self):
        result = json.loads(
            build_curl_command("https://example.com/api", headers={"X-Evil": "$(rm -rf /)"})
        )
        # shlex.quote wraps the "key: value" pair in single quotes so the
        # shell can't expand the embedded command substitution.
        assert "'X-Evil: $(rm -rf /)'" in result["command"]

    def test_missing_url(self):
        result = json.loads(build_curl_command(""))
        assert result["success"] is False

    def test_invalid_method(self):
        result = json.loads(build_curl_command("https://example.com", method="BOGUS"))
        assert result["success"] is False


class TestDispatch:
    @pytest.mark.asyncio
    async def test_unknown_action(self):
        result = json.loads(await _http_client_dispatch({"action": "nope"}))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_curl_export_action(self):
        result = json.loads(
            await _http_client_dispatch({"action": "curl_export", "url": "https://example.com"})
        )
        assert result["success"] is True
        assert result["command"].startswith("curl")

    def test_schema_registered(self):
        from tools.registry import registry

        entry = registry.get_entry("http_client")
        assert entry is not None
        assert entry.is_async is True
        assert entry.schema["name"] == "http_client"
