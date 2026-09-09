# Conseil d'État — Reconnaissance du corpus

Document d'audit technique et de cartographie de la jurisprudence administrative algérienne, réalisé le 09/09/2026.

---

## 1. Résumé exécutif

Cette reconnaissance cartographie l'accessibilité, le volume, la structure et la qualité des décisions administratives du Conseil d'État algérien à travers trois sources cibles.

Les constats majeurs issus des sondes techniques réelles :
1. **Source officielle unique exploitable** : Le site officiel [`https://conseildetat.dz/`](https://conseildetat.dz/) (CMS Drupal 11) héberge l'intégralité du corpus public disponible.
2. **Portail du Ministère de la Justice ([`droit.mjustice.gov.dz`](https://droit.mjustice.gov.dz/fr))** : Ne dispose d'aucun moteur ni corpus propre pour le Conseil d'État ; sa rubrique redirige directement vers `conseildetat.dz`.
3. **Ancien domaine ([`conseil-etat-dz.org`](https://conseil-etat-dz.org/))** : Totalement décommissionné et abandonné (HTTP 404 sur hébergement OVH partagé, certificat invalide).
4. **Volume réel exact recensé** : **328 décisions** au total (324 fiches de jurisprudence standard + 4 arrêts sélectionnés) et **1 revue annuelle en PDF** (216 pages).
5. **Couverture temporelle** : 
   - **Corpus ordinaire de jurisprudence (324 arrêts)** : s'étend de **1998 à 2017** (aucun arrêt ordinaire publié pour 2018–2026).
   - **Arrêts sélectionnés (4 arrêts)** : 3 arrêts historiques (1998/2000, 2005, 2017) et **1 unique décision isolée du 19/12/2021** (Arrêt n° 214445 relatif au Conseil Supérieur de la Magistrature, NID 30).
   - Constat : Absence totale d'alimentation continue du site depuis 2018 (hormis cette décision isolée de 2021).
6. **Langue** : **100 % Arabe** (0 % Français). La justice administrative algérienne est rendue exclusivement en arabe.
7. **Format et structure** : Modèle hybride d'excellente qualité. Chaque fiche HTML fournit des métadonnées structurées avec le **principe juridique (*Mabda*) en clair (100 %)** et un **PDF de l'arrêt intégral (100 %)** (scans administratifs nécessitant un OCR pour le texte complet de l'arrêt).

---

## 2. Sources étudiées

Trois sources ont été inspectées via sondes réseau HTTP/TLS dédiées :
1. **Portail du Droit Algérien (Ministère de la Justice)** : [`https://droit.mjustice.gov.dz/fr`](https://droit.mjustice.gov.dz/fr) et version `/ar`.
2. **Site officiel du Conseil d'État** : [`https://conseildetat.dz/`](https://conseildetat.dz/) (et sous-domaines/chemins associés).
3. **Ancien domaine historique** : [`https://conseil-etat-dz.org/`](https://conseil-etat-dz.org/).

---

## 3. Portail du Droit Algérien

* **URL cible** : [`https://droit.mjustice.gov.dz/fr`](https://droit.mjustice.gov.dz/fr) et [`https://droit.mjustice.gov.dz/ar`](https://droit.mjustice.gov.dz/ar)
* **Status HTTP** : 200 OK (Drupal 7).
* **Rubrique « Jurisprudence > Conseil d'État »** :
  * Lien FR : pointe vers `https://www.conseildetat.dz/fr/documentations/publications/magazines-ce`
  * Lien AR : pointe vers `https://www.conseildetat.dz/ar/الإجتهاد-القضائي/الوثائق`
* **Constat technique** : Le portail du Ministère de la Justice **ne stocke aucune décision du Conseil d'État dans ses propres tables**. Il agit comme un annuaire de liens hypertextes vers `conseildetat.dz`. Les seuls moteurs internes sur `droit.mjustice.gov.dz` concernent les cours d'appel ordinaires (chambres commerciale et sociale).
* **API / Endpoints** : Aucun endpoint API pour le Conseil d'État sur ce domaine.

---

## 4. Site officiel conseildetat.dz

* **URL cible** : [`https://conseildetat.dz/`](https://conseildetat.dz/) (Serveur Apache, Drupal 11).
* **Navigation et rubriques identifiées** :
  * `الإجتهاد القضائي` (`/ar/الإجتهاد-القضائي` ou `/ar/الإجتهاد-القضائي/الوثائق`) : Vue de recherche avec filtres exposés Drupal (`field_chamber_juris_value`, `field_sect_jurisp_value`, `field_adapt_juris_value`, `field_sujet_value`, dates).
  * `القرارات المختارة` (`/ar/القرارات-المختارة`) : Rubrique des arrêts sélectionnés (NIDs 30, 367, 368, 369).
  * `مجلات مجلس الدولة` (`/ar/مجلات-مجلس-الدولة`) : Publications PDF (`/sites/default/files/magazines_pdf/`).
  * `فهرس المكتبة` (`/ar/فهرس-المكتبة`) : Fiches bibliographiques d'ouvrages (NIDs 387+).
* **Comportement des vues Drupal et pagination** :
  * La vue exposed `/ar/الإجتهاد-القضائي` n'affiche aucun listing par défaut sans paramètre et la pagination AJAX standard n'expose pas de flux continu.
  * Cependant, l'ensemble des contenus est directement et exhaustivement accessible via les nœuds canoniques `/node/{nid}`.
* **Recensement complet des nœuds Drupal** :
  * 561 nœuds existants (scannés jusqu'à NID 625, arrêt après 40 codes 404 consécutifs).
  * **324 nœuds de type `jurisprudence`**.
  * **4 nœuds de type `arrets-selectionnes`**.
  * **1 nœud de type `publications-revue`** (Revue n° 13 - 2015, 216 pages).
  * 138 fiches de bibliothèque (`index-bibliotheque`), 49 tribunaux (`geo-map`), 20 pages institutionnelles, 11 textes de lois.
  * 10 actualités (`actualites`), 2 albums photos (`album-photos`), 2 publications/mises à jour (`lmnshwrt-lmhdrt`).
  * **Total vérifié** : 324 + 4 + 1 + 138 + 49 + 20 + 11 + 10 + 2 + 2 = **561 nœuds** ✅ (aucune jurisprudence cachée dans les 14 nœuds non comptabilisés initialement).

---

## 5. Ancien domaine conseil-etat-dz.org

* **URL cible** : [`https://conseil-etat-dz.org/`](https://conseil-etat-dz.org/)
* **Résolution DNS** : IP `213.186.33.4` (Hébergement mutualisé OVHcloud).
* **Réponse HTTP & HTTPS** : **HTTP 404** direct (`<title>Site not installed - OVHcloud</title>`).
* **Certificat TLS** : Invalide (CN mismatch).
* **Statut d'exploitation** : **Source morte / abandonnée**. Aucune décision historique n'est récupérable sur ce domaine.

---

## 6. Robots.txt et contraintes techniques

### A. [`https://droit.mjustice.gov.dz/robots.txt`](https://droit.mjustice.gov.dz/robots.txt)
* Fichier standard Drupal 7.
* `User-agent: *` avec `Crawl-delay: 10`.
* `Disallow` sur les répertoires d'administration et de gestion de compte (`/admin/`, `/comment/`, `/search/`, `/user/`).

### B. [`https://conseildetat.dz/robots.txt`](https://conseildetat.dz/robots.txt)
* Fichier standard Drupal 11.
* `User-agent: *`.
* `Disallow` sur `/admin/`, `/core/`, `/search/`, `/user/`.
* Les chemins de contenu `/node/`, `/ar/`, `/sites/default/files/` sont **parfaitement autorisés**.

### C. Protections et contraintes observées
* **Aucun CAPTCHA** rencontré.
* **Aucune authentification requise** pour les décisions publiques.
* **Aucun WAF agressif (Cloudflare, Incapsula)** bloquant les requêtes respectueuses.
* **Contrainte de politesse** : Imposer un délai minimal de **2 secondes** entre les requêtes, avec User-Agent explicite et client TLS compatible (OpenSSL legacy renegotiation).

---

## 7. Structure des décisions

Chaque décision sur `conseildetat.dz` (`node--type-jurisprudence`) présente une structure remarquablement constante et propre :

```
<article class="jurisprudence full clearfix">
  ├── field--name-field-numm-arr       (Numéro de décision)
  ├── field--name-field-date-arr       (Date de décision)
  ├── field--name-field-chamber-juris  (Chambre)
  ├── field--name-field-sect-jurisp    (Section)
  ├── field--name-field-keywords-juris (Mots-clés)
  ├── field--name-field-adapt-juris    (Classification / Tkayyuf)
  ├── field--name-field-sujet          (Objet / Sujet)
  ├── field--name-field-princ-arret    (Principe juridique / Mabda)
  └── field--name-field-details-arret  (Fichier PDF complet attaché)
```

Exemple réel observé (Nœud #61) :
* **Numéro** : `081422`
* **Date** : `10 septembre 2015`
* **Chambre** : `الغرفة الأولى` (1ère Chambre)
* **Section** : `القسم الثاني` (2ème Section)
* **Mots-clés** : `حق الشفعة- جمعية أسقفية جزائرية- أملاك وطنية`
* **Classification** : `سكنات`
* **Sujet** : `حق الشفعة`
* **Principe (*Mabda*)** : 
  > أعضاء الجمعية الأسقفية الجزائرية، جزائريو الجنسية، غير مطالبين بتقديم رخصة لبيع أملاكهم. لا يحق للوالي ممارسة حق الشفعة، بعد مرور (5) سنوات من تسجيل عقد البيع وموافقة المديرية العامة للأملاك الوطنية (وزارة المالية) على البيع.
* **PDF attaché** : [`https://conseildetat.dz/sites/default/files/jurisp_file/arretn081422.pdf`](https://conseildetat.dz/sites/default/files/jurisp_file/arretn081422.pdf)

---

## 8. Volume et période

### A. Volume exact accessible
* **Total des décisions individuelles** : **328 décisions** (324 standard + 4 sélectionnées).
* **Publications périodiques** : 1 revue complète de 216 pages (`revuen-13-2015.pdf`).

### B. Distribution temporelle (1998–2017)
Le Conseil d'État a été installé en 1998 (succédant à la Chambre administrative de la Cour suprême). La distribution des 324 décisions standard par année est la suivante :

| Année | Décisions | Année | Décisions |
|:---:|:---:|:---:|:---:|
| **1998** | 2 | **2008** | 9 |
| **1999** | 4 | **2009** | 11 |
| **2000** | 3 | **2010** | 22 |
| **2001** | 12 | **2011** | 35 |
| **2002** | 21 | **2012** | 24 |
| **2003** | 30 | **2013** | 28 |
| **2004** | 20 | **2014** | 27 |
| **2005** | 17 | **2015** | 22 |
| **2006** | 10 | **2016** | 10 |
| **2007** | 14 | **2017** | 3 |

*Observation* : Comme pour la Cour suprême, ce volume de 328 décisions représente un **recueil d'arrêts de principe sélectionnés**, et non l'intégralité du greffe contentieux.

### C. Répartition par chambre
* **2ème Chambre (الغرفة الثانية)** : 84 décisions (25,9 %)
* **3ème Chambre (الغرفة الثالثة)** : 69 décisions (21,3 %)
* **4ème Chambre (الغرفة الرابعة)** : 62 décisions (19,1 %)
* **1ère Chambre (الغرفة الأولى)** : 54 décisions (16,7 %)
* **5ème Chambre (الغرفة الخامسة)** : 48 décisions (14,8 %)
* **Chambres réunies (الغرف مجتمعة)** : 7 décisions (2,2 %)

---

## 9. Langues

* **Arabe (AR)** : **100 % du corpus de décisions**.
* **Français (FR)** : **0 % des décisions judiciaires**. 
  * La version française du site (`/fr`) ne contient que des pages d'accueil et des actualités institutionnelles.
  * Les arrêts et principes juridiques administratifs sont rédigés exclusivement en langue arabe, conformément au Code de procédure civile et administrative (Loi 08-09).

---

## 10. HTML / PDF / OCR

Le corpus présente une complémentarité HTML / PDF :
1. **HTML (Fiche de synthèse)** :
   * Métadonnées complètes + **Principe juridique (*Mabda*) en texte natif propre**.
   * Extraction directe sans OCR.
2. **PDF attachés (`/sites/default/files/jurisp_file/arretnXXXXXX.pdf`)** :
   * **100 % des décisions** ont un PDF attaché.
   * Analyse des PDF : **Scans de documents dactylographiés/imprimés originaux** (tampons, signatures des magistrats).
   * **Nécessité de l'OCR** : Oui, si l'on souhaite extraire le texte intégral des motifs et du dispositif détaillé (phase ultérieure avec pipeline OCR arabe type Mistral OCR).

---

## 11. Métadonnées disponibles

Pour les 324 décisions de jurisprudence standard :
* **Numéro de décision** : 324 / 324 (**100 %**)
* **Date de l'audience / prononcé** : 324 / 324 (**100 %**)
* **Chambre** : 324 / 324 (**100 %**)
* **Section** : 186 / 324 (**57,4 %**)
* **Mots-clés** : 324 / 324 (**100 %**)
* **Classification (*Tkayyuf*)** : 324 / 324 (**100 %**)
* **Sujet / Thématique** : 324 / 324 (**100 %**)
* **Principe juridique (*Mabda*)** : 324 / 324 (**100 %**)
* **URL du PDF source** : 324 / 324 (**100 %**)

---

## 12. Doublons et recouvrement entre sources

* **Recouvrement entre sources** : Nul. `droit.mjustice.gov.dz` renvoie vers `conseildetat.dz`, et `conseil-etat-dz.org` est éteint. `conseildetat.dz` est la **source primaire unique**.
* **Doublons internes sur `conseildetat.dz`** :
  * 3 numéros de décisions apparaissent 2 fois dans des nœuds différents (ex: NID 74 et NID 76 pour le numéro 094209). Une clé de déduplication composite `(decision_number, date)` ou par `nid` garantit l'unicité.
* **Différence entre « Jurisprudence » et « Arrêts sélectionnés »** :
  * `jurisprudence` (324 nœuds) : décisions de chambres ordinaires avec fiche standardisée.
  * `arrets-selectionnes` (4 nœuds) : arrêts solennels majeurs (notamment recours contre le Conseil Supérieur de la Magistrature ou arrêts des chambres réunies).

---

## 13. Données personnelles / anonymisation

* **Niveau HTML (Métadonnées & Principes)** : Totalement anonymisé. Les principes juridiques ne contiennent que des formulations abstraites de règles de droit.
* **Niveau PDF intégral** : Les décisions numérisées mentionnent les parties publiques (personnes morales : ministères, walis, communes, établissements publics) et parfois les noms ou initiales de particuliers requérants.
* **Recommandation** : Appliquer la même politique que pour la Cour suprême :
  1. *RAW* : PDF et HTML originaux conservés sans altération.
  2. *PROCESSED* : Métadonnées et principes extraits fidèlement.
  3. *ANONYMIZED* : Masquage systématique des noms de personnes physiques lors de la génération du dataset d'entraînement.

---

## 14. Faisabilité du scraping

* **Accessibilité technique** : **Excellente (100 %)**.
* **Mode d'extraction optimal** : Parcours séquentiel des nœuds `/node/{nid}` de 25 à 380, direct et déterministe, sans dépendre du moteur de recherche ou de la pagination frontale.
* **Temps estimé de collecte** : À raison d'une requête toutes les 2 secondes (politesse serveur), la collecte complète des 328 fiches HTML et métadonnées prend moins de **12 minutes**. Le téléchargement des 328 PDF associés (~50 Mo au total) prend environ **15 minutes**.

---

## 15. Qualité potentielle pour le dataset

| Critère | Note / 5 | Commentaire |
|---|:---:|---|
| **1. Autorité de la source** | 5/5 | Juridiction suprême de l'ordre administratif algérien. |
| **2. Accessibilité** | 5/5 | Pages publiques sans anti-bot ni CAPTCHA. |
| **3. Volume** | 3/5 | Échantillon compact (328 décisions) de haute valeur qualitative. |
| **4. Période couverte** | 3/5 | 1998–2017 (20 ans de recul historique, manque 2018–2026). |
| **5. Structure des données** | 5/5 | Structure Drupal rigoureuse avec 100 % de principes en clair. |
| **6. Qualité textuelle** | 5/5 | Textes HTML propres, diacritiques légers, vocabulaire juridique standard. |
| **7. Métadonnées** | 5/5 | 9 champs normalisés (chambre, section, sujet, mots-clés, date, etc.). |
| **8. Facilité d'extraction** | 5/5 | Nœuds REST/HTML prédictibles et légers. |
| **9. Risque de doublons** | 5/5 | Très faible, déduplication simple par numéro et NID. |
| **10. Données personnelles** | 4/5 | Principes HTML déjà anonymisés, PDF à traiter avec précaution. |
| **11. Valeur pour fine-tuning** | 5/5 | Paires *(Faits/Questions juridiques → Principe de droit administratif)* idéales pour l'instruction tuning. |

---

## 16. Limitations

1. **Volume modéré (328 décisions)** : Ce corpus ne constitue pas un registre exhaustif de tous les arrêts rendus depuis 1998, mais la sélection officielle des arrêts faisant jurisprudence.
2. **Trou temporel post-2017** : Le site n'a pas publié de nouvelles décisions de chambres pour la période 2018–2026.
3. **OCR requis pour les PDF intégraux** : Les PDF attachés sont des scans d'archives.
4. **Monolinguisme arabe** : Le corpus administratif est 100 % en langue arabe.

---

## 17. Recommandation

* **VERDICT** : **`SCRAPABLE`**
* Le corpus du Conseil d'État est immédiatement exploitable, parfaitement délimité, léger et d'une valeur doctrinale très élevée pour le futur modèle juridique.

---

## 18. Proposition de prochaine étape

1. **Créer le scraper Conseil d'État sous `sources/conseildetat/`** :
   * `discover.py` : indexation des 328 nœuds et extraction des métadonnées structurées.
   * `storage.py` : persistance SQLite dans `databases/conseildetat.db`.
   * `downloader.py` : téléchargement optionnel et vérification SHA-256 des 328 PDF attachés.
2. **Générer le rapport de qualité initial** sous `reports/conseildetat_quality_report.json`.

---

## 19. Tableau de synthèse

| Source | Accessible | Format | Pagination | Volume | Période | Langues | Métadonnées | Structure | Doublons | Scraping |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Portail Droit (mjustice)** | YES | Liens / HTML | N/A | 0 (Redir) | N/A | FR / AR | PARTIAL | Redirection | N/A | NO (Redirige) |
| **conseildetat.dz** | YES | HTML + PDF | YES (`/node/`) | **328 arrêts** | 1998–2017 | **AR (100%)** | **YES (100%)** | **EXCELLENT** | LOW (<1%) | **YES** |
| **conseil-etat-dz.org** | NO | Inaccessible (404) | NO | 0 | Inconnu | Inconnu | NO | Abandonné | N/A | **NO** |

---

## 20. Réponses aux questions d'orientation

1. **Quelle source doit être scrapée en premier ?**
   * **`conseildetat.dz`** : C'est la seule et unique source primaire active détenant les données.
2. **Quelle source doit être conservée uniquement comme archive historique/complémentaire ?**
   * Aucune : `conseil-etat-dz.org` est mort et `droit.mjustice.gov.dz` redirige vers la source principale.
3. **Quel est le volume estimé réellement accessible ?**
   * **328 décisions individuelles** (324 standard + 4 sélectionnées) et **1 revue de 216 pages**.
4. **Faut-il créer un scraper HTML, PDF ou les deux ?**
   * **Les deux en 2 temps** : Scraper HTML pour capturer les 9 champs de métadonnées et les 328 principes juridiques textuels, puis un downloader PDF pour archiver les pièces justificatives intégrales.
5. **Faut-il prévoir l'OCR ?**
   * **Optionnel pour les fiches HTML** (les principes *Mabda* sont déjà en texte numérique natif à 100 %).
   * **Requis pour exploiter le corps complet des PDF attachés** (scans d'archives).
6. **Comment éviter les doublons ?**
   * Clé primaire SQLite sur `source_url` (ou `nid`) et contrainte d'unicité composite sur `(decision_number, date)`.
7. **Quelle stratégie d'anonymisation utiliser ?**
   * Les textes HTML des principes juridiques sont déjà anonymisés à la source. Pour les PDF complets (si OCRisés plus tard), appliquer un masquage NER sur les entités de personnes physiques requérantes.
