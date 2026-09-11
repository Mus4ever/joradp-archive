"""Tests unitaires de l'adaptateur Cour suprême HTML et de son intégration dans CorpusDB."""

import pytest
from pathlib import Path

from corpus.coursupreme_adapter import CourSupremeAdapter
from corpus.models import (
    CanonicalDocument,
    DocumentNature,
    DocumentType,
    Jurisdiction,
    Language,
    TextCompleteness,
)
from corpus.schema import CorpusDB

ROOT = Path(__file__).resolve().parent.parent


def test_build_base_canonical_id():
    """Vérifie la génération déterministe de l'identifiant de base."""
    cid = CourSupremeAdapter.build_base_canonical_id("1068024", "2017-06-15")
    assert cid == "cs_decision_1068024_2017-06-15_ar"

    # Caractères spéciaux et zéros
    cid2 = CourSupremeAdapter.build_base_canonical_id("007799", "2016-01-13")
    assert cid2 == "cs_decision_007799_2016-01-13_ar"

    # Valeurs manquantes
    cid_none = CourSupremeAdapter.build_base_canonical_id(None, None)
    assert cid_none == "cs_decision_sans_numero_sans_date_ar"


def test_adapter_disambiguation_logic():
    """Vérifie que seules les réelles collisions reçoivent un suffixe de hash."""
    raw_samples = [
        {
            "id": 1,
            "decision_number": "100",
            "date": "2020-01-01",
            "text": "Texte unique",
            "content_hash": "aaaa111122223333",
            "raw_path": "fake/path/1.html",
        },
        {
            "id": 2,
            "decision_number": "200",
            "date": "2020-02-02",
            "text": "Texte collision 1",
            "content_hash": "bbbb111122223333",
            "raw_path": "fake/path/2.html",
        },
        {
            "id": 3,
            "decision_number": "200",
            "date": "2020-02-02",
            "text": "Texte collision 2",
            "content_hash": "cccc111122223333",
            "raw_path": "fake/path/3.html",
        },
    ]

    docs = CourSupremeAdapter.to_canonical_documents(raw_samples)
    assert len(docs) == 3

    # Doc 1 : Pas de collision -> base_id pur
    assert docs[0].canonical_id == "cs_decision_100_2020-01-01_ar"

    # Docs 2 et 3 : Collision -> désambiguïsateur par hash
    assert docs[1].canonical_id == "cs_decision_200_2020-02-02_ar_bbbb1111"
    assert docs[2].canonical_id == "cs_decision_200_2020-02-02_ar_cccc1111"


def test_adapter_against_coursupreme_db():
    """Vérifie la conversion complète des 1 253 décisions réelles depuis coursupreme.db."""
    db_path = ROOT / "databases" / "coursupreme.db"
    if not db_path.exists():
        pytest.skip("databases/coursupreme.db non trouvée")

    raw_decisions = CourSupremeAdapter.load_raw_decisions_from_db(db_path)
    assert len(raw_decisions) == 1253

    docs = CourSupremeAdapter.to_canonical_documents(raw_decisions)
    assert len(docs) == 1253

    # Unicité stricte des IDs
    ids = [d.canonical_id for d in docs]
    assert len(set(ids)) == 1253

    # Exactement 4 décisions avec suffixe de hash (les 2 paires de collisions)
    disambiguated = [d for d in docs if "_" in d.canonical_id and len(d.canonical_id.split("_")[-1]) == 8]
    assert len(disambiguated) == 4

    # Typage et métadonnées canoniques
    for d in docs:
        assert d.document_type == DocumentType.DECISION
        assert d.document_nature == DocumentNature.JUDICIAL_DECISION
        assert d.jurisdiction == Jurisdiction.SUPREME_COURT
        assert d.language == Language.AR
        assert d.provenance is not None
        assert d.provenance.source_db == "coursupreme.db"
        assert d.canonical_hash is not None
        assert d.full_text is not None and len(d.full_text) > 50


def test_insertion_in_corpus_db_memory():
    """Vérifie l'insertion et l'idempotence des décisions Cour suprême dans CorpusDB (:memory:)."""
    db = CorpusDB(":memory:")
    db.open()

    raw_samples = [
        {
            "id": 1,
            "decision_number": "12345",
            "date": "2019-05-15",
            "subject": "مسؤولية مدنية",
            "text": "نص القرار الكامل...",
            "chamber": "الغرف المدنية",
            "principle": "المبدأ القانوني",
            "court_response": "رد المحكمة",
            "disposition": "منطوق القرار",
            "content_hash": "abcd1234efgh5678" * 4,
            "raw_path": "fake/1.html",
            "source_url": "https://coursupreme.dz/decision/1/",
        }
    ]

    docs = CourSupremeAdapter.to_canonical_documents(raw_samples)
    doc = docs[0]

    # Première insertion
    ok1 = db.insert_document(doc)
    assert ok1 is True
    ok_p1 = db.insert_provenance(doc.canonical_id, doc.provenance)
    assert ok_p1 is True

    # Relecture
    retrieved = db.get_document(doc.canonical_id)
    assert retrieved is not None
    assert retrieved["document_number"] == "12345"
    assert retrieved["subject"] == "مسؤولية مدنية"
    assert retrieved["jurisdiction"] == "SUPREME_COURT"

    # Idempotence (INSERT OR IGNORE)
    ok2 = db.insert_document(doc)
    assert ok2 is False  # Ignore car déjà existant

    db.close()
