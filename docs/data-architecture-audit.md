# Audit d'Architecture des Données — Corpus Juridique Algérien

> **Document de référence — Phase 1**  
> **Projet** : https://github.com/Mus4ever/joradp-archive  
> **Date** : 10 septembre 2026  
> **Objectif** : Dresser l'état des lieux rigoureux de toutes les données et composants existants, identifier les verrous de qualité et définir l'architecture canonique cible pour préparer le corpus avant l'entraînement d'un Small Language Model (SLM) juridique spécialisé en droit algérien.

---

## 1. Résumé Exécutif et État Actuel du Corpus

Le dépôt rassemble actuellement quatre fonds documentaires complémentaires couvrant la législation et la jurisprudence algérienne :

| Source | Volume / Fichiers | Période | Langues | Format RAW | Format Actuel | Statut Global |
|---|---|---|---|---|---|---|
| **1. JORADP** | **10 432 numéros** (5 302 FR, 5 130 AR) | 1962–2026 | FR, AR | 10 432 PDF (8,4 Go) | Markdown (`Extraction/`) | ✅ Collecte 100% terminée.<br>✅ Format A homogène sur tout le corpus (FR 1962–2026 & AR 1964–2026). Aucune ré-extraction nécessaire. Prochaine étape : parsing en actes/articles. |
| **2. Cour suprême (HTML)** | **1 253 décisions uniques** | 1979–2023 (pic 2016-18) | AR (100%) | HTML brut (`raw/coursupreme/`) | SQLite (`databases/coursupreme.db`) | ✅ Fiches HTML complètes et structurées (99% complétude sur les champs clés). |
| **3. Cour suprême (Revue)** | **80 numéros** (86 PDF, 32 065 pages OCRisées, 5 737 entrées d'index) | 1989–2023 | AR (majoritaire), FR ponctuel | PDF revue + PDF guide dans `data/revue/` | SQLite (`databases/coursupreme_revue.db`) + pages OCR | ✅ 3 274 décisions identifiées (1 955 segmentées texte, 1 319 issues du guide/index). Distinction texte vs index à formaliser. |
| **4. Conseil d'État** | **329 décisions** (324 jurisprudence, 4 arrêts choisis, 1 revue) | 1998–2022 | AR (100%) | HTML brut (`raw/conseildetat/`) + 329 PDF (`downloads/conseildetat/`) | SQLite (`databases/conseildetat.db`) | ✅ Fiches HTML extraites à 100%, 329 PDF téléchargés et vérifiés par SHA-256. Audit de lisibilité PDF native à réaliser. |

### Les 4 bases SQLite existantes

1. `joradp.db` (3,16 Mo) : table `sources` (10 432 entrées — suivi téléchargement/SHA-256 des PDF).
2. `databases/coursupreme.db` (11,38 Mo) : table `decisions` (1 253 décisions avec 32 colonnes).
3. `databases/coursupreme_revue.db` (21,51 Mo) : tables `revue_resources` (91 lignes), `revue_index` (5 737 lignes), `revue_matches` (5 704 lignes), `revue_decisions` (3 274 lignes).
4. `databases/conseildetat.db` (1,08 Mo) : table `decisions` (329 décisions avec 27 colonnes).

---

## 2. Analyse Détaillée par Source

### 2.1. JORADP (Journal Officiel de la République Algérienne)
- **Nature** : Textes normatifs (lois, ordonnances, décrets législatifs, décrets exécutifs, arrêtés ministériels, circulaires, décisions, avis).
- **Organisation physique** :
  - `Extraction/OCR-Fr/` (1962–2026) : 65 dossiers annuels.
  - `Extraction/OCR-Ar/` (1964–2026) : 63 dossiers annuels.
- **Formats constatés** :
  - **Format A généralisé (FR 1962–2026 & AR 1964–2026)** : Les 10 432 numéros sont tous sous l'arborescence standardisée Format A (`FR{année}{numéro}.pdf/markdown.md` et `pages/page-N/` avec `page-metadata.json`, `header.md`).
  - L'ancienne hypothèse d'une défaillance spécifique à FR 2002–2026 est **caduque** : l'audit d'échantillonnage sur 1965, 1985, 1998, 2005, 2015, 2024 confirme une structure sémantique régulière (sommaire, hiérarchie des actes, articles, métadonnées).
- **Ce qui reste à faire** :
  - Un parser juridique transformant les fichiers Markdown bruts de numéros complets en entités textuelles normatives individuelles (une loi = un document, un décret = un document).
  - Un découpage fin au niveau des **articles** (`Article 1er`, `المادة الأولى`, sections, chapitres).
  - La préservation du lien entre la version FR et la version AR d'un même texte législatif sans traduction automatique.

### 2.2. Cour suprême — Fiches HTML (`sources/coursupreme/`)
- **Nature** : Jurisprudence judiciaire de cassation (chambres civile, commerciale, sociale, pénale, statut personnel, etc.).
- **Métadonnées** : `court`, `chamber`, `chamber_class`, `decision_number`, `date`, `subject`, `parties`, `keywords`, `legal_references`, `principle`, `court_response`, `disposition`, `president`, `rapporteur`, `clerk`.
- **Qualité** : 1 253 fiches extraites, 0 échec, texte moyen de 4 100 caractères, HTML archivé dans `raw/coursupreme/`.
- **Points d'attention** :
  - Les parties sont déjà anonymisées sous forme d'initiales par la Cour suprême sur son site web (`(ب.ع)` contre `(ف.م)`).
  - Couverture temporelle sélective : seulement 35 décisions avant 2014, pic en 2016-2018 (789 décisions), aucune publication post-2023.

### 2.3. Cour suprême — Revue Judiciaire (`sources/coursupreme/revue/`)
- **Nature** : Revue trimestrielle/semestrielle (المجلة القضائية) publiée par la Cour suprême (1989–2023) + Guides de recherche thématiques (notamment le Guide v4).
- **Ressources** : 86 PDF téléchargés (353 Mo), 32 065 pages OCRisées avec Mistral OCR.
- **Décisions extraites** : **3 274 décisions** enregistrées dans `revue_decisions` :
  - **1 955 décisions** segmentées à partir du texte complet via les marqueurs OCR (`ملف رقم ... قرار بتاريخ ...`).
  - **1 319 décisions** issues de l'index du Guide (numéros legacy où le texte intégral n'a pas encore de marqueur clair ou provient de l'index/guide officiel).
- **Points d'attention** :
  - Distinction formelle indispensable entre les décisions en texte intégral (`FULL_TEXT`), texte partiel (`PARTIAL_TEXT`) et métadonnées d'index seules (`INDEX_ONLY`).
  - Risque d'anonymisation : les décisions imprimées dans les revues physiques historiques comportent souvent les noms complets des parties, contrairement aux fiches HTML.
  - Recouvrement mesuré : seulement ~148 décisions de la Revue sont déjà présentes dans les 1 253 fiches HTML. La Revue apporte donc plus de 3 100 décisions inédites.

### 2.4. Conseil d'État (`sources/conseildetat/`)
- **Nature** : Jurisprudence administrative souveraine (contentieux administratif, excès de pouvoir, marchés publics, fonction publique, fiscalité).
- **Ressources** : 329 décisions (324 jurisprudence générale, 4 arrêts sélectionnés récents, 1 numéro de revue de 2015).
- **Métadonnées** : `nid`, `court`, `node_type`, `decision_number`, `date`, `date_raw`, `year`, `chamber`, `section`, `keywords`, `classification`, `subject`, `principle`, `pdf_url`, `pdf_path`, `pdf_hash`.
- **Qualité actuelle** :
  - Fiches HTML Drupal 11 : 329/329 scrapées avec succès, 100% des HTML bruts archivés dans `raw/conseildetat/`.
  - Pièces jointes PDF : 329/329 téléchargées dans `downloads/conseildetat/`, intégrité SHA-256 calculée.
  - Le texte dans la fiche HTML correspond à la fiche analytique Drupal (moyenne 456 caractères). Le texte intégral se trouve dans le fichier PDF attaché.
- **Points d'attention** :
  - **Audit de lisibilité native des PDF requis** : avant tout OCR, il faut inspecter chaque PDF pour déterminer s'il s'agit d'un PDF avec couche texte exploitable ou d'un scan nécessitant un OCR ciblé.

---

## 3. Problèmes Détectés et Risques Techniques

### 3.1. Absence d'un Schéma Canonique Unifié
Chaque source possède aujourd'hui sa propre table SQLite (`sources` dans `joradp.db`, `decisions` dans `coursupreme.db`, `revue_decisions` dans `coursupreme_revue.db`, `decisions` dans `conseildetat.db`).
- Les noms de champs diffèrent (`date` vs `annee`, `chamber` vs `chamber_raw`, `type` vs `node_type`).
- Il n'existe pas d'identifiant universel permettant de lier ou dédoublonner les entités entre la Revue et le HTML de la Cour suprême, ou entre JORADP FR et AR.

### 3.2. Risque de Perte de Provenance (Data Lineage)
Pour le modèle de langage, il est impératif de savoir si un paragraphe provient :
- D'un article de loi promulgué au JORADP (force légale absolue).
- D'un attendu de principe d'un arrêt de la Cour suprême (jurisprudence constante).
- D'un simple sommaire ou index de revue juridique (`INDEX_ONLY`).
- D'un texte issu d'un OCR à faible confiance (`OCR_LOW_CONFIDENCE`).
Si ces statuts ne sont pas explicitement enregistrés, le modèle apprendra des index comme s'il s'agissait de textes intégraux.

### 3.3. Risque de Faux Doublons et Mauvais Dédoublonnage
Dans le droit algérien :
- Un numéro de décision (ex. `129299`) peut exister à la fois à la Cour suprême et au Conseil d'État.
- Plusieurs décisions d'une même chambre peuvent porter sur le même sujet le même jour.
- Une même décision peut apparaître dans le recueil HTML officiel et dans le numéro de la Revue de 2017 avec de légères variations d'espacement ou d'OCR.
- **Règle absolue** : la clé de déduplication ne doit jamais reposer uniquement sur le numéro, mais sur le tuple `(juridiction, numéro, date, chambre, hash_normalisé)`. Le dédoublonnage doit créer une relation (`duplicate_of`, `canonical_document`), **sans jamais supprimer la donnée source**.

### 3.4. Risque d'Anonymisation Incomplète
- Cour suprême HTML : initiales déjà appliquées (`(ف.م)`).
- Revue imprimée et JORADP : contiennent des patronymes complets, adresses, décrets individuels de nomination ou condamnations pénales.
- Une chaîne de traitement stricte `RAW` → `PROCESSED` → `ANONYMIZED` est indispensable, avec statut de revue humaine pour les cas ambigus.

---

## 4. Architecture Recommandée pour le Corpus Canonique

### 4.1. Modèle Conceptuel `CanonicalLegalDocument`

```text
CanonicalLegalDocument
├── id                      : UUID ou slug canonique déterministe
├── document_type           : law | decree | order | decision | review_article | index_entry
├── document_nature         : legislative_norm | judicial_decision | doctrine_review | index_metadata
├── jurisdiction            : "Cour suprême" | "Conseil d'État" | "République Algérienne"
├── court_level             : supreme_court | state_council | appellate | legislative
├── chamber                 : Chambre normalisée
├── section                 : Section le cas échéant
├── title                   : Titre de l'acte ou de la décision
├── document_number         : Numéro de décision / numéro de loi/décret
├── publication_number      : Numéro du JO ou numéro de livraison de la revue
├── date                    : Date ISO (YYYY-MM-DD)
├── year                    : Année
├── language                : "ar" | "fr"
├── subject                 : Matière / Objet / Thématique
├── keywords                : Liste de mots-clés normalisés
├── legal_references        : Textes légaux visés / appliqués
├── principle               : Principe juridique (المبدأ)
├── court_response          : Réponse de la juridiction
├── disposition             : Dispositif (منطوق القرار)
├── full_text               : Texte complet propre
├── text_format             : "markdown" | "plain_text"
├── text_completeness       : FULL_TEXT | PARTIAL_TEXT | INDEX_ONLY
├── extraction_method       : native_html | native_pdf | ocr_mistral | index_table
├── extraction_quality      : HIGH | MEDIUM | LOW_CONFIDENCE | CORRUPTED
├── provenance              : { source_db, source_table, source_id, source_url, raw_path, pdf_path }
├── language_pair_id        : ID du document miroir dans l'autre langue (si avéré)
├── parent_document_id      : Pour les articles reliés à une loi parente
├── canonical_hash          : SHA-256 du texte normalisé
├── anonymization_status    : NOT_ANONYMIZED | ANONYMIZED | REVIEW_REQUIRED
└── timestamps              : created_at, updated_at
```

### 4.2. Représentation Hiérarchique des Normes JORADP (Lois / Décrets / Articles)
Pour le JORADP, un numéro de Journal Officiel contient plusieurs textes juridiques, et chaque texte contient plusieurs articles :
```text
JORADP Issue (ex: FR1962001)
  ├── Legal Act 1 (ex: Ordonnance 62-1)
  │     ├── Article 1
  │     ├── Article 2
  │     └── Article 3
  └── Legal Act 2 (ex: Décret 62-502)
        ├── Article 1
        └── Article 2
```
Le parser JORADP doit extraire ces entités sans détruire le document source.

---

## 5. Matrice des Fichiers Existants et Fichiers à Créer

### 5.1. Fichiers Existants à Conserver Intacts
- `tools/http_client.py`, `tools/rate_limiter.py`, `tools/database.py`, `tools/download_optimized.py` : pile réseau et archivage JORADP.
- `sources/coursupreme/` : parser, models, storage, scraper de la Cour suprême.
- `sources/coursupreme/revue/` : pipeline revue (downloader, guide_parser, segmenter, matching, ocr_pilot).
- `sources/conseildetat/` : models, storage, parser, discover, scraper, downloader, rapport_qualite.
- `Extraction/`, `raw/`, `downloads/`, `data/` : tous les répertoires de données RAW.

### 5.2. Nouveaux Fichiers Recommandés (Architecture Corpus Unifié)

Pour garantir une séparation propre sans polluer les scrapers spécialisés, les modules du corpus unifié seront regroupés sous un nouveau namespace : **`corpus/`**

1. **`corpus/models.py`** : Définition des dataclasses canoniques (`CanonicalDocument`, `Article`, `DocumentProvenance`, `TextCompleteness`, `ExtractionQuality`).
2. **`corpus/schema.py`** : DDL SQLite canonique unifié (`corpus/corpus.db`) avec tables `documents`, `articles`, `provenance`, `relations` (doublons, bilinguisme).
3. **`corpus/joradp_parser.py`** : Parser regex/sémantique des fichiers Markdown JORADP (détection sommaire, bornes d'actes, détection des articles `Art. X` / `المادة X`).
4. **`corpus/conseildetat_audit.py`** : Outil d'analyse géométrique et textuelle des 329 PDF du Conseil d'État via `pdfplumber`/`pypdf` pour produire `reports/conseildetat_text_quality.json`.
5. **`corpus/revue_classifier.py`** : Typage strict des 3 274 décisions de la Revue (`FULL_TEXT`, `PARTIAL_TEXT`, `INDEX_ONLY`).
6. **`corpus/deduplicator.py`** : Moteur de déduplication multi-critères créant des liens d'équivalence sans suppression.
7. **`corpus/normalizer.py`** : Fonctions de normalisation légères et réversibles pour l'arabe et le français.
8. **`corpus/anonymizer.py`** : Masquage contrôlé des entités nommées et gestion du cycle `RAW` → `PROCESSED` → `ANONYMIZED`.
9. **`corpus/rapport_global.py`** : Générateur de synthèse du corpus total (`reports/corpus_quality_report.json` et `.md`).
10. **`tests/test_corpus_*.py`** : Suite de tests unitaires couvrant l'ensemble du pipeline.

---

## 6. Prochaines Étapes Recommandées

1. **Validation de l'audit** par le porteur du projet.
2. **Phase 2** : Implémentation du schéma canonique (`corpus/models.py`, `corpus/schema.py`).
3. **Phase 3** : Développement et test du parser JORADP sur échantillons FR et AR.
4. **Phase 5** : Audit qualité natif des 329 PDF du Conseil d'État et classification (GOOD / WEAK / FAILED).
5. **Phase 6** : Structuration de la provenance de la Revue Cour suprême (FULL_TEXT vs INDEX_ONLY).
6. **Phases 7 à 12** : Normalisation, déduplication, anonymisation, tests unitaires et rapport qualité global.
