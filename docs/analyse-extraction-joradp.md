# Analyse complète des markdown d'extraction JORADP

> Objectif : déterminer si les fichiers de `Extraction/` sont assez bien
> structurés pour servir de matière première au dataset du futur SLM
> juridique. Analyse par échantillonnage représentatif des 3 formats,
> lecture approfondie, puis métriques. Date : septembre 2026.

## 1. Rappel : les trois formats présents

| Format | Période | Langue | Nombre | Structure disque |
|---|---|---|---:|---|
| **A. OCR Mistral** | FR 1962-2001 | FR | 3 286 | dossier `F{année}{n°}.pdf/markdown.md` + `pages/page-N/` |
| **A. OCR Mistral** | AR 1964-2026 (tout) | AR | 5 130 | idem |
| **B. Extraction native** | FR 2002-2026 | FR | 2 016 | fichier plat `{F…}.md` + `{F…}.json` |

Total : 10 432 numéros, tous extraits.

## 2. Format A (OCR Mistral) — VERDICT : bien structuré, exploitable

### Ce qui est réussi (vérifié sur échantillon 1962, 1970, 1990, 2026)

- **Structure sémantique réelle**, pas juste du texte brut :
  - `# JOURNAL OFFICIEL` (titre du numéro) ;
  - `## SOMMAIRE` / `## فهرس` (la table des matières du JO, présente dans
    **16/16** numéros échantillonnés) ;
  - `### ORDONNANCES`, `### قوانين` (catégories d'actes) ;
  - italiques pour les types d'actes (`*Ordonnance* n° 62-1 du ...`) ;
  - **tableaux reconstruits** en markdown (tarifs d'abonnement, résultats
    de référendum, comptes financiers) — 4 967 lignes de tableau sur 8
    numéros FR OCR, 748 sur 8 numéros AR.
- **Métadonnées par page riches** : `page-metadata.json` contient chaque
  bloc OCR avec ses coordonnées (`topLeftX/Y`, `bottomRightX/Y`) et son
  type (`header`, `body`) — on peut donc re-découper proprement.
- **`header.md` isole l'en-tête de page** (« 1re année. — N° 1,
  BI-HEBDOMADAIRE, Vendredi 6 juillet 1962 ») : idéal pour nettoyer les
  répétitions d'en-têtes sans risquer le contenu.
- **Arabe sain** : RTL correct, ligatures gérées, aucune inversion bidi
  observée (contrairement aux PDF de la revue), qualité uniforme de 1964 à
  2026 (6/6 numéros récents avec فهرس, 356 titres sur 6 numéros).
- **Deux granularités disponibles** : le document complet (`markdown.md`)
  ET la page par page (`pages/page-N/markdown.md`) — la segmentation en
  documents individuels (loi, décret...) pourra s'appuyer sur le sommaire
  qui donne les pages.

### Faiblesses observées (mineures)

1. **Ordre des entrées du sommaire parfois brouillé** (colonnes du sommaire
   lues dans le mauvais ordre : en 1990 AR, le n° 89-24 apparaît après le
   89-27). Sans gravité : les textes eux-mêmes sont dans le bon ordre.
2. **Artefacts typographiques** : exposants mistraliens (`1$^{er}$`,
   `$^{re}$`), images inline (`![img-0.jpeg]`), en-têtes de page répétés
   dans le document complet.
3. **Erreurs OCR ponctuelles** inévitables sur les scans anciens
   (caractères isolés), sans impact structurel.
4. Les tableaux complexes multi-colonnes peuvent fusionner des cellules
   (années 1990, revues financières).

**Conclusion format A : 8 416 fichiers directement exploitables pour le
dataset après un nettoyage léger (en-têtes répétés, exposants, images).**

## 3. Format B (extraction native FR 2002-2026) — VERDICT : défaillance
structurelle majeure, INUTILISABLE en l'état

### Le défaut (systémique, vérifié sur 25/25 numéros échantillon)

Les pages du JO moderne sont composées en **2 colonnes**. L'outil
d'extraction natif n'a pas détecté les colonnes et a :

1. **Converti les pages en tableaux markdown** `|colonne gauche|colonne
   droite|` avec des `<br>` à l'intérieur des cellules — **25/25** fichiers
   échantillon touchés, soit ≈ 2 016 fichiers ;
2. **Détruit l'ordre de lecture** — preuve mesurée sur `FR2010001.md` :
   la séquence des articles du décret 10-01 sort dans l'ordre
   **Art. 2, 4, 5, 6, 8, 9, 10, 11, puis Art. 7** (l'article 7 se retrouve
   après l'article 11, prisonnier de la cellule de gauche d'un tableau) ;
3. **Tronqué le texte aux bords de colonnes** — preuves dans le même
   fichier : « `|écret n°76-66` » (le D de *Décret* est perdu), « `430
   correspondant` » (perdu : *14*30), « `al.` » (perdu : *nationale*). Ce
   ne sont pas de simples réordonnancements : **des caractères sont perdus**.

### Structure des titres quasi inexistante

Sur 6 numéros natifs : 576 titres, dont **174 sont de simples marqueurs
« ## Page N »** et le reste des lignes en gras issus de la mise en page.
Aucune hiérarchie sémantique comparable au format A. Le sommaire contient
des pointillés de conduite (`...... 3`), la page 1 mélange les colonnes du
bandeau (direction/rédaction/abonnements entrelacés), et des commentaires
`<!-- Start of picture text -->` jalonnent les zones non textuelles.

### Conséquence

**Les 2 016 fichiers FR natifs (2002-2026) ne doivent PAS être utilisés
tels quels pour l'entraînement du SLM** : des articles hors ordre et des
mots tronqués corrompraient silencieusement les paires questions-réponses
(« citer l'article 7 » renverrait vers un texte déplacé).

## 4. Pourquoi ce n'est pas grave — et les 3 voies de réparation

La bonne nouvelle : **la version arabe des mêmes textes existe en OCR
Mistral de qualité** (l'AR couvre toutes les années), et les PDF originaux
FR sont intacts dans `downloads/FR/2002-2026/`. Trois voies :

1. **Re-extraction native avec détection de colonnes** (recommandée en
   premier) : refaire l'extraction des 2 016 PDF avec un découpage par
   colonne (pdfplumber : crop moitié gauche/moitié droite, lecture
   colonne par colonne). 100 % local, gratuit, quelques heures. À
   prototyper sur 10 numéros et valider contre l'OCR.
2. **Re-OCR Mistral des 2 016 PDF FR récents** (comme la revue) : qualité
   garantie, format identique au format A, mais coût API/temps manuel.
3. **Hybride** : la voie 1 pour tout, avec re-OCR ciblé des pages que la
   validation rejette.

## 5. Nettoyage transversal recommandé (avant dataset)

Pour le format A (et le format B réparé) :

1. retirer les en-têtes/pieds répétés — **`header.md` les fournit déjà
   isolés** ;
2. retirer `![img-N.jpeg]` et les commentaires `<!-- ... -->` ;
3. normaliser les exposants (`1$^{er}$` → `1er`) ;
4. exploiter le sommaire (numéro → type d'acte → page) pour segmenter en
   documents individuels, et croiser avec `page-metadata.json` ;
5. conserver toujours le texte brut (principe RAW jamais détruit).

## 6. Synthèse

| Format | Fichiers | Structure | Ordre de lecture | Verdict dataset |
|---|---:|---|---|---|
| A. OCR FR 1962-2001 | 3 286 | sémantique, tableaux, sommaire | correct | ✅ exploitable |
| A. OCR AR 1964-2026 | 5 130 | sémantique, فهرس | correct | ✅ exploitable |
| B. Natif FR 2002-2026 | 2 016 | quasi nulle (« ## Page N ») | **cassé + troncatures** | ❌ à réparer |

Priorité : réparer le format B (voie 1), car c'est la seule partie
défaillante — 80 % du corpus (format A) est prêt.
