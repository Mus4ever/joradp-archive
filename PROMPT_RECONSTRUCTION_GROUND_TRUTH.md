# MISSION — RECONSTRUCTION DU GROUND TRUTH ET BENCHMARK DÉFINITIF

## Contexte

`RAPPORT_AUDIT_MANUEL_GROUND_TRUTH.md` a démontré, sur 4 pages examinées
visuellement, que `benchmark/ground_truth.json` contient des textes qui ne
correspondent pas au contenu réel des images scannées (ex : FR-14 comparé à
un texte sur l'Agence Spatiale Algérienne au lieu du décret métro d'Alger
réellement présent). Un cas (FR-14) a été validé indépendamment avec `jiwer` :
93,41% de précision réelle contre 12,7% mesuré avec le faux ground truth.

**Cette découverte est probablement bonne nouvelle pour l'OCR**, mais elle
n'est pas encore une preuve complète. Ta mission est de la transformer en
certitude chiffrée sur l'ensemble de l'échantillon, pas seulement sur 4 pages.

## Étape 1 — Identifier la cause racine de la corruption

Avant de tout reconstruire à la main, comprends comment `ground_truth.json` a
été généré à l'origine (script, méthode, source). Réponds précisément à :

- Le ground truth a-t-il été transcrit manuellement, généré par un ancien
  passage OCR, ou extrait automatiquement d'une autre source (ex. sommaire
  JORADP en ligne, base de données de décrets) ?
- Y a-t-il un décalage systématique (off-by-one page, mauvais numéro de JO,
  mauvaise année) qui expliquerait plusieurs erreurs d'un coup, ou des
  erreurs isolées et aléatoires ?
- Ce même mécanisme de mapping (fichier image ↔ contenu attendu) est-il
  utilisé ailleurs dans le pipeline (téléchargement, classification de
  page) ? Si oui, vérifie qu'il n'a pas introduit une corruption similaire
  en dehors du benchmark.

Documente la cause avant de continuer — ça détermine si le problème est
isolé au benchmark ou plus large.

## Étape 2 — Auditer les 30 pages une par une, pas seulement les 4 déjà vues

Pour chacune des 30 pages (15 AR + 15 FR) :

1. Affiche l'image scannée à côté du `ground_truth.json` actuel.
2. Vérifie ligne par ligne que le ground truth correspond bien au contenu
   visible sur CETTE image précise (pas une autre page, pas un autre numéro).
3. Classe chaque page : `GT_CORRECT` / `GT_CORROMPU` / `GT_PARTIELLEMENT_FAUX`
   (ex. bon numéro de JO mais mauvaise page, ou texte tronqué).

Produis un tableau récapitulatif des 30 pages avec ce statut — c'est la
preuve qu'il manque actuellement au rapport.

## Étape 3 — Reconstruire un ground truth fiable, avec traçabilité

Pour toute page classée `GT_CORROMPU` ou `GT_PARTIELLEMENT_FAUX` :

1. Transcris fidèlement le texte réellement visible sur l'image (les
   premières lignes significatives suffisent, comme dans le benchmark
   original — pas besoin de la page entière).
2. Enregistre pour chaque entrée sa provenance : nom exact du fichier image,
   date/numéro de JO, et comment la transcription a été vérifiée (lecture
   directe de l'image, pas une source externe).
3. Fais relire ce nouveau ground truth par un second passage indépendant
   (toi-même à un moment différent, ou une autre méthode) pour détecter une
   erreur de transcription avant de l'utiliser comme référence.

## Étape 4 — Rejouer le benchmark complet avec le ground truth corrigé

Relance exactement le même pipeline que celui déjà validé comme le meilleur
(Tesseract + Sauvola + découpage bicolonne + `--psm 6`, `tessdata_best` pour
le français, `tessdata_fast` pour l'arabe) sur les 30 pages, avec le nouveau
ground truth. Utilise `jiwer` en parallèle du script maison
(`phase5_ocr_benchmark.py`) sur au moins 10 pages (5 AR + 5 FR) pour confirmer
que les deux méthodes de scoring s'accordent maintenant, côté arabe comme
côté français — pas seulement sur le cas FR-14 déjà vérifié.

## Étape 5 — Verdict final, par langue et par ère

Produis un tableau final : précision mot et exactitude des nombres, par
langue (AR/FR) et par ère (Legacy/Transition/Moderne), avec le ground truth
corrigé. Applique le même seuil que la mission précédente (≥85% précision
mot, ≥90% exactitude nombres) pour décider, période par période :

- si le seuil est atteint → GO pour le traitement de masse de cette période ;
- si une période spécifique reste sous le seuil (ex. Legacy très dégradé)
  → NO-GO ciblé sur cette période seulement, pas sur tout le corpus.

## Règle non négociable

Ne déclare pas de verdict global "GO" ou "NO-GO" avant d'avoir audité les
30 pages (Étape 2), pas seulement les 4 exemples déjà trouvés. Un bug de
ground truth partiel ne garantit pas que les 26 autres pages étaient
également fausses — ni qu'elles étaient toutes correctes. Chaque page compte.
