"""Unit tests for FR-009 M3 deterministic duplicate detection."""

from __future__ import annotations

from career_intelligence.duplicates import (
    build_candidate,
    compare_identities,
    detect_candidates,
    normalise_company,
    normalise_title,
)
from tests.unit.duplicates.helpers import (
    FINGERPRINT,
    ID_1,
    ID_2,
    ID_3,
    OTHER_FINGERPRINT,
    ad,
)


def test_same_platform_and_job_id_is_definite() -> None:
    left = ad(ID_1, source_kind="seek", platform_job_id="12345")
    right = ad(ID_2, source_kind="seek", platform_job_id="12345", title="AI Engineer II")
    candidate = build_candidate(left, right)

    assert candidate is not None
    assert candidate.confidence == "definite"
    assert candidate.comparison.matches("platform_job_id")


def test_same_platform_with_different_job_id_is_not_definite() -> None:
    """A repost on the same platform stays owner-reviewable, never auto-confirmed."""
    left = ad(ID_1, source_kind="seek", platform_job_id="12345")
    right = ad(ID_2, source_kind="seek", platform_job_id="99999")
    candidate = build_candidate(left, right)

    assert candidate is not None
    assert candidate.confidence == "probable"
    assert candidate.comparison.differs("platform_job_id")


def test_same_canonical_url_is_definite_across_platforms() -> None:
    left = ad(
        ID_1,
        source_kind="seek",
        canonical_url="https://www.seek.com.au/job/777",
        company="Acme",
    )
    right = ad(
        ID_2,
        source_kind="linkedin",
        canonical_url="https://www.seek.com.au/job/777/",
        company="Totally Different Co",
    )
    candidate = build_candidate(left, right)

    assert candidate is not None
    assert candidate.confidence == "definite"


def test_company_and_title_with_location_is_probable() -> None:
    left = ad(ID_1, source_kind="seek", location_text="Sydney, NSW")
    right = ad(ID_2, source_kind="linkedin", location_text="Sydney NSW Australia")
    candidate = build_candidate(left, right)

    assert candidate is not None
    assert candidate.confidence == "probable"
    assert candidate.comparison.matches("location")


def test_company_and_title_without_corroboration_is_possible() -> None:
    left = ad(ID_1, location_text="Sydney, NSW")
    right = ad(ID_2, location_text="Melbourne, VIC")
    candidate = build_candidate(left, right)

    assert candidate is not None
    assert candidate.confidence == "possible"


def test_fingerprint_alone_is_only_possible() -> None:
    left = ad(ID_1, company="Acme", title="AI Engineer", content_fingerprint=FINGERPRINT)
    right = ad(
        ID_2,
        company="Beta Industries",
        title="Data Scientist",
        location_text="Perth, WA",
        content_fingerprint=FINGERPRINT,
    )
    candidate = build_candidate(left, right)

    assert candidate is not None
    assert candidate.confidence == "possible"
    assert candidate.rationale == "Identical description text only"


def test_unrelated_records_are_not_candidates() -> None:
    left = ad(ID_1, company="Acme", title="AI Engineer", content_fingerprint=FINGERPRINT)
    right = ad(
        ID_2,
        company="Beta Industries",
        title="Warehouse Manager",
        location_text="Perth, WA",
        content_fingerprint=OTHER_FINGERPRINT,
    )

    assert build_candidate(left, right) is None


def test_missing_facets_are_unknown_not_matching() -> None:
    left = ad(ID_1, platform_job_id=None, canonical_url=None)
    right = ad(ID_2, platform_job_id="12345", canonical_url=None)
    comparison = compare_identities(left.identity, right.identity)

    assert "platform_job_id" in comparison.unknown
    assert "canonical_url" in comparison.unknown
    assert not comparison.matches("platform_job_id")


def test_manual_source_kind_does_not_count_as_platform_evidence() -> None:
    comparison = compare_identities(ad(ID_1).identity, ad(ID_2).identity)

    assert "platform" in comparison.unknown


def test_pair_order_and_confidence_order_are_deterministic() -> None:
    strong_left = ad(ID_1, source_kind="seek", platform_job_id="12345")
    strong_right = ad(ID_2, source_kind="seek", platform_job_id="12345")
    weak = ad(ID_3, location_text="Brisbane, QLD")

    forwards = detect_candidates([strong_left, strong_right, weak])
    backwards = detect_candidates([weak, strong_right, strong_left])

    assert forwards == backwards
    assert forwards[0].confidence == "definite"
    assert forwards[0].pair == (ID_1, ID_2)
    assert [candidate.confidence for candidate in forwards] == sorted(
        [candidate.confidence for candidate in forwards],
        key=lambda value: {"definite": 0, "probable": 1, "possible": 2}[value],
    )


def test_confirmed_pairs_are_not_re_suggested() -> None:
    canonical = ad(ID_1, source_kind="seek", platform_job_id="12345")
    member = ad(
        ID_2, source_kind="seek", platform_job_id="12345", duplicate_of=ID_1
    )

    assert detect_candidates([canonical, member]) == ()


def test_records_in_the_same_group_are_not_re_suggested() -> None:
    canonical = ad(ID_1)
    first = ad(ID_2, duplicate_of=ID_1)
    second = ad(ID_3, duplicate_of=ID_1)

    assert detect_candidates([canonical, first, second]) == ()


def test_rejected_pairs_never_reappear() -> None:
    left = ad(ID_1, source_kind="seek", platform_job_id="12345", rejected_against=(ID_2,))
    right = ad(ID_2, source_kind="seek", platform_job_id="12345", rejected_against=(ID_1,))

    assert detect_candidates([left, right]) == ()


def test_rejection_recorded_on_one_side_still_suppresses_the_pair() -> None:
    left = ad(ID_1, source_kind="seek", platform_job_id="12345", rejected_against=(ID_2,))
    right = ad(ID_2, source_kind="seek", platform_job_id="12345")

    assert detect_candidates([left, right]) == ()


def test_normalisation_ignores_formatting_noise_only() -> None:
    assert normalise_company("Acme Pty Ltd") == normalise_company("ACME")
    assert normalise_title("Senior AI Engineer (Remote)") == normalise_title(
        "senior ai engineer"
    )
    assert normalise_company("Acme") != normalise_company("Acme Digital")
    assert normalise_title("AI Engineer") != normalise_title("Senior AI Engineer")
