import unittest
from pathlib import Path
from collections import Counter

from corpus.conseildetat_adapter import ConseilEtatAdapter
from corpus.models import (
    CanonicalDocument,
    DocumentType,
    DocumentNature,
    Jurisdiction,
    CourtLevel,
    Language,
    TextCompleteness,
    ExtractionQuality,
    ExtractionMethod,
)

class TestConseilEtatAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = ConseilEtatAdapter.load_raw_decisions_from_db("databases/conseildetat.db")
        cls.docs = ConseilEtatAdapter.to_canonical_documents(cls.raw, "data/Conseil")

    def test_total_count(self):
        self.assertEqual(len(self.docs), 329)
        self.assertEqual(len(self.raw), 329)

    def test_canonical_id_uniqueness(self):
        ids = [d.canonical_id for d in self.docs]
        self.assertEqual(len(ids), 329)
        self.assertEqual(len(set(ids)), 329, "All 329 canonical_ids must be 100% unique!")

    def test_idempotence(self):
        # Run conversion a second time
        docs_second = ConseilEtatAdapter.to_canonical_documents(self.raw, "data/Conseil")
        ids_first = [d.canonical_id for d in self.docs]
        ids_second = [d.canonical_id for d in docs_second]
        self.assertEqual(ids_first, ids_second, "Canonical IDs must be strictly identical across runs!")
        
        hashes_first = [d.canonical_hash for d in self.docs]
        hashes_second = [d.canonical_hash for d in docs_second]
        self.assertEqual(hashes_first, hashes_second, "Hashes must be strictly identical across runs!")

    def test_document_attributes(self):
        for doc in self.docs:
            self.assertIsNotNone(doc.canonical_id)
            self.assertIn(doc.document_type, [DocumentType.DECISION, DocumentType.REVIEW_ARTICLE])
            self.assertEqual(doc.jurisdiction, Jurisdiction.STATE_COUNCIL)
            self.assertEqual(doc.court_level, CourtLevel.STATE_COUNCIL)
            self.assertEqual(doc.language, Language.AR)
            self.assertIsNotNone(doc.full_text)
            self.assertGreater(len(doc.full_text), 500)
            self.assertEqual(doc.text_format, "markdown")
            self.assertEqual(doc.extraction_method, ExtractionMethod.OCR_MISTRAL)
            self.assertEqual(doc.provenance.source_db, "conseildetat.db")
            self.assertEqual(doc.provenance.source_table, "decisions")

    def test_disposition_extraction(self):
        with_disp = [d for d in self.docs if d.disposition]
        self.assertGreaterEqual(len(with_disp), 325, "At least 98% of decisions must have disposition extracted!")

    def test_corpus_db_counts(self):
        import sqlite3
        conn = sqlite3.connect("databases/corpus.db")
        c_docs = conn.execute("SELECT count(*) FROM documents").fetchone()[0]
        c_arts = conn.execute("SELECT count(*) FROM articles").fetchone()[0]
        c_prov = conn.execute("SELECT count(*) FROM provenance").fetchone()[0]
        conn.close()
        self.assertEqual(c_docs, 236090, "corpus.db documents must be 236090 post-integration!")
        self.assertEqual(c_arts, 853500, "corpus.db articles must remain exactly 853500!")
        self.assertEqual(c_prov, 236090, "corpus.db provenance must be 236090 post-integration!")

if __name__ == "__main__":
    unittest.main()
