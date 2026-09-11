# Histoire Complète du Projet — De l'Archivage Initial au Corpus Juridique Canonique

> **Document de Référence Technique & Scientifique**  
> **Dépôt** : `https://github.com/Mus4ever/joradp-archive`  
> **Auteur** : Équipe de Développement  
> **Date de rédaction** : 11 septembre 2026  
> **État du système** : Corpus consolidé et validé dans `databases/corpus.db` (236 090 documents, 853 500 articles).  
> **Statut IA** : Données prêtes. Modèle de fine-tuning non encore entraîné. Dataset final non encore généré.

---

## 1. Résumé Exécutif

Le projet `joradp-archive` a débuté comme un pipeline de scraping et d'archivage des 10 432 journaux officiels algériens (JORADP) en format PDF. Face au constat de la pauvreté des modèles d'IA généralistes sur le droit algérien et à l'objectif académique de construire un Small Language Model (SLM) juridique spécialisé, le projet s'est mué en un programme complet de construction de corpus juridique unifié.

Aujourd'hui, le projet a achevé l'ingestion, le nettoyage, la segmentation, la normalisation et la validation de **quatre grands fonds documentaires** algériens :
1. La législation complète du Journal Officiel (1962–2026) : 231 234 actes découpés en 853 500 articles.
2. La jurisprudence HTML récente de la Cour suprême (1979–2023) : 1 253 décisions structurées.
3. La jurisprudence historique de la Revue de la Cour suprême (1989–2023) : 3 274 décisions (1 955 segmentées dans le texte moderne et 1 319 réconciliées avec les scans OCR des numéros anciens via détection d'offset).
4. Le contentieux administratif du Conseil d'État (1998–2022) : 329 décisions et revues doctrinales.

L'ensemble est hébergé dans une base relationnelle SQLite normalisée (`databases/corpus.db`, 2,04 Go) dotée d'une traçabilité documentaire intégrale (`DocumentProvenance`) et d'un graphe de 146 relations inter-sources.

---

## 2. Idée et Motivation

### 2.1. Le Problème du Droit Algérien dans les LLMs Actuels
Les modèles fondationnels propriétaires ou open-source (GPT-4, Claude 3.5, Llama 3) souffrent de limitations critiques lorsqu'ils sont confrontés au droit algérien :
- **Absence de corpus d'entraînement spécialisé** : Le droit algérien n'étant pas numérisé sous forme de base de données ouverte et structurée sur le web, les modèles n'ont ingéré que des fragments textuels épars et désuets.
- **Hallucinations juridiques graves** : Les modèles inventent des numéros d'articles de codes (Code civil, Code pénal, Code de procédure civile et administrative) ou citent des jurisprudences égyptiennes ou françaises sous couvert de droit algérien.
- **Bilinguisme juridique asymétrique** : La législation est bilingue (arabe et français), tandis que la jurisprudence des juridictions suprêmes est rédigée exclusivement en langue arabe depuis l'arabisation de la justice.

### 2.2. Objectif Scientifique et Produit
- **Scientifique** : Démontrer qu'un petit modèle de langage (SLM de 7B à 8B paramètres) adapté par fine-tuning supervisé (SFT) et adaptation par bas rang (QLoRA) sur un corpus juridique national nettoyé surpasse un LLM généraliste de 70B+ en précision de citation, exactitude textuelle et raisonnement en droit local.
- **Produit envisagé à terme** : Un assistant d'aide à la décision juridique pour professionnels (magistrats, avocats, juristes d'entreprise) capable, à partir d'un exposé des faits, d'identifier le droit positif applicable, de citer les articles pertinents et d'exposer la jurisprudence constante de la Cour suprême.

---

## 3. Évolution de l'Architecture Technique

### 3.1. Phase Initiale (Août 2026) : Simple Archivage JORADP
Le projet visait initialement le téléchargement brut des PDF depuis le site officiel `joradp.dz`.  
*Outils créés :* `tools/discover.py`, `tools/download_optimized.py`, base de suivi `joradp.db`.  
*Contraintes résolues :* Serveurs d'État appliquant d'anciens chiffrements TLS (nécessitant `truststore` et renégociation legacy) et imposant un rate-limiting rigide de 2 secondes.

### 3.2. Phase Intermédiaire (Fin Août - Début Septembre 2026) : Traitement de Masse OCR JORADP
Extraction textuelle des 10 432 PDF :
- Scans anciens (FR 1962–2001 et tout l'AR 1964–2026) traités par Mistral OCR (678 000 blocs et fichiers de coordonnées).
- Numériques récents (FR 2002–2026) extraits nativement.
- Constat d'homogénéité : 100% du corpus JORADP structuré en Format A (`markdown.md`, `header.md`, `page-metadata.json`).

### 3.3. Phase d'Expansion Juridique (Septembre 2026) : Jurisprudence Multi-Sources
Intégration de la Cour suprême (fiches HTML du portail officiel + 80 revues papier numérisées) et du Conseil d'État.  
*Changement conceptuel :* Passage de simples dossiers de scraping à une **couche d'abstraction canonique** (`corpus/models.py`, `corpus/schema.py`) permettant de fusionner normes législatives et arrêts judiciaires au sein de `databases/corpus.db`.

---

## 4. Documentation Détaillée par Source

### 4.1. JORADP (Journal Officiel)
- **Volume** : 10 432 numéros (5 302 FR, 5 130 AR).
- **Période** : 1962 à 2026.
- **Segmentation** : Le module `corpus/joradp_parser.py` segmente les journaux complets en actes juridiques unitaires (lois, ordonnances, décrets, arrêtés) et isole chaque article (`Article 1er`, `المادة الأولى`).
- **Résultat en base** : **231 234 documents normatifs** et **853 500 articles**.

### 4.2. Cour Suprême — Fiches HTML (`coursupreme.dz`)
- **Volume** : 1 253 décisions uniques.
- **Période** : 1979–2023 (forte concentration sur 2016-2018).
- **Structure** : Parsing HTML des sections normalisées : en-tête de chambre, visas, dispositif, réponse de la Cour, principe de droit.
- **Qualité** : 100% complétude, absence de doublons après détection par numéro et date ISO.

### 4.3. Cour Suprême — Revue Judiciaire (المجلة القضائية)
- **Volume** : 80 numéros (86 PDF, 32 065 pages OCRisées avec Mistral OCR).
- **Index Officiel** : Guide de recherche v4 (760 pages) extrait via `sources/coursupreme/revue/guide_parser.py` (5 227 entrées d'index).
- **Le problème de la double inversion bidi** : Dans les versions initiales, les tokens extraits du PDF étaient triés de droite à gauche avant l'application de `visual_to_logical()`, ce qui inversait l'ordre des mots dans les principes en arabe. Corrigé en septembre 2026 par tri visuel gauche-droite préalable (test unitaire validé, 937 principes commençant par « من المقرر », 0 inversé).
- **Le problème du décalage de pagination (Offset)** : La page 30 du guide papier ne correspond pas à la page 30 du fichier PDF. Le module `offset_calculator.py` a déterminé l'offset pour chacune des 80 revues. Le script `segment_legacy.py` a permis d'extraire le texte intégral pour **1 310 décisions historiques** (8,7 millions de caractères récupérés).
- **Total Revue** : **3 274 décisions** intégrées (1 955 modernes + 1 319 legacy).

### 4.4. Conseil d'État
- **Volume** : 329 fiches extraites du portail Drupal 11 et 329 PDF téléchargés.
- **Typologie** : 328 décisions judiciaires du contentieux administratif (1998–2022) et 1 fascicule doctrinal de la revue du Conseil d'État (2015).
- **Adaptateur** : `corpus/conseildetat_adapter.py` avec extraction des dispositifs et principes.

---

## 5. Architecture de CorpusDB (`databases/corpus.db`)

La base unifiée repose sur SQLite en mode Write-Ahead Logging (WAL) et garantit l'intégrité relationnelle :
- **Table `documents` (236 090 lignes)** : Entité juridique unifiée dotée d'un identifiant canonique (`canonical_id`), d'une classification hiérarchique (`jurisdiction`, `court_level`, `document_type`, `document_nature`), du texte intégral et de métadonnées juridiques.
- **Table `articles` (853 500 lignes)** : Découpage granulaire des actes du Journal Officiel.
- **Table `provenance` (236 090 lignes)** : Traçabilité absolue liant chaque document à sa base staging (`source_db`), sa table source, son URL publique et son hash SHA-256.
- **Table `relations` (146 lignes)** : Correspondances avérées `SAME_DECISION_DIFFERENT_SOURCE` reliant les fiches HTML de la Cour suprême aux décisions publiées dans la Revue.

---

## 6. Table Récapitulative des Problèmes et Solutions

| Composant | Problème Rencontré | Solution Apportée | Statut |
|---|---|---|---|
| **Réseau / TLS** | Échec des requêtes vers `joradp.dz` et `coursupreme.dz` avec OpenSSL 3. | Client HTTP personnalisé avec truststore système et support sécurisé des renégociations legacy. | **RÉSOLU** |
| **Revue (Bidi)** | Inversion de l'ordre des mots arabes dans les cellules de principe du Guide. | Correction du tri horizontal des tokens (LTR avant `visual_to_logical`). | **RÉSOLU & TESTÉ** |
| **Revue (Pagination)** | Décalage entre pages papier du Guide et pages réelles des scans PDF. | Module `offset_calculator.py` multi-critères (marqueurs, pieds de page, recherche). | **RÉSOLU & VALIDÉ** |
| **Identifiants** | Collisions de clés primaires sur les décisions partageant un numéro de rôle. | Construction d'identifiants déterministes incorporant la date ou une empreinte cryptographique. | **RÉSOLU** |
| **Intégrité CorpusDB** | Risque d'altération des 231 234 actes JORADP lors des mises à jour de jurisprudence. | Transactions SQLite strictes et scripts de répercussion ciblés avec clause WHERE sur `source_db`. | **RÉSOLU & AUDITÉ** |

---

## 7. Ce qui est Fait vs Ce qui Reste à Faire

### État de Maturité par Composant :

| Composant | Statut | Preuve / Artefact | Limites Connues |
|---|---|---|---|
| **Collecte JORADP** | **DONE** | 10 432 PDF téléchargés, base `joradp.db` | Aucune |
| **Parsing & Articles JORADP** | **DONE** | 231 234 docs, 853 500 articles en base | Sommaires parfois non linéaires sur vieux scans |
| **Cour suprême HTML** | **DONE** | 1 253 décisions dans `databases/coursupreme.db` | Période limitée (essentiellement post-2014) |
| **Cour suprême Revue** | **DONE** | 3 274 décisions, Guide v4 parsé (5 227 entrées) | Textes legacy extraits par plages de pages |
| **Conseil d'État** | **DONE** | 329 fiches/PDF dans `databases/conseildetat.db` | Volume modeste (329 décisions disponibles) |
| **CorpusDB Unifié** | **VALIDATED** | `databases/corpus.db` (PRAGMA integrity_check: ok) | 2 Go localement |
| **Dataset de Fine-Tuning** | **NOT STARTED** | — | Nécessite définition du format d'instruction |
| **Entraînement SLM** | **NOT STARTED** | — | Choix du modèle de base à arrêter |
| **Architecture RAG / Multi-Agents** | **NEEDS DECISION** | — | Discussion d'orientation avec le professeur |

---

## 8. Note sur le Reel Haiku et Orientations Futures

Le professeur a partagé une vidéo présentant **Haiku**, un système d'IA juridique reposant sur une architecture multi-agents et des moteurs de recherche spécialisés.

**Constat d'équipe :**  
- L'infrastructure actuelle de `joradp-archive` n'a volontairement pas intégré d'architecture multi-agents hâtive, afin de privilégier la pureté, l'intégrité et la documentation de la base documentaire.
- **CorpusDB** constitue le socle indispensable à tout système aval. Que la décision finale s'oriente vers un modèle de langage compact entraîné par QLoRA, un pipeline RAG dense/sparse ou une société d'agents spécialisés (législation, jurisprudence, rédaction), la bibliothèque de données est prête, propre, traçable et directement exploitable.
