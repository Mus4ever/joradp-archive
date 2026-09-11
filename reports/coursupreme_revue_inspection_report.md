# Rapport d'Inspection Approfondie — Cour suprême : Revue Judiciaire (مجلة المحكمة العليا)

**Date d'inspection** : 10 septembre 2026  
**Auteur** : Antigravity (Inspection Offline — Lecture seule stricte)  
**CorpusDB sous contrôle** : Inchangée (232 487 documents, 853 500 articles JORADP intacts)  
**Verdict d'inspection** : **`NEEDS_PARSER_FIX`** ⚠️

---

## 1. Inventaire Complet du Corpus

L'inspection physique et directe du système de fichiers et des bases SQLite locales a permis d'établir avec certitude l'état des lieux suivant :

| Composant | Emplacement réel | Volume / Décompte | Description / Statut |
| :--- | :--- | :---: | :--- |
| **Fichiers PDF originaux** | `data/revue/*.pdf` | **86 fichiers** (344,76 Mo) | 80 numéros réguliers + 4 guides officiels + 2 numéros spéciaux. Tous présents sur disque (0 manquant). |
| **Fichiers OCR structurés** | `data/revue/{année}/issue_{NN}/pages/page-N/` | **80 numéros** (32 065 pages) | Sorties OCR Mistral complètes : `markdown.md`, images extraites et métadonnées JSON par numéro. |
| **Base de données Staging** | `databases/coursupreme_revue.db` | **22,55 Mo** | 4 tables actives : `revue_resources`, `revue_index`, `revue_matches`, `revue_decisions`. |
| **Index officiel (Guide)** | Table `revue_index` (issue du Guide v4 2024) | **5 737 entrées** | Index officiel des décisions de 1989 à 2023 extrait par géométrie `pdfplumber` et bidi-normalisation. |
| **Décisions extraites existantes**| Table `revue_decisions` | **3 274 décisions** | Données pré-segmentées selon l'état actuel de la pipeline. |
| **Période temporelle couverte** | 1989 à 2023 (35 années) | **1989 – 2023** | 4 numéros/an (1989–1994) puis 2 numéros/an (1995–2023). Trous confirmés : 1994 n°04 et 2023 n°02. |
| **Scripts et Modules existants** | `sources/coursupreme/revue/` | **10 fichiers Python** | `arabic_normalize.py`, `downloader.py`, `guide_parser.py`, `ingest_all.py`, `matching.py`, `models.py`, `revue_store.py`, `segmenter.py`, `segment_legacy.py`. |
| **Tests existants** | `tests/test_revue.py` | **16 tests** (100% passés) | Couvre normalisation bidi, extraction de formes de présentation arabe, matching à 3 niveaux. |

---

## 2. Inventaire Détaillé des Revues et Ressources

Sur les 91 URLs inventoriées dans `revue_resources` :
- **80 numéros réguliers (`REVUE`)** : Tous téléchargés en PDF et entièrement OCRisés en Markdown (32 065 pages, 100 % de couverture OCR).
- **4 guides d'indexation (`GUIDE`)** :
  1. *Guide de recherche v4 (2024)* : 760 pages (`guide_دليل-البحث-الطبعة-الرابعة_b26b27fe.pdf`).
  2. *Guide de recherche v3* : 739 pages.
  3. *Guide des décisions de la Commission d'indemnisation v2* : 63 pages.
  4. *Guide des décisions de la Commission d'indemnisation v1* : 59 pages.
- **2 numéros spéciaux (`OTHER`)** :
  1. Numéro spécial *المسؤولية المدنية* (2020) : 332 pages.
  2. Numéro spécial *دور التشريع* : 141 pages.
- **5 liens de navigation WordPress (`OTHER`)** : Pages de listing HTML sans PDF propre.

---

## 3. Structure d'une Décision dans la Revue (Modèle Physique Réel)

Contrairement au HTML du site de la Cour suprême (où chaque décision est une page isolée avec des classes CSS et balises WordPress structurées), la Revue présente **deux régimes éditoriaux historiques radicalement différents** :

### A. Régime Moderne (2005 – 2023)
- Les décisions sont introduites par un en-tête typographique explicite :
  `ملف رقم [NNNNNN] قرار بتاريخ [AAAA/MM/JJ]`
- Les métadonnées sont titrées avec deux-points :
  - `الموضوع:` (Sujet / Objet)
  - `الكلمات الأساسية:` (Mots-clés)
  - `المرجع القانوني:` (Visa textuel)
  - `المبدأ:` (Principe de droit)
- Corps judiciaire : `إن المحكمة العليا...` suivi des visas, de la composition de la formation, de la motivation des moyens.
- Fin de décision : Formule solennelle `فلهذه الأسباب قررت المحكمة العليا...` ou `تقضي المحكمة العليا...`.

### B. Régime Ancien / Legacy (1989 – 2004)
- La juridiction s'intitule **المجلس الأعلى** (Cour suprême avant réformes).
- **Absence de marqueur standard de début** : Pas de `ملف رقم ... قرار بتاريخ ...`.
- Le titre commence directement par le sommaire / principe en gras, ou par `إن المجلس الأعلى`.
- Les dates sont formulées en toutes lettres arabes dans le dispositif final (ex. *الخامس عشر من شهر نوفمبر سنة تسع وثمانين وتسعمائة وألف*), rendant la détection par regex de date ISO inopérante.
- Le numéro de dossier n'est souvent pas répété dans le texte courant de la page (ou seulement référencé dans les visas).
- **Point d'ancrage fondamental** : Le Guide officiel v4 fournit pour chaque décision de cette période son `decision_number`, sa chambre, son sujet, son principe, et sa **page exacte de publication** dans la revue (`start_page`).

---

## 4. Analyse Critique de la Segmentation Actuelle et des ~3 274 Décisions

Le nombre de **3 274 décisions** actuellement enregistrées dans `revue_decisions` provient d'une composition hybride :
1. **1 955 décisions (59,7 %)** détectées par le script `segmenter.py` via les regex de texte (`DECISION_START_RE`).
2. **1 319 décisions (40,3 %)** insérées par le script `segment_legacy.py` directement depuis `revue_index` (Guide officiel).

### Matrice Réelle de la Segmentation Actuelle

| Catégorie | Nombre | Pourcentage | Analyse et Nature du Contenu |
| :--- | :---: | :---: | :--- |
| **Décisions détectées par le texte (Marqueurs OCR)** | **1 955** | 59,7 % | Texte intégral et dispositif présents (ou quasi-présents). Période dominante : 2005–2023 et 1989–1990. |
| **Entrées injectées depuis l'Index (Legacy)** | **1 319** | 40,3 % | **Métadonnées seules de l'Index Guide !** Le script `segment_legacy.py` n'a extrait **aucun texte** du dossier OCR pour ces 1 319 entrées (le champ de texte n'a pas été lu, seule la référence a été copiée). |
| **Total table `revue_decisions`** | **3 274** | 100,0 % | — |

> [!WARNING]
> ### DÉCOUVERTE CRITIQUE : Nature des 1 319 décisions "Legacy"
> L'inspection du code de `segment_legacy.py` (lignes 75–85) prouve que les 1 319 décisions des années 1991 à 2004 ont été insérées comme de simples coquilles de métadonnées depuis l'index, **sans lier le texte des pages Markdown correspondantes** qui sont pourtant bien présentes sur disque (ex. `data/revue/1991/issue_01/pages/page-25/markdown.md`).
> Si nous les chargions telles quelles dans `CorpusDB`, 40,3 % des décisions de la Revue seraient dépourvues de texte intégral !

---

## 5. Classification de Qualité Rigoureuse

Selon les exigences du modèle canonique `CanonicalDocument` :

| Statut Qualité | Critères stricts | Volume Réel Actuel | % | Action requise |
| :--- | :--- | :---: | :---: | :--- |
| **`FULL_TEXT`** | Décision ayant son texte intégral délimité (début, corps, motivation, dispositif) et longueur > 500 caractères. | **1 359** | 41,5 % | Prêtes pour l'ingestion une fois les bornes affinées. |
| **`PARTIAL_TEXT`** | Décision détectée dans le texte OCR mais avec coupure de page ou sans dispositif explicite (`has_disposition = 0`). | **596** | 18,2 % | Vérifier le raccordement avec la page $N+1$. |
| **`INDEX_ONLY`** | Entrée disposant uniquement des métadonnées du guide (numéro, matière, principe) sans texte intégral extrait. | **1 319** | 40,3 % | **Doit être transformée en `FULL_TEXT`** en lisant les pages OCR à partir de `start_page` avant ingestion. |
| **`OCR_LOW_CONFIDENCE`** | Pages avec fort taux de bruit OCR ou inversion de colonnes (estimé sur revues 1989-1994). | ~150 | ~4,5 % | Marquage qualité explicite sans rejet. |

---

## 6. Analyse du Guide / Index (5 737 Entrées)

- **Total entrées Guide v4** : 5 737.
- **Entrées exploitables avec `start_page` et `decision_number`** : **4 717 (82,2 %)**.
- **Entrées groupées / multi-décisions (`partial`)** : **987 (17,2 %)** (plusieurs numéros de pourvoi regroupés sous un même arrêt de principe).
- **Erreurs de parsing du guide (`error`)** : **33 (0,6 %)**.

### Chevauchement avec les 1 253 décisions Cour suprême HTML :
- **MATCH_EXACT** (même numéro + même année/date) : **148 à 176** (~3 % à 4,5 %).
- **NEW** (décisions historiques inédites absentes du portail HTML) : **plus de 5 500 décisions** (95,5 %).
- **Conclusion** : La Revue apporte un corpus de jurisprudence massivement inédit (1989-2023) qui décuple le patrimoine jurisprudentiel algérien disponible.

---

## 7. Analyse des Problèmes OCR Réels

L'inspection des fichiers `markdown.md` réels (notamment 1989, 1991, 2005, 2023) montre :
1. **Qualité globale du texte** : Mistral OCR a fourni une transcription arabe de très haute qualité sémantique. Les termes juridiques (*المجلس الأعلى, عريضة الطعن بالنقض, الوجه الأول, خرق القانون*) sont orthographiés avec fidélité.
2. **Sommaires et tables des matières** : Dans certains numéros, les lignes du sommaire en début de revue se terminent par des pointillés et un numéro de page (ex. `... 24`). Si la regex est laxiste, une ligne de sommaire peut être faussement prise pour une décision.
3. **Absence de numéros en tête (Legacy 1991-2004)** : Les pages débutant une décision ne contiennent souvent pas la mention `ملف رقم`, car la décision commence directement par le texte du principe ou l'intitulé de la chambre.
4. **Pagination Guide vs Pagination PDF** :
   - Sur l'échantillon vérifié (ex. revue 1991-01, arrêt n° 55985 indexé à la page 27 du guide), le texte de la décision démarre physiquement à la **page 25 du fichier PDF/OCR** (qui porte le numéro imprimé `- 27 -` en pied de page).
   - **Constat clé** : La pagination indiquée dans le Guide officiel correspond à la **pagination imprimée au bas de la page**, qui est décalée de 1 à 4 pages par rapport à la numérotation des pages du PDF (à cause de la couverture et des pages de titre).

---

## 8. Proposition de Stratégie pour `canonical_id`

Pour éviter toute collision et garantir la traçabilité absolue :

### Structure proposée :
$$\text{canonical\_id} = \texttt{cs\_revue\_\{issue\_year\}\_\{issue\_number\}\_p\{start\_page\}\_\{decision\_number\}\_ar}$$

Exemples :
- `cs_revue_2023_01_p44_1435440_ar`
- `cs_revue_1991_01_p27_55985_ar`

### Avantages majeurs :
1. **100 % déterministe et reproductible** : Lié aux coordonnées éditoriales physiques de la revue.
2. **Zéro collision** : Même si deux arrêts partagent un numéro de dossier (cas des pourvois joints ou arrêts rectificatifs), ils se distinguent par leur numéro de revue ou page de début.
3. **Distingue nettement la Revue du HTML** : Les décisions HTML utilisent le préfixe `cs_decision_...`, tandis que la Revue utilise `cs_revue_...`. Lorsqu'une décision est commune aux deux sources, la table `relations` de CorpusDB formalisera le lien `SAME_AS` / `DUPLICATE`.

---

## 9. Adéquation avec le Modèle Canonique (`corpus/models.py`)

Les classes existantes `CanonicalDocument` et `DocumentProvenance` couvrent 95 % des besoins.

### Champs directement réutilisables :
- `document_type = DocumentType.DECISION`
- `document_nature = DocumentNature.JUDICIAL_DECISION`
- `jurisdiction = Jurisdiction.SUPREME_COURT`
- `court_level = CourtLevel.SUPREME_COURT`
- `chamber`, `title`, `document_number`, `date`, `year`, `language = Language.AR`
- `subject`, `keywords`, `legal_references`, `principle`, `court_response`, `disposition`, `full_text`
- `provenance` : `source_db="coursupreme_revue.db"`, `source_table="revue_decisions"`, `source_id`, `pdf_path`, `raw_path`

### Champs spécifiques recommandés (dans `extra_metadata` ou extension légère) :
- `publication_number` : Renseigné avec `f"{issue_year}/{issue_number:02d}"` (numéro officiel de livraison de la revue).
- `page_start` / `page_end` : Numéros de pages physiques dans le volume imprimé.
- `detection_source` : `OCR_TEXT_MARKER` vs `INDEX_GUIDE_LINKED`.

---

## 10. Proposition de Stratégie pour le Gold Set

Il est recommandé de constituer un **Gold Set de 30 décisions annotées manuellement** (environ 1 % du corpus) réparti ainsi :
1. **Régime Moderne (2005–2023)** : 10 décisions (couvrant chambres civile, commerciale, sociale, pénale, statut personnel).
2. **Régime Ancien (1989–2004)** : 12 décisions (dont 1989-01, 1991-01, 1995-01, 2001-02) pour valider l'extraction du texte via l'index.
3. **Cas avec dispositif complexe** : 4 décisions.
4. **Cas de matching avec le HTML (148 arrêts communs)** : 4 décisions pour vérifier la conformité du texte entre la version Web HTML et la version imprimée Revue.

---

## 11. Risques et Problèmes Détectés

### Problèmes Bloquants pour une Ingestion Immédiate :
1. **Les 1 319 décisions "Legacy" n'ont pas de texte attaché** : Le script existant `segment_legacy.py` n'a fait que copier l'index. Si nous ingérons la base telle quelle, nous injecterions 1 319 coquilles vides (`full_text = None`).
2. **Décalage de pagination (Offset Guide vs PDF)** : Le numéro de page du Guide correspond au numéro imprimé (ex. page 27 imprimée = page 25 PDF). Le parseur doit appliquer un raccordement précis page imprimée ↔ page OCR.

### Problèmes Non Bloquants :
1. Les dates en toutes lettres des décisions 1989-2004 ne sont pas normalisées en format ISO `YYYY-MM-DD` (le champ `date` reste NULL pour 40 % des arrêts, mais le champ `year` est connu avec exactitude via la revue).
2. 33 entrées de l'index du guide ont un statut `error` (cas atypiques de tableau corrompu dans le PDF du guide).

---

## 12. Verdict Final

> ### ⚠️ VERDICT : **`NEEDS_PARSER_FIX`**
> 
> **Motif circonstancié** :  
> Bien que 100 % des données physiques soient présentes (86 PDF, 32 065 pages OCR en Markdown haute fidélité, 5 737 entrées d'index), **le pipeline de segmentation actuel est incomplet** : il n'a pas encore lié les 1 319 décisions anciennes (1991–2004) à leurs pages de texte Markdown respectives et traite ces décisions comme de simples métadonnées d'index.
> 
> **Avant toute ingestion dans CorpusDB**, il est impératif de :
> 1. Ajuster le segmentateur de texte pour lire les pages Markdown correspondant au `start_page` du Guide.
> 2. Délimiter le texte intégral pour l'ensemble des ~3 274 décisions.
> 3. Valider l'extraction sur le Gold Set de 30 décisions.
> 
> **Aucune modification n'a été apportée à CorpusDB (232 487 documents préservés à l'octet près).**
