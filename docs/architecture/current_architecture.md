# Architecture Actuelle du Système — Corpus Juridique Algérien

> **Statut du document** : Architecture constatée et validée (septembre 2026).  
> **Composant central** : `databases/corpus.db` (2,04 Go, 236 090 documents, 853 500 articles).  
> **Note d'étape** : Le Small Language Model (SLM) et le Dataset Builder ne sont **pas encore construits**. Le projet se situe actuellement au jalon : **Corpus Juridique Structuré + CorpusDB Validé**.

---

## 1. Vue d'Ensemble du Flux de Données

```
========================================================================================================
                                     SOURCES PRIMAIRES BRUTES
========================================================================================================
   [ JORADP (Site Officiel) ]     [ Cour suprême (HTML) ]      [ Cour suprême (Revue) ]   [ Conseil d'État (HTML/PDF) ]
     10 432 PDF (1962-2026)         1 253 Fiches HTML             80 Numéros (86 PDF)       329 Fiches HTML & PDF
      (8,4 Go archivés)              (raw/coursupreme/)           32 065 pages OCR          (raw/ & downloads/)
             |                               |                              |                           |
             v                               v                              v                           v
========================================================================================================
                                     EXTRACTION & OCR PIPELINES
========================================================================================================
   - Mistral OCR (Scans)           - Parsing BeautifulSoup       - Mistral OCR pages         - PDF Plumber / Tesseract
   - Extraction native (PDF num)   - Extraction métadonnées       - Guide v4 (760 pages)      - Normalisation dates ISO
   - Sorties dans Extraction/                                    - Offset Calculator
             |                               |                              |                           |
             v                               v                              v                           v
========================================================================================================
                                     BASES STAGING INTERMÉDIAIRES
========================================================================================================
      [ joradp.db ]               [ coursupreme.db ]          [ coursupreme_revue.db ]        [ conseildetat.db ]
   10 432 entrées sources          1 253 décisions classées      3 274 décisions unifiées        329 décisions classées
                                                                 (1955 mod. + 1319 leg.)
             |                               |                              |                           |
             +-------------------------------+------------------------------+---------------------------+
                                             |
                                             v
========================================================================================================
                                  ADAPTATEURS CANONIQUES (corpus/)
========================================================================================================
    - JORADP Parser & Segmenter (`corpus/joradp_parser.py`)
    - Cour Suprême HTML Adapter (`corpus/coursupreme_adapter.py`)
    - Cour Suprême Revue Adapter (`corpus/coursupreme_revue_adapter.py`)
    - Conseil d'État Adapter (`corpus/conseildetat_adapter.py`)
    - Modèle unifié (`corpus/models.py`) : CanonicalDocument, DocumentProvenance, Article
             |
             v
========================================================================================================
                                      CORPUSDB CENTRALISÉ
========================================================================================================
                                  `databases/corpus.db` (SQLite WAL)
        -----------------------------------------------------------------------------------------
        * documents   : 236 090 entrées (lois, ordonnances, décrets, arrêts, revues)
        * articles    : 853 500 entrées (articles normatifs fins JORADP)
        * provenance  : 236 090 entrées (traçabilité source_db, table, URL, chemin, hash)
        * relations   : 146 liens inter-sources vérifiés (SAME_DECISION_DIFFERENT_SOURCE)
        -----------------------------------------------------------------------------------------
                                             |
                                             | (Prochaines étapes - Non démarrées)
                                             v
========================================================================================================
                                  FUTURS COMPOSANTS (HORS DU SCOPE ACTUEL)
========================================================================================================
    [ Future Dataset Builder ] --------> [ Future Fine-Tuning Pipeline ] -------> [ Future SLM Juridique ]
    (Génération SFT / Q&A pairs)          (LoRA / QLoRA / Instruct)                 (Droit Algérien)
```

---

## 2. Modèle de Données Canonique

Le modèle repose sur des structures dataclasses rigides (`corpus/models.py`) sérialisables en SQLite :

1. **`CanonicalDocument`** :
   - `canonical_id` (PRIMARY KEY) : Identifiant pérenne et déterministe (`{prefix}_{id}_{lang}`).
   - `document_type` : Type juridique normalisé (`LAW`, `DECREE`, `DECISION`, `ORDER`, etc.).
   - `document_nature` : Nature de premier niveau (`LEGISLATIVE_NORM`, `JUDICIAL_DECISION`, `DOCTRINE_REVIEW`).
   - `jurisdiction` : Organe émetteur (`REPUBLIC`, `SUPREME_COURT`, `STATE_COUNCIL`).
   - `court_level` : Degré juridictionnel (`SUPREME_COURT`, `STATE_COUNCIL`, etc.).
   - `chamber` & `section` : Formation de jugement.
   - `title`, `document_number`, `date`, `year`, `language`.
   - `subject`, `keywords`, `legal_references`, `principle`, `court_response`, `disposition`.
   - `full_text` : Texte intégral unifié nettoyé des artefacts d'extraction.
   - `text_completeness` : Degré de complétude (`FULL_TEXT`, `PARTIAL_TEXT`, `INDEX_ONLY`).
   - `extraction_method` : Provenance technique (`OCR_MISTRAL`, `NATIVE_HTML`, `NATIVE_PDF`).
   - `canonical_hash` : SHA-256 du texte intégral et des attributs clés pour détection de duplication.

2. **`DocumentProvenance`** :
   - Clé étrangère 1-à-1 avec `CanonicalDocument`.
   - Trace la base staging source (`source_db`), la table d'origine (`source_table`), l'identifiant local (`source_id`), l'URL web (`source_url`), le chemin du fichier brut (`raw_path`), le chemin PDF (`pdf_path`), et le hash d'intégrité (`content_hash`).

3. **`Article`** :
   - Rattaché aux textes normatifs JORADP (`parent_document_id`).
   - Capture le découpage textuel (`article_number`, `article_title`, `article_content`, `order_index`).

4. **`Relation`** :
   - Graphe de liens bi-directionnels ou orientés entre documents.
   - Actuellement peuplé par les 146 relations `SAME_DECISION_DIFFERENT_SOURCE` (confiance 1.0) reliant une fiche HTML Cour suprême à sa contrepartie issue de la Revue.

---

## 3. Stratégie de Résolution des Collisions et Identifiants Déterministes

Les identifiants ne dépendent **jamais** d'un auto-incrément séquentiel ou de l'ordre d'ingestion :
- JORADP : `jo_{lang}_{year}_{issue:03d}_{num_slug}`
- Cour suprême HTML : `cs_decision_{num}_{date}_{lang}` (avec suffixe hash de désambiguïsation en cas de doublon strict de numéro).
- Cour suprême Revue : `cs_revue_{issue_year}_{issue_number:02d}_{decision_number}_{lang}`
- Conseil d'État : `ce_decision_{decision_number}_{date}_{lang}` (ou `ce_doctrine_revue_...` pour l'unique fascicule doctrinal).

---

## 4. Outil d'Exploration Local

Pour naviguer et inspecter la base sans manipulation SQL directe, le serveur web local interactif [explorer_server.py](file:///c:/Users/Gaming/OneDrive/Bureau/Scraping/joradp-archive/tools/explorer_server.py) (accessible via `python tools/explorer_server.py` sur le port 8501) propose :
- Tableaux de bord synthétiques et répartition par source/langue/nature.
- Filtrage temps réel par juridiction, chambre, type d'acte, année et mot-clé.
- Visualisation bilingue avec gestion RTL complète pour l'arabe.
