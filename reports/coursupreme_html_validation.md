# Rapport d'Intégration & de Validation — Cour suprême HTML → CorpusDB

**Date** : 10 septembre 2026  
**Pipeline exécuté** : `Cour suprême HTML → parser existant → coursupreme_adapter.py → CanonicalDocument → validation exhaustive → Gold Set → CorpusDB`  
**Verdict global** : **GO VALIDÉ** 🚀 (100 % conforme, intégrité vérifiée, non-régression validée)

---

## 1. Synthèse Volumétrique et Chaîne de Traitement

| Étape | Entité / Table | Compteur Réel | Compteur Attendu | Statut |
| :--- | :--- | :---: | :---: | :---: |
| **SOURCE (HTML brut)** | Fichiers HTML archivés (`raw/coursupreme/*.html`) | **1 253** | 1 253 | ✅ CONFORME (100 %) |
| **SOURCE (Staging)** | Table `decisions` (`databases/coursupreme.db`) | **1 253** | 1 253 | ✅ CONFORME (100 %) |
| **ADAPTER** | Objets `CanonicalDocument` générés | **1 253** | 1 253 | ✅ CONFORME (100 %) |
| **CANONICAL ID** | Identifiants uniques déterministes | **1 253** | 1 253 | ✅ CONFORME (0 collision résiduelle) |
| **DATABASE (Jurisprudence)** | Table `documents` (`SUPREME_COURT`) | **1 253** | 1 253 | ✅ CONFORME (100 %) |
| **DATABASE (Provenance)** | Table `provenance` (`SUPREME_COURT`) | **1 253** | 1 253 | ✅ CONFORME (100 %) |
| **DATABASE (JORADP inchangé)** | Table `documents` (`REPUBLIC`) | **231 234** | 231 234 | ✅ INTACT (0 modification) |
| **DATABASE (Articles inchangés)**| Table `articles` (JORADP) | **853 500** | 853 500 | ✅ INTACT (0 modification) |
| **DATABASE (Total documents)** | Table `documents` (Global) | **232 487** | 232 487 | ✅ CONFORME (231 234 + 1 253) |

---

## 2. Déterminisme et Résolution des Collisions de `canonical_id`

Le format de base imposé est :
$$\text{canonical\_id} = \texttt{cs\_decision\_\{decision\_number\}\_\{date\}\_ar}$$

### Traitement des collisions réelles
Exactement deux paires (soit 4 décisions) partagent à la fois le même numéro et la même date dans la source officielle de la Cour suprême. L'audit a prouvé qu'il s'agit de **décisions juridiquement et textuellement distinctes** (pourvois différents, objets différents, textes distincts).

Conformément à la contrainte, un désambiguïsateur SHA-256 tronqué aux 8 premiers caractères du texte intégral normalisé a été appliqué **uniquement** sur ces collisions avérées :

1. **Paire 1 — 29 juillet 1980 (Dossier n° 20906)** :
   - `cs_decision_20906_1980-07-29_ar_17530de8` (Objet : *معارضة* — Opposition)
   - `cs_decision_20906_1980-07-29_ar_79879c49` (Objet : *استئناف* — Appel)
2. **Paire 2 — 21 février 2018 (Dossier n° 994311)** :
   - `cs_decision_994311_2018-02-21_ar_7806f490` (Objet : *محضر المرافعات* — Procès-verbal des débats)
   - `cs_decision_994311_2018-02-21_ar_2bd62980` (Objet : *اسئلة* — Questions posées)

- **Total décisions désambiguïsées** : **4**
- **Collisions résiduelles** : **0**
- **Taux d'unicité globale des `canonical_id`** : **100,0 %**

---

## 3. Taux de Présence et Qualité des Champs Juridiques

Chaque champ a été vérifié sur les 1 253 décisions au niveau de la source brute, du parseur et de la base de données finale `CorpusDB`. **Aucun champ manquant n'a été inventé** (les champs absents restent strictement `NULL`/`None`).

| Champ Canonique | Champ Staging | Présent en DB | Taux Réel | Taux Audit Source | Statut |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `document_number` | `decision_number` | **1 253** | **100.0%** | 100.0% | ✅ Identique |
| `date` | `date` | **1 253** | **100.0%** | 100.0% | ✅ Identique |
| `year` | `date` (déduit) | **1 253** | **100.0%** | 100.0% | ✅ Identique |
| `chamber` | `chamber` | **1 252** | **99.9%** | 99.9% | ✅ Identique (1 cas sans chambre dans HTML source) |
| `subject` | `subject` | **1 253** | **100.0%** | 100.0% | ✅ Identique |
| `full_text` | `text` | **1 253** | **100.0%** | 100.0% | ✅ Identique |
| `disposition` | `disposition` | **1 247** | **99.5%** | 99.5% | ✅ Identique (6 cas sans dispositif dans HTML source) |
| `principle` | `principle` | **1 241** | **99.0%** | 99.0% | ✅ Identique (12 cas sans principe explicite) |
| `court_response` | `court_response` | **1 239** | **98.9%** | 98.9% | ✅ Identique |
| `keywords` | `keywords` | **1 234** | **98.5%** | 98.5% | ✅ Identique |
| `legal_references`| `legal_references`| **1 213** | **96.8%** | 96.8% | ✅ Identique |
| `provenance.raw_path` | `raw_path` | **1 253** | **100.0%** | 100.0% | ✅ Identique |
| `provenance.source_url` | `source_url` | **1 253** | **100.0%** | 100.0% | ✅ Identique |
| `canonical_hash` | SHA-256 | **1 253** | **100.0%** | 100.0% | ✅ Identique |

### Distribution par Chambre
- **Chambres civiles (*الغرف المدنية*)** : 805 décisions (64,2 %)
- **Chambres pénales (*الغرف الجزائية*)** : 389 décisions (31,0 %)
- **Commission d'indemnisation (*لجنة التعويض*)** : 34 décisions (2,7 %)
- **Décisions importantes (*قرارات مهمة*)** : 24 décisions (1,9 %)
- **Sans chambre explicite dans la taxonomie** : 1 décision (`cs_decision_201823_2001-03-27_ar`)

---

## 4. Évaluation du Gold Set Représentatif

Un Gold Set représentatif de **15 décisions** a été constitué pour valider l'intégrité de bout en bout contre les fichiers HTML natifs réels :
1. **Les 4 décisions des 2 paires de collisions réelles** (1980 et 2018).
2. **La décision atypique sans chambre** (n° 201823 du 27/03/2001).
3. **Cas complets de chaque juridiction/formation** (Chambres civiles, pénales, indemnisation, décisions importantes).
4. **Cas structurellement incomplets dans la source HTML** (sans principe, sans dispositif, sans visa légal, sans mots-clés).
5. **Couverture temporelle multi-décennies** (1979 à 2023).

### Métriques d'Évaluation (120 vérifications directes)
- **Vrais Positifs (TP)** : **120**
- **Faux Positifs (FP)** : **0**
- **Faux Négatifs (FN)** : **0**
- **Précision** : **100,00 %**
- **Rappel** : **100,00 %**
- **F1-Score** : **100,00 %**

---

## 5. Classification des Décisions (Classes A, B, C, D)

- **Classe A (Complètes & exploitables immédiatement)** : **1 232** (98,3 %)
  - Texte intégral, chambre, numéro, date, sujet, principe, réponse de la Cour, dispositif.
- **Classe B (Exploitables avec omission mineure d'origine HTML)** : **21** (1,7 %)
  - Texte intégral intact et métadonnées essentielles présentes, mais section secondaire absente sur le portail de la Cour suprême (ex. décisions constitutionnelles avec mention spéciale, ou arrêt sans mention de dispositif HTML séparé).
- **Classe C (Texte tronqué ou altéré)** : **0** (0,0 %)
- **Classe D (Incohérences ou collisions non résolues)** : **0** (0,0 %)

---

## 6. Audit Post-Ingestion et Intégrité SQLite

Exécuté sur `databases/corpus.db` (taille : 1,97 Go) :
- `PRAGMA integrity_check` : **`ok`**
- `PRAGMA foreign_key_check` : **`ok` (0 violation)**
- **Décisions sans provenance** : **0**
- **Provenances orphelines** : **0**
- **Doublons de canonical_id** : **0**
- **Décisions sans texte intégral** : **0**
- **Test d'idempotence** : **Validé** (la ré-exécution de l'ingestion n'insère aucun doublon et conserve les compteurs à 232 487 documents).

---

## 7. Tests Automatisés

- Suite de tests `pytest tests/` : **85 tests passés / 85 tests (100 % de succès)**.
  - `tests/test_corpus.py` : 27 passed
  - `tests/test_coursupreme.py` : 19 passed
  - `tests/test_coursupreme_adapter.py` : 4 passed
  - `tests/test_joradp_parser.py` : 15 passed
  - `tests/test_rate_limiter.py` : 4 passed
  - `tests/test_revue.py` : 16 passed

---

## 8. Verdict Final

> ### 🏁 VERDICT : **GO VALIDÉ**
> 
> L'ensemble du corpus **Cour suprême HTML (1 253 décisions)** est désormais rigoureusement validé, modélisé selon le schéma canonique sans aucune hallucination de champ, et stocké de manière idempotente dans `databases/corpus.db`.
> 
> Le corpus global unifié compte à présent :
> - **232 487 documents canoniques** (231 234 JORADP + 1 253 Cour suprême)
> - **853 500 articles individuels**
> - **232 487 provenances complètes**
> - **0 collision, 0 orphelin, 100 % d'intégrité SQLite**.
