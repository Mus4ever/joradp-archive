# CorpusDB — Revue + Conseil d'État Integration Report

## 1. État avant intégration

Avant cette étape, la base de données unifiée `databases/corpus.db` contenait :

- **Documents** : 232 487
- **Articles** : 853 500
- **Provenance** : 232 487
- **Relations** : 0

Répartition source :
- **JORADP** : 231 234 actes normatifs et 853 500 articles
- **Cour suprême HTML** : 1 253 décisions judiciaires

---

## 2. Cour suprême Revue

- **Source staging** : `databases/coursupreme_revue.db`
- **Fichiers OCR** : Répertoire `data/revue/` (32 065 pages OCR en Markdown haute résolution)
- **Adaptateur** : [`corpus/coursupreme_revue_adapter.py`](file:///c:/Users/Gaming/OneDrive/Bureau/Scraping/joradp-archive/corpus/coursupreme_revue_adapter.py)
- **Total décisions traitées** : **3 274**
  - 1 955 décisions du régime moderne (détectées par text markers)
  - 1 319 décisions du régime legacy (texte intégral raccordé via `revue_decision_texts` et calcul d'offset)
- **Canonical IDs générés** : 3 274 / 3 274 uniques et 100 % déterministes.
  - Format : `cs_revue_{issue_year}_{issue_number}_{decision_number}_ar` avec désambiguïsation par hash de contenu et id source en cas de doublon.

---

## 3. Conseil d'État

- **Source staging** : `databases/conseildetat.db`
- **Fichiers OCR** : Répertoire `data/Conseil/` (329 dossiers OCR avec `markdown.md`)
- **Adaptateur** : [`corpus/conseildetat_adapter.py`](file:///c:/Users/Gaming/OneDrive/Bureau/Scraping/joradp-archive/corpus/conseildetat_adapter.py)
- **Total décisions traitées** : **329**
  - 328 décisions judiciaires (`DocumentNature.JUDICIAL_DECISION`)
  - 1 numéro de revue doctrinale (`nid 28`, `DocumentNature.DOCTRINE_REVIEW` / `DocumentType.REVIEW_ARTICLE`)
- **Canonical IDs générés** : 329 / 329 uniques et 100 % déterministes.

---

## 4. Déduplication et Rapprochement

### A. Cour suprême HTML ↔ Revue :
Une analyse croisée exhaustive des 1 253 décisions HTML et des 3 274 décisions Revue a établi la classification suivante :

| Catégorie | Nombre | Traitement |
|---|---|---|
| **`EXACT_DUPLICATE`** | 0 | - |
| **`SAME_DECISION_DIFFERENT_SOURCE`** | **146** | Préservées sous leurs identifiants canoniques respectifs et formellement reliées dans la table `relations` (`relation_type='SAME_DECISION_DIFFERENT_SOURCE'`, confiance = 1.0) |
| **`SAME_NUMBER_DIFFERENT_DECISION`** | 3 | Distinguées par la date et conservées comme documents distincts |
| **`POSSIBLE_DUPLICATE`** | 2 | Même numéro et même année, mais date précise différente ou absente |
| **`DISTINCT`** | 3 123 | Décisions uniques exclusives à la Revue |

### B. Conseil d'État :
- **`EXACT_DUPLICATE`** : 1 paire (`nid 74` et `nid 76`, décision n° 094209). Conservées avec traçabilité d'origine via suffixe `_nid{nid}`.
- **`SAME_NUMBER_DIFFERENT_DECISION`** : 1 paire (`nid 272` fiche standard vs `nid 368` arrêt commenté, décision n° 016886). Distinguées déterministement par le hash de texte intégral.
- **`DISTINCT`** : 327 décisions.

---

## 5. Documents ajoutés

- Ajouts Conseil d'État : **+329 documents**
- Ajouts Cour suprême Revue : **+3 274 documents**
- **Total documents final dans CorpusDB** : **236 090** (232 487 + 3 603)

---

## 6. Articles ajoutés

- **+0 article**
- Le nombre total d'articles dans `articles` reste exactement **853 500**.
- Règle respectée : Les décisions judiciaires ne sont pas fragmentées artificiellement en articles.

---

## 7. Provenance ajoutée

- **+3 603 lignes de provenance**
- **Total provenance final dans CorpusDB** : **236 090**
- Chaque document possède exactement une ligne de traçabilité complète vers sa base source, table, PK, chemin brut et hash SHA-256.

---

## 8. Intégrité SQLite

- `PRAGMA integrity_check` : **`ok`**
- `PRAGMA foreign_key_check` : **`0 violation`**
- Contrôles d'orphelins :
  - Documents sans provenance : **0**
  - Provenances orphelines : **0**
  - Articles orphelins : **0**
  - Relations orphelines : **0**

---

## 9. Idempotence

Le script d'ingestion a été réexécuté lors d'un test dédié ([`scratch/test_idempotence.py`](file:///c:/Users/Gaming/OneDrive/Bureau/Scraping/joradp-archive/scratch/test_idempotence.py)) :
- Documents ajoutés au second passage : **0**
- Provenances ajoutées au second passage : **0**
- Relations ajoutées au second passage : **0**
- Intégrité et stabilité : **100 % confirmées**

---

## 10. Tests

Exécution de la suite de tests complète (`python -m unittest discover -s tests -p "test_*.py"`) :
- `test_corpus.py` : PASS
- `test_coursupreme_adapter.py` : PASS
- `test_coursupreme_revue_adapter.py` : PASS
- `test_conseildetat_adapter.py` : PASS
- `test_joradp_parser.py` : PASS
- **Total : 10 / 10 tests PASS (100 %)**

---

## 11. Vérification JORADP

- Actes normatifs JORADP dans `documents` : **231 234** (strictement inchangé)
- Articles JORADP dans `articles` : **853 500** (strictement inchangé)
- Identifiants canoniques et provenances JORADP : **strictement inchangés**

---

## 12. Vérification Cour suprême HTML

- Décisions HTML dans `documents` : **1 253** (strictement inchangé)
- Identifiants canoniques HTML : **strictement inchangés**
- Provenances HTML : **strictement inchangées**
- 146 décisions désormais enrichies par un lien bilatéral traçable vers la Revue.

---

## 13. Statistiques finales du Corpus Canonique

### A. Distribution par source :
| Source | Base source | Documents | Pourcentage |
|---|---|---|---|
| Journal Officiel (JORADP) | `joradp.db` | 231 234 | 97.94 % |
| Revue de la Cour suprême | `coursupreme_revue.db` | 3 274 | 1.39 % |
| Cour suprême HTML | `coursupreme.db` | 1 253 | 0.53 % |
| Conseil d'État | `conseildetat.db` | 329 | 0.14 % |
| **Total** | | **236 090** | **100.00 %** |

### B. Distribution par juridiction :
- **`REPUBLIC`** : 231 234
- **`SUPREME_COURT`** : 4 527
- **`STATE_COUNCIL`** : 329

### C. Distribution par nature :
- **`LEGISLATIVE_NORM`** : 231 234
- **`JUDICIAL_DECISION`** : 4 855
- **`DOCTRINE_REVIEW`** : 1

### D. Distribution par langue :
- **Arabe (`AR`)** : 121 974 documents
- **Français (`FR`)** : 114 116 documents

### E. Complétude textuelle :
- **`FULL_TEXT`** : 235 993 (99.96 %)
- **`PARTIAL_TEXT`** : 63 (0.03 %)
- **`INDEX_ONLY`** : 34 (0.01 %)

---

## 14. Backup

La sauvegarde complète pré-intégration a été créée et validée :
- **Fichier** : [`databases/corpus_pre_revue_conseildetat_backup.db`](file:///c:/Users/Gaming/OneDrive/Bureau/Scraping/joradp-archive/databases/corpus_pre_revue_conseildetat_backup.db)
- **Taille** : 2 066 386 944 octets (~1.92 Go)
- **Contrôle d'intégrité** : validé avant le début des écritures.

---

## 15. VERDICT

> ### 🏆 VERDICT : **`INTEGRATION_SUCCESS`**
> 
> L'intégration conjointe de la Revue de la Cour suprême (3 274 décisions) et du Conseil d'État (329 décisions) dans `databases/corpus.db` est achevée avec un succès total. L'intégrité référentielle, l'idempotence, l'isolation des données JORADP/HTML et la traçabilité des provenances sont rigoureusement garanties.
