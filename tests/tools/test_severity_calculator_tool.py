"""Tests for the severity calculator tool (Bugcrowd VRT lookup + CVSS v3.1)."""

import textwrap

import pytest

from tools.severity_calculator_tool import (
    cvss_calculate,
    cvss_rating,
    load_vrt,
    parse_cvss_vector,
    severity_lookup,
)


# ---------------------------------------------------------------------------
# Bugcrowd VRT lookup
# ---------------------------------------------------------------------------

_FIXTURE_VRT = textwrap.dedent("""\
    ================================================================================
    BUGCROWD VULNERABILITY RATING TAXONOMY (VRT) - COMPLETE EXTRACT
    ================================================================================
    Entry #1
    Category:                      Server-Side Injection
    Vulnerability Name:            SQL Injection
    Variant / Affected Function:   N/A
    Severity:                      P1
    --------------------------------------------------------------------------------
    Entry #2
    Category:                      Cross-Site Scripting (XSS)
    Vulnerability Name:            Reflected
    Variant / Affected Function:   Non-Self
    Severity:                      P3
    --------------------------------------------------------------------------------
    Entry #3
    Category:                      Cross-Site Scripting (XSS)
    Vulnerability Name:            Stored
    Variant / Affected Function:   Self
    Severity:                      P5
    --------------------------------------------------------------------------------
""")


class TestLoadVrt:
    def test_loads_real_shipped_file(self):
        # The real ~2,626-line Bugcrowd VRT extract shipped with the repo.
        entries = load_vrt()
        assert len(entries) > 400
        assert any(e.name == "SQL Injection" and e.severity == "P1" for e in entries)

    def test_parses_fixture_correctly(self, tmp_path):
        vrt_path = tmp_path / "fixture_vrt.txt"
        vrt_path.write_text(_FIXTURE_VRT)
        entries = load_vrt(str(vrt_path))
        assert len(entries) == 3
        assert entries[0].category == "Server-Side Injection"
        assert entries[0].name == "SQL Injection"
        assert entries[0].variant == "N/A"
        assert entries[0].severity == "P1"

    def test_missing_file_returns_empty(self, tmp_path):
        assert load_vrt(str(tmp_path / "nope.txt")) == []


class TestSeverityLookup:
    def test_exact_name_match_returns_correct_p_rating(self, tmp_path):
        vrt_path = tmp_path / "fixture_vrt.txt"
        vrt_path.write_text(_FIXTURE_VRT)
        matches = severity_lookup("SQL Injection", path=str(vrt_path))
        assert matches
        assert matches[0]["name"] == "SQL Injection"
        assert matches[0]["severity"] == "P1"

    def test_partial_description_still_matches(self, tmp_path):
        vrt_path = tmp_path / "fixture_vrt.txt"
        vrt_path.write_text(_FIXTURE_VRT)
        matches = severity_lookup("blind sql injection in login form", path=str(vrt_path))
        assert matches
        assert matches[0]["name"] == "SQL Injection"

    def test_reflected_xss_matches_correct_variant(self, tmp_path):
        vrt_path = tmp_path / "fixture_vrt.txt"
        vrt_path.write_text(_FIXTURE_VRT)
        matches = severity_lookup("reflected cross-site scripting", path=str(vrt_path))
        assert matches
        top = matches[0]
        assert top["name"] == "Reflected"
        assert top["severity"] == "P3"

    def test_no_match_returns_empty_list(self, tmp_path):
        vrt_path = tmp_path / "fixture_vrt.txt"
        vrt_path.write_text(_FIXTURE_VRT)
        assert severity_lookup("completely unrelated gibberish zzz qqq", path=str(vrt_path)) == []

    def test_empty_query_returns_empty(self, tmp_path):
        vrt_path = tmp_path / "fixture_vrt.txt"
        vrt_path.write_text(_FIXTURE_VRT)
        assert severity_lookup("", path=str(vrt_path)) == []

    def test_top_n_respected(self):
        matches = severity_lookup("injection", top_n=3)
        assert len(matches) <= 3

    def test_results_sorted_best_first(self, tmp_path):
        vrt_path = tmp_path / "fixture_vrt.txt"
        vrt_path.write_text(_FIXTURE_VRT)
        matches = severity_lookup("SQL Injection", path=str(vrt_path))
        scores = [m["score"] for m in matches]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# CVSS v3.1 base score — exact formula verification against published vectors
# ---------------------------------------------------------------------------


class TestParseCvssVector:
    def test_bare_vector(self):
        metrics = parse_cvss_vector("AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")
        assert metrics == {
            "AV": "N", "AC": "L", "PR": "N", "UI": "N",
            "S": "U", "C": "H", "I": "H", "A": "H",
        }

    def test_prefixed_vector(self):
        metrics = parse_cvss_vector("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")
        assert metrics["AV"] == "N"

    def test_missing_metric_raises(self):
        with pytest.raises(ValueError, match="missing"):
            parse_cvss_vector("AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H")

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError, match="Invalid value"):
            parse_cvss_vector("AV:Z/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")


class TestCvssCalculateKnownVectors:
    """Verified against the published FIRST.org CVSS v3.1 base formula.

    These three vectors correspond to widely-cited real-world CVEs and their
    officially published NVD base scores:
      - AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H = 9.8  (unauthenticated network
        RCE with full C/I/A impact, scope unchanged — e.g. Log4Shell-class)
      - AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H = 10.0 (CVE-2017-5638, Apache
        Struts OGNL RCE — scope changed, saturates at the 10.0 ceiling)
      - AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N = 7.5  (CVE-2014-0160,
        Heartbleed — confidentiality-only network read)
    """

    def test_critical_network_rce(self):
        result = cvss_calculate("AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")
        assert result["base_score"] == 9.8
        assert result["severity"] == "Critical"

    def test_scope_changed_saturates_at_ceiling(self):
        result = cvss_calculate("AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H")
        assert result["base_score"] == 10.0
        assert result["severity"] == "Critical"

    def test_heartbleed_confidentiality_only(self):
        result = cvss_calculate("AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N")
        assert result["base_score"] == 7.5
        assert result["severity"] == "High"

    def test_zero_impact_gives_zero_score(self):
        result = cvss_calculate("AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N")
        assert result["base_score"] == 0.0
        assert result["severity"] == "None"

    def test_low_severity_local_vector(self):
        # Hand-verified against the FIRST.org formula:
        # ISS=0.22, Impact=6.42*0.22=1.4124,
        # Exploitability=8.22*0.55*0.44*0.27*0.62=0.333, sum=1.7454 -> Roundup 1.8
        result = cvss_calculate("AV:L/AC:H/PR:H/UI:R/S:U/C:L/I:N/A:N")
        assert result["base_score"] == 1.8
        assert result["severity"] == "Low"

    def test_medium_scope_changed_vector(self):
        # Hand-verified: ISS=0.3916, Impact(scope changed)~=2.7271,
        # Exploitability=8.22*0.85*0.44*0.85*0.62~=1.6201,
        # 1.08*(2.7271+1.6201)=4.695 -> Roundup 4.7
        result = cvss_calculate("AV:N/AC:H/PR:N/UI:R/S:C/C:L/I:L/A:N")
        assert result["base_score"] == 4.7
        assert result["severity"] == "Medium"

    def test_accepts_dict_input(self):
        metrics = {"AV": "N", "AC": "L", "PR": "N", "UI": "N", "S": "U", "C": "H", "I": "H", "A": "H"}
        result = cvss_calculate(metrics)
        assert result["base_score"] == 9.8

    def test_accepts_cvss_prefixed_vector(self):
        result = cvss_calculate("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")
        assert result["base_score"] == 9.8

    def test_normalized_vector_round_trips(self):
        result = cvss_calculate("AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")
        assert result["vector"] == "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"

    def test_malformed_vector_raises(self):
        with pytest.raises(ValueError):
            cvss_calculate("not-a-vector")

    def test_wrong_type_raises(self):
        with pytest.raises(TypeError):
            cvss_calculate(12345)


class TestCvssRating:
    @pytest.mark.parametrize(
        "score,expected",
        [
            (0.0, "None"),
            (2.5, "Low"),
            (5.0, "Medium"),
            (8.0, "High"),
            (9.5, "Critical"),
            (10.0, "Critical"),
        ],
    )
    def test_boundaries(self, score, expected):
        assert cvss_rating(score) == expected
