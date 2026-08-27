# Archive bilingue JORADP

Pipeline reproductible destiné à inventorier, télécharger et extraire les
sources natives du *Journal officiel de la République algérienne démocratique
et populaire* (JORADP), sans traduction ni reconstitution de texte.

## État

La phase de cadrage est en cours. Aucun parseur, crawl ni téléchargement de
corpus n'est lancé tant que la structure des index français, arabes et des
archives arabes page-à-page n'est pas validée sur des échantillons réels.

## Principes non négociables

- Un seul site source : `https://www.joradp.dz`.
- Au moins deux secondes entre deux requêtes HTTP, avec User-Agent explicite,
  trois tentatives maximum et backoff exponentiel.
- SQLite est la source de vérité de l'état du pipeline.
- Les deux langues conservent uniquement leur contenu source natif.
- Un document illisible est signalé (`needs_review` / `needs_ocr`) ; il n'est
  jamais complété, traduit ni inféré.
