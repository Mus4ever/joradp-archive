# Rapport Pédagogique du Projet — À l'Attention du Professeur

> **Titre** : Constitution d'un Corpus Juridique Algérien Unifié et Structuré pour le Futur Entraînement d'un Small Language Model (SLM)  
> **Auteur** : Équipe de développement  
> **Dépôt GitHub** : `https://github.com/Mus4ever/joradp-archive`  
> **Date** : Septembre 2026  
> **Statut d'avancement** : **Phase Données & CorpusDB Terminée et Validée** (SLM et Fine-Tuning non encore commencés).

---

## 1. Pourquoi ce Projet ? Le Problème et l'Idée

### 1.1. Le Constat
Les modèles de langage généralistes actuels (GPT-4, Claude, Llama 3) possèdent des connaissances superficielles sur les droits nationaux hautement spécifiques. Concernant l'Algérie :
- Le système juridique est mixte (droit civil d'inspiration romano-germanique, droit musulman pour le statut personnel, spécificités administratives post-indépendance).
- Les textes sont bilingues (arabe et français pour les lois, arabe quasi-exclusif pour la jurisprudence).
- Les modèles généralistes ont tendance à **halluciner** des numéros d'articles ou à transposer des règles de droit français ou égyptien en lieu et place du droit algérien.

### 1.2. L'Objectif
Construire la **première bibliothèque numérique juridique algérienne complète, canonique, traçable et rigoureusement structurée**, capable de servir de matière première d'apprentissage pour un futur modèle de langage compact spécialisé (Small Language Model - SLM).

---

## 2. Mini-Glossaire des Notions Techniques Utilisées

| Terme | Définition Vulgarisée |
|---|---|
| **Scraper** | Programme automatisé téléchargeant respectueusement et méthodiquement des pages ou fichiers web depuis des sites publics. |
| **OCR** (*Optical Character Recognition*) | Procédé transformant des images de texte (scans de vieux journaux ou PDF non sélectionnables) en caractères informatiques éditables. |
| **Bidi / Ordre Visuel vs Logique** | Phénomène spécifique à l'arabe : dans certains PDF, les lettres s'écrivent de droite à gauche visuellement mais sont stockées de gauche à droite dans le flux binaire. Une correction mathématique est indispensable pour éviter que le texte ne soit inversé. |
| **Base Staging** | Base de données temporaire intermédiaire propre à une source, permettant de nettoyer et stabiliser les données avant leur intégration générale. |
| **CorpusDB** | Base de données relationnelle SQLite finale unifiant l'ensemble des textes du droit algérien selon un schéma commun. |
| **CanonicalDocument** | Modèle de données universel standardisant une loi, un décret ou un jugement avec des champs uniformes (titre, date, juridiction, texte, etc.). |
| **Provenance** | « Carte d'identité » technique accompagnant chaque texte (URL d'origine, fichier source, hash SHA-256, date d'ingestion), permettant de remonter au document officiel. |
| **Gold Set** | Échantillon de test contrôlé manuellement servant d'étalon-or pour valider automatiquement la précision des algorithmes d'extraction. |
| **Idempotence** | Propriété garantissant que relancer un traitement dix fois produit exactement le même résultat sans créer de doublon ni corrompre les données. |
| **SLM / SFT / LoRA / QLoRA** | Techniques d'intelligence artificielle permettant d'adapter un petit modèle de base (7B ou 8B paramètres) à une tâche précise en ajustant ses poids neuronaux. *(Phase future du projet).* |
| **RAG** (*Retrieval-Augmented Generation*) | Technique consistant à rechercher des articles de loi pertinents dans une base vectorielle pour les donner en contexte au modèle au moment de sa réponse. |
| **Multi-Agents** | Architecture logicielle où plusieurs modules spécialisés (ex. agent chercheur, agent analyste, agent rédacteur) collaborent pour résoudre un problème juridique complexe. |

---

## 3. Les 4 Piliers Documentaires Intégrés

Le projet rassemble désormais **4 fonds majeurs** couvrant l'intégralité du droit positif et de la jurisprudence supérieure algérienne :

```
                                  [ CORPUS GLOBAL : 236 090 DOCUMENTS ]
                                                    |
         +--------------------------+---------------+--------------------------+
         |                          |                                          |
   [ 1. JORADP ]         [ 2. Cour Suprême (HTML) ]            [ 3. Cour Suprême (Revue) ]        [ 4. Conseil d'État ]
231 234 textes normatifs     1 253 décisions complètes             3 274 décisions de fond          329 décisions admin.
   853 500 articles           (2015-2023, fiches HTML)              (1989-2023, 80 numéros)           (1998-2022, arrêts)
```

1. **JORADP (Journal Officiel de la République Algérienne Démocratique et Populaire)** :
   - 10 432 numéros (1962 à 2026), 5 302 français, 5 130 arabes.
   - Textes extraits par OCR Mistral (pour les archives scannées) et extraction native (numérique).
   - Découpés et structurés en **231 234 actes juridiques individuels** et **853 500 articles**.

2. **Cour Suprême — Fiches HTML** :
   - 1 253 décisions publiées sur le portail numérique officiel (`coursupreme.dz`).
   - Métadonnées complètes (chambres, visas, attendus, principes, dispositifs).

3. **Cour Suprême — Revue Judiciaire (المجلة القضائية)** :
   - 80 numéros historiques (86 PDF, 32 065 pages OCRisées) de 1989 à 2023.
   - **3 274 décisions** dont 1 955 segmentées dans le texte moderne et 1 319 décisions historiques (« Legacy ») réconciliées avec leur texte intégral grâce à un algorithme d'offset guide-vers-PDF.
   - Apport de plus de 3 100 décisions inédites non présentes sur le site HTML.

4. **Conseil d'État** :
   - 329 fiches et arrêts du contentieux administratif supérieur (1998 à 2022).

---

## 4. Difficultés Majeures Rencontrées et Solutions Apportées

| Difficulté Rencontrée | Impact | Solution Technique Validée |
|---|---|---|
| **TLS Ancien sur les sites gouvernementaux** | Échec des requêtes HTTP modernes (OpenSSL désactivant la renégociation legacy). | Conception d'un client HTTP sur-mesure combinant truststore système et support sécurisé de la renégociation sans désactiver la validation des certificats. |
| **Serveurs fragiles** | Risque d'interruption de service ou de blocage IP. | Implémentation d'un `RateLimiter` global (2 secondes entre requêtes) avec reprise sur panne via statuts SQLite. |
| **Double Inversion Bidi dans le Guide de la Revue** | Les principes juridiques de l'index sortaient à l'envers (`طلباتهم... یعد` au lieu de `یعد...`). | Réorganisation des tokens géométriques de gauche à droite avant normalisation logique. Validation linguistique : 937 principes commencent par la formule rituelle « من المقرر », 0 inversé. |
| **Décalage Page Papier vs Page PDF (Revue)** | Dans les numéros anciens, la page 45 du guide papier ne correspondait pas à la page 45 du fichier numérique PDF. | Création de `offset_calculator.py` identifiant l'offset réel par détection des pieds de page et marqueurs de texte. 99,5% des décisions historiques ont retrouvé leur texte complet (8,7 millions de caractères). |
| **Doublons de Numéros de Décision** | Deux arrêts distincts peuvent porter le même numéro de rôle s'ils sont rendus dans des chambres différentes ou à des dates différentes. | Abandon des compteurs instables au profit d'identifiants canoniques déterministes incorporant la date ou une empreinte cryptographique unique. |

---

## 5. Bilan Chiffré Actuel

- **236 090 documents juridiques** unifiés dans `databases/corpus.db` (2,04 Go).
- **853 500 articles de loi** indexés et rattachés à leurs textes mères.
- **146 correspondances exactes** identifiées et liées entre les arrêts HTML et la Revue papier (`SAME_DECISION_DIFFERENT_SOURCE`).
- **96 tests automatiques** exécutés avec un taux de réussite de **100%**.
- **Intégrité de la base** vérifiée avec succès via SQLite (`PRAGMA integrity_check = ok`).

---

## 6. À Propos du Reel Haiku et des Perspectives d'Architecture

Le professeur a partagé un Reel présentant **Haiku**, une IA juridique spécialisée reposant sur une architecture multi-agents et des moteurs de recherche dédiés.

> **Position technique soumise à la discussion avec le professeur :**  
> 1. **Aucune architecture multi-agents n'a été prématurément imposée dans le code.**  
> 2. Le travail réalisé jusqu'à présent (constitution de la bibliothèque CorpusDB propre et documentée) est le prérequis obligatoire et indispensable, quelle que soit l'architecture finale retenue (modèle fine-tuné monolithique, pipeline RAG ou système multi-agents).  
> 3. La suite logique des opérations doit être concertée :
>    - **Option A** : Fine-tuning direct d'un Small Language Model (ex. Llama 3 8B ou Qwen 2.5 7B) avec QLoRA sur des questions/réponses juridiques extraites du corpus.
>    - **Option B** : Système RAG hybride combinant recherche dense (embeddings vectoriels arabes/français) et recherche lexicale (BM25) sur CorpusDB.
>    - **Option C** : Architecture multi-agents inspirée de Haiku (un agent législation, un agent jurisprudence, un agent synthèse).
