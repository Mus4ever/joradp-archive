# Rapport d'Audit Post-Ingestion — CorpusDB (databases/corpus.db)

> **Date** : 10 septembre 2026  
> **Source** : 10 432 fichiers JORADP (Éditions FR & AR, 1962–2026)  
> **Base de données** : `databases/corpus.db` (SQLite en mode WAL)  
> **Verdict Final** : ✅ **GO — BASE CANONIQUE VALIDÉE À 100 %**

---

## 1. Confrontation Exacte : Parser vs Database

| Entité | Attendu (Parser) | Inséré en Base (`corpus.db`) | Différence | Statut |
|---|---|---|---|---|
| **Actes Juridiques (Documents)** | **231 234** | **231 234** | **0** | ✅ PARFAIT |
| **Articles Juridiques** | **853 500** | **853 500** | **0** | ✅ PARFAIT |
| **Fiches de Provenance (Traçabilité)** | **231 234** | **231 234** | **0** | ✅ PARFAIT |
| **Numéros JO Source Traités** | **10 432** | **10 432** | **0** | ✅ PARFAIT |

---

## 2. Contrôles d'Intégrité et Contraintes Relationnelles

| Contrôle Exécuté | Commande / Vérification | Résultat Constaté | Statut |
|---|---|---|---|
| **Intégrité physique SQLite** | `PRAGMA integrity_check` | `ok` | ✅ CONFORME |
| **Clés Étrangères (Foreign Keys)** | `PRAGMA foreign_key_check` | `0 violation` | ✅ CONFORME |
| **Unicité des Clés Primaires** | `canonical_id UNIQUE` | `231 234 / 231 234 distincts (0 collision)` | ✅ CONFORME |
| **Actes sans Traçabilité** | Documents sans ligne `provenance` | **0** | ✅ CONFORME |
| **Orphelins Provenance** | Provenance sans `documents` parent | **0** | ✅ CONFORME |
| **Articles sans Document Parent** | Articles dont `parent_document_id` n'existe pas | **0** | ✅ CONFORME |
| **Doublons d'Articles** | Unicité sur `(parent_document_id, ordinal)` | **0 doublon** | ✅ CONFORME |
| **FTS5 Full-Text Search** | Tables virtuelles plein texte | *Non configuré dans le schéma standard (prévu pour phase RAG/SLM)* | ℹ️ NORMAL |

---

## 3. Répartitions Juridiques et Linguistiques

### 3.1. Répartition par Langue
* **Documents (Actes)** :
  - **Arabe (`AR`)** : **117 118** actes (50,65 %)
  - **Français (`FR`)** : **114 116** actes (49,35 %)
* **Articles** :
  - **Arabe (`AR`)** : **425 448** articles (49,85 %)
  - **Français (`FR`)** : **428 052** articles (50,15 %)
* *Équilibre quasi parfait entre les deux versions linguistiques.*

### 3.2. Répartition par Type d'Acte
- **`DECREE`** (Décrets présidentiels, exécutifs, législatifs) : **140 483** (60,75 %)
- **`ORDER`** (Arrêtés ministériels, règlements, résolutions) : **84 109** (36,37 %)
- **`DECISION`** (Décisions réglementaires et administratives) : **4 258** (1,84 %)
- **`LAW`** (Lois et lois organiques) : **1 813** (0,78 %)
- **`NOTICE`** (Avis et proclamations officielles) : **396** (0,17 %)
- **`OTHER`** (Accords internationaux, lettres) : **130** (0,06 %)
- **`CIRCULAR`** (Circulaires administratives) : **45** (0,02 %)

### 3.3. Couverture Temporelle
- **Période couverte** : **1962 à 2026** (65 années pleines consécutives).

---

## 4. Test d'Idempotence et Robustesse

* **Méthode** : Ré-exécution du script d'ingestion sur un lot témoin de 500 numéros déjà insérés.
* **Résultats** :
  - Nouveaux actes insérés : **0**
  - Nouveaux articles insérés : **0**
  - Compteurs après ré-ingestion : **strictement identiques** (231 234 actes et 853 500 articles).
* **Conclusion** : L'ingestion est **100 % idempotente**.

---

## 5. Performances et Volumétrie Finale

| Métrique | Valeur |
|---|---|
| **Temps d'Ingestion Total** | **32,05 secondes** (325,4 numéros/s) |
| **Taille finale de `corpus.db`** | **1 960,33 Mo** (1,96 Go) |
| **Suite de Tests de Non-Régression** | **81 / 81 réussis** (100 %) |
| **Mode SQLite** | `WAL` (Write-Ahead Logging) |

---

## 6. Verdict Final

### ✅ **GO SANS RÉSERVE**
La base de données canonique `databases/corpus.db` est intégralement constituée, exempte de toute collision ou orphelin, et certifiée conforme pour servir de socle à la **construction du dataset juridique d'entraînement et de fine-tuning**.
