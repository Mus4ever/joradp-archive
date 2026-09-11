"""Tests unitaires du corpus canonique unifié.

Couvre :
    - Création de la base en mémoire (:memory:)
    - Insertion / lecture de documents avec provenance
    - Insertion d'articles JORADP et navigation hiérarchique
    - Relations inter-documents (duplicate, language_pair)
    - Contraintes d'unicité (canonical_id, relations)
    - Round-trip : insertion → lecture → comparaison
    - Statistiques (count_by, find_duplicates_by_hash)
"""

import pytest
from datetime import datetime

from corpus.models import (
    CanonicalDocument,
    Article,
    DocumentProvenance,
    DocumentType,
    DocumentNature,
    Jurisdiction,
    CourtLevel,
    TextCompleteness,
    ExtractionMethod,
    ExtractionQuality,
    AnonymizationStatus,
    Language,
)
from corpus.schema import CorpusDB


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture
def db():
    """Base en mémoire, créée et détruite à chaque test."""
    corpus = CorpusDB(db_path=":memory:")
    corpus.open()
    yield corpus
    corpus.close()


def _make_cs_decision(canonical_id: str = "cs_decision_129299_2017-04-20_ar") -> CanonicalDocument:
    """Fabrique une décision Cour suprême type pour les tests."""
    return CanonicalDocument(
        canonical_id=canonical_id,
        document_type=DocumentType.DECISION,
        document_nature=DocumentNature.JUDICIAL_DECISION,
        jurisdiction=Jurisdiction.SUPREME_COURT,
        court_level=CourtLevel.SUPREME_COURT,
        chamber="الغرف المدنية",
        document_number="129299",
        date="2017-04-20",
        year=2017,
        language=Language.AR,
        subject="عقد بيع",
        keywords='["عقد", "بيع", "فسخ"]',
        principle="المبدأ: يجب على المحكمة...",
        court_response="رد المحكمة العليا عن الوجه المثار...",
        disposition="قبول الطعن ونقض القرار",
        full_text="نص القرار الكامل...",
        text_format="plain_text",
        text_completeness=TextCompleteness.FULL_TEXT,
        extraction_method=ExtractionMethod.NATIVE_HTML,
        extraction_quality=ExtractionQuality.HIGH,
        canonical_hash="abc123def456",
        anonymization_status=AnonymizationStatus.ANONYMIZED,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )


def _make_cs_provenance() -> DocumentProvenance:
    """Fabrique une provenance Cour suprême type."""
    return DocumentProvenance(
        source_db="coursupreme.db",
        source_table="decisions",
        source_id=42,
        source_url="https://www.coursupreme.dz/decision/129299",
        raw_path="raw/coursupreme/129299.html",
        content_hash="sha256_of_html",
        ingested_at=datetime.now().isoformat(),
    )


def _make_cde_decision() -> CanonicalDocument:
    """Fabrique une décision Conseil d'État type."""
    return CanonicalDocument(
        canonical_id="cde_decision_015456_2013-06-18_ar",
        document_type=DocumentType.DECISION,
        document_nature=DocumentNature.JUDICIAL_DECISION,
        jurisdiction=Jurisdiction.STATE_COUNCIL,
        court_level=CourtLevel.STATE_COUNCIL,
        chamber="الغرفة الثانية",
        section="القسم الأول",
        document_number="015456",
        date="2013-06-18",
        year=2013,
        language=Language.AR,
        subject="إلغاء قرار إداري",
        principle="المبدأ: يتعين على القاضي الإداري...",
        full_text="نص القرار الكامل للمجلس...",
        text_completeness=TextCompleteness.FULL_TEXT,
        extraction_method=ExtractionMethod.NATIVE_HTML,
        extraction_quality=ExtractionQuality.HIGH,
        canonical_hash="xyz789",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )


def _make_joradp_law() -> CanonicalDocument:
    """Fabrique un acte JORADP type (loi)."""
    return CanonicalDocument(
        canonical_id="joradp_loi_06-01_2006-02-20_fr",
        document_type=DocumentType.LAW,
        document_nature=DocumentNature.LEGISLATIVE_NORM,
        jurisdiction=Jurisdiction.REPUBLIC,
        court_level=CourtLevel.LEGISLATIVE,
        title="Loi n° 06-01 du 20 février 2006 relative à la prévention et à la lutte contre la corruption",
        document_number="06-01",
        publication_number="FR2006014",
        date="2006-02-20",
        year=2006,
        language=Language.FR,
        full_text="Le Président de la République...",
        text_format="markdown",
        text_completeness=TextCompleteness.FULL_TEXT,
        extraction_method=ExtractionMethod.MARKDOWN_PARSE,
        extraction_quality=ExtractionQuality.HIGH,
        canonical_hash="law_hash_001",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )


def _make_index_entry() -> CanonicalDocument:
    """Fabrique une entrée d'index Revue (INDEX_ONLY)."""
    return CanonicalDocument(
        canonical_id="cs_index_098765_2005_ar",
        document_type=DocumentType.INDEX_ENTRY,
        document_nature=DocumentNature.INDEX_METADATA,
        jurisdiction=Jurisdiction.SUPREME_COURT,
        court_level=CourtLevel.SUPREME_COURT,
        document_number="098765",
        date="2005-03-15",
        year=2005,
        language=Language.AR,
        subject="تعويض",
        principle="المبدأ المستخلص من الفهرس...",
        text_completeness=TextCompleteness.INDEX_ONLY,
        extraction_method=ExtractionMethod.INDEX_TABLE,
        extraction_quality=ExtractionQuality.MEDIUM,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )


# ──────────────────────────────────────────────────────────────────────
# Tests — Création de la base
# ──────────────────────────────────────────────────────────────────────

class TestSchemaCreation:
    """Vérifie que la base est créée correctement avec toutes les tables et index."""

    def test_tables_exist(self, db: CorpusDB):
        tables = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = {r["name"] for r in tables}
        assert "documents" in names
        assert "provenance" in names
        assert "articles" in names
        assert "relations" in names

    def test_indexes_exist(self, db: CorpusDB):
        indexes = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        ).fetchall()
        idx_names = {r["name"] for r in indexes}
        # Vérifier quelques index critiques
        assert "idx_doc_type" in idx_names
        assert "idx_doc_hash" in idx_names
        assert "idx_doc_search" in idx_names
        assert "idx_prov_source" in idx_names
        assert "idx_art_parent" in idx_names
        assert "idx_rel_source" in idx_names

    def test_empty_counts(self, db: CorpusDB):
        counts = db.table_counts()
        assert counts == {"documents": 0, "provenance": 0, "articles": 0, "relations": 0}

    def test_foreign_keys_enabled(self, db: CorpusDB):
        fk = db.conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1


# ──────────────────────────────────────────────────────────────────────
# Tests — Insertion et lecture de documents
# ──────────────────────────────────────────────────────────────────────

class TestDocumentCRUD:
    """Insertion, lecture et contraintes des documents."""

    def test_insert_cs_decision(self, db: CorpusDB):
        doc = _make_cs_decision()
        assert db.insert_document(doc) is True
        assert db.count_documents() == 1

    def test_insert_with_provenance(self, db: CorpusDB):
        doc = _make_cs_decision()
        prov = _make_cs_provenance()
        db.insert_document(doc)
        assert db.insert_provenance(doc.canonical_id, prov) is True
        counts = db.table_counts()
        assert counts["documents"] == 1
        assert counts["provenance"] == 1

    def test_get_document_with_provenance(self, db: CorpusDB):
        """Round-trip : insertion → lecture → comparaison des champs."""
        doc = _make_cs_decision()
        prov = _make_cs_provenance()
        db.insert_document(doc)
        db.insert_provenance(doc.canonical_id, prov)

        result = db.get_document(doc.canonical_id)
        assert result is not None
        assert result["canonical_id"] == "cs_decision_129299_2017-04-20_ar"
        assert result["document_type"] == "DECISION"
        assert result["jurisdiction"] == "SUPREME_COURT"
        assert result["chamber"] == "الغرف المدنية"
        assert result["document_number"] == "129299"
        assert result["year"] == 2017
        assert result["language"] == "AR"
        assert result["text_completeness"] == "FULL_TEXT"
        # Provenance jointe
        assert result["source_db"] == "coursupreme.db"
        assert result["source_table"] == "decisions"
        assert result["source_id"] == 42

    def test_duplicate_canonical_id_ignored(self, db: CorpusDB):
        """INSERT OR IGNORE : le deuxième insert est silencieusement ignoré."""
        doc = _make_cs_decision()
        assert db.insert_document(doc) is True
        assert db.insert_document(doc) is False  # Doublon ignoré
        assert db.count_documents() == 1

    def test_get_nonexistent_returns_none(self, db: CorpusDB):
        assert db.get_document("inexistant_id") is None

    def test_multiple_jurisdictions(self, db: CorpusDB):
        """Insertion de documents de 3 juridictions différentes."""
        db.insert_document(_make_cs_decision())
        db.insert_document(_make_cde_decision())
        db.insert_document(_make_joradp_law())
        assert db.count_documents() == 3

        by_jurisdiction = db.count_by("jurisdiction")
        assert by_jurisdiction["SUPREME_COURT"] == 1
        assert by_jurisdiction["STATE_COUNCIL"] == 1
        assert by_jurisdiction["REPUBLIC"] == 1

    def test_index_only_document(self, db: CorpusDB):
        """Un document INDEX_ONLY est correctement typé."""
        doc = _make_index_entry()
        db.insert_document(doc)
        result = db.get_document(doc.canonical_id)
        assert result["text_completeness"] == "INDEX_ONLY"
        assert result["extraction_method"] == "INDEX_TABLE"
        assert result["document_nature"] == "INDEX_METADATA"


# ──────────────────────────────────────────────────────────────────────
# Tests — Articles JORADP
# ──────────────────────────────────────────────────────────────────────

class TestArticles:
    """Insertion et navigation hiérarchique des articles."""

    def test_insert_articles(self, db: CorpusDB):
        law = _make_joradp_law()
        db.insert_document(law)

        articles = [
            Article(
                parent_document_id=law.canonical_id,
                article_number="1er",
                title="Objet",
                text="La présente loi a pour objet de renforcer...",
                language=Language.FR,
                ordinal=1,
                created_at=datetime.now().isoformat(),
            ),
            Article(
                parent_document_id=law.canonical_id,
                article_number="2",
                title="Champ d'application",
                text="Les dispositions de la présente loi s'appliquent...",
                language=Language.FR,
                ordinal=2,
                created_at=datetime.now().isoformat(),
            ),
            Article(
                parent_document_id=law.canonical_id,
                article_number="3",
                text="Au sens de la présente loi, on entend par...",
                language=Language.FR,
                ordinal=3,
                created_at=datetime.now().isoformat(),
            ),
        ]
        for art in articles:
            assert db.insert_article(art) is True

        counts = db.table_counts()
        assert counts["articles"] == 3

    def test_get_articles_ordered(self, db: CorpusDB):
        """Les articles sont retournés triés par ordinal."""
        law = _make_joradp_law()
        db.insert_document(law)

        # Insertion dans le désordre
        for ordinal, num in [(3, "3"), (1, "1er"), (2, "2")]:
            db.insert_article(Article(
                parent_document_id=law.canonical_id,
                article_number=num,
                text=f"Texte de l'article {num}",
                language=Language.FR,
                ordinal=ordinal,
                created_at=datetime.now().isoformat(),
            ))

        arts = db.get_articles(law.canonical_id)
        assert len(arts) == 3
        assert arts[0]["article_number"] == "1er"
        assert arts[1]["article_number"] == "2"
        assert arts[2]["article_number"] == "3"

    def test_no_articles_for_decision(self, db: CorpusDB):
        """Une décision judiciaire n'a pas d'articles."""
        doc = _make_cs_decision()
        db.insert_document(doc)
        assert db.get_articles(doc.canonical_id) == []


# ──────────────────────────────────────────────────────────────────────
# Tests — Relations inter-documents
# ──────────────────────────────────────────────────────────────────────

class TestRelations:
    """Relations de duplication, bilinguisme et citations."""

    def test_insert_duplicate_relation(self, db: CorpusDB):
        cs = _make_cs_decision()
        idx = _make_index_entry()
        db.insert_document(cs)
        db.insert_document(idx)

        assert db.insert_relation(
            source_id=idx.canonical_id,
            target_id=cs.canonical_id,
            relation_type="duplicate_of",
            confidence=0.85,
        ) is True

        rels = db.get_relations(cs.canonical_id)
        assert len(rels) == 1
        assert rels[0]["relation_type"] == "duplicate_of"
        assert rels[0]["confidence"] == 0.85

    def test_language_pair_relation(self, db: CorpusDB):
        """Lien bilinguisme FR ↔ AR."""
        law_fr = _make_joradp_law()
        law_ar = CanonicalDocument(
            canonical_id="joradp_loi_06-01_2006-02-20_ar",
            document_type=DocumentType.LAW,
            document_nature=DocumentNature.LEGISLATIVE_NORM,
            jurisdiction=Jurisdiction.REPUBLIC,
            court_level=CourtLevel.LEGISLATIVE,
            document_number="06-01",
            date="2006-02-20",
            year=2006,
            language=Language.AR,
            full_text="رئيس الجمهورية...",
            text_completeness=TextCompleteness.FULL_TEXT,
            extraction_method=ExtractionMethod.MARKDOWN_PARSE,
            extraction_quality=ExtractionQuality.HIGH,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        db.insert_document(law_fr)
        db.insert_document(law_ar)

        db.insert_relation(
            source_id=law_fr.canonical_id,
            target_id=law_ar.canonical_id,
            relation_type="language_pair",
        )

        rels_fr = db.get_relations(law_fr.canonical_id)
        rels_ar = db.get_relations(law_ar.canonical_id)
        assert len(rels_fr) == 1
        assert len(rels_ar) == 1  # La même relation apparaît des deux côtés

    def test_duplicate_relation_ignored(self, db: CorpusDB):
        """UNIQUE(source_id, target_id, relation_type) empêche les doublons."""
        cs = _make_cs_decision()
        idx = _make_index_entry()
        db.insert_document(cs)
        db.insert_document(idx)

        assert db.insert_relation(idx.canonical_id, cs.canonical_id, "duplicate_of") is True
        assert db.insert_relation(idx.canonical_id, cs.canonical_id, "duplicate_of") is False

    def test_same_pair_different_types_allowed(self, db: CorpusDB):
        """Deux documents peuvent avoir plusieurs types de relation."""
        cs = _make_cs_decision()
        idx = _make_index_entry()
        db.insert_document(cs)
        db.insert_document(idx)

        db.insert_relation(idx.canonical_id, cs.canonical_id, "duplicate_of")
        db.insert_relation(idx.canonical_id, cs.canonical_id, "cites")

        rels = db.get_relations(cs.canonical_id)
        types = {r["relation_type"] for r in rels}
        assert types == {"duplicate_of", "cites"}


# ──────────────────────────────────────────────────────────────────────
# Tests — Statistiques et doublons
# ──────────────────────────────────────────────────────────────────────

class TestStatistics:
    """Comptages et détection de doublons."""

    def test_count_by_jurisdiction(self, db: CorpusDB):
        db.insert_document(_make_cs_decision())
        db.insert_document(_make_cde_decision())
        db.insert_document(_make_joradp_law())
        db.insert_document(_make_index_entry())

        by_j = db.count_by("jurisdiction")
        assert by_j["SUPREME_COURT"] == 2  # CS decision + index
        assert by_j["STATE_COUNCIL"] == 1
        assert by_j["REPUBLIC"] == 1

    def test_count_by_completeness(self, db: CorpusDB):
        db.insert_document(_make_cs_decision())
        db.insert_document(_make_index_entry())

        by_c = db.count_by("text_completeness")
        assert by_c["FULL_TEXT"] == 1
        assert by_c["INDEX_ONLY"] == 1

    def test_count_by_invalid_field_raises(self, db: CorpusDB):
        with pytest.raises(ValueError, match="Nom de champ invalide"):
            db.count_by("DROP TABLE documents; --")

    def test_find_duplicates_by_hash(self, db: CorpusDB):
        """Deux documents avec le même hash sont détectés comme doublons."""
        doc1 = _make_cs_decision("cs_decision_001_2017-04-20_ar")
        doc2 = _make_cs_decision("cs_decision_002_2017-04-20_ar")
        # Même hash
        doc1.canonical_hash = "SAME_HASH"
        doc2.canonical_hash = "SAME_HASH"
        db.insert_document(doc1)
        db.insert_document(doc2)

        dupes = db.find_duplicates_by_hash()
        assert len(dupes) == 1
        assert dupes[0]["cnt"] == 2
        ids = dupes[0]["ids"].split(",")
        assert set(ids) == {"cs_decision_001_2017-04-20_ar", "cs_decision_002_2017-04-20_ar"}

    def test_no_duplicates_when_unique_hashes(self, db: CorpusDB):
        db.insert_document(_make_cs_decision())
        db.insert_document(_make_cde_decision())
        assert db.find_duplicates_by_hash() == []


# ──────────────────────────────────────────────────────────────────────
# Tests — Modèles (sérialisation)
# ──────────────────────────────────────────────────────────────────────

class TestModels:
    """Vérifie la sérialisation des dataclasses et enums."""

    def test_document_to_dict_enums_serialized(self):
        doc = _make_cs_decision()
        d = doc.to_dict()
        assert d["document_type"] == "DECISION"
        assert d["jurisdiction"] == "SUPREME_COURT"
        assert d["language"] == "AR"
        assert d["text_completeness"] == "FULL_TEXT"
        assert d["anonymization_status"] == "ANONYMIZED"

    def test_provenance_to_dict(self):
        prov = _make_cs_provenance()
        d = prov.to_dict()
        assert d["source_db"] == "coursupreme.db"
        assert d["source_id"] == 42

    def test_article_to_dict(self):
        art = Article(
            parent_document_id="joradp_loi_06-01_2006-02-20_fr",
            article_number="1er",
            text="Texte...",
            language=Language.FR,
            ordinal=1,
        )
        d = art.to_dict()
        assert d["language"] == "FR"
        assert d["ordinal"] == 1

    def test_enum_values_consistency(self):
        """Chaque enum a une valeur string identique à son nom."""
        for e in DocumentType:
            assert e.value == e.name
        for e in TextCompleteness:
            assert e.value == e.name
        for e in ExtractionQuality:
            assert e.value == e.name
