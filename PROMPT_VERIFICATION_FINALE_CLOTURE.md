# MISSION — VÉRIFICATION FINALE ET CLÔTURE PROPRE DE LA PHASE 5

## Contexte

`RAPPORT_FINAL_GROUND_TRUTH_RECONSTRUCTION.md` a corrigé le ground truth et
obtenu des résultats crédibles sur certaines pages (ex. FR-14 : 93,4% aux
deux méthodes de scoring). Mais un problème subsiste : sur plusieurs pages,
le score "Monotone" (script maison) et le score `jiwer` (bibliothèque
indépendante) divergent fortement — jusqu'à un facteur ×4 (ex. AR-02 : 16,8%
vs 67,5% ; FR-15 : 33,4% vs 64,5% ; AR-08 : 19,3% vs 50,6%).

Le tableau de synthèse final (section 4 du rapport) a été calculé avec les
moyennes du score **Monotone** — la métrique la moins fiable des deux. Cette
mission a pour but de produire un verdict final basé sur la métrique la plus
fiable, et de vérifier que les scores catastrophiques restants (ex. AR-15 à
1,1%/5,1%) sont de vrais échecs OCR et non un dernier résidu de bug.

C'est la dernière étape avant clôture. L'objectif du projet est de livrer un
scraping + texte extrait propre — pas de poursuivre indéfiniment
l'optimisation OCR.

## Étape 1 — Diagnostiquer pourquoi le score Monotone diverge encore de jiwer

Sur les 4-5 pages avec le plus grand écart (AR-02, AR-14, AR-08, FR-15),
inspecte `find_best_window()` et la logique d'alignement dans
`phase5_ocr_benchmark.py` :

1. Vérifie si la fenêtre de recherche (`N-2` à `N+4` mots) est trop étroite
   quand l'OCR insère des mots-parasites entre les mots corrects.
2. Détermine si l'écart vient d'un problème d'ordre de lecture (colonnes
   mal réordonnées) qui pénalise le score monotone mais pas `jiwer` (qui
   compare le texte global sans respecter un ordre strict).
3. Conclusion attendue : soit tu corriges le script maison, soit tu
   documentes que `jiwer` est désormais la métrique de référence officielle
   du projet et que le script maison sert seulement de contrôle secondaire.

## Étape 2 — Recalculer le tableau de synthèse final avec `jiwer` comme métrique officielle

Reprends exactement la structure du tableau de la section 4 du rapport
(Langue × Ère : précision mot, exactitude nombres, verdict GO/NO-GO au
seuil ≥85%/≥90%), mais avec les moyennes `jiwer` au lieu des moyennes
Monotone. Indique les deux chiffres si tu veux garder une trace, mais le
verdict GO/NO-GO doit se baser sur `jiwer`.

## Étape 3 — Vérification visuelle ciblée des pires cas seulement

Pour les 3 pages avec le score `jiwer` le plus bas (probablement AR-15,
AR-12, et une troisième à identifier) :

1. Affiche l'image et le ground truth corrigé côte à côte, confirme que le
   ground truth correspond bien maintenant au contenu réel (pas de résidu
   du bug initial).
2. Si le ground truth est confirmé correct et le score reste très bas
   (<20%), c'est un vrai échec OCR sur cette page (probablement scan très
   dégradé ou typographie ancienne) — documente-le comme tel, n'essaie pas
   de le corriger davantage.

Ne réaudite pas les 30 pages une deuxième fois — seulement ces 3 cas
extrêmes, pour clore le doute.

## Étape 4 — Verdict final et action de clôture (pas de nouvelle piste d'optimisation)

Produis un verdict final court, par catégorie, avec l'action concrète à
appliquer dans l'export du corpus — pas de nouvelle piste d'amélioration
(pas de fine-tuning, pas de VLM cloud à ce stade) :

| Catégorie | Verdict | Action dans l'export |
|---|---|---|
| Pages `NATIVE_RTL_REORDER` (Phase 4) | GO | Texte natif utilisé directement |
| FR Moderne, scans propres | GO (si confirmé ≥85% avec jiwer) | Texte OCR utilisé, confiance haute |
| Tout le reste (Legacy, Transition, AR général) | NO-GO | Texte OCR inclus quand même, mais avec un champ `confidence: low` explicite dans l'export, pas exclu du corpus |

## Étape 5 — Rédiger le README de clôture du projet

Un court README final (pas un rapport technique de plus) qui explique en
langage clair, pour quelqu'un qui n'a pas suivi tout le projet :

1. Ce qui a été scrapé (couverture, période, langues).
2. Comment le texte a été extrait (natif RTL vs OCR).
3. Le niveau de confiance par catégorie (tableau de l'étape 4), en une
   phrase compréhensible par un non-technicien : "le texte est fiable à
   plus de 85% pour X, et doit être vérifié manuellement pour Y".
4. Une liste claire des limites connues, assumées, pas cachées.

## Règle de clôture

Une fois ce rapport produit, le projet est terminé pour ce qui concerne le
scraping et l'extraction de texte. N'ouvre pas de nouvelle piste
d'amélioration OCR après cette étape (fine-tuning, nouveau moteur, etc.)
sauf demande explicite — l'objectif était un texte propre et honnête, pas
une précision parfaite sur l'intégralité du corpus.
