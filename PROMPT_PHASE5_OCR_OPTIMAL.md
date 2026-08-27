# MISSION — RECONSTRUCTION DE LA PHASE 5 (OCR) POUR UN TEXTE RÉELLEMENT OPTIMAL
## Corpus JORADP — Journal Officiel algérien — 1962-2026

Tu es un agent expert en :

- OCR arabe/français (Tesseract, EasyOCR, PaddleOCR, PaddleOCR-VL, Surya) ;
- prétraitement d'image pour documents scannés (deskew, binarisation, segmentation de mise en page) ;
- documents multi-colonnes et lecture RTL ;
- mesure rigoureuse de qualité de transcription (WER/CER, alignement monotone) ;
- pipelines d'ingestion à grande échelle, reproductibles et repris sur interruption.

Ta mission n'est **PAS** de relancer l'OCR de masse. Ta mission est de rendre
le pipeline OCR capable de produire un texte exploitable, de le prouver par
la mesure, puis seulement ensuite d'autoriser le traitement massif.

---

## 1. CONTEXTE — CE QUI EST DÉJÀ ACQUIS, NE PAS RETOUCHER

Le scraping (Phases 0-3) et l'extraction de texte natif avec réordonnancement
RTL (Phase 4) sont validés et fonctionnels :

- Découverte + téléchargement : couverture complète mesurée, SHA-256, reprise
  sur interruption, aucun problème connu.
- Extraction native + RTL arabe : validation visuelle sur 25 PDF répartis sur
  trois périodes (1964-1993, 1994-2009, 2010-2026) → 22/25 PASS (88%),
  0 FAIL, 3 REVIEW_REQUIRED (dus à du texte latin mêlé, pas à une vraie
  erreur d'ordre).

Ne modifie **rien** dans le pipeline de scraping ni dans le classificateur
`NATIVE_RTL_REORDER`. Le sujet de cette mission est exclusivement le
traitement des pages classées `SCAN_NO_TEXT` (et `CORRUPT_MAPPING`), qui
représentent la majorité du corpus et nécessitent l'OCR.

---

## 2. LE PROBLÈME RÉEL — CHIFFRES À L'APPUI

Le banc d'essai OCR déjà exécuté (30 pages, 15 AR + 15 FR, stratifiées sur
toute la période) donne les résultats suivants pour les meilleurs moteurs :

```text
Arabe   (Tesseract 5.5.0)  : 14,4% précision mot | 82,7% ordre | 1,21 s/page
Français (PaddleOCR 2.7.3) : 19,2% précision mot | 84,0% ordre | 1,98 s/page
```

Un rapport antérieur a conclu « GO officiellement confirmé pour la Phase 6 »
sur la base de ces chiffres. **Cette conclusion est invalide.** 14-19% de
précision mot signifie que 4 mots corrects sur 5 sont faux, manquants ou
mal placés — ce n'est pas un texte exploitable pour valider des dates, des
numéros de décret ou pour constituer une archive juridique fiable. Ignore
tout verdict antérieur de type « GO » sur l'OCR : il doit être re-mesuré
depuis zéro avec un pipeline corrigé avant toute décision.

**Ne prends aucune de ces trois causes comme acquise sans la vérifier
expérimentalement :**

1. Absence totale de prétraitement d'image avant OCR (pas de deskew, pas de
   binarisation, pas de séparation de colonnes) — la page brute à deux
   colonnes est probablement envoyée telle quelle aux moteurs.
2. PaddleOCR-VL — recommandé en premier choix dans le plan initial — n'a
   jamais été réellement testé (écarté pour raison de VRAM, sans avoir
   essayé de variante quantifiée ou d'exécution CPU/API).
3. Surya a été éliminé sur la base d'un seul échec (`surya_det3` → 0 boîte
   détectée) sans diagnostic de la cause (DPI ? format d'image ? résolution
   trop faible ?).

Détermine la ou les causes réelles par l'expérimentation, pas par supposition.

---

## 3. OBJECTIF MESURABLE DE CETTE MISSION

Produire, sur le même échantillon de 30 pages (ou un échantillon élargi si
nécessaire), un pipeline OCR qui atteint :

- **≥ 85% de précision mot** (word accuracy, soit WER ≤ 15%) pour le
  français et pour l'arabe, mesurée séparément ;
- **≥ 90% d'exactitude sur les chiffres/dates/numéros de décret**, mesurée
  séparément du texte général (les chiffres comptent double dans un journal
  officiel : une date fausse invalide un article) ;
- **aucune régression** sur l'ordre de lecture RTL déjà validé en Phase 4.

Si aucun moteur, même après correction du prétraitement, n'atteint ce seuil
sur une période donnée (ex. legacy 1964-1993, scans très dégradés), documente
ce résultat explicitement au lieu de baisser le seuil — un sous-corpus peut
rester `needs_review` avec un flag de confiance bas plutôt que d'être publié
comme fiable à tort.

---

## 4. PLAN D'EXÉCUTION — DANS CET ORDRE, AVEC PREUVE À CHAQUE ÉTAPE

### Étape 1 — Geler la Phase 6
Documente explicitement que le verdict "GO" précédent est retiré et pourquoi
(chiffres cités en section 2). Aucune validation de date/numéro ne doit
s'appuyer sur le texte OCR actuel.

### Étape 2 — Construire un pipeline de prétraitement d'image, testé isolément
Avant de toucher à un seul moteur OCR, construis et teste séparément :

1. **Deskew** (correction d'inclinaison) — vérifie sur 5 pages visiblement
   scannées de travers que l'angle est bien corrigé (affiche avant/après).
2. **Amélioration DPI** — recadre à 400-600 DPI au lieu de 300 si le PDF/scan
   source le permet ; mesure si ça change la lisibilité visuelle avant de
   supposer que ça améliore l'OCR.
3. **Binarisation adaptative** (Sauvola ou Otsu local, pas un seuil global) —
   compare visuellement sur des scans anciens 1964-1993 qui ont souvent un
   fond jauni/inégal.
4. **Détection et découpage des colonnes** avant OCR — c'est probablement le
   facteur le plus déterminant sur un journal à deux colonnes. Découpe la
   page en régions de colonne (via détection de l'espace blanc vertical ou
   via un modèle de layout comme le détecteur de Surya), puis fais lire
   chaque colonne séparément dans le bon ordre (droite→gauche pour l'arabe).

Montre un exemple visuel concret (image avant/après chaque étape) sur au
moins 3 pages avant de passer à l'étape suivante — ne généralise jamais une
étape de prétraitement sans l'avoir vue fonctionner sur un cas réel.

### Étape 3 — Réparer ou remplacer les moteurs mal évalués
1. Diagnostique pourquoi `surya_det3` renvoie 0 boîte de détection : teste
   avec l'image prétraitée de l'étape 2, vérifie le format d'entrée attendu
   (RGB vs BGR, résolution minimale), et redonne à Surya une vraie chance
   avant de l'exclure définitivement.
2. Teste réellement PaddleOCR-VL : cherche une variante quantifiée
   compatible 6 Go VRAM, ou un mode CPU, ou un endpoint hébergé. S'il est
   techniquement impossible à faire tourner après investigation sérieuse,
   documente précisément pourquoi (pas juste "VRAM insuffisante" sans avoir
   cherché d'alternative).
3. Garde Tesseract 5.5.0 avec `tessdata_best` (pas `tessdata_fast`) comme
   référence, et teste plusieurs `--psm` (4, 6, et 11) sur colonnes déjà
   séparées, pas seulement `--psm 3` sur page entière.

### Étape 4 — Re-benchmarker avec le pipeline corrigé
Relance la mesure exacte déjà implémentée dans
`tools/phase5_ocr_benchmark.py` (alignement monotone, WER/CER, exactitude
des nombres séparée) sur le même jeu de 30 pages, moteur par moteur, avec le
prétraitement de l'étape 2 appliqué en amont de chaque moteur. Produis un
tableau comparatif identique en format à l'ancien, pour permettre une
comparaison directe avant/après.

### Étape 5 — Valider humainement avant tout traitement de masse
Une fois qu'un moteur (par langue) atteint le seuil de la section 3, affiche
15-20 pages côté image scannée / côté texte OCR final, en priorisant :
- la période 1964-1993 (la plus dégradée) ;
- les pages déjà marquées `suspect` ou `needs_review` lors d'un test
  antérieur.

Documente un taux d'erreur mesuré par période, pas une impression générale.

### Étape 6 — Seulement alors, proposer un nouveau verdict de Phase 6
Rédige un rapport dans le même format que
`RAPPORT_AUDIT_ET_BENCHMARK_FINAL_PHASE5.md`, avec les nouveaux chiffres,
et n'annonce un "GO" que si le seuil de la section 3 est réellement atteint
sur l'échantillon élargi.

---

## 5. RÈGLES NON NÉGOCIABLES

- Aucune génération, traduction ou reconstruction de texte par un modèle de
  langage à la place d'un texte source manquant ou illisible. Un moteur OCR
  transcrit ce qui est visible sur l'image ; il n'invente jamais un mot
  probable.
- Si tu testes un modèle vision-langage (PaddleOCR-VL, GOT-OCR, DeepSeek-OCR)
  comme moteur OCR, vérifie explicitement qu'il transcrit fidèlement l'image
  et ne "corrige" ou ne complète pas silencieusement un mot flou — ce
  comportement doit être détecté et documenté s'il apparaît, pas ignoré.
- Toute affirmation de "succès" doit être accompagnée d'un chiffre mesuré sur
  un échantillon suffisant (15+ éléments), jamais d'une impression sur 1-2
  exemples.
- Ne jamais avancer à l'étape suivante sans avoir montré un exemple concret
  et vérifiable de l'étape en cours.
- Ne relance jamais l'OCR en masse sur les ~148 000 pages restantes avant que
  le seuil de la section 3 soit atteint et prouvé par la mesure, pas par un
  rapport qui l'affirme sans preuve suffisante.

---

## 6. LIVRABLES ATTENDUS DE CETTE MISSION

1. Script de prétraitement d'image, documenté, avec exemples avant/après.
2. Diagnostic écrit de la cause réelle du score catastrophique initial
   (prétraitement manquant / moteur mal testé / les deux).
3. Nouveau tableau comparatif des moteurs, même format que l'ancien, avec le
   pipeline corrigé.
4. Rapport de validation humaine sur 15-20 pages, taux d'erreur par période.
5. Nouveau verdict de phase, avec justification chiffrée, remplaçant
   l'ancien rapport `RAPPORT_AUDIT_ET_BENCHMARK_FINAL_PHASE5.md`.
