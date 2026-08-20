#!/usr/bin/env python3
"""
HTTP Client Tool

A raw HTTP client for security testing and API debugging: arbitrary
GET/POST/PUT/DELETE/OPTIONS/HEAD requests with custom headers, query
params, body, and cookies; TLS certificate inspection for any
host:port (cipher, expiry, SANs, issuer — no HTTP request involved);
and cURL command export for reproducibility (e.g. for a bug bounty
report or handoff to another tool).

This is a single compressed tool dispatched by ``action``, following the
same action-dispatch convention as ``tools/cronjob_tools.py`` /
``tools/kanban_tools.py``.

Actions:
    request      - Perform a raw HTTP request, return status/headers/body.
    tls_info     - Inspect the TLS certificate presented by host:port.
    curl_export  - Render the request as a reproducible curl command
                   (no network call).

Security:
    - ``request`` and ``tls_info`` run the same SSRF gate the rest of the
      codebase uses (``tools.url_safety.async_is_safe_url`` /
      ``is_safe_url``) so private/internal targets are blocked by default,
      matching ``web_extract_tool``.
    - URLs containing an embedded credential (API-key-shaped token) are
      rejected before any request is made, matching ``web_extract_tool``.
    - Response bodies are truncated with ``tools.file_tools._truncate_to_char_budget``
      (the same head-preserving char-budget truncator ``read_file`` uses)
      so a huge response can't blow the model's context.
    - Response headers/body are passed through ``agent.redact.redact_sensitive_text``
      before being returned to the model, so a target that echoes back an
      Authorization header (or similar) doesn't leak it into the transcript.

Usage:
    from tools.http_client_tool import http_request, tls_cert_info, build_curl_command
"""

import json
import logging
import shlex
import socket
import ssl
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urlparse

import httpx

from agent.redact import _PREFIX_RE, redact_sensitive_text
from tools.file_tools import _truncate_to_char_budget
from tools.url_safety import async_is_safe_url, normalize_url_for_request, sensitive_query_param_name

logger = logging.getLogger(__name__)

# Methods this tool is willing to issue. Kept explicit (not "anything httpx
# supports") so a typo doesn't silently become a GET.
_ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"}

# Response body char budget sent back to the model. Mirrors web_tools'
# DEFAULT_EXTRACT_CHAR_LIMIT order of magnitude — generous for headers/JSON
# bodies inspected during API testing, without risking a multi-MB body
# blowing out context.
DEFAULT_BODY_CHAR_LIMIT = 20_000

# Hard request timeout (seconds) — a hung target must not hang the agent.
DEFAULT_TIMEOUT = 30.0


def _normalize_headers(headers: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if not headers:
        return {}
    return {str(k): str(v) for k, v in headers.items()}


def _normalize_params(params: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if not params:
        return {}
    return {str(k): str(v) for k, v in params.items()}


def _normalize_cookies(cookies: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if not cookies:
        return {}
    return {str(k): str(v) for k, v in cookies.items()}


def _blocked_url_reason(url: str) -> Optional[str]:
    """Return a rejection reason if *url* embeds a credential-shaped token
    or a sensitive query param, or None if it's clear to send.

    Mirrors the guard ``web_extract_tool`` applies before dispatching to a
    backend (``tools/web_tools.py``), reusing the same maintained secret
    prefix regex (``agent.redact._PREFIX_RE``) rather than duplicating it.
    """
    from urllib.parse import unquote

    if _PREFIX_RE.search(url) or _PREFIX_RE.search(unquote(url)):
        return (
            "Blocked: URL contains what appears to be an API key or token. "
            "Pass secrets via the headers/params/cookies fields, not embedded in the URL."
        )
    sensitive_key = sensitive_query_param_name(url)
    if sensitive_key:
        return (
            f"Blocked: URL contains a credential-like query parameter ({sensitive_key}). "
            "Pass it via the params field instead so it isn't logged as part of the raw URL."
        )
    return None


async def http_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    body: Optional[Any] = None,
    cookies: Optional[Dict[str, Any]] = None,
    timeout: float = DEFAULT_TIMEOUT,
    follow_redirects: bool = True,
    body_char_limit: Optional[int] = None,
) -> str:
    """Perform a raw HTTP request and return status/headers/body as JSON.

    Args:
        url: Target URL (scheme required).
        method: HTTP method — one of GET/POST/PUT/DELETE/OPTIONS/HEAD/PATCH.
        headers: Optional request headers.
        params: Optional query string params (merged with any already on the URL).
        body: Optional request body. A dict/list is sent as JSON
            (Content-Type: application/json, unless overridden in ``headers``);
            a string is sent as-is (raw text/form body).
        cookies: Optional cookies to send.
        timeout: Request timeout in seconds (default 30).
        follow_redirects: Whether to follow HTTP redirects (default True).
        body_char_limit: Optional response-body char budget (default 20000).

    Returns:
        JSON string: {"success": bool, "status_code": int, "headers": {...},
        "body": str, "elapsed_ms": float, "truncated": bool, "error": str|None}
    """
    method_upper = (method or "GET").strip().upper()
    if method_upper not in _ALLOWED_METHODS:
        return json.dumps(
            {
                "success": False,
                "error": f"Unsupported method {method!r}. Allowed: {sorted(_ALLOWED_METHODS)}",
            },
            ensure_ascii=False,
        )

    if not url or not isinstance(url, str):
        return json.dumps({"success": False, "error": "url is required"}, ensure_ascii=False)

    normalized_url = normalize_url_for_request(url)
    reject_reason = _blocked_url_reason(url) or _blocked_url_reason(normalized_url)
    if reject_reason:
        return json.dumps({"success": False, "error": reject_reason}, ensure_ascii=False)

    if not await async_is_safe_url(normalized_url):
        return json.dumps(
            {
                "success": False,
                "error": "Blocked: URL targets a private or internal network address",
            },
            ensure_ascii=False,
        )

    req_headers = _normalize_headers(headers)
    req_params = _normalize_params(params)
    req_cookies = _normalize_cookies(cookies)

    json_body = None
    content_body = None
    if body is not None:
        if isinstance(body, (dict, list)):
            json_body = body
        else:
            content_body = str(body)

    try:
        clamped_timeout = max(1.0, min(float(timeout) if timeout else DEFAULT_TIMEOUT, 120.0))
    except (TypeError, ValueError):
        clamped_timeout = DEFAULT_TIMEOUT

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(
            timeout=clamped_timeout,
            follow_redirects=bool(follow_redirects),
            cookies=req_cookies,
        ) as client:
            response = await client.request(
                method_upper,
                normalized_url,
                headers=req_headers,
                params=req_params,
                json=json_body,
                content=content_body,
            )
    except httpx.TimeoutException:
        return json.dumps(
            {"success": False, "error": f"Request timed out after {clamped_timeout}s"},
            ensure_ascii=False,
        )
    except httpx.HTTPError as exc:
        return json.dumps(
            {"success": False, "error": f"Request failed: {redact_sensitive_text(str(exc))}"},
            ensure_ascii=False,
        )
    except Exception as exc:  # noqa: BLE001 — surfaced to the model as a normal tool error
        return json.dumps(
            {"success": False, "error": f"Unexpected error: {redact_sensitive_text(str(exc))}"},
            ensure_ascii=False,
        )
    elapsed_ms = round((time.monotonic() - start) * 1000, 1)

    try:
        char_limit = int(body_char_limit) if body_char_limit else DEFAULT_BODY_CHAR_LIMIT
    except (TypeError, ValueError):
        char_limit = DEFAULT_BODY_CHAR_LIMIT
    char_limit = max(500, min(char_limit, 500_000))

    raw_body_text = response.text
    body_text, _kept_lines, truncated = _truncate_to_char_budget(raw_body_text, char_limit)
    if truncated:
        body_text += (
            f"\n\n[... truncated {len(raw_body_text):,} -> {len(body_text):,} chars; "
            "raise body_char_limit for more ...]"
        )

    resp_headers = {k: v for k, v in response.headers.items()}
    result = {
        "success": True,
        "status_code": response.status_code,
        "reason_phrase": response.reason_phrase,
        "headers": redact_sensitive_text(json.dumps(resp_headers, ensure_ascii=False), force=True, file_read=True),
        "body": redact_sensitive_text(body_text, force=True, file_read=True),
        "elapsed_ms": elapsed_ms,
        "truncated": truncated,
        "final_url": str(response.url),
        "error": None,
    }
    # headers was serialized then redacted as a JSON string to reuse the
    # single redact pass; deserialize back to a dict for the caller.
    try:
        result["headers"] = json.loads(result["headers"])
    except (TypeError, ValueError, json.JSONDecodeError):
        pass  # leave as the redacted string if it somehow doesn't round-trip

    return json.dumps(result, ensure_ascii=False)


async def tls_cert_info(host: str, port: Optional[int] = None, timeout: float = 10.0) -> str:
    """Inspect the TLS certificate a host presents, without an HTTP request.

    Uses the stdlib ``ssl``/``socket`` modules to open a TLS connection and
    read the peer certificate's subject, issuer, SANs, validity window, and
    negotiated cipher/protocol — useful for checking expiry, weak ciphers,
    or hostname/SAN mismatches ahead of (or instead of) an HTTP request.

    Args:
        host: Hostname (or IP) to connect to.
        port: TCP port (default 443).
        timeout: Connection timeout in seconds (default 10).

    Returns:
        JSON string: {"success": bool, "subject": {...}, "issuer": {...},
        "san": [...], "not_before": str, "not_after": str, "expired": bool,
        "days_until_expiry": int, "cipher": str, "tls_version": str,
        "protocol": str, "serial_number": str, "error": str|None}
    """
    if not host or not isinstance(host, str):
        return json.dumps({"success": False, "error": "host is required"}, ensure_ascii=False)
    host = host.strip()
    # Strip an accidental scheme/path — this is a bare host:port inspector.
    # If the caller passed a full URL and didn't override ``port``, the
    # URL's own port (if any) is honored — otherwise default to 443.
    url_port: Optional[int] = None
    if "://" in host:
        parsed = urlparse(host)
        url_port = parsed.port
        host = parsed.hostname or host
    host = host.split("/")[0]

    try:
        if port:
            port_int = int(port)
        elif url_port:
            port_int = url_port
        else:
            port_int = 443
    except (TypeError, ValueError):
        port_int = 443
    port_int = max(1, min(port_int, 65535))

    try:
        clamped_timeout = max(1.0, min(float(timeout) if timeout else 10.0, 60.0))
    except (TypeError, ValueError):
        clamped_timeout = 10.0

    if not await async_is_safe_url(f"https://{host}:{port}"):
        return json.dumps(
            {
                "success": False,
                "error": "Blocked: host resolves to a private or internal network address",
            },
            ensure_ascii=False,
        )

    import asyncio

    return await asyncio.to_thread(_tls_cert_info_sync, host, port_int, clamped_timeout)


def _tls_cert_info_sync(host: str, port: int, timeout: float) -> str:
    """Blocking socket/TLS handshake — run via ``asyncio.to_thread`` so it
    doesn't block the event loop. The SSRF guard runs before this is called."""
    context = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as tls_sock:
                cert = tls_sock.getpeercert()
                cipher_name, tls_version, _bits = tls_sock.cipher()
                protocol = tls_sock.version()
    except ssl.SSLCertVerificationError as exc:
        # Still worth reporting — retry without verification so an expired /
        # self-signed / hostname-mismatched cert can be inspected rather than
        # just erroring out. This is a read-only inspection tool, not a trust
        # decision, so relaxing verification here is safe.
        try:
            insecure_ctx = ssl.create_default_context()
            insecure_ctx.check_hostname = False
            insecure_ctx.verify_mode = ssl.CERT_NONE
            with socket.create_connection((host, port), timeout=timeout) as sock:
                with insecure_ctx.wrap_socket(sock, server_hostname=host) as tls_sock:
                    cert = tls_sock.getpeercert()
                    cipher_name, tls_version, _bits = tls_sock.cipher()
                    protocol = tls_sock.version()
            verification_note = f"Certificate did not verify: {exc}"
        except Exception as inner_exc:  # noqa: BLE001
            return json.dumps(
                {
                    "success": False,
                    "error": f"TLS verification failed and unverified retry also failed: {exc}; {inner_exc}",
                },
                ensure_ascii=False,
            )
    except (socket.timeout, TimeoutError):
        return json.dumps(
            {"success": False, "error": f"Connection to {host}:{port} timed out"},
            ensure_ascii=False,
        )
    except (socket.gaierror, ConnectionRefusedError, OSError) as exc:
        return json.dumps(
            {"success": False, "error": f"Could not connect to {host}:{port}: {exc}"},
            ensure_ascii=False,
        )
    else:
        verification_note = None

    return json.dumps(_format_cert_result(cert, cipher_name, tls_version, protocol, verification_note), ensure_ascii=False)


def _format_cert_result(
    cert: Optional[Dict[str, Any]],
    cipher_name: Optional[str],
    tls_version: Optional[str],
    protocol: Optional[str],
    verification_note: Optional[str],
) -> Dict[str, Any]:
    if not cert:
        return {
            "success": True,
            "warning": "No certificate details returned by peer (unverified connection?)",
            "cipher": cipher_name,
            "tls_version": tls_version,
            "protocol": protocol,
        }

    def _tuple_to_dict(pairs) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for rdn in pairs or ():
            for key, value in rdn:
                out[key] = value
        return out

    subject = _tuple_to_dict(cert.get("subject"))
    issuer = _tuple_to_dict(cert.get("issuer"))
    san = [v for k, v in cert.get("subjectAltName", []) if k == "DNS"]

    not_before_str = cert.get("notBefore")
    not_after_str = cert.get("notAfter")
    expired = None
    days_until_expiry = None
    if not_after_str:
        try:
            not_after_dt = ssl.cert_time_to_seconds(not_after_str)
            import datetime

            now = datetime.datetime.now(datetime.timezone.utc).timestamp()
            expired = now > not_after_dt
            days_until_expiry = int((not_after_dt - now) / 86400)
        except Exception:  # noqa: BLE001
            pass

    result = {
        "success": True,
        "subject": subject,
        "issuer": issuer,
        "san": san,
        "not_before": not_before_str,
        "not_after": not_after_str,
        "expired": expired,
        "days_until_expiry": days_until_expiry,
        "serial_number": cert.get("serialNumber"),
        "cipher": cipher_name,
        "tls_version": tls_version,
        "protocol": protocol,
        "error": None,
    }
    if verification_note:
        result["verification_warning"] = verification_note
    return result


def build_curl_command(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    body: Optional[Any] = None,
    cookies: Optional[Dict[str, Any]] = None,
) -> str:
    """Render a request as a reproducible, copy-pasteable curl command.

    Makes no network call. Values are shell-quoted with ``shlex.quote`` so
    the emitted command is safe to paste into a shell/report as-is.

    Args:
        url: Target URL.
        method: HTTP method (default GET).
        headers: Optional request headers.
        params: Optional query string params appended to the URL.
        body: Optional request body — dict/list is emitted as ``--data`` JSON
            with a Content-Type header (unless already set); a string is
            emitted as raw ``--data``.
        cookies: Optional cookies, emitted via ``-b``.

    Returns:
        JSON string: {"success": bool, "command": str, "error": str|None}
    """
    if not url or not isinstance(url, str):
        return json.dumps({"success": False, "error": "url is required"}, ensure_ascii=False)

    method_upper = (method or "GET").strip().upper()
    if method_upper not in _ALLOWED_METHODS:
        return json.dumps(
            {
                "success": False,
                "error": f"Unsupported method {method!r}. Allowed: {sorted(_ALLOWED_METHODS)}",
            },
            ensure_ascii=False,
        )

    req_params = _normalize_params(params)
    final_url = url
    if req_params:
        parsed = urlparse(url)
        sep = "&" if parsed.query else "?"
        final_url = f"{url}{sep}{urlencode(req_params)}"

    parts: List[str] = ["curl", "-sS"]
    if method_upper != "GET":
        parts += ["-X", shlex.quote(method_upper)]

    req_headers = _normalize_headers(headers)
    has_content_type = any(k.lower() == "content-type" for k in req_headers)

    data_flag = None
    if body is not None:
        if isinstance(body, (dict, list)):
            data_flag = json.dumps(body, ensure_ascii=False)
            if not has_content_type:
                req_headers["Content-Type"] = "application/json"
        else:
            data_flag = str(body)

    for key, value in req_headers.items():
        parts += ["-H", shlex.quote(f"{key}: {value}")]

    req_cookies = _normalize_cookies(cookies)
    if req_cookies:
        cookie_str = "; ".join(f"{k}={v}" for k, v in req_cookies.items())
        parts += ["-b", shlex.quote(cookie_str)]

    if data_flag is not None:
        parts += ["--data", shlex.quote(data_flag)]

    parts.append(shlex.quote(final_url))

    return json.dumps({"success": True, "command": " ".join(parts), "error": None}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
from tools.registry import registry, tool_error  # noqa: E402


async def _http_client_dispatch(args: Dict[str, Any], **_kw) -> str:
    action = (args.get("action") or "").strip().lower()

    if action == "request":
        return await http_request(
            url=args.get("url", ""),
            method=args.get("method", "GET"),
            headers=args.get("headers"),
            params=args.get("params"),
            body=args.get("body"),
            cookies=args.get("cookies"),
            timeout=args.get("timeout", DEFAULT_TIMEOUT),
            follow_redirects=args.get("follow_redirects", True),
            body_char_limit=args.get("body_char_limit"),
        )
    if action == "tls_info":
        host = args.get("host") or args.get("url") or ""
        return await tls_cert_info(
            host=host,
            port=args.get("port"),
            timeout=args.get("timeout", 10.0),
        )
    if action == "curl_export":
        return build_curl_command(
            url=args.get("url", ""),
            method=args.get("method", "GET"),
            headers=args.get("headers"),
            params=args.get("params"),
            body=args.get("body"),
            cookies=args.get("cookies"),
        )

    return tool_error(f"Unknown http_client action '{action}'. Use request, tls_info, or curl_export.")


HTTP_CLIENT_SCHEMA = {
    "name": "http_client",
    "description": (
        "Raw HTTP client for API testing and web security work. "
        "action='request' sends a GET/POST/PUT/DELETE/OPTIONS/HEAD/PATCH request with custom "
        "headers/params/body/cookies and returns status/headers/body. "
        "action='tls_info' inspects the TLS certificate a host:port presents (issuer, subject, "
        "SANs, expiry, cipher) without issuing an HTTP request. "
        "action='curl_export' renders the same request as a copy-pasteable curl command for "
        "reproduction in a report — no network call. "
        "SSRF-guarded: requests to private/internal network addresses are blocked, and URLs "
        "containing embedded credentials are rejected (pass secrets via headers/params/cookies)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["request", "tls_info", "curl_export"],
                "description": "Which operation to perform.",
            },
            "url": {
                "type": "string",
                "description": "Target URL. Required for request/curl_export; also accepted for tls_info (host is extracted from it).",
            },
            "host": {
                "type": "string",
                "description": "For action=tls_info: bare hostname or IP (alternative to url).",
            },
            "port": {
                "type": "integer",
                "description": "For action=tls_info: TCP port (default 443).",
                "default": 443,
            },
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
                "description": "HTTP method. Default GET.",
                "default": "GET",
            },
            "headers": {
                "type": "object",
                "description": "Optional request headers as a flat string->string object.",
            },
            "params": {
                "type": "object",
                "description": "Optional query-string params as a flat string->string object.",
            },
            "body": {
                "description": "Optional request body. Object/array is sent as JSON; a string is sent raw.",
            },
            "cookies": {
                "type": "object",
                "description": "Optional cookies as a flat string->string object.",
            },
            "timeout": {
                "type": "number",
                "description": "Timeout in seconds (default 30 for request, 10 for tls_info; max 120/60).",
            },
            "follow_redirects": {
                "type": "boolean",
                "description": "For action=request: follow HTTP redirects (default true).",
                "default": True,
            },
            "body_char_limit": {
                "type": "integer",
                "description": "For action=request: response body char budget sent back (default 20000).",
            },
        },
        "required": ["action"],
    },
}


def check_http_client_available() -> bool:
    """Always available — stdlib ssl/socket + the httpx dependency the rest of the codebase already requires."""
    return True


registry.register(
    name="http_client",
    toolset="http_client",
    schema=HTTP_CLIENT_SCHEMA,
    handler=_http_client_dispatch,
    check_fn=check_http_client_available,
    is_async=True,
    emoji="🌐",
    max_result_size_chars=150_000,
)
