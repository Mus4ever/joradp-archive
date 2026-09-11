import unittest
from corpus.coursupreme_revue_adapter import CourSupremeRevueAdapter
from corpus.models import (
    DocumentType,
    DocumentNature,
    Jurisdiction,
    CourtLevel,
    Language,
    ExtractionMethod,
)

class TestCourSupremeRevueAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = CourSupremeRevueAdapter.load_raw_decisions_from_db("databases/coursupreme_revue.db")
        cls.docs = CourSupremeRevueAdapter.to_canonical_documents(cls.raw, "data/revue", "databases/coursupreme_revue.db")

    def test_total_count(self):
        self.assertEqual(len(self.docs), 3274)
        self.assertEqual(len(self.raw), 3274)

    def test_canonical_id_uniqueness(self):
        ids = [d.canonical_id for d in self.docs]
        self.assertEqual(len(ids), 3274)
        self.assertEqual(len(set(ids)), 3274, "All 3274 canonical_ids must be 100% unique!")

    def test_idempotence(self):
        docs_second = CourSupremeRevueAdapter.to_canonical_documents(self.raw, "data/revue", "databases/coursupreme_revue.db")
        ids_first = [d.canonical_id for d in self.docs]
        ids_second = [d.canonical_id for d in docs_second]
        self.assertEqual(ids_first, ids_second)
        hashes_first = [d.canonical_hash for d in self.docs]
        hashes_second = [d.canonical_hash for d in docs_second]
        self.assertEqual(hashes_first, hashes_second)

    def test_document_attributes(self):
        for doc in self.docs:
            self.assertIsNotNone(doc.canonical_id)
            self.assertEqual(doc.document_type, DocumentType.DECISION)
            self.assertEqual(doc.document_nature, DocumentNature.JUDICIAL_DECISION)
            self.assertEqual(doc.jurisdiction, Jurisdiction.SUPREME_COURT)
            self.assertEqual(doc.court_level, CourtLevel.SUPREME_COURT)
            self.assertEqual(doc.language, Language.AR)
            self.assertEqual(doc.provenance.source_db, "coursupreme_revue.db")
            self.assertEqual(doc.provenance.source_table, "revue_decisions")

if __name__ == "__main__":
    unittest.main()
