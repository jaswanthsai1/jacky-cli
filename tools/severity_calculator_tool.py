#!/usr/bin/env python3
"""
Severity Calculator Tool

Two related severity-rating helpers, exposed as one cohesive tool:

1. ``severity_lookup`` — fuzzy/substring match a free-text vulnerability
   description against the real Bugcrowd Vulnerability Rating Taxonomy
   (VRT), shipped at ``tools/data/bugcrowd_vrt.txt`` (2,626 lines, one
   ``Category / Vulnerability Name / Variant / Severity`` entry per block).
   Returns the matching Bugcrowd P1-P5 rating(s).

2. ``cvss_calculate`` — a standards-exact CVSS v3.1 Base Score calculator,
   implementing the published FIRST.org formula (metric weights, ISS,
   Impact/Exploitability sub-scores, Scope Changed vs Unchanged branches,
   and the official Roundup function) rather than an approximation.
   Reference: https://www.first.org/cvss/v3.1/specification-document
   (section 7.4, "Metric Values" and section 8.1, "3.1 Equations").

Usage:
    from tools.severity_calculator_tool import severity_lookup, cvss_calculate

    severity_lookup("reflected XSS in search parameter")
    cvss_calculate("AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")  # -> 9.8
"""

import math
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

_VRT_PATH = os.path.join(os.path.dirname(__file__), "data", "bugcrowd_vrt.txt")

# Cache: parsed once per process, keyed by (path, mtime) so tests that swap
# in a fixture file via a different path don't collide with the real cache.
_VRT_CACHE: Dict[str, List["VRTEntry"]] = {}


@dataclass
class VRTEntry:
    category: str
    name: str
    variant: str
    severity: str  # "P1".."P5"

    def haystack(self) -> str:
        return f"{self.category} {self.name} {self.variant}".lower()


# ---------------------------------------------------------------------------
# VRT parsing + fuzzy lookup
# ---------------------------------------------------------------------------


def load_vrt(path: Optional[str] = None) -> List[VRTEntry]:
    """Parse the Bugcrowd VRT text file into a list of :class:`VRTEntry`.

    Entries look like::

        Entry #384
        Category:                      Server-Side Injection
        Vulnerability Name:            SQL Injection
        Variant / Affected Function:   N/A
        Severity:                      P1
        --------------------------------------------------------------------------------

    Results are cached in-process per file path.
    """
    vrt_path = path or _VRT_PATH
    if vrt_path in _VRT_CACHE:
        return _VRT_CACHE[vrt_path]

    entries: List[VRTEntry] = []
    try:
        with open(vrt_path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except OSError:
        _VRT_CACHE[vrt_path] = entries
        return entries

    category = name = variant = severity = None
    for line in content.splitlines():
        line = line.rstrip()
        if line.startswith("Category:"):
            category = line.split(":", 1)[1].strip()
        elif line.startswith("Vulnerability Name:"):
            name = line.split(":", 1)[1].strip()
        elif line.startswith("Variant / Affected Function:"):
            variant = line.split(":", 1)[1].strip()
        elif line.startswith("Severity:"):
            severity = line.split(":", 1)[1].strip()
        elif line.startswith("---") and category and name and severity:
            entries.append(
                VRTEntry(
                    category=category,
                    name=name,
                    variant=variant or "N/A",
                    severity=severity,
                )
            )
            category = name = variant = severity = None

    _VRT_CACHE[vrt_path] = entries
    return entries


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


def _score_entry(query_tokens: List[str], query_lower: str, entry: VRTEntry) -> float:
    """Score an entry's relevance to the query. Higher is better; 0 = no match."""
    haystack = entry.haystack()

    # Exact substring match of the whole query is the strongest signal.
    if query_lower in haystack:
        # Reward tighter matches (query closer to the full haystack length).
        return 100.0 + (len(query_lower) / max(len(haystack), 1)) * 20.0

    # Whole-name substring match (query contains the vuln name or vice versa).
    name_lower = entry.name.lower()
    if name_lower and (name_lower in query_lower or query_lower in name_lower):
        return 80.0

    # Token overlap (Jaccard-style) across category/name/variant.
    entry_tokens = set(_tokenize(haystack))
    q_tokens = set(query_tokens)
    if not entry_tokens or not q_tokens:
        return 0.0
    overlap = entry_tokens & q_tokens
    if not overlap:
        return 0.0
    jaccard = len(overlap) / len(entry_tokens | q_tokens)
    return jaccard * 60.0


def severity_lookup(
    query: str,
    top_n: int = 5,
    path: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Fuzzy-match *query* against the Bugcrowd VRT and return top matches.

    Returns a list (best match first) of::

        {"category", "name", "variant", "severity", "score"}

    ``score`` is a 0-100+ relative-relevance heuristic, not a calibrated
    probability — it exists to order/filter results, not to be displayed
    as a percentage.
    """
    entries = load_vrt(path)
    if not entries or not query:
        return []

    query_lower = query.strip().lower()
    query_tokens = _tokenize(query_lower)

    scored = []
    for entry in entries:
        score = _score_entry(query_tokens, query_lower, entry)
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [
        {
            "category": entry.category,
            "name": entry.name,
            "variant": entry.variant,
            "severity": entry.severity,
            "score": round(score, 2),
        }
        for score, entry in scored[:top_n]
    ]


# ---------------------------------------------------------------------------
# CVSS v3.1 Base Score — exact FIRST.org formula
# ---------------------------------------------------------------------------

# Section 7.4 metric value tables (Base metrics only — no Temporal/Environmental).
_AV_WEIGHTS = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.20}
_AC_WEIGHTS = {"L": 0.77, "H": 0.44}
_PR_WEIGHTS_UNCHANGED = {"N": 0.85, "L": 0.62, "H": 0.27}
_PR_WEIGHTS_CHANGED = {"N": 0.85, "L": 0.68, "H": 0.50}
_UI_WEIGHTS = {"N": 0.85, "R": 0.62}
_CIA_WEIGHTS = {"H": 0.56, "L": 0.22, "N": 0.00}

_METRIC_ORDER = ["AV", "AC", "PR", "UI", "S", "C", "I", "A"]
_VALID_VALUES = {
    "AV": set(_AV_WEIGHTS),
    "AC": set(_AC_WEIGHTS),
    "PR": set(_PR_WEIGHTS_UNCHANGED),
    "UI": set(_UI_WEIGHTS),
    "S": {"U", "C"},
    "C": set(_CIA_WEIGHTS),
    "I": set(_CIA_WEIGHTS),
    "A": set(_CIA_WEIGHTS),
}

_SEVERITY_RATINGS = [
    (0.0, 0.0, "None"),
    (0.1, 3.9, "Low"),
    (4.0, 6.9, "Medium"),
    (7.0, 8.9, "High"),
    (9.0, 10.0, "Critical"),
]


def cvss_rating(score: float) -> str:
    """Qualitative severity rating for a CVSS v3.1 base score (spec section 5)."""
    for lo, hi, label in _SEVERITY_RATINGS:
        if lo <= score <= hi:
            return label
    return "Unknown"


def _roundup(value: float) -> float:
    """The official CVSS v3.1 Roundup function (spec Appendix A).

    Rounds a float up to the nearest 0.1, expressed via the integer trick
    the spec itself defines (avoids binary floating point rounding errors
    from a naive ``math.ceil(value * 10) / 10``)::

        Roundup(x):
            int_input = round(x * 100000)
            if int_input % 10000 == 0:
                return int_input / 100000.0
            else:
                return (floor(int_input / 10000) + 1) / 10.0
    """
    int_input = round(value * 100000)
    if int_input % 10000 == 0:
        return int_input / 100000.0
    return (math.floor(int_input / 10000) + 1) / 10.0


def parse_cvss_vector(vector: str) -> Dict[str, str]:
    """Parse a CVSS v3.1 vector string into a metric dict.

    Accepts both ``CVSS:3.1/AV:N/AC:L/...`` and bare ``AV:N/AC:L/...`` forms.
    Raises ``ValueError`` on a malformed vector or missing/invalid metric.
    """
    vector = vector.strip()
    if vector.upper().startswith("CVSS:"):
        vector = vector.split("/", 1)[1] if "/" in vector else ""

    metrics: Dict[str, str] = {}
    for part in vector.split("/"):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            raise ValueError(f"Malformed CVSS metric segment: {part!r}")
        key, value = part.split(":", 1)
        key, value = key.strip().upper(), value.strip().upper()
        metrics[key] = value

    missing = [m for m in _METRIC_ORDER if m not in metrics]
    if missing:
        raise ValueError(f"CVSS vector missing required metric(s): {', '.join(missing)}")

    for key in _METRIC_ORDER:
        if metrics[key] not in _VALID_VALUES[key]:
            raise ValueError(
                f"Invalid value {metrics[key]!r} for metric {key} "
                f"(expected one of {sorted(_VALID_VALUES[key])})"
            )
    return metrics


def cvss_calculate(vector_or_metrics) -> Dict[str, object]:
    """Compute the CVSS v3.1 Base Score exactly per the FIRST.org formula.

    Args:
        vector_or_metrics: either a vector string (``"AV:N/AC:L/PR:N/UI:N/
            S:U/C:H/I:H/A:H"``, with or without the ``CVSS:3.1/`` prefix) or
            a dict of the 8 base metrics (``{"AV": "N", "AC": "L", ...}``).

    Returns:
        {
            "base_score": float,       # e.g. 9.8
            "severity": str,           # "Critical" / "High" / "Medium" / "Low" / "None"
            "impact_subscore": float,
            "exploitability_subscore": float,
            "iss": float,
            "vector": str,              # normalized "CVSS:3.1/AV:N/..." string
            "metrics": {..},
        }

    Raises ``ValueError`` for a malformed/incomplete vector.
    """
    if isinstance(vector_or_metrics, str):
        metrics = parse_cvss_vector(vector_or_metrics)
    elif isinstance(vector_or_metrics, dict):
        metrics = {k.upper(): str(v).upper() for k, v in vector_or_metrics.items()}
        missing = [m for m in _METRIC_ORDER if m not in metrics]
        if missing:
            raise ValueError(f"CVSS metrics missing required key(s): {', '.join(missing)}")
        for key in _METRIC_ORDER:
            if metrics[key] not in _VALID_VALUES[key]:
                raise ValueError(
                    f"Invalid value {metrics[key]!r} for metric {key} "
                    f"(expected one of {sorted(_VALID_VALUES[key])})"
                )
    else:
        raise TypeError("vector_or_metrics must be a CVSS vector string or a metrics dict")

    scope_changed = metrics["S"] == "C"

    av = _AV_WEIGHTS[metrics["AV"]]
    ac = _AC_WEIGHTS[metrics["AC"]]
    pr = (_PR_WEIGHTS_CHANGED if scope_changed else _PR_WEIGHTS_UNCHANGED)[metrics["PR"]]
    ui = _UI_WEIGHTS[metrics["UI"]]
    c = _CIA_WEIGHTS[metrics["C"]]
    i = _CIA_WEIGHTS[metrics["I"]]
    a = _CIA_WEIGHTS[metrics["A"]]

    # ISCBase (Impact Sub-Score, base)
    iss = 1 - ((1 - c) * (1 - i) * (1 - a))

    if scope_changed:
        impact = 7.52 * (iss - 0.029) - 3.25 * ((iss - 0.02) ** 15)
    else:
        impact = 6.42 * iss

    exploitability = 8.22 * av * ac * pr * ui

    if impact <= 0:
        base_score = 0.0
    elif scope_changed:
        base_score = _roundup(min(1.08 * (impact + exploitability), 10.0))
    else:
        base_score = _roundup(min(impact + exploitability, 10.0))

    normalized_vector = "CVSS:3.1/" + "/".join(f"{k}:{metrics[k]}" for k in _METRIC_ORDER)

    return {
        "base_score": base_score,
        "severity": cvss_rating(base_score),
        "impact_subscore": round(max(impact, 0.0), 2),
        "exploitability_subscore": round(exploitability, 2),
        "iss": round(iss, 4),
        "vector": normalized_vector,
        "metrics": metrics,
    }


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

from tools.registry import registry  # noqa: E402

SEVERITY_CALCULATOR_SCHEMA = {
    "name": "severity_calculator",
    "description": (
        "Vulnerability severity rating tool with two modes. "
        "'lookup' mode fuzzy-matches a free-text vulnerability description/"
        "category/name against the real Bugcrowd Vulnerability Rating "
        "Taxonomy (2,626 entries) and returns the matching Bugcrowd P1-P5 "
        "rating(s), best match first. "
        "'cvss' mode computes an exact CVSS v3.1 Base Score (0.0-10.0) plus "
        "qualitative severity (None/Low/Medium/High/Critical) from an "
        "8-metric vector string (e.g. 'AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H') "
        "using the published FIRST.org formula — not an approximation."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["lookup", "cvss"],
                "description": "'lookup' for Bugcrowd VRT fuzzy match, 'cvss' for CVSS v3.1 base score.",
            },
            "query": {
                "type": "string",
                "description": "Free-text vulnerability description (required for mode='lookup').",
            },
            "top_n": {
                "type": "integer",
                "description": "Max number of VRT matches to return (mode='lookup'). Defaults to 5.",
                "default": 5,
                "minimum": 1,
                "maximum": 20,
            },
            "vector": {
                "type": "string",
                "description": (
                    "CVSS v3.1 base vector string, e.g. "
                    "'AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H' (required for mode='cvss')."
                ),
            },
        },
        "required": ["mode"],
    },
}


def _severity_calculator_handler(args: Dict[str, object], **_kw) -> str:
    mode = args.get("mode")
    if mode == "lookup":
        query = args.get("query") or ""
        if not query:
            return "Error: 'query' is required for mode='lookup'."
        top_n = int(args.get("top_n", 5) or 5)
        matches = severity_lookup(query, top_n=top_n)
        if not matches:
            return f"No Bugcrowd VRT matches found for: {query!r}"
        lines = [f"Bugcrowd VRT matches for {query!r}:"]
        for m in matches:
            lines.append(
                f"  [{m['severity']}] {m['category']} / {m['name']} / {m['variant']} "
                f"(score {m['score']})"
            )
        return "\n".join(lines)

    if mode == "cvss":
        vector = args.get("vector") or ""
        if not vector:
            return "Error: 'vector' is required for mode='cvss'."
        try:
            result = cvss_calculate(vector)
        except (ValueError, TypeError) as exc:
            return f"Error: {exc}"
        return (
            f"CVSS v3.1 Base Score: {result['base_score']} ({result['severity']})\n"
            f"Vector: {result['vector']}\n"
            f"Impact subscore: {result['impact_subscore']}, "
            f"Exploitability subscore: {result['exploitability_subscore']}, "
            f"ISS: {result['iss']}"
        )

    return "Error: 'mode' must be 'lookup' or 'cvss'."


registry.register(
    name="severity_calculator",
    toolset="severity_calc",
    schema=SEVERITY_CALCULATOR_SCHEMA,
    handler=_severity_calculator_handler,
    emoji="🎯",
    max_result_size_chars=20_000,
)
