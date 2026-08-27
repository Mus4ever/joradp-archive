# MISSION — DIAGNOSTIC ET DÉBLOCAGE DE LA PHASE 4
## Corpus juridique algérien — JORADP — Extraction PDF arabe/français

Tu es un agent expert en :

- extraction de texte PDF ;
- PyMuPDF / MuPDF ;
- PDF text layer, glyphs et ToUnicode ;
- document layout analysis ;
- lecture RTL arabe ;
- documents multi-colonnes ;
- OCR arabe/français ;
- qualité des corpus juridiques ;
- pipelines d'ingestion à grande échelle ;
- validation expérimentale de systèmes d'extraction.

Ta mission n'est **PAS** de lancer immédiatement l'extraction des 10 432 PDF.

Ta mission est d'abord de comprendre le problème actuel, d'identifier sa
cause réelle et de définir puis valider la stratégie d'extraction correcte
avant toute extraction massive.

---

## 1. CONTEXTE DU PROJET

Le projet consiste à constituer un corpus du Journal Officiel algérien (JORADP).

Corpus actuellement téléchargé :

- environ 10 432 sources ;
- PDF déjà téléchargés localement ;
- FR : 1962–2026 ;
- AR : 1964–2026 ;
- les PDF originaux sont conservés ;
- SHA-256 calculé ;
- état des sources suivi dans SQLite.

La Phase 3 de téléchargement est **TERMINÉE**.

IMPORTANT :

Le problème actuel ne concerne **PAS** le scraping ni le téléchargement.

Le problème concerne UNIQUEMENT la Phase 4 :

```text
PDF local
    ↓
extraction de texte natif
    ↓
texte exploitable
```

---

## 2. OBJECTIF DE LA PHASE 4

Pour chaque page PDF :

1. déterminer si un texte natif exploitable existe ;
2. extraire le texte page par page ;
3. identifier les pages nécessitant OCR ;
4. préserver l'ordre logique du document ;
5. gérer correctement les documents arabes RTL ;
6. gérer les contenus mixtes arabe + latin + nombres ;
7. stocker le résultat dans SQLite ;
8. ne jamais inventer, corriger ou reformuler le texte juridique.

Aucun LLM ne doit être utilisé pour « reconstruire » un texte juridique
illisible ou manquant.

---

## 3. LE PROBLÈME DÉCOUVERT

Un exemple concret est le PDF arabe :

```text
AR 2007-019
```

La page visuelle contient un texte arabe parfaitement lisible.

Mais l'extraction PyMuPDF par défaut produit une sortie du type :

```text
19 ﺔ / اﻟﻌﺪد ...
...
اﺗﻔﺎﻗﻴﺔ اﻧﺸﺎء
اﺗﻔﺎﻗﻴﺔ اﻧﺸﺎء
...
ـﺆﺗﻤﺮH...
...
pاﻟﺪول...
```

On observe :

- répétitions ;
- fragments de caractères ;
- caractères parasites ;
- morceaux de mots ;
- ordre des blocs incohérent ;
- ordre des colonnes potentiellement incorrect ;
- texte techniquement présent mais pas forcément exploitable.

Le problème est donc plus large que « RTL ».

---

## 4. CE QUI A DÉJÀ ÉTÉ TESTÉ

Sur 10 PDF problématiques, plusieurs méthodes PyMuPDF ont été comparées :

1. `page.get_text()`
2. `page.get_text("blocks")`
3. `page.get_text("words")`
4. `page.get_text("dict")`
5. `page.get_text(sort=True)`

Constats :

- plusieurs PDF ont un fort problème d'ordre des blocs ;
- certains textes contiennent des duplications ;
- certains PDF contiennent des caractères apparemment mal mappés ;
- 2/10 PDF testés sont des scans et semblent nécessiter OCR ;
- `get_text("dict")` a échoué dans les tests effectués ;
- `get_text("blocks")` expose les coordonnées des blocs ;
- le simple `get_text()` n'est pas fiable comme unique méthode de référence
  pour certains PDF arabes.

Les résultats ont montré de très faibles similarités entre certaines sorties
de méthodes, mais ces similarités ne doivent **PAS** être considérées comme
une mesure suffisante de qualité linguistique.

---

## 5. HYPOTHÈSE ACTUELLE — À NE PAS PRENDRE COMME FAIT

L'hypothèse actuelle est qu'une partie du problème vient de :

```text
mauvais ordre des blocs / colonnes RTL
```

et qu'une autre partie peut venir de :

```text
problème de mapping de caractères / font / ToUnicode
```

Il faut distinguer ces deux phénomènes.

IMPORTANT :

Ne pars **PAS** du principe que tout problème visible est causé par le RTL.

Tu dois déterminer expérimentalement la cause.

---

## 6. PROTOTYPE DÉJÀ IMPLÉMENTÉ

Un prototype nommé :

```text
rtl_block_ordering.py
```

a été développé.

Principe actuel :

1. extraction des blocs avec coordonnées ;
2. classement vertical par Y ;
3. classement horizontal RTL par X ;
4. détection approximative des colonnes ;
5. ordre des colonnes de droite vers la gauche.

Le prototype a été testé notamment sur :

- AR 2007-003
- AR 2007-016
- AR 2007-034
- AR 2018-072
- AR 2012-001

Résultats rapportés :

- AR 2007-003 : 73 blocks, 51 lines, 3405 chars
- AR 2007-016 : 73 blocks, 43 lines, 3927 chars
- AR 2007-034 : 60 blocks, 48 lines, 2232 chars
- AR 2018-072 : 81 blocks, 57 lines, 2856 chars
- AR 2012-001 : 81 blocks, 62 lines, 4890 chars

Mais ce prototype n'est **PAS** encore validé définitivement.

---

## 7. VALIDATION RTL DÉJÀ EFFECTUÉE

Une validation sur 25 PDF arabes a été préparée.

Répartition :

- 1964–1993 : 8 ;
- 1994–2009 : 9 ;
- 2010–2026 : 8.

Le rapport actuel donne :

- PASS : 22 ;
- FAIL : 0 ;
- REVIEW_REQUIRED : 3.

Cependant, cette validation a révélé des problèmes supplémentaires.

Exemple important :

### AR 2005-042

- Arabic characters = 0 ;
- Latin characters = 1034 ;
- Numbers = 203 ;
- verdict automatique = PASS.

Mais le texte extrait affiché est manifestement corrompu/illisible.

### AR 2008-001

Présente aussi des fragments et caractères suspects.

De nombreux PDF historiques ont été classés PASS alors que :

```text
Arabic characters = 0
```

Cela signifie que le système de validation précédent est trop permissif.

### CONCLUSION

```text
0 alertes RTL
```

ne signifie **PAS** :

```text
extraction correcte
```

---

## 8. PROBLÈME ACTUEL À RÉSOUDRE

Nous devons maintenant distinguer quatre situations :

### A. PDF avec couche texte native réellement exploitable

```text
PDF
 ↓
native text
 ↓
correct
 ↓
conserver
```

### B. PDF scanné / aucune couche texte exploitable

```text
PDF
 ↓
pas de texte natif
 ↓
NEEDS_OCR
```

### C. PDF contenant une couche texte mais avec mapping de caractères défectueux

```text
PDF
 ↓
texte natif présent
 ↓
caractères incorrects
 ↓
NEEDS_REVIEW ou OCR
```

### D. PDF avec caractères corrects mais ordre de blocs incorrect

```text
PDF
 ↓
texte natif
 ↓
blocs mal ordonnés
 ↓
reconstruction layout/RTL
```

Une même page peut potentiellement combiner plusieurs difficultés.

---

## 9. PROBLÈME PARTICULIER DES PDF ARABES

Les PDF arabes peuvent contenir :

- arabe ;
- chiffres ;
- lettres latines ;
- noms propres ;
- termes techniques ;
- références ;
- sociétés ;
- autres fragments latins légitimes.

Donc :

```text
présence de caractères latins
≠
erreur RTL
```

Une heuristique qui déclenche une alerte simplement parce qu'une ligne
latine apparaît dans un contexte arabe est insuffisante.

---

## 10. CONTRAINTE CRITIQUE

**NE LANCE PAS LES 10 432 PDF.**

**NE FAIS PAS D'EXTRACTION MASSIVE.**

Nous voulons d'abord une validation expérimentale solide.

---

## 11. TA PREMIÈRE MISSION

Commence par analyser le problème sur un petit échantillon contrôlé.

Utilise au minimum ces documents déjà problématiques :

- AR 2007-003
- AR 2007-016
- AR 2007-034
- AR 2018-072
- AR 2012-001
- AR 2007-019
- AR 2005-042
- AR 2008-001

Puis ajoute 2 PDF scanners connus.

Total minimal :

```text
10 PDF
```

---

## 12. POUR CHAQUE PAGE TESTÉE

Produis :

1. rendu visuel de la page ;
2. `page.get_text()` ;
3. `page.get_text("blocks")` ;
4. `page.get_text("words")` ;
5. `page.get_text(sort=True)` ;
6. méthode alternative native si utile ;
7. résultat du prototype RTL ;
8. diagnostic de cause.

Pour chaque résultat, distingue :

- qualité des caractères ;
- duplication ;
- ordre des blocs ;
- ordre des colonnes ;
- ordre des articles ;
- mélange des langues ;
- structure de la page.

---

## 13. POINT CRITIQUE : CHARACTER MAPPING

Tu dois vérifier si des caractères comme :

```text
H
r
p
W
```

ou d'autres fragments suspects viennent de :

- mauvais mapping Unicode ;
- police PDF ;
- ToUnicode absent/corrompu ;
- glyphs ;
- extraction MuPDF ;
- structure du document.

Ne conclus **PAS** automatiquement que le tri RTL peut résoudre ces
problèmes.

Si le caractère lui-même est faux, réordonner les blocs ne suffit pas.

---

## 14. POINT CRITIQUE : BLOCK ORDERING

Pour les cas où les caractères sont corrects mais l'ordre est incorrect :

analyse :

- coordonnées X/Y ;
- blocs ;
- lignes ;
- colonnes ;
- direction RTL ;
- ordre vertical ;
- espaces entre colonnes.

Teste le prototype de reconstruction.

Compare le résultat visuellement au PDF.

---

## 15. POINT CRITIQUE : OCR

Pour les pages sans texte natif exploitable :

```text
NEEDS_OCR
```

Pour les pages dont le texte natif existe mais semble irrécupérable à cause
du mapping des caractères :

teste si une autre méthode native permet de récupérer correctement les
caractères.

Si aucune méthode native fiable ne fonctionne :

```text
NEEDS_OCR
```

ou :

```text
NEEDS_REVIEW
```

Ne jamais inventer le texte.

---

## 16. VALIDATION HUMAINE

Le jugement visuel doit être utilisé comme référence sur les échantillons.

Pour chaque page :

```text
IMAGE PDF
   ↕
TEXTE EXTRAIT
```

Vérifier :

- contenu ;
- ordre ;
- colonnes ;
- articles ;
- paragraphes ;
- caractères ;
- nombres ;
- fragments latins légitimes.

---

## 17. NE PAS UTILISER UNE SIMPLE SIMILARITÉ DE CHAÎNES

Une faible similarité entre deux extracteurs ne signifie pas forcément
que l'un est faux.

Une forte similarité ne garantit pas non plus la qualité.

La référence principale est :

```text
visual layout
+
linguistic readability
+
logical reading order
```

---

## 18. OBJECTIF FINAL DE L'ANALYSE

À la fin du diagnostic, propose une stratégie robuste de routage **PAGE PAR
PAGE** :

```text
PDF PAGE
   ↓
native extraction
   ↓
quality check
   ↓
┌────────────────────────────┐
│                            │
↓                            ↓
correct                    problematic
│                            │
↓                      ┌─────┴─────┐
SAVE                    ↓           ↓
                    ordering     mapping
                    problem      problem
                      ↓             ↓
                  RTL/layout   OCR/review
```

---

## 19. VALIDATION À GRANDE ÉCHELLE

Après avoir validé la méthode sur les premiers cas :

- test minimum 50 PDF ;
- couvrir 1964–1993 ;
- couvrir 1994–2009 ;
- couvrir 2010–2026 ;
- arabe + français ;
- cas simples ;
- cas multi-colonnes ;
- cas avec contenu mixte ;
- cas scannés ;
- cas avec problèmes de mapping.

**NE PAS** passer automatiquement à 10 432 avant validation.

---

## 20. CRITÈRES DE SORTIE

Avant d'autoriser l'extraction massive, le système doit avoir :

1. une méthode claire pour détecter le texte natif ;
2. une méthode claire pour détecter les scans ;
3. une méthode pour détecter les textes corrompus ;
4. une méthode pour gérer l'ordre RTL ;
5. une stratégie pour les pages mixtes ;
6. des statuts SQLite fiables ;
7. des preuves visuelles sur l'échantillon ;
8. un benchmark sur au moins 50 PDF ;
9. aucun texte juridique inventé ou reconstruit ;
10. une stratégie de fallback OCR.

---

## 21. CE QUE TU DOIS PRODUIRE MAINTENANT

**NE LANCE PAS LA MASSE.**

Produis d'abord :

### A. Diagnostic des 10 PDF de référence

### B. Analyse de la cause pour chaque cas

### C. Comparaison des méthodes d'extraction

### D. Validation du prototype RTL

### E. Identification des problèmes qui ne peuvent PAS être résolus par
l'ordre RTL

### F. Proposition de l'architecture finale page-level

### G. Tests nécessaires sur 50 PDF

### H. Rapport final avec :

- ce qui fonctionne ;
- ce qui ne fonctionne pas ;
- cause racine ;
- méthode recommandée ;
- méthode de fallback ;
- critères de décision ;
- risques restants.

---

## 22. RÈGLE ABSOLUE

Ne jamais considérer :

```text
"texte présent"
```

ou :

```text
"0 alertes RTL"
```

comme preuve que le texte est exploitable.

La question centrale est :

> **Le texte extrait représente-t-il fidèlement le contenu visible du PDF,
> dans le bon ordre logique, sans corruption de caractères ?**

Tant que cette question n'est pas suffisamment validée :

```text
MASS EXTRACTION = INTERDITE
```
