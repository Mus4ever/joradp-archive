# Source : Cour suprême d'Algérie (coursupreme.dz)

Document de référence du scraper `sources/coursupreme/`. Tous les constats
ci-dessous ont été **vérifiés sur le HTML réel** le 09/09/2026 (fixtures dans
`sources/coursupreme/fixtures/`).

## 1. Source et périmètre

- Site officiel : https://coursupreme.dz (WordPress, arabe uniquement).
- Contenu utile : pages de décisions individuelles, HTML intégral —
  **aucun OCR nécessaire** pour cette source.
- Volumétrie réelle constatée (parcours complet de la pagination) :
  **1 253 décisions uniques**. La catégorie « قرارات-مصنفة-حسب-المواضيع »
  (décisions classées par thèmes) est un sur-ensemble : les autres catégories
  n'ajoutent aucune URL nouvelle.

## 2. Pages de listing (URLs exactes)

| Catégorie | Slug | Pages | Uniques |
|---|---|---:|---:|
| Décisions par thèmes | `/قرارات-مصنفة-حسب-المواضيع/` | 18 | 1253 |
| Chambres pénales | `/الغرف-الجزائية/` | 10 | 389 |
| Chambres civiles | `/الغرف-المدنية/` | 19 | 805 |
| Commission d'indemnisation | `/لجنة-التعويض/` | 3 | 35 |
| Chambres réunies | `/الغرف-المجتمعة/` | 1 | 7 |
| Décisions importantes | `/قرارات-مهمة/` | 2 | 25 |

## 3. Pagination

- Liens annoncés par le site : `?paged=N` → répond **301** (le client ne
  suit pas les redirections).
- Format canonique utilisé : **`/page/N/`** → HTTP 200 direct.
- Dernière page lue dans `div.pagination > ul.page-numbers` (aucun probing).
- Arrêt de sécurité : une page qui liste 0 décision stoppe la catégorie.

## 4. Structure d'une décision (`/decision/<slug>/`)

- `<article class="decision type-decision status-publish <taxonomie>-N">`
  → chambre déduite de la classe taxonomie :
  `civil-chambers-*`, `criminal-chambers-*`, `compensation-committee-*`,
  `significant-decisions-*`, `joint-chambers-*`.
- `div.entry-content` contient :
  1. un `<ul>` de métadonnées `<li>` « label: valeur » :
     رقم القرار (numéro), تاريخ القرار (date AAAA/MM/JJ), الموضوع (sujet),
     الأطراف (parties), الكلمات الأساسية (mots-clés, optionnel),
     المرجع القانوني (référence légale, optionnel) ;
  2. des sections `<li><h5>label</h5><p>contenu</p></li>` :
     المبدأ (principe), وجه الطعن (moyen du pourvoi),
     رد المحكمة العليا (réponse de la Cour), منطوق القرار (dispositif),
     الرئيس / المستشار المقرر / أمين الضبط (magistrats).
- **Variante « قرارات مهمة »** (décisions importantes) : sections
  أوجه الدفع بعدم الدستورية / رد المحكمة عن أوجه الدفع au lieu du trio
  principe/moyen/réponse ; le `<li>` « réponse » peut être vide et le texte
  vivre dans un `<p>` orphelin entre deux `h5` — le parser applique un repli
  sur l'ordre du document (collecte des `<p>` entre le `h5` courant et le
  suivant, sans sortir du conteneur).
- Sections réellement vides à la source (h5 sans contenu) → champ `NULL`,
  comptées par le rapport qualité.

## 5. Méthode de découverte

`discover.py` : parcours de chaque catégorie page par page (`/page/N/`),
extraction des `href` contenant `/decision/`, normalisation URL (query et
fragment retirés, slash final) = clé de déduplication, insertion
`INSERT OR IGNORE` sur `source_url` UNIQUE.

## 6. Schéma de données

Table `decisions` (`storage.py`) : un enregistrement par décision avec
métadonnées, sections, texte intégral, `source_url`, `content_hash`
(SHA-256 du HTML brut), `raw_path` (HTML brut conservé sous `raw/coursupreme/`),
`discovered_at`/`downloaded_at`, `status` (`decouvert`/`telecharge`/`erreur`),
`error`. Base : `databases/coursupreme.db`.

## 7. Rate limiting et politesse

- Client HTTP JORADP réutilisé (`tools/http_client.py`) : limiteur global
  thread-safe, **2 s minimum entre requêtes**, 3 tentatives avec backoff
  exponentiel.
- User-Agent explicite : `AlgerianLegalCorpusBot/0.1 (academic legal
  research; polite crawler)`.
- Séquentiel, 1 worker. Interruption possible à tout moment : reprise
  intégrale au prochain lancement (statuts SQLite).

## 8. robots.txt

```
User-agent: ChatGPT-User
Disallow: /
```

Seul l'agent `ChatGPT-User` est interdit. Aucune règle ne s'applique à
notre User-Agent explicite. Aucune protection anti-bot, CAPTCHA ou
authentification rencontrée sur les pages publiques. Le scraper ne
contourne rien : il ne collecte que des pages publiquement listées.

## 9. Anonymisation / données personnelles

- Constat sur l'échantillon réel : la Cour publie les parties sous forme
  d'**initiales** — « الطاعن: (س.س) / المطعون ضده: … ». Les noms des
  magistrats (président, rapporteur, greffier) sont publics par fonction.
- Politique à trois niveaux (conformément au plan projet) :
  - **RAW** : HTML brut conservé intact sous `raw/coursupreme/` (jamais
    modifié ni supprimé automatiquement) — provenance et audit ;
  - **PROCESSED** : champs structurés en base (texte nettoyé, fidèle) ;
  - **ANONYMIZED** : à produire au moment du dataset IA — les champs
    `parties` et `text` seront re-vérifiés (adresses, identifiants,
    mineurs) avant tout entraînement ; l'anonymisation à la source n'est
    **pas considérée comme une garantie suffisante**.

## 10. Limites connues

- **Couverture temporelle très inégale** (constat sur les 1 253 décisions,
  septembre 2026) : de 1979 à 2023, mais concentrée sur 2015-2021
  (2015: 119, 2016: 273, 2017: 191, 2018: 325, 2019: 41, 2020: 101,
  2021: 101, 2022: 28, 2023: 31) ; moins de 25 décisions avant 2014.
  1 253 décisions HTML = un échantillon, pas l'historique complet de la
  jurisprudence. Le canal de la profondeur historique reste les **revues
  de la Cour suprême** (PDF téléchargeables, annoncées 1989-2019 sur le
  portail du ministère de la Justice) — source séparée, hors périmètre
  de ce scraper. Contrairement à une information antérieure, le site
  publie bien des décisions post-2020 en HTML (261 décisions 2020-2023).
- Le champ `decision_number` mélange numéros de dossier (ex. 1040786) et
  numéros de décision (ex. 01) selon les catégories — conservé tel quel ;
  les numéros « importants » (01-06…) se répètent par année.
- `legal_references` absent pour 40/1253 (3,2 %) : vérifié dans le HTML
  brut, le libellé المرجع القانوني n'est pas publié par le site pour ces
  décisions (défaillance de la source, pas du parser). 17/40 citent
  malgré tout des articles dans les motifs — récupérables en phase
  dataset par extraction depuis le texte. Globalement, 1 168/1253
  décisions (93 %) mentionnent au moins un article de loi.
- Site monolingue arabe : la dimension FR viendra d'autres sources.

## 11. Procédure d'exécution

```powershell
# découverte uniquement (listings + pagination)
python sources/coursupreme/discover.py

# prototype (20 décisions)
python sources/coursupreme/scraper.py --limit 20

# pilote (500) puis suite — reprise automatique après interruption
python sources/coursupreme/scraper.py --limit 500

# rapport qualité
python sources/coursupreme/rapport_qualite.py
```

## 12. Tests

`tests/test_coursupreme.py` — 19 tests hors ligne (aucun réseau) sur
fixtures HTML réelles : parser standard/variante/champs manquants/page non
décision, normalisation (espaces, dates, numéros, arabe), URLs et
déduplication, pagination, stockage SQLite (découverte, doublons, erreurs,
reprise).
