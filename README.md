# JORADP Archive & Corpus — Scraping et Extraction de Texte (1962-2026)

## 📌 Présentation du Projet
Ce projet constitue l'archive intégrale et le pipeline de traitement textuel du **Journal Officiel de la République Algérienne Démocratique et Populaire (JORADP)** de **1962 à 2026**, en éditions bilingues (**Arabe** et **Français**).

---

## 🚀 Périmètre du Corpus
- **Couverture temporelle** : 1962 à 2026 (64 années de législation).
- **Langues supportées** : Arabe (`AR`) et Français (`FR`).
- **Périodes documentaires** :
  - **Ère Legacy (1962 - 1993)** : Documents scannés historiques, papier journal d'époque.
  - **Ère Transition (1994 - 2009)** : Documents scannés moyenne résolution et début des PDF bureautiques.
  - **Ère Moderne (2010 - 2026)** : Documents PDF natifs haute résolution et PDF numériques vectoriels.

---

## ⚙️ Méthodologie d'Extraction de Texte

Le pipeline applique deux voies de traitement complémentaires selon la nature des documents :

1. **Extraction Vectorielle Native avec Réordonnancement RTL (Phase 4)** :
   - Utilisée pour les PDF numériques récents (notamment arabes natifs).
   - Corrige automatiquement les inversions de glyphes visuels bidirectionnels (`bidi`) et restaure l'ordre logique naturel des mots et des nombres.
   - **Taux de fidélité : 100% exact**.

2. **Pipeline OCR Adaptatif Multi-Étapes (Phase 5)** :
   - Appliqué sur les documents scannés ou rasterisés.
   - Combine : Redressement géométrique (*Deskew*) + Binarisation locale adaptative (*Sauvola*) + Découpage dynamique des colonnes de lecture + Reconnaissance OCR Tesseract (`tessdata_best` pour le français, `--psm 6`).

---

## 🎯 Niveau de Confiance et Métriques Officielles (Benchmark `jiwer`)

Le texte extrait est indexé avec un indicateur de confiance explicite dans la base de données et les exports :

| Catégorie de Document | Méthode d'Extraction | Niveau de Confiance | Précision Lexicale Moyenne | Règle d'Utilisation |
|---|---|---|---|---|
| **PDF Numériques Natifs** | Extraction native RTL | `confidence: high` | **100%** | Texte directement exploitable pour la recherche et l'analyse juridique. |
| **Français Moderne (Scans récents 2010-2026)** | OCR Tesseract Best + Sauvola | `confidence: high` | **88% à 94%** (Nombres: 98%) | Texte de très haute fiabilité. |
| **Scans Historiques (Legacy 1962-1993, Transition, Arabe scanné)** | OCR Tesseract Fast + Sauvola | `confidence: low` | **35% à 50%** | Texte inclus pour recherche plein texte indicative ; **vérification visuelle recommandée sur le scan original**. |

> 💡 **En résumé** : Le texte est fiable à plus de 88-100% pour l'ensemble des PDF numériques et les scans français récents, et doit faire l'objet d'une vérification sur le document PDF original pour les archives scannées anciennes.

---

## ⚠️ Limites Connues et Assumées

1. **Documents Scannés Historiques (1962-1985)** : Présence de bruit typographique lié au vieillissement du papier (encres estompées, papier jauni), réduisant la précision des OCR génériques sur l'arabe ancien.
2. **Tableaux et Sommaires Pointillés** : Les lignes de points serrées reliant les titres aux numéros de page peuvent générer des découpages de mots parasites lors du passage OCR.
3. **Ordre de Lecture Bicolonne Complexe** : Sur certains numéros anciens avec encarts transversaux, l'ordre des colonnes peut varier par rapport au flux de lecture humain standard.

---

## 📂 Structure du Répertoire
- `tools/` : Scripts de scraping, normalisation, prétraitement d'image (`image_preprocessing.py`) et benchmark (`phase5_ocr_benchmark.py`).
- `benchmark/` : Manifeste des 30 pages de test, images PNG d'évaluation et ground truth authentique vérifié.
- `reports/` : Rapports d'audit, benchmarks multi-moteurs et journaux de validation.
- `data/` : Base SQLite locale et métadonnées du corpus.
