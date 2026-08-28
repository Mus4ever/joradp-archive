# Archive des PDF JORADP

Ce projet découvre et télécharge les PDF du Journal officiel algérien (JORADP)
en français et en arabe. Son périmètre s’arrête à l’archivage des fichiers PDF :
il ne contient ni extraction de texte, ni OCR, ni traitement d’images.

## Contenu

- `SITE_STRUCTURE.md` : structure du site confirmée avant le scraping.
- `tools/discover.py` : découverte des liens PDF.
- `tools/download_batch.py` et `tools/download_optimized.py` : téléchargement
  reprenable des PDF.
- `tools/database.py` : suivi SQLite des sources, statuts, tailles, sommes
  SHA-256 et erreurs.
- `tools/http_client.py` et `tools/rate_limiter.py` : accès HTTP poli au site.

Les fichiers téléchargés sont écrits dans `downloads/` et la base SQLite est
locale. Ces deux emplacements ne sont pas versionnés.

## Utilisation

Installer les dépendances puis initialiser la base et lancer la découverte :

```powershell
pip install -r requirements.txt
python tools/database.py
python tools/discover.py --all
python tools/download_optimized.py
```

Le client applique un délai minimal entre les requêtes, un User-Agent explicite
et des tentatives limitées afin de ne pas surcharger le site source.
