# Reconnaissance — مجلة المحكمة العليا (Revue de la Cour suprême)

**Date :** 09/09/2026 — **Phase : reconnaissance uniquement** (aucun scraping
massif, aucun OCR de masse, corpus des 1 253 décisions HTML intact).

## 1. Résumé exécutif

La revue de la Cour suprême n'est **pas** exposée en ligne comme une archive
numérotée par année/numéro. La page officielle « تحميل مجلة المحكمة العليا »
ne liste que **4 numéros réguliers (2021-2023) + 2 numéros spéciaux**, chacun
dans sa propre sous-page avec un PDF. La vraie richesse est ailleurs : les
**guides officiels de recherche** (دليل البحث), notamment la **4e édition
(760 pages, 2024)**, qui est un **index structuré complet** des décisions
publiées dans la revue de **1989 à 2023**, avec les colonnes exactes :
رقم القرار / السنة / العدد / الصفحة / الغرفة / الموضوع / المبدأ / المرجع
القانوني. Les PDF de revue ont un texte **inextractible** (encodage cassé en
zone privée Unicode) → OCR requis. Le chevauchement avec nos 1 253 décisions
HTML est faible (~3 % d'un échantillon du guide) : la revue est un corpus
massivement nouveau.

## 2. Sources officielles identifiées

- Page de téléchargement : `https://coursupreme.dz/تحميل-مجلة-المحكمة-العليا/`
  (HTTP 200, pas de pagination — 1 page).
- Sous-pages par numéro/guide : 10 identifiées (6 revues, 4 guides).
- Sitemap WordPress officiel : `sitemap_index.xml` → 50 sitemaps :
  **38 `book`** (6 899 URLs uniques = catalogue de la **bibliothèque**,
  titres d'ouvrages de doctrine — PAS des numéros de revue), **7 `decision`**
  (1 066 URLs uniques), 3 `post`, 1 `page`, 1 `category`.
- Page « آخر مجلة معروضة للبيع » (dernière revue en vente) et « المكتبة » :
  aucun PDF direct.

## 3. Architecture de la page des revues

Pas d'arborescence par année. Une page unique → vignettes liées vers des
sous-pages WordPress, chacune contenant **un seul PDF** dans
`wp-content/uploads/`. Structure réellement observée :

```
تحميل-مجلة-المحكمة-العليا/
├── مجلة-المحكمة-العليــا-العدد-01-2023/  → PDF revue 2023 n°01
├── مجلة-المحكمة-العليــا-العدد-02-2022/  → PDF revue 2022 n°02
├── مجلة-المحكمة-العليــا-العدد-01-2022/  → PDF revue 2022 n°01
├── مجلة-المحكمة-العليا-العدد-02-2021/    → PDF revue 2021 n°02
├── عدد-خاص-المسوؤلي-…/                    → PDF numéro spécial (2020)
├── عدد-خاص-دور-التشريع-…/                 → PDF numéro spécial (URL tronquée)
├── دليل-البحث-…-الط-2 (4e éd. 2024)      → PDF guide 760 p.
├── دليل-البحث-…-الط (3e éd.)             → PDF guide
├── دليل-قرارات-لجنة-التعويض-… (2 éd.)    → PDF guide 63 p.
└── دليل-قرارات-لجنة-التعويض-… (1re éd.)  → PDF guide
```

## 4. Inventaire des numéros

Voir `reports/revue_cour_supreme_inventory.json` (machine-readable). En l'état
du site : **6 numéros de revue accessibles** (4 réguliers + 2 spéciaux) ;
2021 n°01 non trouvé ; années antérieures à 2021 **non disponibles en ligne**
(cohérent avec le canal « point de vente » documenté par le ministère).

## 5. Période couverte

- **En ligne (PDF revues)** : 2021-2023 (+ 2 numéros spéciaux sans année
  visible, l'un daté 2020 par son chemin d'upload).
- **Via le guide v4 (index)** : décisions de la revue de **1989 à 2023**
  (années observées dans l'échantillonnage du texte ; 2024 n'apparaît que
  comme en-tête).

## 6. Guides et index — PRIORITAIRE

Le **دليل البحث — الطبعة الرابعة (2024, 760 pages)** est l'index officiel :
il mappe **décision → numéro de revue → page**, avec en plus la chambre, le
sujet, le principe et la référence légale. C'est exactement la relation
prioritaire demandée. Le texte est natif mais en **formes de présentation
arabe** (U+FExx + coupures de kashida) — normalisable (NFKC + table de
ligatures + recollage), pas besoin d'OCR. Édition 3 + guides lجنة التعويض
disponibles également. La 3e éd. couvre vraisemblablement la période
antérieure (à confirmer au scraping).

## 7-9. Structure interne des PDF + échantillonnage + OCR

| PDF | Pages | Texte | Verdict |
|---|---:|---|---|
| revue 2023 n°01 | 335 | codes zone privée (\uf2d2…), 0-2 images/page | **OCR requis** |
| revue 2021 n°02 | 293 | idem (producteur doPDF/Windows 7) | **OCR requis** |
| numéro spécial (2020) | ? | URL tronquée dans le HTML — à re-extraire | ? |
| guide v4 (2024) | 760 | natif (présentation arabe) | **normalisation, pas d'OCR** |
| guide lجنة التعويض v2 | 63 | natif | normalisation |

Les revues ne sont **pas des scans images** : texte vectoriel rendu avec une
police sans table ToUnicode → extraction = charabia. La voie pratique est le
pipeline déjà éprouvé sur JORADP : rendu image des pages → **OCR (Mistral,
sortie markdown + métadonnées par page)**.

## 10. Méthode potentielle de segmentation

Marqueurs à valider après OCR d'un numéro complet : « قرار رقم » / « رقم
القرار » / « بتاريخ » / « لهذه الأسباب » / en-têtes de chambre (الغرفة …).
Le guide donne par avance **le numéro de revue et la page de début** de
chaque décision — la segmentation peut donc être **guidée par l'index
officiel** plutôt que par des marqueurs seuls (approche recommandée :
croiser les deux). Nombre de décisions par numéro : UNKNOWN à ce stade
(pas deviné).

## 11. Métadonnées disponibles

- **Présentes explicitement** (guide v4) : numéro, année, revue, page,
  chambre, sujet, principe, référence légale.
- **Dérivables** : parties, motifs, dispositif (après OCR du corps).
- **Non disponibles** : procédure détaillée, pages de fin (dérivable du
  début de l'entrée suivante).

## 12-13. Chevauchement et doublons avec les 1 253 HTML

Test : 60 pages échantillon du guide v4 → 436 numéros candidats (4-7
chiffres) → **13 correspondances exactes avec `decision_number` en base
(~3 %)**. Caveats : extraction de tables bruitée (page/dates polluent les
candidats) ; correspondances réelles confirmées par des numéros de dossier
à 6-7 chiffres. Conclusion : le corpus revue est **majoritairement nouveau**
par rapport au HTML. Stratégie de déduplication : clé principale
`decision_number + date`, secondaire `decision_number + chambre`, tertiaire
comparaison de texte après OCR ; conserver la provenance (site HTML vs
revue+page).

## 14. robots.txt et contraintes

Identiques au reste du site (déjà documentés dans `docs/coursupreme.md`) :
seul `ChatGPT-User` est interdit ; pas de CAPTCHA/anti-bot rencontré ;
User-Agent explicite + 2 s de délai appliqués pendant toute la
reconnaissance (14 requêtes pages + 4 PDF).

## 15. Données personnelles / anonymisation

À traiter après OCR (même politique 3 niveaux : RAW/PROCESSED/ANONYMIZED).
La revue étant imprimée, elle publie les décisions **avec des noms
probablement complets** (contrairement au HTML qui anonymise en initiales) —
vérifier sur le premier numéro OCRisé : cela rendra l'étape ANONYMIZED
obligatoire avant tout dataset.

## 16-17. Faisabilité

- **Scraping** : trivial — 10 sous-pages, 10 PDF, ~30 Mo estimés, 1 requête
  par fichier.
- **OCR** : nécessaire pour les revues uniquement ; volume en ligne faible
  (≈ 1 000 pages pour 4 numéros) ; pipeline JORADP réutilisable tel quel.
  La vraie valeur (l'index 1989-2023) est dans les **guides, sans OCR**.

## 18. Valeur pour le dataset juridique

Élevée et **complémentaire** : (a) l'index guide fournit pour ~35 ans de
jurisprudence les métadonnées structurées (chambre, sujet, principe,
référence légale) — idéales comme graine du dataset QA ; (b) les décisions
de la revue, une fois OCRisées, fournissent le texte intégral ; (c)
l'association index↔corpus HTML se fait sur numéro+date.

## 19. Limitations

Seuls 6 numéros de revue sont en ligne — l'historique complet reste physique
(point de vente). L'URL d'un PDF spécial est tronquée dans le HTML source.
La date « 2020+ uniquement physique » du portail ministériel est contredite
pour le canal HTML (voir docs/coursupreme.md §10).

## 20. Verdict

**OCR_REQUIRED** (pour les revues) — avec la nuance importante : la
**composante la plus précieuse (guides/index) est du texte natif**, sans OCR.

## 21. Proposition de prochaine étape

1. **A. Scraping PDF** : les 10 fichiers (6 revues + 4 guides) — léger,
   poli, réutilise `http_client`/`rate_limiter`.
2. **B. Parser les guides (texte natif)** : normaliser NFKC + recoller les
   kashidas, extraire la table index → SQLite (`revue_index`) — c'est la
   table décision→revue→page 1989-2023, priorité absolue.
3. **C. OCR pilote** : 1 numéro de revue (335 p.) via le pipeline JORADP,
   pour valider segmentation et qualité.

## Tableau final

| Élément | Résultat | Preuve / URL | Confiance |
|---|---|---|---|
| Page officielle | 1 page, 10 sous-pages | تحميل-مجلة-المحكمة-العليا | HIGH |
| Nombre de numéros en ligne | 6 (4 réguliers + 2 spéciaux) | inventaire JSON | HIGH |
| Période (revues en ligne) | 2021-2023 + spéciaux | chemins d'upload | HIGH |
| Période (index guide v4) | 1989-2023 | échantillonnage texte | MEDIUM |
| PDF accessibles | 10 (6 revues + 4 guides) | sous-pages | HIGH |
| PDF scannés | Non (texte vectoriel encodage cassé) | pypdf, PUA | HIGH |
| OCR requis | Oui pour les revues ; non pour les guides | analyse échantillon | HIGH |
| Index disponible | OUI — guide v4, 760 p., colonnes complètes | pages 31/102/302 | HIGH |
| Segmentation possible | Oui, guidée par l'index + marqueurs | à valider post-OCR | MEDIUM |
| Doublons avec HTML | ~3 % (échantillon) | matching n° | MEDIUM |
