# Projet : archivage des PDF du Journal officiel algérien (JORADP)

## Objectif

Découvrir et télécharger les PDF disponibles du Journal officiel algérien depuis
[joradp.dz](https://www.joradp.dz), sans extraction de texte, OCR, analyse de
contenu ou traitement d’images.

Couverture visée :

- édition française : de 1962 à 2026 ;
- édition arabe : de 1964 à 2026 ;
- les numéros arabes historiques distribués page par page sont archivés comme
  des PDF individuels.

Source unique : [https://www.joradp.dz](https://www.joradp.dz)

## Phase 0 — Cadrage et respect du site

1. Vérifier `robots.txt` et respecter les règles publiées.
2. Prévoir un délai minimal de deux secondes entre les requêtes, un User-Agent
   explicite et trois tentatives avec backoff exponentiel.
3. Utiliser un environnement Python isolé et un `requirements.txt` versionné.
4. Confirmer manuellement la structure des index annuels et des liens PDF
   avant toute automatisation ; documenter les résultats dans `SITE_STRUCTURE.md`.

## Phase 1 — Outils de scraping

1. Vérifier que les liens utiles sont présents dans le HTML brut.
2. Utiliser un client HTTP compatible avec le site, BeautifulSoup/lxml pour
   lire les index et SQLite pour conserver l’état du travail.
3. Enregistrer pour chaque source l’année, le numéro, la langue, l’URL, le
   type de PDF, le statut, la taille et le SHA-256.

## Phase 2 — Découverte automatique

1. Parcourir les index annuels pour trouver les PDF français et arabes.
2. Pour l’arabe historique, gérer les numéros fournis page par page et le
   nombre de pages variable.
3. Enregistrer chaque URL avant le téléchargement.
4. Produire un rapport de couverture par année et par langue afin d’identifier
   les numéros absents.

## Phase 3 — Téléchargement des PDF

1. Télécharger par lots contrôlés, en conservant le délai de deux secondes.
2. Vérifier que chaque fichier est bien un PDF, puis calculer et stocker son
   SHA-256.
3. Permettre la reprise après interruption sans retélécharger les fichiers
   déjà validés.
4. Enregistrer les erreurs de téléchargement (timeout, 404, fichier invalide)
   dans SQLite.

## Livrable

Le livrable du projet est l’archive locale des PDF téléchargés, accompagnée de
la base SQLite qui liste les sources, leur statut, leur taille, leur somme
SHA-256 et les éventuelles erreurs. Aucune extraction de texte, OCR, image,
benchmark ou métadonnée juridique ne fait partie de ce projet.
