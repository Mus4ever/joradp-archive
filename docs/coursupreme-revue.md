# Pipeline Revue de la Cour suprême — architecture et stratégies

Module : `sources/coursupreme/revue/` — document de référence (Phase 11).
Données de pilotage : `reports/revue_inventory_report.{json,md}`.

## 1. Architecture et flux de données

```
Site officiel (pages + sitemaps WordPress)
    ↓ inventaire_complet.py (réconciliation A/B/C/D)
reports/revue_inventory_report.json          → 91 ressources, 80 numéros 1989-2023
    ↓ storage.RevueStore → databases/coursupreme_revue.db (revue_resources)
downloader.py  (Phase 2 : .part + os.replace + SHA-256 + pypdf)
data/revue/*.pdf                              → 86/86 PDF, 353 Mo, 0 erreur
    ↓
guide_parser.py (Phase 3 : grille géométrique pdfplumber + bidi)
databases/coursupreme_revue.db (revue_index)  → 5 737 entrées du guide v4
    ↓ matching.py (Phase 7 : 3 niveaux)
revue_matches                                 → 176 exact / 10 probables / 5 518 NEW
    ↓ ocr_pilot.py (Phases 4-5 : à exécuter avec accès Mistral)
data/revue/2023/issue_01/{raw,pages,markdown,metadata.json}
    ↓ segmentation (Phase 6, après OCR)
décisions structurées de la revue → corpus unifié
```

## 2. Schéma SQLite (`databases/coursupreme_revue.db`)

- **revue_resources** : inventaire + téléchargements. `url` UNIQUE,
  `pdf_url`, `sha256`, `pdf_pages`, `status` (decouvert/telecharge/erreur),
  `discovery_methods` (JSON) — reprise intégrale par statut.
- **revue_index** : entrées du guide. `decision_number`, `decision_year`,
  `issue_number`/`issue_year` (revue), `start_page`, `chamber`, `subject`,
  `principle`, `legal_reference`, `source_pdf`, `source_page` (page du
  guide), **`raw_text`** (jamais jeté), **`normalized_text`**,
  `parser_status` (ok/partial/error).
- **revue_matches** : `entry_id`, `verdict` (MATCH_EXACT/MATCH_PROBABLE/
  NEW/UNCERTAIN), `level`, `decision_id`, `sources` (provenance).

## 3. Inventaire réconcilié (Phase 1) — fait saillant

La page officielle de téléchargement n'expose que 2021-2023 (7 ressources).
Le **sitemap `post` révèle 80 numéros de 1989 à 2023** (المجلة القضائية,
4/an en 1989-1993 puis 2/an), invisibles en navigation. Réconciliation :
76 ressources trouvées uniquement par sitemap, 7 uniquement par la page
officielle, 0 doublon de PDF, 2 trous dans la série (1994 n°04, 2023 n°02).
Les 6 899 URLs `book` du sitemap = catalogue de bibliothèque (doctrine),
pas des numéros de revue (vérifié sur les slugs).

## 4. Stratégie OCR (Phases 4-5)

- Les PDF de revue ont un texte **techniquement présent mais inutilisable**
  (police sans table ToUnicode → codes en zone d'usage privé Unicode ;
  vérifié : ~97 % des caractères en PUA sur le pilote 2023-01).
- Pipeline retenu = celui éprouvé sur JORADP : **OCR Mistral** (API si
  `MISTRAL_API_KEY`, sinon ingestion manuelle depuis Mistral Studio via
  `ocr_pilot.py --from-file`).
- Sortie structurée par page, format identique à JORADP
  (`data/revue/{année}/issue_{NN}/...`), RAW jamais écrasé.
- **Pilote unique** : 2023-01 (335 pages, SHA-256 validé). Pas d'expansion
  avant validation qualité (Phase 11).

## 5. Stratégie de segmentation (Phase 6, post-OCR)

Signaux combinés : (1) la page de début de chaque décision vient de
`revue_index` (guide officiel) ; (2) marqueurs OCR (قرار رقم، لهذه
الأسباب…) ; (3) structure chambre/titres. `end_page = start_page(i+1) - 1`
hypothèse à **vérifier avec un offset** mesuré sur le pilote (la pagination
PDF peut différer de la pagination imprimée).

## 6. Stratégie de matching (Phase 7) — résultats

Numéros comparés sans zéros de tête. L1 numéro+année → MATCH_EXACT ;
L2 numéro+chambre, L3 numéro seul → MATCH_PROBABLE ; jamais de suppression
automatique, `sources` conserve la multi-provenance. Résultat sur les
5 704 entrées matchables du guide v4 : **176 MATCH_EXACT, 10
MATCH_PROBABLE, 5 518 NEW** (~3 % de chevauchement avec les 1 253 HTML —
la revue est un corpus massivement nouveau, 1989-2023).

## 7. Provenance (Phase 8)

RAW (PDF + raw_text) / PROCESSED (champs structurés) / ANONYMIZED (à
produire avant dataset — la revue imprimée publie probablement des noms
complets, contrairement au HTML en initiales : à vérifier sur le pilote
OCR). Chaque entrée : `source_pdf`, `source_page`, méthode d'extraction,
horodatage.

## 8. Limites connues

- 2 numéros absents du site (1994 n°04, 2023 n°02) ; historique 1989-2023
  en ligne seulement — avant 1989, physique.
- 987 entrées `partial` du guide = **entrées groupées** (plusieurs décisions
  partageant un principe) : les cellules multi-numéros devront être
  éclatées (alignement ligne-à-ligne numéro/chambre) à la Phase 6.
- 33 entrées `error` conservées avec raw_text pour re-traitement.
- L'encodage cassé des PDF rend la complétude du matching dépendante du
  guide uniquement — le texte OCR n'y est pas encore intégré.
