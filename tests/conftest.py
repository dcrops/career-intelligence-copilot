from pathlib import Path

import pytest

from career_intelligence.profile import CareerProfile, CareerProfileService
from tests.unit.application_package.helpers import write_mini_master

FIXTURES = Path(__file__).parent / "fixtures"

_PDF_STUB = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\nstub\n%%EOF\n"


def _weasyprint_available() -> bool:
    try:
        import weasyprint  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.fixture(autouse=True)
def _offline_package_generation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep pytest package prepare off the live Master CV and OpenAI network."""
    master = write_mini_master(tmp_path / "offline_master_cv.md")
    monkeypatch.setenv("CIC_MASTER_CV_PATH", str(master))
    monkeypatch.setenv("CIC_COVER_LETTER_COMPOSER", "fixture")


@pytest.fixture(autouse=True)
def _stub_pdf_when_weasyprint_missing(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    """Allow package/CV/cover-letter prepare paths without system WeasyPrint.

    PDF-renderer unit tests still exercise the real import path and skip/fail
    when WeasyPrint is absent; all other tests get a deterministic stub.
    """
    if _weasyprint_available():
        return
    node_id = request.node.nodeid
    if "test_pdf_renderer" in node_id or "test_render_pdf" in node_id:
        return

    def _stub(_html: str) -> bytes:
        return _PDF_STUB

    monkeypatch.setattr(
        "career_intelligence.cv_generation.pdf_renderer.render_pdf_from_html",
        _stub,
    )
    monkeypatch.setattr(
        "career_intelligence.cv_generation.draft_writer.render_pdf_from_html",
        _stub,
    )
    monkeypatch.setattr(
        "career_intelligence.cover_letter.draft_writer.render_pdf_from_html",
        _stub,
    )


@pytest.fixture
def minimal_profile_path() -> Path:
    return FIXTURES / "minimal_valid_profile.yaml"


@pytest.fixture
def valid_profile(minimal_profile_path: Path) -> CareerProfile:
    return CareerProfileService.from_path(minimal_profile_path).load()


@pytest.fixture
def tmp_profile_path(tmp_path: Path, minimal_profile_path: Path) -> Path:
    destination = tmp_path / "career_profile.yaml"
    destination.write_bytes(minimal_profile_path.read_bytes())
    return destination


@pytest.fixture
def golden_profile_path() -> Path:
    return FIXTURES / "golden" / "career_profile.yaml"
