"""Tests hors ligne du module coursupreme : parser, normalisation,
découverte, déduplication, stockage. Aucune requête réseau.

Fixtures : HTML réels copiés depuis coursupreme.dz (09/09/2026),
parties déjà publiées en initiales par la Cour.
"""

import sys
from pathlib import Path

import pytest

CS = Path(__file__).resolve().parent.parent / "sources" / "coursupreme"
# tools/ d'abord, CS ensuite : CS gagne les collisions de noms (discover.py)
sys.path.insert(0, str(CS.parents[1] / "tools"))
sys.path.insert(0, str(CS))

from parser import (  # noqa: E402
    parse_decision_from_file,
    is_decision_url,
    chamber_from_class,
)
from normalize import (  # noqa: E402
    clean_text,
    normalize_date,
    normalize_decision_number,
    normalize_arabic,
)
from discover import normalize_url, extract_decision_urls, last_page_number  # noqa: E402
from storage import DecisionStore  # noqa: E402
from models import Decision  # noqa: E402

FIXTURES = CS / "fixtures"


# --- Parser ----------------------------------------------------------------

def test_parser_fixture_standard():
    """Fixture type (chambres civiles) : tous les champs clés extraits."""
    f = FIXTURES / "decision_القرار-رقم-007799-المؤرخ-في-13-01-2016.html"
    d = parse_decision_from_file(f, source_url="https://coursupreme.dz/decision/a/")
    assert d.decision_number == "7799"
    assert d.date == "2016-01-13"
    assert d.chamber == "الغرف المدنية"
    assert d.chamber_class == "civil-chambers-200"
    assert d.subject == "نقل بري"
    assert d.parties and "الطاعن" in d.parties
    assert d.principle and "تعويض" in d.principle
    assert d.disposition
    assert d.court_response
    assert d.president and d.rapporteur
    assert d.content_hash and len(d.content_hash) == 64
    assert d.text and len(d.text) > 500


def test_parser_fixture_sans_reference_legale():
    """Fixture sans 'المرجع القانوني' : le champ reste None, pas d'erreur."""
    f = FIXTURES / "decision_القرار-رقم-1040786-المؤرخ-في-14-10-2015.html"
    d = parse_decision_from_file(f, source_url="https://x/decision/b/")
    assert d.decision_number == "1040786"
    assert d.legal_references is None  # champ absent du HTML réel
    assert d.keywords  # les mots-clés, eux, sont présents
    assert d.date == "2015-10-14"


def test_parser_fixture_variante_constitutionnelle():
    """Variant 'قرارات مهمة' : sections unconstitutionality au lieu de principe."""
    f = FIXTURES / "decision_ملف-رقم-00001-قرار-بتاريخ-07-17-2019.html"
    d = parse_decision_from_file(f, source_url="https://x/decision/c/")
    assert d.chamber == "قرارات مهمة"
    assert d.unconstitutionality_grounds is not None
    assert d.unconstitutionality_response is not None
    assert d.decision_number == "01"


def test_parser_section_vide_absorbee():
    """h5 sans <p> (وجه الطعن vide) → None, pas d'exception."""
    f = FIXTURES / "decision_القرار-رقم-007799-المؤرخ-في-13-01-2016.html"
    d = parse_decision_from_file(f, source_url="https://x/decision/d/")
    # sur cette décision réelle, le moyen du pourvoi est vide sur le site
    assert d.appeal_ground is None


def test_parser_page_non_decision():
    """Une page sans <article class=decision> lève ValueError."""
    f = FIXTURES / "non_decision_homepage.html"
    with pytest.raises(ValueError):
        parse_decision_from_file(f, source_url="https://x/")


def test_parser_arabe_preserve():
    """Le texte arabe n'est pas dégradé (caractères, sens)."""
    f = FIXTURES / "decision_القرار-رقم-007799-المؤرخ-في-13-01-2016.html"
    d = parse_decision_from_file(f, source_url="https://x/decision/e/")
    assert "المحكمة" in (d.court_response or "") or "المدعي" in (d.court_response or "")
    assert "\u200b" not in (d.text or "")  # zero-width retiré


# --- Normalisation -----------------------------------------------------------

def test_clean_text_espaces():
    assert clean_text("a\u00a0\u200bb  c\t\td") == "a b c d"
    assert clean_text("  x  ") == "x"
    assert clean_text(None) is None
    assert clean_text("   ") is None


def test_normalize_dates():
    assert normalize_date("2016/01/13") == "2016-01-13"       # format métadonnées
    assert normalize_date("13-01-2016", day_first=True) == "2016-01-13"   # slug FR
    assert normalize_date("07-17-2019", day_first=False) == "2019-07-17"  # slug US
    assert normalize_date("2019-10-09") == "2019-10-09"
    assert normalize_date("") is None
    assert normalize_date("pas une date") is None
    assert normalize_date("99-99-2016") is None


def test_normalize_numero():
    assert normalize_decision_number("رقم القرار:\xa0 7799") == "7799"
    assert normalize_decision_number("01") == "01"
    assert normalize_decision_number(None) is None


def test_normalize_arabic_ligature():
    assert normalize_arabic("\ufefb") == "لا"  # ligature lam-alef
    assert normalize_arabic("محكمة") == "محكمة"


# --- URLs / découverte ---------------------------------------------------------

def test_is_decision_url():
    assert is_decision_url("https://coursupreme.dz/decision/ملف-رقم-1-قرار/")
    assert not is_decision_url("https://coursupreme.dz/الغرف-المدنية/")
    assert not is_decision_url("https://coursupreme.dz/")


def test_normalize_url_dedup():
    """Query, fragment et slash → même clé de déduplication."""
    a = normalize_url("https://coursupreme.dz/decision/x?paged=2#top")
    b = normalize_url("/decision/x/")
    assert a == b == "https://coursupreme.dz/decision/x/"


def test_extract_decision_urls_listing_reel():
    html = (FIXTURES / "listing_civiles.html").read_bytes()
    urls = extract_decision_urls(html.decode("utf-8", "replace"), "https://coursupreme.dz/x/")
    assert len(urls) >= 10
    assert all("/decision/" in u for u in urls)


def test_last_page_number_listing_reel():
    html = (FIXTURES / "listing_civiles.html").read_bytes().decode("utf-8", "replace")
    assert last_page_number(html) == 19  # valeur réelle constatée sur le site


# --- Stockage -------------------------------------------------------------------

@pytest.fixture()
def store(tmp_path):
    s = DecisionStore(db_path=str(tmp_path / "test.db"), raw_dir=tmp_path / "raw")
    with s:
        yield s


def test_storage_decouverte_et_dedup(store):
    assert store.add_discovered("https://x/decision/a/", "civiles") is True
    assert store.add_discovered("https://x/decision/a/", "civiles") is False
    assert store.add_discovered_batch([
        ("https://x/decision/a/", "civiles"),
        ("https://x/decision/b/", "themes"),
    ]) == 1
    assert len(store.pending()) == 2


def test_storage_save_et_pending(store):
    store.add_discovered("https://x/decision/a/", "civiles")
    d = Decision(source_url="https://x/decision/a/", decision_number="7799",
                 date="2016-01-13", text="نص القرار")
    store.save_decision(d, raw_html=b"<html>brut</html>")
    assert len(store.pending()) == 0
    counts = store.counts_by_status()
    assert counts.get("telecharge") == 1
    row = store.connect().execute(
        "SELECT decision_number, raw_path, content_hash FROM decisions"
    ).fetchone()
    assert row["decision_number"] == "7799"
    assert Path(row["raw_path"]).read_bytes() == b"<html>brut</html>"


def test_storage_erreur_puis_reprise(store):
    store.add_discovered("https://x/decision/a/", "themes")
    store.mark_error("https://x/decision/a/", "échec HTTP")
    pending = store.pending()
    assert len(pending) == 1  # erreur → reprise au prochain run


def test_storage_doublons_contenu(store):
    for url in ["https://x/decision/a/", "https://x/decision/b/"]:
        store.add_discovered(url, "themes")
        d = Decision(source_url=url, content_hash="abc123")
        store.save_decision(d, raw_html=b"x")
    dups = store.duplicate_hashes()
    assert len(dups) == 1 and dups[0]["n"] == 2


def test_chamber_from_class():
    assert chamber_from_class("civil-chambers-200") == "الغرف المدنية"
    assert chamber_from_class("criminal-chambers-194") == "الغرف الجزائية"
    assert chamber_from_class("unknown-thing-1") is None
    assert chamber_from_class(None) is None
