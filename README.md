# Archive et extraction du Journal officiel algérien (JORADP)

Ce projet constitue l'archive locale complète des PDF du Journal officiel
algérien ([joradp.dz](https://www.joradp.dz)) en français et en arabe, puis
en extrait le texte. Deux phases, toutes deux terminées :

1. **Archivage** — découverte et téléchargement des 10 432 PDF
   (FR 1962-2026 : 5 302 numéros ; AR 1964-2026 : 5 130 numéros ; 8,4 Go),
   avec suivi SQLite et vérification SHA-256.
2. **Extraction de texte** — sortie Markdown de chaque numéro dans
   `Extraction/`, selon deux méthodes selon la nature des PDF :
   - **OCR Mistral** (PDF scannés) : FR 1962-2001 et tout l'AR (1964-2026) ;
     sortie par page (`markdown.md`, `header.md`, `page-metadata.json` avec
     blocs et coordonnées) ;
   - **Extraction texte native** (PDF numériques avec texte embarqué) :
     FR 2002-2026 ; sortie par numéro (`{langue}{année}{numéro}.md` + `.json`).

## Contenu

- `SITE_STRUCTURE.md` : structure du site joradp.dz constatée et validée.
- `docs/journal-phases.md` : journal complet des phases (preuves, mesures,
  décisions, corrections).
- `tools/discover.py` : découverte des liens PDF depuis les index annuels.
- `tools/download_optimized.py` : téléchargement reprenable et validé des PDF.
- `tools/database.py` : suivi SQLite des sources, statuts, tailles, sommes
  SHA-256 et erreurs.
- `tools/http_client.py` : client HTTP avec contexte TLS compatible avec le
  serveur (truststore + renégociation legacy, vérification conservée).
- `tools/rate_limiter.py` : limiteur de cadence global thread-safe.
- `downloads/` : PDF téléchargés (non versionné).
- `Extraction/` : sorties texte/OCR par numéro (non versionné).

## Utilisation

Installer les dépendances dans l'environnement virtuel puis initialiser la
base et lancer la découverte :

```powershell
pip install -r requirements.txt
python tools/database.py
python tools/discover.py --all
python tools/download_optimized.py
```

Le client applique un délai minimal de 2 secondes entre les requêtes, un
User-Agent explicite et trois tentatives avec backoff exponentiel afin de ne
pas surcharger le site source.

Lancer les tests :

```powershell
pytest
```

## État d'avancement de l'extraction

Couverture complète (10 432 / 10 432 numéros). Seul résidu connu : 60 fichiers
`.json` de métadonnées manquants sur les extractions natives FR 2002-2026
(les `.md` de texte sont présents à 100 %).
