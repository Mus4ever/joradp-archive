# Conseil d'État — Audit & Parsing Report

## 1. Inventaire

- **Fiches dans `databases/conseildetat.db`** : 329 enregistrements (329 `nid` uniques).
  - `jurisprudence` : 324 décisions standard.
  - `arrets-selectionnes` : 4 arrêts historiques / majeurs avec commentaires (`nid` 30, 367, 368, 369).
  - `publications-revue` : 1 numéro de la Revue du Conseil d'État (`nid` 28, numéro 13 de l'année 2015).
- **PDF archivés** : 329 fichiers PDF (100 % présents dans `downloads/conseildetat/`).
- **Textes OCR existants** : 329 dossiers sous `data/Conseil/` contenant chacun `markdown.md` (329 / 329, 100 % de couverture).
- **Période couverte** : 1972 à 2022 (pic d'activité entre 2002 et 2017).
- **Langue** : 100 % Arabe (`AR`) pour le corpus de jurisprudence, avec quelques métadonnées bilingues pour la Revue.

---

## 2. Qualité OCR

Statistiques calculées sur l'intégralité des 329 fichiers `markdown.md` :

| Métrique | Valeur |
|---|---|
| Fichiers OCR disponibles | **329 / 329 (100.0%)** |
| Textes vides (0 caractère) | **0 (0.0%)** |
| Textes < 100 caractères | **0 (0.0%)** |
| Textes < 500 caractères | **0 (0.0%)** |
| Textes ≥ 500 caractères | **329 / 329 (100.0%)** |
| Textes ≥ 1 000 caractères | **329 / 329 (100.0%)** |
| Longueur minimale | 1 286 caractères (`nid_231`) |
| Longueur médiane | 2 944 caractères |
| Longueur moyenne | 3 817 caractères |
| Longueur maximale | 186 526 caractères (`nid_28`, revue complète) |

### Analyse des cas particuliers :
- Le texte le plus court (1 286 caractères) correspond à une décision concise de recevabilité de pourvoi en cassation parfaitement lisible et complète avec dispositif.
- Aucun texte dégradé, corrompu ou illisible n'a été détecté.

---

## 3. Métadonnées

Taux de présence dans `databases/conseildetat.db` combinés aux métadonnées extraites de l'OCR :

| Champ | Présence brute DB | Présence enrichie Parser | Notes |
|---|---|---|---|
| `decision_number` | 324 / 329 (98.5%) | **329 / 329 (100.0%)** | Les 5 cas particuliers résolus via l'OCR |
| `date` | 327 / 329 (99.4%) | **329 / 329 (100.0%)** | Date ISO YYYY-MM-DD normalisée |
| `year` | 328 / 329 (99.7%) | **329 / 329 (100.0%)** | Année extraite avec exactitude |
| `chamber` | 324 / 329 (98.5%) | 324 / 329 (98.5%) | Renseigné pour toute la jurisprudence standard |
| `section` | 141 / 329 (42.9%) | 141 / 329 (42.9%) | Section de chambre (lorsqu'applicable) |
| `subject` | 324 / 329 (98.5%) | 324 / 329 (98.5%) | Objet / Thème du litige |
| `principle` | 324 / 329 (98.5%) | 324 / 329 (98.5%) | Principe juridique / Mabda |
| `keywords` | 324 / 329 (98.5%) | 324 / 329 (98.5%) | Formatés en JSON array structuré |
| `disposition` | 0 / 329 (0.0% en DB) | **327 / 329 (99.4%)** | Extrait avec succès depuis l'OCR (« لهذه الأسباب ») |
| `legal_references` | 0 / 329 (0.0% en DB) | **315 / 329 (95.7%)** | Extrait depuis visas (« بمقتضى ») et motifs de l'OCR |
| `parties` | 0 / 329 (0.0% en DB) | **316 / 329 (96.0%)** | Extrait depuis l'en-tête de l'instance OCR |

---

## 4. Parsing

- **Adaptateur implémenté** : [`corpus/conseildetat_adapter.py`](file:///c:/Users/Gaming/OneDrive/Bureau/Scraping/joradp-archive/corpus/conseildetat_adapter.py).
- **Documents parsés** : **329 / 329 (100 %)**.
- Modèles cibles générés : `CanonicalDocument` et `DocumentProvenance`.
- Nature et types :
  - 328 documents de type `DocumentType.DECISION` / `DocumentNature.JUDICIAL_DECISION`
  - 1 document de type `DocumentType.REVIEW_ARTICLE` / `DocumentNature.DOCTRINE_REVIEW` (`nid_28`)

---

## 5. Doublons et Collisions

1. **Doublon strict de décision (EXACT_DUPLICATE)** :
   - `decision_number=094209`, `date=2015-01-08` :
     - `nid=74` (`nid_74_arretn094209.pdf`)
     - `nid=76` (`nid_76_arretn094209_0.pdf`)
   - Analyse d'intégrité : Fichiers PDF et textes OCR strictement identiques à l'octet près (hash `ba0c95ca...`).
   - Résolution : Les deux enregistrements sont conservés en traçant l'origine source via suffixe `_nid{nid}` pour garantir une unicité absolue sans perte de données.
2. **Même numéro, décisions / versions distinctes (SAME_NUMBER_DIFFERENT_DECISION)** :
   - `decision_number=016886` :
     - `nid=272` : Fiche standard (`date=2005-06-07`), 4 131 caractères.
     - `nid=368` : Fiche arrêt sélectionné avec commentaire de doctrine, 3 833 caractères.
   - Résolution déterministe : Différenciation par le préfixe de hash du texte intégral (`_37c70b06` vs `_61e966f6`).

---

## 6. Canonical IDs

Structure canonique retenue :
```text
cde_decision_{decision_number}_{date}_ar
```
- **Total base_ids** : 329
- **Base_ids uniques** : 327 (2 collisions)
- **Résolution déterministe** :
  - Ajout du préfixe SHA-256 du texte (`_{hash[:8]}`) pour les collisions de contenu.
  - Ajout du préfixe `_nid{nid}` pour les doublons stricts de hash.
- **Unicité finale des `canonical_id`** : **329 / 329 (100.0 % uniques, 0 collision)**.

---

## 7. Provenance

Chaque `CanonicalDocument` conserve un objet `DocumentProvenance` complet :
- `source_db` : `"conseildetat.db"`
- `source_table` : `"decisions"`
- `source_id` : `id` SQLite de l'enregistrement original
- `source_url` : URL Drupal d'origine (`https://conseildetat.dz/node/{nid}`)
- `raw_path` : Chemin absolu vers le fichier `markdown.md` OCR correspondant
- `content_hash` : SHA-256 du texte intégral nettoyé
- `ingested_at` : Horodatage ISO UTC

---

## 8. Gold Set

Un ensemble représentatif de 30 décisions a été évalué de manière exhaustive ([`scratch/eval_gold_set.py`](file:///c:/Users/Gaming/OneDrive/Bureau/Scraping/joradp-archive/scratch/eval_gold_set.py)) :
- Couverture : Décisions courtes (<1.5k chars), décisions longues (>12k chars), arrêts de 2002 à 2021, chambres 1 à 5, cas spéciaux (arrêts commentés, revue), et cas de collisions.
- **Score : 30 / 30 PASS (100 %)**.

---

## 9. Tests

La suite de tests unitaire et d'intégration ([`tests/test_conseildetat_adapter.py`](file:///c:/Users/Gaming/OneDrive/Bureau/Scraping/joradp-archive/tests/test_conseildetat_adapter.py)) vérifie :
- Parsing des 329 décisions.
- Unicité stricte des 329 `canonical_id`.
- Idempotence complète (runs successifs produisant des identifiants et hashes identiques).
- Extraction du dispositif et des attributs juridiques.
- Intégrité absolue de `corpus.db`.
- **Résultat : 6/6 tests du projet PASS (0 régression, 0 échec)**.

---

## 10. Idempotence

Exécution répétée du pipeline :
- 329 / 329 identifiants canoniques strictement identiques.
- 329 / 329 hashes de contenu textuel strictement identiques.
- 0 doublon supplémentaire, 0 dérive.

---

## 11. CorpusDB

Vérification d'intégrité de `databases/corpus.db` avant et après exécution :

| Table | Attendu | Actuel | Statut |
|---|---|---|---|
| `documents` | 232 487 | 232 487 | **NON MODIFIÉ ✅** |
| `articles` | 853 500 | 853 500 | **NON MODIFIÉ ✅** |
| `provenance` | 232 487 | 232 487 | **NON MODIFIÉ ✅** |

---

## 12. Fichiers créés / modifiés

### Créés :
1. [`corpus/conseildetat_adapter.py`](file:///c:/Users/Gaming/OneDrive/Bureau/Scraping/joradp-archive/corpus/conseildetat_adapter.py) : Adaptateur canonique et extracteur d'entités juridiques depuis l'OCR.
2. [`tests/test_conseildetat_adapter.py`](file:///c:/Users/Gaming/OneDrive/Bureau/Scraping/joradp-archive/tests/test_conseildetat_adapter.py) : Tests unitaires et d'intégration du Conseil d'État.
3. [`reports/conseildetat_audit_report.md`](file:///c:/Users/Gaming/OneDrive/Bureau/Scraping/joradp-archive/reports/conseildetat_audit_report.md) : Le présent rapport complet.

### Modifiés :
- Aucun fichier de parsing existant (JORADP, Cour suprême HTML, Cour suprême Revue) n'a été altéré.

---

## 13. VERDICT

> ### ✅ VERDICT : **`READY_FOR_INTEGRATION`**
> 
> Le corpus Conseil d'État (329 décisions, 329 OCR) est parfaitement structuré, normalisé, dédoublonné et prêt pour l'ingestion dans `databases/corpus.db`.
