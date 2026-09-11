# Audit Exhaustif du Format A JORADP — Toutes Périodes FR (1962–2026) et AR (1964–2026)

> **Rapport de référence — Étape 2**  
> **Date** : 10 septembre 2026  
> **Source des données** : `Extraction/OCR-Fr/` et `Extraction/OCR-Ar/`  
> **Données quantitatives associées** : `reports/joradp_format_a_audit.json`

---

## 1. Rectification Majeure : Unicité du Format A

L'ancienne distinction technique opposant un « Format A » (OCR Mistral FR 1962–2001 / AR 1964–2026) à un « Format B » défaillant (extraction native FR 2002–2026 en tableau 2 colonnes) est **définitivement caduque**.

L'inspection physique du répertoire `Extraction/OCR-Fr/` montre que **toutes les années de 1962 à 2026** (notamment 2005, 2015, 2024) sont organisées selon la même architecture rigoureuse :
- Répertoire par numéro : `FR{année}{numéro}.pdf/`
- Fichier consolidé : `markdown.md`
- Sous-dossier de granularité par page : `pages/page-{N}/` contenant :
  - `markdown.md` (texte de la page)
  - `header.md` (en-tête de page isolé)
  - `page-metadata.json` (coordonnées polygonales et types de blocs)
  - `img-{N}.jpeg` (éventuels visuels / en-têtes)

Le pipeline est donc **100% harmonisé en Format A**. Aucune ré-extraction PDF ni aucun nouvel OCR n'est nécessaire.

---

## 2. Résultats de l'Échantillonnage Multi-Époques

Dix périodes clés ont été échantillonnées et analysées en profondeur (arabe et français, scans anciens et publications numériques récentes) :

| Échantillon | Chemin Testé | Lignes / Caractères | Sommaire | Actes Détectés | Articles Trouvés | Tables MD | Pages & Métadonnées |
|---|---|---|---|---|---|---|---|
| **FR 1962–1970** | `Extraction/OCR-Fr/1965/FR1965001.pdf` | 642 l. / 49 218 c. | ✅ Oui | 16 | 109 | 4 | 8 pages (`page-metadata.json` OK) |
| **FR 1980–1990** | `Extraction/OCR-Fr/1985/FR1985001.pdf` | 592 l. / 43 657 c. | ✅ Oui | 30 | 62 | 3 | 10 pages (`page-metadata.json` OK) |
| **FR 1995–2001** | `Extraction/OCR-Fr/1998/FR1998001.pdf` | 1 199 l. / 65 441 c. | ✅ Oui | 96 | 47 | 2 | 19 pages (`page-metadata.json` OK) |
| **FR 2002–2010** | `Extraction/OCR-Fr/2005/FR2005001.pdf` | 1 520 l. / 121 957 c. | ✅ Oui (`S O M M A I R E`) | 45 | 153 | 8 | 27 pages (`page-metadata.json` OK) |
| **FR 2011–2020** | `Extraction/OCR-Fr/2015/FR2015001.pdf` | 1 942 l. / 134 234 c. | ✅ Oui (`SOMMAIRE`) | 120 | 267 | 20 | 34 pages (`page-metadata.json` OK) |
| **FR 2021–2026** | `Extraction/OCR-Fr/2024/FR2024001.pdf` | 2 465 l. / 227 464 c. | ✅ Oui (`SOMMAIRE`) | 208 | 102 | 296 | 101 pages (`page-metadata.json` OK) |
| **AR 1964–1970** | `Extraction/OCR-Ar/1966/AR1966001.pdf` | 936 l. / 36 890 c. | ✅ Oui (`فهرس`) | 119 | 68 | 14 | 12 pages (`page-metadata.json` OK) |
| **AR 1980–1990** | `Extraction/OCR-Ar/1985/AR1985001.pdf` | 612 l. / 30 257 c. | ✅ Oui (`فهرس`) | 26 | 62 | 3 | 14 pages (`page-metadata.json` OK) |
| **AR 2000–2010** | `Extraction/OCR-Ar/2005/AR2005001.pdf` | 1 659 l. / 89 345 c. | ✅ Oui (`فهرس`) | 45 | 133 | 11 | 32 pages (`page-metadata.json` OK) |
| **AR 2020–2026** | `Extraction/OCR-Ar/2024/AR2024001.pdf` | 2 316 l. / 189 078 c. | ✅ Oui (`فهرس`) | 148 | 103 | 312 | 104 pages (`page-metadata.json` OK) |

---

## 3. Analyse Structurelle & Qualité Linguistique

### 3.1. Structure du Sommaire (Table des matières)
- Dans **10/10 échantillons**, la table des matières du Journal Officiel est fidèlement présente :
  - Français : `# SOMMAIRE`, `## SOMMAIRE`, `# S O M M A I R E` ou `# SOMMAIRE (suite)`.
  - Arabe : `## فهرس` ou `### فهرس`.
- Les entrées du sommaire listent les actes avec le numéro de page correspondant (`... 6`, `... 27`), ce qui offre un point d'ancrage fort pour la segmentation.

### 3.2. Hiérarchie des Actes Normatifs
- Les types d'actes sont identifiés avec précision :
  - Français : `Loi n°`, `Loi organique n°`, `Ordonnance n°`, `Décret présidentiel n°`, `Décret exécutif n°`, `Arrêté`, `Décision`.
  - Arabe : `قانون رقم`, `قانون عضوي رقم`, `أمر رقم`, `مرسوم رئاسي رقم`, `مرسوم تنفيذي رقم`, `قرار`, `مقرر`.
- Les dates sont rédigées avec double calendrier (Hégirien et Grégorien) :
  - *Exemple FR* : `du 18 Joumada Ethania 1445 correspondant au 31 décembre 2023`
  - *Exemple AR* : `في 18 جمادى الثانية عام 1445 الموافق 31 ديسمبر سنة 2023`

### 3.3. Découpage des Articles
- Les articles suivent des motifs réguliers et identifiables :
  - **Français** : `Article 1er.`, `Article 1.`, `Art. 1er.`, `Art. 2.`, `Article 2.`
  - **Arabe** : `المادة الأولى :`, `المادة 1 :`, `المادة 2 -`, `مادة 3` (avec chiffres arabes occidentaux `1, 2` ou orientaux `١, ٢` selon l'époque).
- Les subdivisions supérieures sont également balisées : `CHAPITRE Ier`, `SECTION 1`, `TITRE II`, `الباب الأول`, `الفصل الأول`, `القسم الأول`.

### 3.4. Tableaux Législatifs
- Les lois de finances, répartitions de crédits budgétaires et grilles indiciaires de salaires sont retranscrites sous forme de tableaux Markdown (`| ... | --- | ... |`).
- Les tableaux complexes sont particulièrement abondants dans les numéros récents (ex. 296 tableaux dans FR 2024 n°01 et 312 dans AR 2024 n°01).

---

## 4. Recommandations pour le Parser JORADP (Phase 7)

1. **Ne pas écraser le Markdown original** : les fichiers de `Extraction/` restent en lecture seule stricte (RAW).
2. **Double passage d'analyse** :
   - *Passage 1 (Sommaire)* : extraire la liste prévisionnelle des actes du numéro.
   - *Passage 2 (Corps du texte)* : segmenter chaque acte à partir des en-têtes et capturer l'ensemble de ses articles.
3. **Gestion des numéros de pages** : exploiter `header.md` pour éliminer le bruit des hauts de page répétés sans altérer les articles.
4. **Conservation bilingue étanche** : stocker chaque version dans sa langue (`fr` ou `ar`) avec un lien relationnel `language_pair` uniquement lorsque l'acte a été formellement apparié par son numéro et son année.
