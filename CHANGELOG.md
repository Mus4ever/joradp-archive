# Changelog Technique du Projet

Toutes les modifications notables documentées sur ce dépôt sont consignées ci-dessous, établies à partir de l'historique Git officiel et des états de travail validés.

---

## [Phase 10] - Intégration CorpusDB & Correction Bidi Revue (2026-09-10 / 2026-09-11)
### Added
- Intégration complète des sources Cour suprême Revue (3 274 décisions) et Conseil d'État (329 décisions) dans `databases/corpus.db`.
- Détection et création de 146 relations documentaires univoques `SAME_DECISION_DIFFERENT_SOURCE` entre la Cour suprême HTML et la Revue.
- Test de non-régression bidi arabe `test_guide_cell_bidi_direction` dans `tests/test_revue.py`.
- Outil interactif d'exploration locale `tools/explorer_server.py`.
- Documentation exhaustive de l'architecture (`docs/architecture/`), du dictionnaire de données (`docs/data/`) et de la reproductibilité (`docs/methodology/`).

### Fixed
- Correction du bug d'inversion droite-gauche (double inversion) dans `sources/coursupreme/revue/guide_parser.py` : alignement des mots dans l'ordre visuel gauche-droite avant normalisation logique.
- Re-parsing de 5 227 entrées d'index du Guide v4 et répercussion dans `revue_decisions` et `corpus.db` (validation de 937 principes commençant par « من المقرر قانونا », 0 inversé).
- Résolution des ambiguïtés de clés primaires dans la gestion des doublons stricts via suffixe hash et id source déterministe.

### Validated
- 96 tests automatisés validés (`python -m pytest tests/` : 100% PASS).
- `PRAGMA integrity_check` : OK sur `databases/corpus.db` (236 090 documents, 853 500 articles, 146 relations).

---

## [Phase 9] - Intégration Conseil d'État (2026-09-09 / 2026-09-10)
### Added
- Adaptateur canonique `corpus/conseildetat_adapter.py`.
- Tests unitaires et d'idempotence `tests/test_conseildetat_adapter.py`.
- Ingestion des 329 décisions du Conseil d'État (328 décisions judiciaires, 1 fascicule doctrinal).

### Validated
- Validation Gold Set Conseil d'État 30/30 (100% concordance).
- Absence de collision sur les canonical IDs.

---

## [Phase 8] - Calcul des Offsets & Textes Intégraux Legacy Revue (2026-09-09 / 2026-09-10)
### Added
- Module `sources/coursupreme/revue/offset_calculator.py` calculant l'offset page imprimée vs page PDF (text markers, footers, search, fallback).
- Script `sources/coursupreme/revue/segment_legacy.py` associant le texte OCR intégral aux 1 319 décisions Legacy.
- Création des tables `revue_decision_texts` (1 311 textes, 1 303 non-vides) et `revue_offsets` (80 offsets).

### Validated
- Évaluation Gold Set 30/30 sur les textes Legacy.

---

## [Phase 7] - Corpus Jurisprudence Multi-Sources (Commit `e3e2f19` - 2026-09-09)
### Added
- Modèle canonique `corpus/models.py` (`CanonicalDocument`, `DocumentProvenance`, `Article`).
- Schéma relationnel `corpus/schema.py` (`CorpusDB`).
- Adaptateur Cour suprême HTML (`corpus/coursupreme_adapter.py`).
- Adaptateur Cour suprême Revue (`corpus/coursupreme_revue_adapter.py`).
- Parser JORADP (`corpus/joradp_parser.py`).

---

## [Phase 6] - Scraper Jurisprudence Cour Suprême HTML (2026-09-08 / 2026-09-09)
### Added
- Scraper complet pour la Cour suprême (`sources/coursupreme/`).
- Parsing HTML, normalisation, détection de chambre par classe CSS stable.
- 1 253 fiches décisions uniques collectées et stockées dans `databases/coursupreme.db`.
- Script de vérification de complétude `verif_completude.py`.

---

## [Phases 1-5] - Archivage & Traitement JORADP (2026-08-27 / 2026-08-28)
### Added
- Pipeline d'archivage des 10 432 PDF du Journal officiel (1962-2026).
- Gestion du vieux protocole TLS via truststore et renégociation legacy.
- Rate limiter thread-safe (délai 2s).
- Suivi SQLite `joradp.db` avec vérification SHA-256 intégrale.
- Benchmark OCR multi-moteurs (Tesseract, EasyOCR, PaddleOCR, Surya) documenté dans les rapports.
