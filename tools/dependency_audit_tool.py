#!/usr/bin/env python3
"""
Dependency / SCA (Software Composition Analysis) Audit Tool

Parses common dependency manifests (package.json, requirements.txt,
pyproject.toml, go.mod, Cargo.lock) and queries the free, public OSV.dev
API (https://osv.dev/docs/#tag/api) for known vulnerabilities affecting the
resolved package/version pairs.

This is a *general* SCA scanner over a project's declared/resolved
dependencies. It is distinct from ``tools/osv_check.py``, which only checks
a single MCP extension package (npx/uvx argv) for MAL-* malware advisories
immediately before launching it — that module is reused here for its
proven, fail-open OSV HTTP request pattern, but this tool covers full
manifests and all (not just malware) advisory classes.

The OSV API is free, public, and requires no auth key. Two endpoints are
used:
    POST https://api.osv.dev/v1/querybatch  — bulk vuln-ID lookup (cheap,
        returns only ``{id, modified}`` per hit)
    POST https://api.osv.dev/v1/vulns/{id}  — GET, full advisory detail
        (summary, severity, aliases) for a capped number of top hits

Fail-open: network errors never raise out of the public entry points —
they are reported in the result's ``error`` field so a caller can decide
whether to treat "audit unreachable" as blocking or not.

Usage:
    from tools.dependency_audit_tool import audit_dependencies

    result = audit_dependencies("/path/to/project")
    print(result["summary"])
"""

import json
import logging
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_OSV_QUERYBATCH_ENDPOINT = os.getenv(
    "OSV_QUERYBATCH_ENDPOINT", "https://api.osv.dev/v1/querybatch"
)
_OSV_VULN_ENDPOINT = os.getenv("OSV_VULN_ENDPOINT", "https://api.osv.dev/v1/vulns")
_TIMEOUT = 15  # seconds
_MAX_DETAIL_FETCHES = 25  # cap enrichment calls per audit run
_MAX_DEPS_PER_QUERY = 1000  # OSV querybatch practical batch ceiling

# Manifest filename -> parser function name, resolved at call time to avoid
# forward references.
_MANIFEST_FILENAMES = {
    "package.json": "parse_package_json",
    "requirements.txt": "parse_requirements_txt",
    "pyproject.toml": "parse_pyproject_toml",
    "go.mod": "parse_go_mod",
    "Cargo.lock": "parse_cargo_lock",
}


# ---------------------------------------------------------------------------
# Manifest parsers — each returns List[(name, version, ecosystem)].
# ``version`` may be None when a manifest declares a range instead of a
# resolved/pinned version (e.g. package.json's "^1.2.3", requirements.txt's
# unpinned "requests"); OSV's ``query`` endpoint accepts a bare package name
# with no version and returns vulns for all versions in that case.
# ---------------------------------------------------------------------------


def parse_package_json(content: str) -> List[Tuple[str, Optional[str], str]]:
    """Parse npm package.json 'dependencies' + 'devDependencies' into (name, version, 'npm')."""
    deps: List[Tuple[str, Optional[str], str]] = []
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return deps

    for key in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        section = data.get(key)
        if not isinstance(section, dict):
            continue
        for name, spec in section.items():
            if not isinstance(name, str) or not isinstance(spec, str):
                continue
            version = _clean_semver_range(spec)
            deps.append((name, version, "npm"))
    return deps


def _clean_semver_range(spec: str) -> Optional[str]:
    """Strip npm range prefixes (^, ~, >=, etc.) to get a bare version, when possible."""
    spec = spec.strip()
    # Anything that isn't a plain pinned version (ranges, git urls, "workspace:*",
    # "file:...", "*", "latest") is left as None — OSV can't resolve a range.
    match = re.match(r"^[\^~]?(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?)$", spec)
    if match:
        return match.group(1)
    if re.match(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?$", spec):
        return spec
    return None


def parse_requirements_txt(content: str) -> List[Tuple[str, Optional[str], str]]:
    """Parse a pip requirements.txt into (name, version, 'PyPI') tuples.

    Handles ``name==1.2.3``, ``name>=1.0,<2.0`` (version dropped — range),
    ``name[extra]==1.2.3``, comments, and ``-r other.txt`` / ``-e .`` lines
    (skipped: not a resolvable package).
    """
    deps: List[Tuple[str, Optional[str], str]] = []
    for raw_line in content.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith(("-r", "-e", "--", "-c")):
            continue
        # Strip environment markers: "name==1.2.3; python_version>='3.8'"
        line = line.split(";", 1)[0].strip()
        match = re.match(
            r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*(==)?\s*([0-9][A-Za-z0-9.\-+]*)?", line
        )
        if not match:
            continue
        name = match.group(1)
        pinned = match.group(2)
        version = match.group(3) if pinned else None
        if not name:
            continue
        deps.append((name, version, "PyPI"))
    return deps


def parse_pyproject_toml(content: str) -> List[Tuple[str, Optional[str], str]]:
    """Best-effort pyproject.toml dependency extraction (PEP 621 + Poetry).

    Uses ``tomllib``/``tomli`` when available for correctness; falls back to
    a line-scan regex so the tool still works on Python < 3.11 without the
    ``tomli`` backport installed.
    """
    data = _load_toml(content)
    deps: List[Tuple[str, Optional[str], str]] = []

    if data is not None:
        project = data.get("project", {})
        for spec in project.get("dependencies", []) or []:
            name, version = _parse_pep508(spec)
            if name:
                deps.append((name, version, "PyPI"))
        opt_deps = project.get("optional-dependencies", {})
        if isinstance(opt_deps, dict):
            for group in opt_deps.values():
                for spec in group or []:
                    name, version = _parse_pep508(spec)
                    if name:
                        deps.append((name, version, "PyPI"))

        poetry = data.get("tool", {}).get("poetry", {})
        for section_name in ("dependencies", "dev-dependencies"):
            section = poetry.get(section_name, {})
            if isinstance(section, dict):
                for name, spec in section.items():
                    if name.lower() == "python":
                        continue
                    version = None
                    if isinstance(spec, str):
                        version = _clean_semver_range(spec.lstrip("^~"))
                        if version is None and re.match(r"^\d+\.\d+\.\d+$", spec.lstrip("^~=")):
                            version = spec.lstrip("^~=")
                    elif isinstance(spec, dict):
                        version = _clean_semver_range(str(spec.get("version", "")).lstrip("^~"))
                    deps.append((name, version, "PyPI"))
        return deps

    # Fallback: regex scan for `"name==1.2.3"` / `"name>=1.2.3"` style entries
    # inside dependencies = [ ... ] blocks.
    in_deps_block = False
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if re.match(r"^dependencies\s*=\s*\[", line):
            in_deps_block = True
            if line.rstrip().endswith("]"):
                in_deps_block = False
            continue
        if in_deps_block:
            if line.startswith("]"):
                in_deps_block = False
                continue
            m = re.search(r'"([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:==\s*([0-9][A-Za-z0-9.\-+]*))?', line)
            if m:
                deps.append((m.group(1), m.group(2), "PyPI"))
    return deps


def _load_toml(content: str) -> Optional[dict]:
    try:
        import tomllib  # Python 3.11+
        return tomllib.loads(content)
    except ImportError:
        pass
    try:
        import tomli  # type: ignore
        return tomli.loads(content)
    except Exception:
        return None


def _parse_pep508(spec: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse a PEP 508 dependency string: 'name[extra]==1.2.3' / 'name>=1.0'."""
    spec = spec.strip()
    m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)", spec)
    if not m:
        return None, None
    name = m.group(1)
    version_match = re.search(r"==\s*([0-9][A-Za-z0-9.\-+]*)", spec)
    version = version_match.group(1) if version_match else None
    return name, version


def parse_go_mod(content: str) -> List[Tuple[str, Optional[str], str]]:
    """Parse go.mod 'require' directives into (module_path, version, 'Go')."""
    deps: List[Tuple[str, Optional[str], str]] = []
    in_require_block = False
    for raw_line in content.splitlines():
        line = raw_line.split("//", 1)[0].strip()
        if not line:
            continue
        if line.startswith("require ("):
            in_require_block = True
            continue
        if in_require_block and line == ")":
            in_require_block = False
            continue

        if in_require_block:
            m = re.match(r"^([^\s]+)\s+(v[0-9][^\s]*)", line)
        else:
            m = re.match(r"^require\s+([^\s]+)\s+(v[0-9][^\s]*)", line)
        if m:
            module_path, version = m.group(1), m.group(2)
            deps.append((module_path, version, "Go"))
    return deps


def parse_cargo_lock(content: str) -> List[Tuple[str, Optional[str], str]]:
    """Parse Cargo.lock '[[package]]' entries into (name, version, 'crates.io')."""
    deps: List[Tuple[str, Optional[str], str]] = []
    name: Optional[str] = None
    version: Optional[str] = None
    in_package = False
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line == "[[package]]":
            if in_package and name and version:
                deps.append((name, version, "crates.io"))
            in_package = True
            name, version = None, None
            continue
        if not in_package:
            continue
        m_name = re.match(r'^name\s*=\s*"([^"]+)"', line)
        if m_name:
            name = m_name.group(1)
            continue
        m_version = re.match(r'^version\s*=\s*"([^"]+)"', line)
        if m_version:
            version = m_version.group(1)
            continue
    if in_package and name and version:
        deps.append((name, version, "crates.io"))
    return deps


_PARSERS = {
    "package.json": parse_package_json,
    "requirements.txt": parse_requirements_txt,
    "pyproject.toml": parse_pyproject_toml,
    "go.mod": parse_go_mod,
    "Cargo.lock": parse_cargo_lock,
}


def parse_manifest(filename: str, content: str) -> List[Tuple[str, Optional[str], str]]:
    """Dispatch to the correct parser based on manifest basename.

    Returns [] for unrecognized filenames.
    """
    base = os.path.basename(filename)
    # requirements*.txt variants (requirements-dev.txt, etc.)
    if base == "requirements.txt" or (base.startswith("requirements") and base.endswith(".txt")):
        return parse_requirements_txt(content)
    parser = _PARSERS.get(base)
    if parser is None:
        return []
    return parser(content)


def find_manifests(project_dir: str, max_depth: int = 4) -> List[str]:
    """Walk *project_dir* (bounded depth) and return manifest file paths found."""
    found: List[str] = []
    base_depth = project_dir.rstrip(os.sep).count(os.sep)
    skip_dirs = {"node_modules", ".git", "venv", ".venv", "__pycache__", "dist", "build", "target"}
    for root, dirs, files in os.walk(project_dir):
        depth = root.rstrip(os.sep).count(os.sep) - base_depth
        if depth >= max_depth:
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fname in files:
            base = os.path.basename(fname)
            is_reqs = base == "requirements.txt" or (base.startswith("requirements") and base.endswith(".txt"))
            if base in _MANIFEST_FILENAMES or is_reqs:
                found.append(os.path.join(root, fname))
    return found


# ---------------------------------------------------------------------------
# OSV.dev querying
# ---------------------------------------------------------------------------


def build_osv_batch_query(
    deps: List[Tuple[str, Optional[str], str]]
) -> Dict[str, Any]:
    """Build a well-formed OSV /v1/querybatch request body from parsed deps.

    Deduplicates (name, version, ecosystem) triples. Each query entry follows
    the documented shape:
        {"package": {"name": ..., "ecosystem": ...}, "version": ...}
    ``version`` is omitted when unknown (unpinned/ranged dependency) — OSV
    then matches vulnerabilities across all known versions of the package.
    """
    seen = set()
    queries = []
    for name, version, ecosystem in deps:
        key = (name, version, ecosystem)
        if key in seen:
            continue
        seen.add(key)
        query: Dict[str, Any] = {"package": {"name": name, "ecosystem": ecosystem}}
        if version:
            query["version"] = version
        queries.append(query)
    return {"queries": queries[:_MAX_DEPS_PER_QUERY]}


def query_osv_batch(
    deps: List[Tuple[str, Optional[str], str]],
    endpoint: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """POST a batch query to OSV.dev. Returns the raw 'results' list.

    Each element of the returned list corresponds positionally to the
    deduplicated query built by :func:`build_osv_batch_query` and has the
    shape ``{"vulns": [{"id": ..., "modified": ...}, ...]}`` (batch results
    are intentionally minimal — see :func:`fetch_vuln_details` for full
    advisory data).

    Raises the underlying exception on network failure; callers that want
    fail-open behavior should catch around this call (see
    :func:`audit_dependencies`).
    """
    payload = build_osv_batch_query(deps)
    if not payload["queries"]:
        return []

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint or _OSV_QUERYBATCH_ENDPOINT,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "jacky-agent-dependency-audit/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        result = json.loads(resp.read())
    return result.get("results", [])


def fetch_vuln_details(vuln_id: str, endpoint: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """GET full advisory details for a single OSV vuln ID (summary, severity, aliases)."""
    url = f"{endpoint or _OSV_VULN_ENDPOINT}/{vuln_id}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "jacky-agent-dependency-audit/1.0"}, method="GET"
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def _extract_severity(detail: Dict[str, Any]) -> Optional[str]:
    """Best-effort severity string from an OSV advisory (CVSS vector or score)."""
    for sev in detail.get("severity", []) or []:
        if sev.get("type", "").startswith("CVSS"):
            return sev.get("score")
    db_specific = detail.get("database_specific", {}) or {}
    if "severity" in db_specific:
        return db_specific["severity"]
    return None


# ---------------------------------------------------------------------------
# Top-level audit entry point
# ---------------------------------------------------------------------------


def audit_dependencies(
    project_dir: str,
    enrich: bool = True,
) -> Dict[str, Any]:
    """Scan *project_dir* for supported manifests and audit them against OSV.dev.

    Returns a dict:
        {
            "manifests_found": [paths],
            "dependencies_scanned": int,
            "vulnerable_dependencies": [
                {"name", "version", "ecosystem", "manifest",
                 "vulns": [{"id", "summary", "severity"}]}
            ],
            "error": Optional[str]   # set on network failure (fail-open: not raised)
        }
    """
    result: Dict[str, Any] = {
        "manifests_found": [],
        "dependencies_scanned": 0,
        "vulnerable_dependencies": [],
        "error": None,
    }

    if os.path.isfile(project_dir):
        manifest_paths = [project_dir]
    else:
        manifest_paths = find_manifests(project_dir)
    result["manifests_found"] = manifest_paths

    if not manifest_paths:
        return result

    # (name, version, ecosystem, manifest_path)
    all_deps: List[Tuple[str, Optional[str], str, str]] = []
    for path in manifest_paths:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError as exc:
            logger.debug("Could not read manifest %s: %s", path, exc)
            continue
        for name, version, ecosystem in parse_manifest(path, content):
            all_deps.append((name, version, ecosystem, path))

    result["dependencies_scanned"] = len(all_deps)
    if not all_deps:
        return result

    dedup_deps = [(n, v, e) for n, v, e, _ in all_deps]
    try:
        batch_results = query_osv_batch(dedup_deps)
    except Exception as exc:
        # Fail-open: report the audit as inconclusive rather than raising.
        logger.debug("OSV querybatch failed (audit inconclusive): %s", exc)
        result["error"] = f"OSV.dev unreachable: {exc}"
        return result

    # Map deduplicated query index back to every (dep, manifest) that produced it.
    seen_order: List[Tuple[str, Optional[str], str]] = []
    seen_set = set()
    for n, v, e, _ in all_deps:
        key = (n, v, e)
        if key not in seen_set:
            seen_set.add(key)
            seen_order.append(key)

    manifests_by_key: Dict[Tuple[str, Optional[str], str], List[str]] = {}
    for n, v, e, path in all_deps:
        manifests_by_key.setdefault((n, v, e), []).append(path)

    detail_fetch_budget = _MAX_DETAIL_FETCHES
    for idx, batch_entry in enumerate(batch_results):
        if idx >= len(seen_order):
            break
        vulns = batch_entry.get("vulns", []) or []
        if not vulns:
            continue
        name, version, ecosystem = seen_order[idx]

        vuln_summaries = []
        for v in vulns:
            vid = v.get("id", "")
            summary, severity = None, None
            if enrich and detail_fetch_budget > 0:
                detail = fetch_vuln_details(vid)
                detail_fetch_budget -= 1
                if detail:
                    summary = detail.get("summary") or detail.get("details", "")[:200]
                    severity = _extract_severity(detail)
            vuln_summaries.append({"id": vid, "summary": summary, "severity": severity})

        for manifest_path in manifests_by_key.get((name, version, ecosystem), [project_dir]):
            result["vulnerable_dependencies"].append(
                {
                    "name": name,
                    "version": version,
                    "ecosystem": ecosystem,
                    "manifest": manifest_path,
                    "vulns": vuln_summaries,
                }
            )

    return result


def format_audit_report(result: Dict[str, Any]) -> str:
    """Render an :func:`audit_dependencies` result as a human-readable report."""
    lines = []
    lines.append(f"Manifests scanned: {len(result.get('manifests_found', []))}")
    lines.append(f"Dependencies scanned: {result.get('dependencies_scanned', 0)}")
    if result.get("error"):
        lines.append(f"WARNING: {result['error']}")

    vulnerable = result.get("vulnerable_dependencies", [])
    if not vulnerable:
        lines.append("No known vulnerabilities found." if not result.get("error") else "Audit incomplete.")
        return "\n".join(lines)

    lines.append(f"\nFound {len(vulnerable)} vulnerable dependency instance(s):\n")
    for dep in vulnerable:
        ver = dep["version"] or "(unpinned)"
        lines.append(f"- {dep['name']}@{ver} [{dep['ecosystem']}] ({dep['manifest']})")
        for v in dep["vulns"]:
            sev = f" [{v['severity']}]" if v.get("severity") else ""
            summary = f" — {v['summary']}" if v.get("summary") else ""
            lines.append(f"    {v['id']}{sev}{summary}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

from tools.registry import registry  # noqa: E402

DEPENDENCY_AUDIT_SCHEMA = {
    "name": "dependency_audit",
    "description": (
        "Software Composition Analysis (SCA): scan a project directory (or a "
        "single manifest file) for package.json, requirements.txt (and "
        "requirements-*.txt), pyproject.toml, go.mod, and Cargo.lock "
        "manifests, then query the free OSV.dev API for known vulnerabilities "
        "affecting the declared/resolved dependency versions. Returns a "
        "report of vulnerable dependencies with advisory IDs, severity, and "
        "summaries. Fails open (reports 'audit incomplete', never raises) if "
        "OSV.dev is unreachable."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory to scan for manifests, or a single manifest file path.",
            },
            "enrich": {
                "type": "boolean",
                "description": (
                    "Fetch full advisory details (summary/severity) for each "
                    "vulnerability found, capped at 25 lookups per run. "
                    "Defaults to true."
                ),
                "default": True,
            },
        },
        "required": ["path"],
    },
}


def _dependency_audit_handler(args: Dict[str, Any], **_kw) -> str:
    path = args.get("path", "")
    if not path:
        return "Error: 'path' is required."
    enrich = args.get("enrich", True)
    result = audit_dependencies(path, enrich=enrich)
    return format_audit_report(result)


registry.register(
    name="dependency_audit",
    toolset="dependency_audit",
    schema=DEPENDENCY_AUDIT_SCHEMA,
    handler=_dependency_audit_handler,
    emoji="📦",
    max_result_size_chars=50_000,
)
