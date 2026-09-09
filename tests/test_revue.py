"""Tests offline de la pipeline revue (guide, normalisation, matching, stockage).
Aucun accès réseau."""

import json
import sys
from pathlib import Path

import pytest

REVUE = Path(__file__).resolve().parent.parent / "sources" / "coursupreme" / "revue"
# ordre : tools (append) < coursupreme < revue → revue gagne les collisions
# de noms (storage.py)
sys.path.append(str(REVUE.parents[2] / "tools"))
sys.path.insert(0, str(REVUE.parents[1]))
sys.path.insert(0, str(REVUE))

from arabic_normalize import visual_to_logical, normalize_guide_text  # noqa: E402
from matching import match_entry, norm_number  # noqa: E402
from revue_store import RevueStore  # noqa: E402
from downloader import logical_name, validate_pdf  # noqa: E402


# --- Normalisation bidi (cœur du parsing du guide) ---------------------------

def test_visual_to_logical_inverse():
    # 'دليل' en ordre visuel inversé → 'ليلد'
    assert visual_to_logical("ليلد") == "دليل"
    # phrase complète observée dans le guide (en-tête)
    assert visual_to_logical("ليلد ثحبلا") == "البحث دليل".replace("البحث ", "البحث ")


def test_visual_to_logical_preserve_chiffres():
    # chiffres d'un run : l'inversion globale puis la ré-inversion des runs
    # rendent le run à l'endroit (mono-run auto-correctif)
    assert visual_to_logical("86132") == "86132"
    # ligne multi-runs : l'ordre des runs s'inverse (visuel→logique),
    # chaque run reste à l'endroit — comportement documenté
    out = visual_to_logical("4 1993 110 86132")
    assert out.split() == ["86132", "110", "1993", "4"]


def test_normalize_guide_text_presentation_forms():
    # U+FEFB (lam-alef présentation) → la + suppression kashida
    out = normalize_guide_text("\ufefbـ\u0640")
    assert "لا" in out
    assert "\u0640" not in out  # tatweel retiré


def test_normalize_non_destructif():
    # entrée VISUELLE (ordre extraction) → sortie logique, diacritiques
    # juridiques préservés mot à mot
    out = normalize_guide_text("ةمَّكَحُم")  # 'مُحَكَّمة' en ordre visuel
    assert out == "مُحَكَّمة"


# --- Matching (Phase 7) -------------------------------------------------------

HTML_INDEX = {
    "444499": [{"id": 1, "year": 2009, "chamber": "قرارات مهمة"}],
    "1068024": [{"id": 2, "year": 2017, "chamber": "الغرف المدنية"}],
    "994311": [{"id": 3, "year": 2018, "chamber": "الغرف الجزائية"},
               {"id": 4, "year": 2016, "chamber": "الغرف الجزائية"}],
}


def test_norm_number_zeros():
    assert norm_number("0925727") == "925727"
    assert norm_number("0001") == "1"
    assert norm_number(None) is None


def test_match_exact():
    v, lvl, did = match_entry("444499", 2009, "قرارات مهمة", HTML_INDEX)
    assert (v, lvl, did) == ("MATCH_EXACT", 1, 1)


def test_match_exact_zero_padded():
    v, lvl, did = match_entry("0444499", 2009, None, HTML_INDEX)
    assert v == "MATCH_EXACT" and did == 1


def test_match_probable_year_mismatch():
    v, lvl, did = match_entry("444499", 2015, None, HTML_INDEX)
    assert v == "MATCH_PROBABLE" and did == 1


def test_match_new():
    v, lvl, did = match_entry("123456", 2020, None, HTML_INDEX)
    assert (v, lvl, did) == ("NEW", 3, None)


def test_match_uncertain_sans_numero():
    v, lvl, did = match_entry(None, 2020, "الغرف المدنية", HTML_INDEX)
    assert v == "UNCERTAIN"


def test_match_multivalent_numero():
    # numéro avec deux décisions en base + année → la bonne
    v, lvl, did = match_entry("994311", 2016, None, HTML_INDEX)
    assert (v, did) == ("MATCH_EXACT", 4)


# --- Stockage (Phases 2-3) ------------------------------------------------------

@pytest.fixture()
def store(tmp_path):
    s = RevueStore(db_path=str(tmp_path / "t.db"))
    with s:
        yield s


def _rec(url="https://x/a/", **kw):
    base = {"title": "t", "url": url, "resource_type": "REVUE",
            "issue_number": 1, "issue_year": 2023, "pdf_url": "https://x/a.pdf",
            "discovery_methods": ["C_sitemaps"]}
    base.update(kw)
    return base


def test_store_upsert_et_pending(store):
    store.upsert_resource(_rec())
    store.upsert_resource(_rec())  # pas de doublon
    assert len(store.pending_pdfs()) == 1
    store.mark_downloaded("https://x/a/", "/tmp/a.pdf", 123, "abc", 335)
    assert store.pending_pdfs() == []
    assert store.counts_by_status() == {"telecharge": 1}


def test_store_erreur_puis_reprise(store):
    store.upsert_resource(_rec())
    store.mark_error("https://x/a/", "HTTP fail")
    assert len(store.pending_pdfs()) == 1  # reprise


def test_store_index_entries(store):
    n = store.insert_entries([
        {"decision_number": "86132", "decision_year": 1993, "issue_number": 4,
         "issue_year": 1993, "start_page": 110, "chamber": "الاجتماعیة",
         "subject": "تنفیذ حكم", "source_pdf": "g.pdf", "source_page": 302,
         "raw_text": "raw", "normalized_text": "norm", "parser_status": "ok"},
    ])
    assert n == 1
    st = store.index_stats()
    assert st["total"] == 1 and st["annees"] == (1993, 1993)


# --- Téléchargement (Phase 2) ----------------------------------------------------

def test_logical_name_unicite(tmp_path):
    a = {"resource_type": "GUIDE", "issue_year": None, "issue_number": None,
         "url": "https://x/page-1/", "pdf_url": "https://x/g1.pdf"}
    b = {"resource_type": "GUIDE", "issue_year": None, "issue_number": None,
         "url": "https://x/page-2/", "pdf_url": "https://x/g1.pdf"}  # même PDF, page différente
    na, nb = logical_name(a), logical_name(b)
    assert na != nb  # pas de collision (bug corrigé)


def test_validate_pdf():
    p = Path(__file__).parent / "_tmp_test.pdf"
    p.write_bytes(b"%PDF-1.7 ..." + b"x" * 20000)
    ok, msg = validate_pdf(p)
    assert ok
    p.write_bytes(b"not a pdf" + b"x" * 20000)
    ok, msg = validate_pdf(p)
    assert not ok
    p.unlink()
