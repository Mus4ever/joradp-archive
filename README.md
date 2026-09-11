# Archive et Corpus Juridique Algérien (Lois & Jurisprudence)

Ce repository héberge l'infrastructure complète d'archivage, d'extraction OCR, de structuration et d'unification du corpus juridique algérien (législation et jurisprudence).

Il constitue le socle documentaire canonique préparatoire à la création d'un futur **Small Language Model (SLM)** spécialisé en droit algérien.

---

## 1. État Actuel du Corpus (`databases/corpus.db`)

À l'issue de l'intégration et de la validation de septembre 2026, la base de données unifiée rassemble **236 090 documents** et **853 500 articles** :

| Source Documentaire | Nature Juridique | Documents | Complétude & Particularités | Base Staging |
|---|---|---:|---|---|
| **JORADP (Journal Officiel)** | Législation (`LEGISLATIVE_NORM`) | **231 234** | Lois, ordonnances, décrets, arrêtés (1962–2026). Découpés en **853 500 articles**. | `joradp.db` |
| **Cour Suprême (HTML)** | Jurisprudence (`JUDICIAL_DECISION`) | **1 253** | Arrêts récents (1979–2023, pic 2016-18) avec texte intégral et métadonnées riches. | `databases/coursupreme.db` |
| **Cour Suprême (Revue)** | Jurisprudence (`JUDICIAL_DECISION`) | **3 274** | Décisions de 1989 à 2023 (1 955 modernes + 1 319 legacy associées à l'OCR). | `databases/coursupreme_revue.db` |
| **Conseil d'État** | Jurisprudence administrative | **328** | Arrêts du contentieux administratif (1998–2022) issus des fiches et PDF. | `databases/conseildetat.db` |
| **Conseil d'État (Revue)** | Doctrine (`DOCTRINE_REVIEW`) | **1** | Publication doctrinale de la revue du Conseil d'État (2015). | `databases/conseildetat.db` |
| **TOTAL** | — | **236 090** | **853 500 articles** & **146 relations inter-sources** vérifiées | `databases/corpus.db` |

---

## 2. Architecture et Organisation du Dépôt

```
joradp-archive/
├── README.md                           ← Synthèse et vue d'ensemble du projet
├── Project_Plan.md                     ← Cahier des charges et historique initial
├── CHANGELOG.md                        ← Journal des évolutions techniques
├── requirements.txt                    ← Dépendances Python versionnées
│
├── corpus/                             ← Couche canonique et adaptateurs unifiés
│   ├── models.py                       ← Classes CanonicalDocument, DocumentProvenance, Article
│   ├── schema.py                       ← Schéma relationnel CorpusDB (SQLite WAL)
│   ├── joradp_parser.py                ← Découpage des JO en actes et articles
│   ├── coursupreme_adapter.py          ← Adaptateur Cour suprême HTML
│   ├── coursupreme_revue_adapter.py    ← Adaptateur Cour suprême Revue
│   └── conseildetat_adapter.py         ← Adaptateur Conseil d'État
│
├── sources/                            ← Outils de scraping et staging par institution
│   ├── coursupreme/                    ← Collecte et parsing des fiches HTML
│   │   └── revue/                      ← Gestion des PDF, OCR, Guide v4 et offsets de la Revue
│   └── conseildetat/                   ← Collecte et parsing Drupal / PDF du Conseil d'État
│
├── databases/                          ← Bases SQLite (fichiers volumineux ignorés par Git)
│   ├── corpus.db                       ← Base de données unifiée cible (2,04 Go)
│   ├── coursupreme.db                  ← Staging Cour suprême HTML (11,38 Mo)
│   ├── coursupreme_revue.db            ← Staging Revue Cour suprême (37,46 Mo)
│   └── conseildetat.db                 ← Staging Conseil d'État (1,08 Mo)
│
├── docs/                               ← Documentation technique de référence
│   ├── architecture/                   ← Architecture actuelle et diagrammes de flux
│   ├── data/                           ← Dictionnaire de données des tables et champs
│   ├── methodology/                    ← Guide de reproductibilité pas à pas
│   └── jurisprudence/                  ← Rapports de reconnaissance des juridictions
│
├── tests/                              ← Suite de 96 tests unitaires et d'intégration
├── tools/                              ← Outils d'infrastructure (rate limiter, explorer web)
└── reports/                            ← Rapports d'audits et historiques de projet
```

---

## 3. Prise en Main et Exécution

### Installation
```bash
pip install -r requirements.txt
```

### Lancer la Suite de Tests (96 tests)
```bash
python -m pytest tests/
```

### Explorer le Corpus Localement
Un dashboard web interactif permet de naviguer dans l'ensemble des 236 090 textes juridiques :
```bash
python tools/explorer_server.py
```
Puis accédez à [http://localhost:8501](http://localhost:8501).

---

## 4. Ce qui est Fait vs Ce qui Reste à Faire

### Réalisé et Validé :
- Collecte et extraction des 10 432 numéros du Journal officiel (1962–2026).
- Scraping et structuration des 1 253 décisions HTML de la Cour suprême.
- Traitement de la Revue de la Cour suprême (80 numéros, 32 065 pages OCR, correction bidi du Guide, résolution des offsets).
- Scraping et structuration des 329 documents du Conseil d'État.
- Conception du modèle canonique unifié avec traçabilité intégrale (`DocumentProvenance`).
- Ingestion sans perte ni doublon dans `databases/corpus.db` avec intégrité SQLite vérifiée.

### Travaux Futurs (Hors Scope Actuel) :
- **Génération du dataset de fine-tuning** (paires d'instructions, questions-réponses juridiques, raisonnement).
- **Anonymisation ciblée** des mentions de personnes physiques identifiables dans les revues anciennes.
- **Entraînement du modèle (SLM)** (SFT, LoRA/QLoRA).
- **Architecture d'inférence** (validation des citations, discussion sur l'architecture multi-agent / RAG avec le professeur).
