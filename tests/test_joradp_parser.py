"""Tests unitaires pour le parser JORADP (corpus/joradp_parser.py).

Couvre :
    - Détection de la langue (FR / AR)
    - Parsing et normalisation des dates grégoriennes
    - Normalisation des numéros d'actes (inversion arabe 01-23 -> 23-01)
    - Typage juridique (DocumentType, slug)
    - Découpage des articles (FR et AR)
    - Isolation et élimination du sommaire
    - Appariement bilingue (link_bilingual_acts)
    - Ingestion complète dans CorpusDB
    - Tests sur fichiers réels (2023 FR/AR, 1962 FR)
"""

import os
from pathlib import Path
import pytest

from corpus.models import (
    Article,
    CanonicalDocument,
    CourtLevel,
    DocumentNature,
    DocumentType,
    Language,
    TextCompleteness,
)
from corpus.schema import CorpusDB
from corpus.joradp_parser import JORADPParser, ParsedArticle, ParsedAct


# ──────────────────────────────────────────────────────────────────────
# 1. Tests unitaires des fonctions utilitaires
# ──────────────────────────────────────────────────────────────────────

class TestParserUtilities:
    """Tests des fonctions de détection et normalisation."""

    def test_detect_language_fr(self):
        text = "Décret exécutif n° 23-09 portant répartition des crédits..."
        assert JORADPParser.detect_language(text) == Language.FR

    def test_detect_language_ar(self):
        text = "مرسوم تنفيذي رقم 09-23 يتضمن توزيع رخص الالتزام..."
        assert JORADPParser.detect_language(text) == Language.AR

    def test_parse_date_fr(self):
        assert JORADPParser.parse_date("du 2 janvier 2023 portant", Language.FR) == "2023-01-02"
        assert JORADPParser.parse_date("du 20 février 2006 relative", Language.FR) == "2006-02-20"
        assert JORADPParser.parse_date("du 1er juillet 1962 portant", Language.FR) == "1962-07-01"
        assert JORADPParser.parse_date("texte sans date", Language.FR) is None

    def test_parse_date_ar(self):
        assert JORADPParser.parse_date("الموافق 2 جانفي سنة 2023", Language.AR) == "2023-01-02"
        assert JORADPParser.parse_date("الموافق 20 فبراير عام 2006", Language.AR) == "2006-02-20"
        assert JORADPParser.parse_date("الموافق 15 جويلية 1962", Language.AR) == "1962-07-15"
        assert JORADPParser.parse_date("نص بدون تاريخ", Language.AR) is None

    def test_normalize_document_number(self):
        # Format standard
        assert JORADPParser.normalize_document_number("23-01", 2023) == "23-01"
        assert JORADPParser.normalize_document_number("06-04", 2006) == "06-04"
        # Inversion arabe fréquente (ordre-annee -> annee-ordre)
        assert JORADPParser.normalize_document_number("01-23", 2023) == "23-01"
        assert JORADPParser.normalize_document_number("04-06", 2006) == "06-04"
        # Numéro simple
        assert JORADPParser.normalize_document_number("129", 1962) == "129"
        assert JORADPParser.normalize_document_number(None, 2023) is None

    def test_detect_document_type_fr(self):
        doc_type, slug = JORADPParser.detect_document_type("Loi n° 06-01 relative à...", Language.FR)
        assert doc_type == DocumentType.LAW
        assert slug == "loi"

        doc_type, slug = JORADPParser.detect_document_type("Loi organique n° 18-15...", Language.FR)
        assert doc_type == DocumentType.LAW
        assert slug == "loi_org"

        doc_type, slug = JORADPParser.detect_document_type("Ordonnance n° 62-1...", Language.FR)
        assert doc_type == DocumentType.ORDER
        assert slug == "ord"

        doc_type, slug = JORADPParser.detect_document_type("Décret présidentiel n° 23-01...", Language.FR)
        assert doc_type == DocumentType.DECREE
        assert slug == "dp"

        doc_type, slug = JORADPParser.detect_document_type("Décret exécutif n° 23-09...", Language.FR)
        assert doc_type == DocumentType.DECREE
        assert slug == "de"

        doc_type, slug = JORADPParser.detect_document_type("Arrêté du 6 juillet 1962...", Language.FR)
        assert doc_type == DocumentType.ORDER
        assert slug == "arr"

        doc_type, slug = JORADPParser.detect_document_type("Circulaire du 6 juillet 1962...", Language.FR)
        assert doc_type == DocumentType.CIRCULAR
        assert slug == "circ"

    def test_detect_document_type_ar(self):
        doc_type, slug = JORADPParser.detect_document_type("قانون رقم 06-01 يتعلق بـ...", Language.AR)
        assert doc_type == DocumentType.LAW
        assert slug == "loi"

        doc_type, slug = JORADPParser.detect_document_type("قانون عضوي رقم 18-15...", Language.AR)
        assert doc_type == DocumentType.LAW
        assert slug == "loi_org"

        doc_type, slug = JORADPParser.detect_document_type("أمر رقم 62-1...", Language.AR)
        assert doc_type == DocumentType.ORDER
        assert slug == "ord"

        doc_type, slug = JORADPParser.detect_document_type("مرسوم رئاسي رقم 23-01...", Language.AR)
        assert doc_type == DocumentType.DECREE
        assert slug == "dp"

        doc_type, slug = JORADPParser.detect_document_type("مرسوم تنفيذي رقم 23-09...", Language.AR)
        assert doc_type == DocumentType.DECREE
        assert slug == "de"

        doc_type, slug = JORADPParser.detect_document_type("قرار مؤرخ في 6 جويلية...", Language.AR)
        assert doc_type == DocumentType.ORDER
        assert slug == "arr"


# ──────────────────────────────────────────────────────────────────────
# 2. Tests de découpage d'articles
# ──────────────────────────────────────────────────────────────────────

class TestArticleSplitting:
    """Tests de découpe des articles au sein d'un acte juridique."""

    def test_split_articles_fr(self):
        text = """
Décret présidentiel n° 23-01 du 2 janvier 2023.
Le Président de la République,
Vu la Constitution...
Décrète :

Article 1er. — Les crédits sont alloués au titre du budget.

Art. 2. — Le ministre est chargé de l'exécution du présent décret.

Art. 3 bis. — Dispositions transitoires applicables immédiatement.

Fait à Alger, le 2 janvier 2023.
Abdelmadjid TEBBOUNE.
"""
        articles = JORADPParser.split_articles(text, Language.FR)
        assert len(articles) == 3

        assert articles[0].article_number == "1er"
        assert "Les crédits sont alloués" in articles[0].text
        assert articles[0].ordinal == 1

        assert articles[1].article_number == "2"
        assert "Le ministre est chargé" in articles[1].text
        assert articles[1].ordinal == 2

        assert articles[2].article_number == "3 bis"
        assert "Dispositions transitoires" in articles[2].text
        # Vérifier que la signature finale n'a pas pollué le texte du dernier article
        assert "Abdelmadjid TEBBOUNE" not in articles[2].text

    def test_split_articles_ar(self):
        text = """
مرسوم رئاسي رقم 23-01 مؤرخ في 2 جانفي سنة 2023.
إنّ رئيس الجمهورية،
بناء على الدستور...
يرسم ما يأتي :

المادة الأولى : توزع رخص الالتزام واعتمادات الدفع المفتوحة.

المادة 2 : يكلف وزير المالية بتنفيذ هذا المرسوم.

المادة 3 مكرر : أحكام انتقالية تطبق على الفور.

حرر بالجزائر في 2 جانفي سنة 2023.
عبد المجيد تبون.
"""
        articles = JORADPParser.split_articles(text, Language.AR)
        assert len(articles) == 3

        assert articles[0].article_number == "الأولى"
        assert "توزع رخص الالتزام" in articles[0].text
        assert articles[0].ordinal == 1

        assert articles[1].article_number == "2"
        assert "يكلف وزير المالية" in articles[1].text
        assert articles[1].ordinal == 2

        assert articles[2].article_number == "3 مكرر"
        assert "أحكام انتقالية" in articles[2].text
        assert "عبد المجيد تبون" not in articles[2].text


# ──────────────────────────────────────────────────────────────────────
# 3. Tests de parsing complet sur texte synthétique
# ──────────────────────────────────────────────────────────────────────

class TestSyntheticParsing:
    """Tests sur un numéro de JO synthétique complet avec sommaire."""

    def test_parse_synthetic_fr_issue(self):
        text = """
# JOURNAL OFFICIEL
DIRECTION DE L'IMPRIMERIE

# SOMMAIRE
Décret présidentiel n° 23-01 du 2 janvier 2023 portant répartition... 3
Décret exécutif n° 23-02 du 2 janvier 2023 relatif à la nomination... 5

# DECRETS

**Décret présidentiel n° 23-01 du 2 janvier 2023 portant répartition des crédits.**

Le Président de la République,
Vu la Constitution,
Décrète :

Article 1er. — Les crédits sont alloués.
Art. 2. — Publication au Journal officiel.

Fait à Alger, le 2 janvier 2023.
Abdelmadjid TEBBOUNE.

**Décret exécutif n° 23-02 du 2 janvier 2023 fixant les attributions ministérielles.**

Le Premier ministre,
Vu la Constitution,
Décrète :

Article 1er. — Les attributions sont fixées.

Fait à Alger, le 2 janvier 2023.
Le Premier ministre.
"""
        items = JORADPParser.parse_text(
            text=text,
            year=2023,
            jo_number="001",
            lang=Language.FR,
            source_id=1,
            raw_path="test/fr_issue.md",
        )

        # Doit extraire exactement 2 actes (et ignorer les 2 lignes du sommaire)
        assert len(items) == 2

        doc1, arts1 = items[0]
        assert doc1.canonical_id == "joradp_2023_001_dp_23-01_fr"
        assert doc1.document_type == DocumentType.DECREE
        assert doc1.document_number == "23-01"
        assert doc1.date == "2023-01-02"
        assert len(arts1) == 2
        assert arts1[0].article_number == "1er"
        assert arts1[1].article_number == "2"

        doc2, arts2 = items[1]
        assert doc2.canonical_id == "joradp_2023_001_de_23-02_fr"
        assert doc2.document_type == DocumentType.DECREE
        assert doc2.document_number == "23-02"
        assert len(arts2) == 1

    def test_link_bilingual_acts(self):
        """Vérifie l'association FR/AR par correspondance de type et de numéro."""
        fr_text = """
Décret présidentiel n° 23-01 du 2 janvier 2023.
Le Président de la République,
Décrète :
Article 1er. — Répartition.
"""
        ar_text = """
مرسوم رئاسي رقم 01-23 مؤرخ في 2 جانفي سنة 2023.
إنّ رئيس الجمهورية،
يرسم ما يأتي :
المادة الأولى : التوزيع.
"""
        fr_items = JORADPParser.parse_text(fr_text, 2023, "001", Language.FR)
        ar_items = JORADPParser.parse_text(ar_text, 2023, "001", Language.AR)

        assert len(fr_items) == 1
        assert len(ar_items) == 1

        linked = JORADPParser.link_bilingual_acts(fr_items, ar_items)
        assert linked == 1

        fr_doc = fr_items[0][0]
        ar_doc = ar_items[0][0]

        assert fr_doc.language_pair_id == ar_doc.canonical_id
        assert ar_doc.language_pair_id == fr_doc.canonical_id


# ──────────────────────────────────────────────────────────────────────
# 4. Test d'ingestion dans CorpusDB
# ──────────────────────────────────────────────────────────────────────

class TestCorpusDBIntegration:
    """Vérifie que les actes et articles extraits s'insèrent correctement dans CorpusDB."""

    def test_ingest_parsed_acts(self):
        db = CorpusDB(":memory:")
        db.open()

        text = """
Décret présidentiel n° 23-01 du 2 janvier 2023 portant répartition.
Le Président de la République,
Vu la Constitution,
Décrète :

Article 1er. — Montant des crédits.
Art. 2. — Exécution.
"""
        items = JORADPParser.parse_text(text, 2023, "001", Language.FR, source_id=42)
        assert len(items) == 1
        doc, articles = items[0]

        # Insertion du document + provenance
        doc_ok = db.insert_document(doc)
        assert doc_ok is True
        prov_ok = db.insert_provenance(doc.canonical_id, doc.provenance)
        assert prov_ok is True

        # Insertion des articles
        for art in articles:
            art_ok = db.insert_article(art)
            assert art_ok is True

        # Vérification en base
        retrieved = db.get_document(doc.canonical_id)
        assert retrieved is not None
        assert retrieved["canonical_id"] == "joradp_2023_001_dp_23-01_fr"
        assert retrieved["source_id"] == 42

        # Vérification des articles
        retrieved_articles = db.get_articles(doc.canonical_id)
        assert len(retrieved_articles) == 2
        assert retrieved_articles[0]["article_number"] == "1er"
        assert retrieved_articles[1]["article_number"] == "2"

        db.close()


# ──────────────────────────────────────────────────────────────────────
# 5. Tests sur fichiers réels du corpus (si présents sur disque)
# ──────────────────────────────────────────────────────────────────────

class TestRealCorpusFiles:
    """Tests sur les données réelles extraites dans Extraction/."""

    @pytest.mark.skipif(
        not Path("Extraction/OCR-Fr/2023/FR2023001.pdf/markdown.md").exists(),
        reason="Fichier réel FR2023001 absent",
    )
    def test_real_fr_2023_001(self):
        path = "Extraction/OCR-Fr/2023/FR2023001.pdf/markdown.md"
        items = JORADPParser.parse_file(path)

        # Le numéro 1 de 2023 contient 49 décrets (23-01 à 23-49)
        assert len(items) >= 45, f"Attendu au moins 45 actes, obtenu {len(items)}"

        # Vérifier le premier acte : Décret présidentiel n° 23-01
        doc1, arts1 = items[0]
        assert doc1.document_type == DocumentType.DECREE
        assert doc1.document_number == "23-01"
        assert doc1.date == "2023-01-02"
        assert len(arts1) == 2
        assert arts1[0].article_number == "1er"

    @pytest.mark.skipif(
        not Path("Extraction/OCR-Ar/2023/AR2023001.pdf/markdown.md").exists(),
        reason="Fichier réel AR2023001 absent",
    )
    def test_real_ar_2023_001(self):
        path = "Extraction/OCR-Ar/2023/AR2023001.pdf/markdown.md"
        items = JORADPParser.parse_file(path)

        assert len(items) >= 45, f"Attendu au moins 45 actes arabes, obtenu {len(items)}"

        doc1, arts1 = items[0]
        assert doc1.document_type == DocumentType.DECREE
        assert doc1.document_number == "23-01"
        assert doc1.date == "2023-01-02"
        assert len(arts1) == 2

    @pytest.mark.skipif(
        not Path("Extraction/OCR-Fr/1962/FR1962001.pdf/markdown.md").exists(),
        reason="Fichier réel FR1962001 absent",
    )
    def test_real_fr_1962_001(self):
        path = "Extraction/OCR-Fr/1962/FR1962001.pdf/markdown.md"
        items = JORADPParser.parse_file(path)

        # Le JO 1962-001 contient exactement 8 actes officiels et 43 articles
        assert len(items) == 8, f"Attendu 8 actes officiels, obtenu {len(items)}"
        total_articles = sum(len(arts) for _, arts in items)
        assert total_articles == 43, f"Attendu 43 articles, obtenu {total_articles}"

        # Trouver l'ordonnance 62-1 (normalisée en 62-01)
        ord_items = [it for it in items if it[0].document_number in ("62-01", "62-1")]
        assert len(ord_items) == 1
        ord_doc, ord_arts = ord_items[0]
        assert ord_doc.document_type == DocumentType.ORDER
        assert len(ord_arts) == 4
        assert ord_arts[0].article_number == "1er"
        assert ord_arts[1].article_number == "2"
        assert ord_arts[2].article_number == "3"
        assert ord_arts[3].article_number == "4"
