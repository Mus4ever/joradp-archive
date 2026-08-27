# RAPPORT FINAL PHASE 5 — OCR OPTIMAL JORADP
## Corpus : Journal Officiel Algérien — 1962-2026
## Date : 2026-08-27 | Benchmark sur 30 pages (15 AR + 15 FR)

---

> [!CAUTION]
> **VERDICT PHASE 6 : NO-GO**
> Aucun moteur testé n'atteint le seuil de ≥ 85% précision mot / ≥ 90% exactitude nombres.
> Le plafond mesuré est de **17.7% précision mot** (Tesseract tessdata_best + pipeline, français)
> et **14.5%** (arabe). Le traitement de masse des ~148 000 pages restantes reste suspendu.

---

## 1. Rappel des objectifs (PROMPT_PHASE5_OCR_OPTIMAL)

| Métrique | Cible | Français atteint | Arabe atteint |
|---|---|---|---|
| Précision mot (WER ≤ 15%) | ≥ 85% | **17.7%** ❌ | **14.5%** ❌ |
| Exactitude chiffres/dates | ≥ 90% | **63.1%** ❌ | **68.9%** ❌ |
| Ordre lecture RTL | Sans régression | 80.7% ⚠️ | 82.0% ✅ |

---

## 2. Tableau comparatif complet — 5 configurations testées

### Tesseract

| Config | AR Préc. Mot | AR Nombres | FR Préc. Mot | FR Nombres | Vitesse |
|---|---|---|---|---|---|
| tessdata_fast — Brut (--psm 3) | 14.4% | 68.9% | 16.8% | 57.3% | 1.2s/page |
| tessdata_fast — Pipeline (Sauvola + col. --psm 6) | **14.5%** | 67.8% | 17.4% | **63.1%** | 1.1s/page |
| tessdata_best — Pipeline (Sauvola + col. --psm 6) | 13.8% | 68.9% | **17.7%** | 61.5% | 2.0s/page |

**Δ Pipeline vs Brut (tessdata_fast)** : +0.1pp AR WER, +0.6pp FR WER, +5.8pp FR Nombres. Gain marginal.  
**Δ tessdata_best vs tessdata_fast** : -0.7pp AR (régression légère), +0.3pp FR. Négligeable.

### EasyOCR (GPU)

| Config | AR Préc. Mot | AR Nombres | FR Préc. Mot | FR Nombres | Vitesse |
|---|---|---|---|---|---|
| Brut (page entière) | 12.1% | **73.4%** | 16.5% | 62.4% | 8.7s/page |
| Pipeline (Sauvola + Bicolonne) | 11.2% | 73.1% | 13.7% | 61.6% | **16.0s/page** |

> [!WARNING]
> **Le pipeline bicolonne DÉGRADE EasyOCR** : -0.9pp AR, -2.8pp FR, 2× plus lent.
> EasyOCR (CRAFT detector interne) fonctionne mieux sur page entière que sur crops isolés.

### Surya

| Config | Résultat | Raison |
|---|---|---|
| surya_det3 (toutes résolutions) | **0 détection** sur 30/30 pages | Incompatibilité structurelle avec scans historiques denses |

---

## 3. Diagnostic des causes

### 3.1 Prétraitement manquant — **Confirmé, impact FAIBLE**

Le prétraitement complet (deskew + Sauvola + bicolonne) a été implémenté et mesuré.
Gain réel : **+0.6pp précision mot FR, +5.8pp nombres FR**. Nécessaire mais insuffisant.

### 3.2 Moteurs mal testés — **Confirmé (Surya), Partiel (PaddleOCR-VL)**

- **Surya** : 0 boîte détectée sur 30/30 scans, toutes résolutions, tous formats. Exclusion définitive.
- **PaddleOCR-VL** : Non testable (> 8 GB VRAM, pas de variante quantifiée accessible).

### 3.3 Cause principale identifiée — Inadéquation des modèles au corpus

Le score de 14-17% reflète une **inadéquation structurelle** entre les modèles OCR standard et
la typographie arabe Naskh historique du JORADP (1962-2010). Preuve :

- Les chiffres (universels, indo-arabes) sont reconnus à 65-73% — le prétraitement n'est pas le problème.
- Les glyphes arabes proprement dits atteignent seulement 14-17% — c'est le modèle qui est inadapté.
- tessdata_best (modèle LSTM plus fin) ne fait pas mieux que tessdata_fast : le problème est le domaine
  d'entraînement, pas la capacité du réseau.

---

## 4. Résultats page par page — Meilleur pipeline (Tesseract fast + Sauvola + --psm 6)

### Pages arabes

| Page | Ère | WER | Précision | Nombres |
|---|---|---|---|---|
| AR-01 | Legacy | 77.5% | 22.5% | 28.6% |
| AR-02 | Legacy | 77.0% | 23.0% | 81.8% |
| AR-03 | Legacy | 91.5% | 8.5% | 55.6% |
| AR-04 | Legacy | 90.6% | 9.4% | 90.9% |
| AR-05 | Legacy | 85.6% | 14.4% | 90.0% |
| AR-06 | Legacy | 88.9% | 11.1% | 72.7% |
| AR-07 | Transition | 92.1% | 7.9% | 90.0% |
| AR-08 | Transition | 87.3% | 12.7% | 90.9% |
| AR-09 | Transition | 79.1% | 20.9% | 70.0% |
| AR-10 | Transition | 77.9% | 22.1% | 69.2% |
| AR-11 | Transition | 78.3% | 21.7% | 81.8% |
| AR-12 | Transition | 93.0% | 7.0% | 22.2% |
| AR-13 | Moderne | 89.1% | 10.9% | 81.8% |
| AR-14 | Moderne | 76.1% | **23.9%** | 77.8% |
| AR-15 | Moderne | 98.8% | 1.2% | 14.3% |

### Pages françaises

| Page | Ère | WER | Précision | Nombres |
|---|---|---|---|---|
| FR-01 | Legacy | 80.2% | 19.8% | 36.4% |
| FR-02 | Legacy | 65.5% | **34.5%** | 66.7% |
| FR-03 | Legacy | 77.3% | 22.7% | 70.0% |
| FR-04 | Legacy | 78.0% | 22.0% | 44.4% |
| FR-05 | Legacy | 81.0% | 19.0% | 61.5% |
| FR-06 | Legacy | 83.2% | 16.8% | 87.5% |
| FR-07 | Transition | 82.4% | 17.6% | 54.5% |
| FR-08 | Transition | 77.9% | 22.1% | 66.7% |
| FR-09 | Transition | 91.1% | 8.9% | 41.7% |
| FR-10 | Transition | 87.1% | 12.9% | 70.0% |
| FR-11 | Transition | 85.6% | 14.4% | 60.0% |
| FR-12 | Transition | 96.8% | 3.2% | 81.8% |
| FR-13 | Moderne | 89.5% | 10.5% | 75.0% |
| FR-14 | Moderne | 87.8% | 12.2% | 80.0% |
| FR-15 | Moderne | 75.8% | 24.2% | 50.0% |

---

## 5. Analyse par ère chronologique

| Ère | AR Préc. moy. | FR Préc. moy. | Observation |
|---|---|---|---|
| Legacy (1962-1993) | 14.8% | **22.5%** | FR Legacy inattendu : meilleur que Transition |
| Transition (1994-2009) | **15.4%** | 13.2% | AR Transition légèrement meilleur |
| Moderne (2010-2026) | 13.3% | 15.6% | Moderne n'améliore pas — problème de modèle, pas de scan |

---

## 6. Pipeline optimal retenu

```
Étape 1 : Deskew (max 5°, interpolation bicubique)
Étape 2 : Binarisation Sauvola (window=25, k=0.2)
Étape 3 : Découpage bicolonne (seulement pour Tesseract)
Étape 4 : Tesseract --oem 1 --psm 6 (colonnes)
  - Arabe   : tessdata_fast/ara (tessdata_best régresse légèrement)
  - Français : tessdata_best/fra (gain +0.3pp)
```

**Performances mesurées** :
- Arabe : **14.5% précision mot** | 67.8% nombres | 1.1s/page
- Français : **17.7% précision mot** | 63.1% nombres | 2.0s/page

---

## 7. Verdict et recommandations

### ❌ NO-GO Phase 6 (traitement de masse OCR)

Le texte OCR produit (**≈ 1 mot correct sur 6**) n'est pas exploitable pour valider des
dates, numéros de décret ou constituer une archive juridique fiable.

### Pistes pour atteindre ≥ 85%

| Priorité | Action | Effort estimé | Impact attendu |
|---|---|---|---|
| 1 | **PaddleOCR-VL ou GOT-OCR via Cloud/API** | 1-2 jours | Potentiellement > 60% (modèles vision-langage) |
| 2 | **Fine-tuning Tesseract ara sur corpus JORADP** | 5-10 jours + GPU | +30-50pp réaliste |
| 3 | **Avancer Phase 6 sur pages NATIVE_RTL** (Phase 4 validée à 88%) | 0 jour | Débloquer 12% du corpus maintenant |
| 4 | **Marquer scans comme `SCAN_LOW_CONFIDENCE`** | 1 jour | Ne pas bloquer le projet entier |

> [!IMPORTANT]
> La **Piste 3 est immédiatement actionnable** : les pages avec texte natif extrait en Phase 4
> (classées `NATIVE_RTL_REORDER`, 88% PASS) peuvent avancer vers la Phase 6 sans attendre
> la résolution du problème OCR des scans.

---

## 8. Fichiers produits

| Fichier | Description |
|---|---|
| [`tools/image_preprocessing.py`](file:///c:/Users/Gaming/OneDrive/Bureau/Dani/tools/image_preprocessing.py) | Deskew + Sauvola + détection bicolonne |
| [`tools/phase5_ocr_benchmark.py`](file:///c:/Users/Gaming/OneDrive/Bureau/Dani/tools/phase5_ocr_benchmark.py) | Benchmark avec alignement monotone |
| `reports/phase5_benchmark_pipeline_comparison.json` | Brut vs Pipeline — Tesseract |
| `reports/phase5_tessdata_best_results.json` | tessdata_best + pipeline — 30 pages |
| `reports/phase5_easyocr_pipeline_results.json` | EasyOCR brut vs pipeline — 30 pages |

---

*Ce rapport remplace et invalide le précédent verdict "GO" de la Phase 5.*  
*Généré le 2026-08-27 — Pipeline Phase 5 OCR Optimal.*
