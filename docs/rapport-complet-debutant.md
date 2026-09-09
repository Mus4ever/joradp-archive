# Rapport complet et pédagogique — le projet de A à Z

> Document de référence écrit pour un lecteur débutant : le but final, chaque
> étape du travail, pourquoi elle existait, ce qu'elle a produit, et ce que
> les chiffres veulent dire.
>
> Projet : https://github.com/Mus4ever/joradp-archive — septembre 2026.

---

## 0. Le grand objectif — la carte du voyage

L'objectif final du prof : construire un **petit modèle de langage (SLM)
spécialisé en droit algérien**. Un jour, un avocat décrit une situation
(« mon client a signé une promesse de vente, le vendeur se rétracte... »)
et le modèle répond avec la loi applicable et ce qu'il faut faire.

Pour entraîner un tel modèle, il faut d'abord une chose : **des données**.
Beaucoup de données juridiques algériennes, propres, structurées. Un modèle
d'IA, c'est comme un étudiant : il ne peut pas apprendre le droit sans
bibliothèque.

Le projet = construire cette bibliothèque. Elle a **trois rayons** :

1. **JORADP** — tous les textes de loi du Journal officiel
   (10 432 PDF, 1962-2026) → *déjà fait avant*
2. **La jurisprudence HTML de la Cour suprême** (coursupreme.dz)
   → *1 253 décisions, récupérées pendant nos sessions*
3. **La revue de la Cour suprême** (مجلة المحكمة العليا) — des PDF de
   magazine juridique contenant décisions + index → *dernière session*

---

## 1. Session 1 — Nettoyage du dépôt GitHub (JORADP)

**Ce qui existait :** le pipeline qui a téléchargé les 10 432 PDF du Journal
officiel. L'audit révélait des bugs et une documentation mensongère.

**Corrections faites :**

- **Suppression d'un script dangereux** (`download_batch.py`) : vieille
  version du téléchargeur qui écrivait les fichiers « direct », sans
  protection — risque de **corrompre** des PDF déjà téléchargés.
- **Bugs corrigés** : ex. une source en échec recevait quand même une date
  de téléchargement en base (comme écrire « livré le... » sur un colis
  jamais envoyé).
- **Documentation remise en accord avec la réalité** : le README disait
  « pas d'OCR » alors que `Extraction/` contient 678 000 fichiers OCR
  (faits avec Mistral). README réécrit, journal historique déplacé dans
  `docs/`, le tout commité et poussé (commit `42fb433`).

**Pourquoi :** un repo propre = un repo que le prof peut lire, et sur lequel
on ne risque rien.

---

## 2. Session 2 — Comprendre le but (état de l'art)

Recherche web pour situer le projet :

- **Produits commerciaux** (Harvey, CoCounsel, Lexis+) : gros modèle
  généraliste + énorme base documentaire. Ils valident que le marché existe.
- **Projets de recherche** (SaulLM, Lawyer LLaMA, Alkafi-Llama3, papier
  jordanien) : ils font ce que le prof demande — prendre un **petit modèle
  existant** et le **fine-tuner** sur les lois d'un pays précis.

**Conclusion clé** : reprendre la recette de SaulLM appliquée à l'Algérie.
Personne ne l'a fait. Le corpus (lois + jurisprudence bilingue) rend ça
possible. Point technique noté pour plus tard : un modèle fine-tuné seul
peut **halluciner** des références de loi ; la pratique de l'état de l'art
combine fine-tuning + vérification des citations contre le corpus.

---

## 3. Sessions 3-4 — Le scraper de la Cour suprême (1 253 décisions)

### a) La reconnaissance (ne jamais deviner)

Avant d'écrire du code, on **regarde comment le site est fait**. Constats
sur le HTML réel :

- Les décisions sont des **pages web HTML intégral** (pas de PDF) —
  pas besoin d'OCR pour cette source ;
- Structure identique partout : bloc de métadonnées (numéro, date, sujet,
  parties...) puis sections titrées (المبدأ = principe, منطوق القرار =
  dispositif...) ;
- La chambre est identifiable par une **classe CSS stable**.

**Règle d'or :** aucun sélecteur inventé. Chaque règle de parsing correspond
à du HTML réellement vu, et des **fixtures** (copies réelles des pages)
permettent de tester sans toucher au serveur.

### b) Le code (`sources/coursupreme/`)

| Fichier | Son métier |
|---|---|
| `models.py` | définit à quoi ressemble une décision (25 champs) |
| `normalize.py` | nettoie le texte (espaces invisibles, dates ISO, arabe) |
| `parser.py` | transforme HTML brut → décision structurée |
| `storage.py` | stocke dans SQLite (base locale requêtable) |
| `discover.py` | parcourt les listes du site, collecte les URLs |
| `scraper.py` | télécharge, parse, stocke — reprise après interruption |
| `rapport_qualite.py` | statistiques de qualité |

Infrastructure JORADP réutilisée telle quelle : client HTTP compatible
avec le vieux TLS du serveur algérien, **limiteur de cadence 2 s** (politesse),
retries avec backoff.

### c) Montée en puissance progressive

1. **Prototype : 20 décisions** → vérifiées une à une à la main. 20/20.
2. **Pilote : 500 décisions** → 500/500, 0 erreur, ~30 min.
3. **Complet : 733 restantes** (lancé manuellement)
   → **1 253/1 253, 0 erreur.**

### d) Vérification indépendante de complétude

« 1 253/1 253 » ne prouve rien : le scraper a peut-être raté des pages.
`verif_completude.py` **re-parcourt tout le site sans rien télécharger** et
compare avec la base : correspondance exacte → verdict **PASS**.

**Anecdote révélatrice :** test au hasard du dossier 444499 (23/02/2009) —
« introuvable ». En creusant : il **était** en base ; la recherche échouait
parce que la base stocke les dates en ISO (`2009-02-23`) et les URLs en
encodage technique. La donnée était là ; c'est la recherche qu'il fallait
formuler autrement.

### Chiffres clés du corpus HTML

- 1 253 décisions uniques, 100 % de réussite, 0 doublon de contenu ;
- pages par chambre : civiles 402, pénales 116... ;
- années : 1979 → 2023, concentrées sur 2015-2021 (2018 : 325) ;
- champ `legal_references` absent pour 3,2 % — **défaillance du site**,
  vérifiée dans le HTML brut ; 93 % des décisions citent au moins un
  article de loi dans leur texte.

---

## 4. Session 5 — Reconnaissance de la revue (le tournant)

Nouvelle source : **مجلة المحكمة العليا** (revue de la Cour suprême —
magazine juridique : décisions commentées + index).

### Découverte en trois couches

1. **La page visible est pauvre** : seulement 6 numéros (2021-2023) et
   4 guides.
2. **Les PDF de revue sont piégés** : leur texte est en « zone d'usage
   privé » d'Unicode (codes internes incompréhensibles hors du logiciel
   d'origine). Verdict : **OCR requis**.
3. **LE TRÉSOR — les guides de recherche (دليل البحث)** : le 4e édition
   fait **760 pages** et indexe chaque décision publiée dans la revue
   depuis **1989** : numéro, année, numéro de revue, page, chambre, sujet,
   principe, référence légale. La table des matières de 35 ans de
   jurisprudence.

**La bombe :** le **sitemap officiel** du site (fichier technique listant
toutes les pages) révèle **80 numéros de revue de 1989 à 2023** — la page
visible n'en montrait que 6. Intuition du user, confirmée par les données.

Constat annexe : les 6 899 URLs « book » du sitemap = catalogue de la
bibliothèque (livres de doctrine), vérifié sur les slugs — pas des revues.

---

## 5. Session 6 — La pipeline complète de la revue

### Phase 1 — Inventaire réconcilié

Comparaison de 4 méthodes de découverte (page officielle, pages voisines,
sitemaps, liens internes) :

- **91 ressources** : 80 numéros de revue + 4 guides + 2 numéros spéciaux ;
- 76 ressources trouvées **uniquement par sitemap**, 7 uniquement par la
  page officielle, **0 doublon de PDF** ;
- 2 trous documentés (1994 n°04 et 2023 n°02 absents du site) ;
- Rapports : `reports/revue_inventory_report.{json,md}`.

### Phase 2 — Téléchargement

**86 PDF, 0 erreur, 353 Mo** — sécurité identique à JORADP : écriture
temporaire `.part` puis renommage atomique, **SHA-256** (empreinte unique
de chaque fichier), nombre de pages vérifié, reprise intégrale.

### Phase 3 — Parser le guide (le problème le plus corsé)

Le guide est un **tableau** par page, en arabe, 8 colonnes. Trois
difficultés résolues :

1. **Ordre inversé (bidi)** : le texte arabe extrait sort en ordre
   *visuel* (gauche→droite, comme à l'impression) alors que l'arabe se lit
   de droite à gauche. Fonction `visual_to_logical` : ré-inversion de chaque
   ligne en **gardant les chiffres à l'endroit**.
2. **Colonnes décalées** : l'outil standard (`extract_table`) mélangeait les
   cellules → solution **grille géométrique** : coordonnées x/y de chaque
   cellule, chaque mot assigné à sa colonne par sa position.
3. **Formes de présentation** : variantes décoratives des lettres arabes
   (U+FExx) → normalisation NFKC. Et **rien de destructif** : le texte brut
   (`raw_text`) est toujours conservé à côté du normalisé.

**Résultat : 5 737 entrées d'index** (4 717 complètes, 987 « groupées »
— plusieurs décisions partageant un principe, 33 erreurs conservées avec
texte brut), années 1989-2023. Table SQLite : `revue_index`.

### Phase 4 — Validation du pilote + OCR (fait par le user)

Pilote choisi : **revue 2023 n°01 (335 pages)**, SHA-256 vérifié, encodage
cassé confirmé (~97 % de caractères en zone privée). Pas de clé API Mistral
dans le projet → **OCR fait manuellement dans Mistral Studio par le user**,
puis ingestion du dossier de résultats dans le projet :
`data/revue/2023/issue_01/` (335 pages structurées + `metadata.json`
provenance : moteur, date, source).

### Phase 6 — Segmentation (du bloc de texte aux décisions)

Le segmenteur cherche le marqueur `ملف رقم N قرار بتاريخ` **en début de
ligne**, en excluant le sommaire (lignes finissant par « ... 19 ») et les
références internes (vérifié : la décision 1155783 citée dans le corps
n'a pas déclenché de faux début).

**Résultat : 43 décisions segmentées** — 43/43 avec numéro + date +
chambre, 39 avec dispositif détecté, 0 doublon. Stockées dans la table
`revue_decisions` avec leur provenance.

**Validation scientifique majeure :** comparaison page de début selon le
guide (papier) vs l'OCR (réel) : **écart = 0 page sur 37 décisions
vérifiables**. La pagination du guide correspond **exactement** au PDF →
pour les 79 autres numéros, on découpera directement en se fiant au guide.

### Phase 7 — Matching (croiser les corpus)

Comparaison numéro (+date) contre les 1 253 décisions HTML :

| Étendue | MATCH_EXACT | NEW (nouvelles) |
|---|---:|---:|
| Pilote 2023-01 (43 décisions) | 7 | 36 |
| Tout le guide v4 (5 704 matchables) | 176 | **5 518** |

La revue est un corpus **massivement nouveau** (~3 % de chevauchement) :
elle couvre 1989-2023 là où le HTML ne couvre quasiment que 2015-2023.
Aucune suppression automatique : `sources` conserve la multi-provenance.

---

## 6. Cartographie du projet

```
joradp-archive/
├── downloads/                  ← 10 432 PDF du Journal officiel (JORADP)
├── Extraction/                 ← texte extrait des 10 432 (OCR Mistral + natif)
├── databases/
│   ├── joradp.db               ← catalogue des 10 432 sources JORADP
│   ├── coursupreme.db          ← 1 253 décisions HTML structurées
│   └── coursupreme_revue.db    ← inventaire 91 ressources + index guide (5 737)
│                                  + 43 décisions pilote OCR + matching
├── data/revue/
│   ├── *.pdf                   ← 86 PDF de la revue (1989-2023 + guides)
│   └── 2023/issue_01/          ← OCR du pilote (335 pages structurées)
├── raw/coursupreme/            ← HTML brut des 1 253 décisions (preuve)
├── sources/coursupreme/        ← scraper décisions
│   └── revue/                  ← pipeline revue (nouveaux modules)
├── tests/                      ← 39 tests automatiques hors ligne
├── reports/                    ← rapports (qualité, complétude, inventaire)
└── docs/                       ← documentation (journal, coursupreme, revue)
```

**Patrimoine de données :** 10 432 textes de loi (texte extrait) + 1 253
décisions HTML structurées + 5 737 entrées d'index couvrant 35 ans de
jurisprudence + 43 décisions de revue complètes.

---

## 7. Mini-glossaire des concepts vus

- **Scraper** : programme qui lit automatiquement les pages d'un site pour
  en extraire des données. Règles : poli (2 s entre requêtes), identifiable
  (User-Agent explicite), jamais de contournement de protections.
- **SQLite** : base de données dans un seul fichier — notre mémoire :
  recherche, comptage, reprise après interruption.
- **SHA-256** : empreinte unique d'un fichier ; change si le fichier change
  d'un octet. Preuve d'intégrité.
- **OCR** : transformer une image de texte en vrai texte (scans, ou PDF au
  texte cassé comme la revue).
- **Bidi / ordre visuel vs logique** : l'arabe se lit droite→gauche mais
  sort des PDF inversé ; fonction de conversion nécessaire.
- **Fine-tuning / QLoRA** : technique qui ré-éduquera un petit modèle
  existant sur ce corpus (Phases 9+ du plan — pas encore commencées).
- **Reprise après interruption** : chaque donnée a un statut en base
  (`decouvert` → `telecharge` → `erreur`) ; relancer ne refait que le reste.
- **Robots.txt** : fichier d'un site indiquant ce que les robots peuvent
  lire. Ici : seul `ChatGPT-User` est interdit ; notre UA explicite est
  autorisé ; aucun CAPTCHA/anti-bot rencontré.

---

## 8. Ce qui reste à faire (ordre du plan du prof)

1. **OCR des 79 autres numéros de revue** (~26 000 pages estimées) —
   même manœuvre manuelle Mistral, ingestion par script, numéro par numéro.
2. **Éclater les 987 entrées « groupées »** de l'index (plusieurs décisions
   partageant une cellule du guide).
3. **Phase 6 du plan : dataset de questions-réponses** à partir de tout le
   corpus (le papier jordanien en fait ~6 000 ; les matériaux algériens
   permettent bien plus).
4. **Anonymisation obligatoire** avant tout dataset : confirmé au pilote,
   la revue publie les **noms complets des magistrats et avocats** (les
   parties restent en initiales) → étape ANONYMIZED requise.
5. Ensuite : choix du modèle de base, fine-tuning, évaluation
   (précision de citation — « a-t-il cité le bon article ? »).

---

## 9. En une phrase

On a transformé un projet de scraping (JORADP) en **bibliothèque juridique
algérienne multi-sources, vérifiée et structurée** : les lois (fait), la
jurisprudence récente (fait, 1 253), et l'historique complet par la revue
(inventaire + téléchargement + index faits, OCR en cours numéro par numéro).
Chaque donnée a sa provenance, chaque étape a ses tests, chaque résultat a
été vérifié indépendamment — c'est exactement le métier d'ingénieur IA :
**80 % de données, 20 % de modèle**.
