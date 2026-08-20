#!/usr/bin/env python3
"""
Passive Recon Tool

Subdomain enumeration and DNS enrichment using only passive sources — the
target's own publicly-exposed Certificate Transparency logs and standard
DNS resolution of names already discovered that way. Safe/legal by
construction: no port scanning, no HTTP requests against the target's own
infrastructure, no brute forcing — only:

1. Certificate Transparency logs via crt.sh's public JSON API
   (https://crt.sh/?q=%25.example.com&output=json) — a passive read of
   certificates the target itself had a CA publish, not a probe of the
   target.
2. Standard DNS resolution (A/AAAA via stdlib ``socket``; CNAME/MX/TXT/NS
   via ``dnspython`` when installed) of the hostnames found in (1) — a
   normal DNS query, the same kind any browser sends, not a scan of the
   target's network.

No active reconnaissance (port scans, service fingerprinting, directory
brute force) belongs here or is performed here — that's a different, more
invasive class of tooling this repo intentionally keeps separate.

Fail-open: crt.sh being unreachable is reported in the result's ``error``
field, never raised. Missing ``dnspython`` degrades gracefully — A/AAAA
records still resolve via stdlib ``socket``; other record types are
reported as unavailable rather than raising an ImportError.

Usage:
    from tools.passive_recon_tool import passive_recon

    result = passive_recon("example.com")
    print(result["subdomains"])
"""

import json
import logging
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_CRTSH_ENDPOINT = os.getenv("CRTSH_ENDPOINT", "https://crt.sh/")
_CRTSH_TIMEOUT = 20  # seconds
_DNS_TIMEOUT = 5  # seconds

DEFAULT_MAX_SUBDOMAINS = 200
DEFAULT_MAX_DNS_LOOKUPS = 200

_HOSTNAME_RE = re.compile(r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))+$")

# Record types resolvable without dnspython (stdlib socket only).
_STDLIB_RECORD_TYPES = {"A", "AAAA"}


def _looks_like_hostname(host: str) -> bool:
    return bool(_HOSTNAME_RE.match(host))


# ---------------------------------------------------------------------------
# Certificate Transparency (crt.sh)
# ---------------------------------------------------------------------------


def _parse_crtsh_loose(text: str) -> List[Dict[str, Any]]:
    """Best-effort recovery when crt.sh returns concatenated JSON objects
    instead of a well-formed array (observed under load on their public
    endpoint). Returns [] if recovery isn't possible."""
    text = text.strip()
    if not text:
        return []
    candidate = "[" + text.replace("}\n{", "},\n{").replace("}{", "},{") + "]"
    try:
        data = json.loads(candidate)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    return []


def query_crtsh(
    domain: str,
    timeout: int = _CRTSH_TIMEOUT,
    endpoint: Optional[str] = None,
) -> List[str]:
    """Query crt.sh's public Certificate Transparency log search for *domain*.

    Returns a sorted, deduplicated list of hostnames found in certificate
    SANs/CNs that end in *domain* (wildcard ``*.`` prefixes stripped).

    Raises the underlying exception (network error, non-2xx, unparsable
    response) on failure — callers that want fail-open behavior should
    catch around this call (see :func:`passive_recon`).
    """
    domain_clean = domain.strip().lower().lstrip(".")
    if not domain_clean:
        raise ValueError("domain is required")

    base = (endpoint or _CRTSH_ENDPOINT).rstrip("/")
    url = f"{base}/?q={urllib.parse.quote('%.' + domain_clean)}&output=json"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "jacky-agent-passive-recon/1.0",
            "Accept": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()

    text = raw.decode("utf-8", errors="replace")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = _parse_crtsh_loose(text)

    if not isinstance(data, list):
        return []

    names: set = set()
    for entry in data:
        if not isinstance(entry, dict):
            continue
        name_value = entry.get("name_value", "") or ""
        for line in name_value.splitlines():
            host = line.strip().lower()
            if host.startswith("*."):
                host = host[2:]
            if not host or not _looks_like_hostname(host):
                continue
            if host == domain_clean or host.endswith("." + domain_clean):
                names.add(host)

    return sorted(names)


# ---------------------------------------------------------------------------
# DNS resolution
# ---------------------------------------------------------------------------


def resolve_a_aaaa(hostname: str, timeout: int = _DNS_TIMEOUT) -> Dict[str, List[str]]:
    """Resolve A/AAAA records for *hostname* via stdlib ``socket`` (no extra deps).

    Never raises — returns empty lists on any resolution failure
    (NXDOMAIN, timeout, no route), since a name found in CT logs may no
    longer resolve (decommissioned host) and that's a normal, expected
    outcome, not an error.
    """
    result: Dict[str, List[str]] = {"A": [], "AAAA": []}
    original_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(timeout)
        infos = socket.getaddrinfo(hostname, None)
    except (socket.gaierror, socket.timeout, OSError):
        return result
    finally:
        socket.setdefaulttimeout(original_timeout)

    for family, _socktype, _proto, _canon, sockaddr in infos:
        ip = sockaddr[0]
        if family == socket.AF_INET and ip not in result["A"]:
            result["A"].append(ip)
        elif family == socket.AF_INET6 and ip not in result["AAAA"]:
            result["AAAA"].append(ip)
    return result


def check_dnspython_available() -> bool:
    try:
        import dns.resolver  # noqa: F401
        return True
    except ImportError:
        return False


def resolve_extended_records(
    hostname: str,
    record_types: List[str],
    timeout: int = _DNS_TIMEOUT,
) -> Dict[str, Optional[List[str]]]:
    """Resolve non-A/AAAA record types (CNAME, MX, TXT, NS, ...) via ``dnspython``.

    Returns ``{record_type: None}`` for every requested type when
    ``dnspython`` isn't installed — a documented "unavailable", not an
    exception — so :func:`passive_recon` keeps working (A/AAAA-only) in a
    minimal environment.
    """
    try:
        import dns.resolver as dns_resolver
        import dns.exception as dns_exception
    except ImportError:
        return {rt: None for rt in record_types}

    out: Dict[str, Optional[List[str]]] = {}
    resolver = dns_resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout
    for rt in record_types:
        try:
            answers = resolver.resolve(hostname, rt)
            out[rt] = sorted({str(r).rstrip(".") for r in answers})
        except dns_exception.DNSException:
            out[rt] = []
        except Exception:  # noqa: BLE001 — defensive: never let one record type kill the scan
            out[rt] = []
    return out


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def passive_recon(
    domain: str,
    resolve_dns: bool = True,
    record_types: Optional[List[str]] = None,
    max_subdomains: int = DEFAULT_MAX_SUBDOMAINS,
    max_dns_lookups: int = DEFAULT_MAX_DNS_LOOKUPS,
    timeout: int = _CRTSH_TIMEOUT,
) -> Dict[str, Any]:
    """Passively enumerate subdomains of *domain* via crt.sh and (optionally) resolve them.

    Args:
        domain: Apex/registrable domain to enumerate, e.g. "example.com".
        resolve_dns: Also resolve DNS records for each discovered hostname (default True).
        record_types: Record types to resolve. A/AAAA always work (stdlib);
            other types (CNAME, MX, TXT, NS, ...) require ``dnspython`` and
            report ``None`` per-type when it isn't installed. Defaults to ["A", "AAAA"].
        max_subdomains: Cap on number of hostnames returned/resolved (default 200).
        max_dns_lookups: Additional cap on how many hostnames get DNS-resolved,
            independent of max_subdomains, to bound total lookup time (default 200).
        timeout: crt.sh request timeout in seconds (default 20).

    Returns:
        {
            "success": bool,
            "domain": str,
            "subdomains": [str, ...],
            "subdomains_found": int,   # total before truncation
            "truncated": bool,
            "dns": {hostname: {"A": [...], "AAAA": [...], ...}},
            "dnspython_available": bool,
            "error": Optional[str],    # set on crt.sh failure (fail-open: not raised)
        }
    """
    result: Dict[str, Any] = {
        "success": False,
        "domain": domain,
        "subdomains": [],
        "subdomains_found": 0,
        "truncated": False,
        "dns": {},
        "dnspython_available": check_dnspython_available(),
        "error": None,
    }

    if not domain or not isinstance(domain, str):
        result["error"] = "domain is required"
        return result

    try:
        subs = query_crtsh(domain, timeout=timeout)
    except Exception as exc:
        logger.debug("passive_recon: crt.sh query failed for %s: %s", domain, exc)
        result["error"] = f"crt.sh unreachable: {exc}"
        return result

    result["subdomains_found"] = len(subs)
    try:
        max_subs = max(1, min(int(max_subdomains) if max_subdomains else DEFAULT_MAX_SUBDOMAINS, 5_000))
    except (TypeError, ValueError):
        max_subs = DEFAULT_MAX_SUBDOMAINS

    if len(subs) > max_subs:
        subs = subs[:max_subs]
        result["truncated"] = True

    result["subdomains"] = subs
    result["success"] = True

    if resolve_dns and subs:
        rts = [rt.strip().upper() for rt in (record_types or ["A", "AAAA"]) if rt and rt.strip()]
        if not rts:
            rts = ["A", "AAAA"]
        extended_types = [rt for rt in rts if rt not in _STDLIB_RECORD_TYPES]

        try:
            max_lookups = max(1, min(int(max_dns_lookups) if max_dns_lookups else DEFAULT_MAX_DNS_LOOKUPS, 5_000))
        except (TypeError, ValueError):
            max_lookups = DEFAULT_MAX_DNS_LOOKUPS

        dns_out: Dict[str, Dict[str, Any]] = {}
        for host in subs[:max_lookups]:
            entry: Dict[str, Any] = {}
            need_stdlib = "A" in rts or "AAAA" in rts
            if need_stdlib:
                resolved = resolve_a_aaaa(host)
                if "A" in rts:
                    entry["A"] = resolved["A"]
                if "AAAA" in rts:
                    entry["AAAA"] = resolved["AAAA"]
            if extended_types:
                entry.update(resolve_extended_records(host, extended_types))
            dns_out[host] = entry
        result["dns"] = dns_out

    return result


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

from tools.registry import registry, tool_error, tool_result  # noqa: E402

PASSIVE_RECON_SCHEMA = {
    "name": "passive_recon",
    "description": (
        "Passive-only subdomain enumeration and DNS enrichment: queries "
        "crt.sh's public Certificate Transparency log search for hostnames "
        "under a domain, then (optionally) resolves DNS records for each "
        "one. Safe/legal by construction — no port scanning, no active "
        "probing beyond standard DNS resolution of names the target already "
        "made public via its own CA-issued certificates. A/AAAA records "
        "always resolve (stdlib); CNAME/MX/TXT/NS require dnspython to be "
        "installed and are reported as unavailable (not an error) otherwise. "
        "Fails open — a crt.sh outage is reported in 'error', never raised."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "domain": {
                "type": "string",
                "description": "Apex/registrable domain to enumerate, e.g. 'example.com'.",
            },
            "resolve_dns": {
                "type": "boolean",
                "description": "Also resolve DNS records for each discovered hostname. Defaults to true.",
                "default": True,
            },
            "record_types": {
                "type": "array",
                "items": {"type": "string", "enum": ["A", "AAAA", "CNAME", "MX", "TXT", "NS"]},
                "description": (
                    "Record types to resolve. A/AAAA always work; CNAME/MX/TXT/NS require "
                    "dnspython. Defaults to ['A', 'AAAA']."
                ),
            },
            "max_subdomains": {
                "type": "integer",
                "description": "Cap on number of hostnames returned/resolved (default 200).",
                "default": DEFAULT_MAX_SUBDOMAINS,
            },
        },
        "required": ["domain"],
    },
}


def _passive_recon_handler(args: Dict[str, Any], **_kw) -> str:
    domain = args.get("domain", "")
    if not domain:
        return tool_error("'domain' is required.")
    resolve_dns = args.get("resolve_dns", True)
    record_types = args.get("record_types")
    try:
        max_subdomains = int(args.get("max_subdomains") or DEFAULT_MAX_SUBDOMAINS)
    except (TypeError, ValueError):
        max_subdomains = DEFAULT_MAX_SUBDOMAINS

    result = passive_recon(
        domain,
        resolve_dns=resolve_dns,
        record_types=record_types,
        max_subdomains=max_subdomains,
    )
    return tool_result(result)


def check_passive_recon_available() -> bool:
    """Always available — pure stdlib (urllib, socket); dnspython is an optional enrichment."""
    return True


registry.register(
    name="passive_recon",
    toolset="passive_recon",
    schema=PASSIVE_RECON_SCHEMA,
    handler=_passive_recon_handler,
    check_fn=check_passive_recon_available,
    emoji="🛰️",
    max_result_size_chars=100_000,
)
