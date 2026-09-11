# Guide de Reproductibilité du Projet

Ce guide décrit l'ensemble des étapes nécessaires pour reproduire l'environnement, vérifier l'intégrité des bases de données et exécuter la suite de tests automatisés.

---

## 1. Environnement et Dépendances

- **Python** : 3.11+
- **Système d'exploitation** : Windows / Linux / macOS
- **Environnement virtuel** :
  ```bash
  python -m venv .venv
  # Sous Windows (PowerShell) :
  .venv\Scripts\Activate.ps1
  # Sous Linux/macOS :
  source .venv/bin/activate
  ```

- **Installation des dépendances** :
  ```bash
  pip install -r requirements.txt
  ```

---

## 2. Exécution des Tests de Validation

Le dépôt inclut une suite de tests unitaires et d'intégration validant les scrapers, adaptateurs, la normalisation bidirectionnelle arabe et l'intégrité des schémas :

```bash
python -m pytest tests/
```

*Résultat attendu : 96 tests passés avec succès (0 échec, 0 régression).*

---

## 3. Contrôle d'Intégrité de CorpusDB

Pour vérifier la santé physique et relationnelle de la base de données unifiée (`databases/corpus.db`) :

```bash
python -c "
import sqlite3
conn = sqlite3.connect('databases/corpus.db')
print('PRAGMA integrity_check :', conn.execute('PRAGMA integrity_check').fetchall())
print('PRAGMA foreign_key_check:', conn.execute('PRAGMA foreign_key_check').fetchall())
"
```

*Résultats attendus :*
- `integrity_check : [('ok',)]`
- `foreign_key_check: []`

---

## 4. Consultation Interactive des Données

Un serveur dashboard web local permet de visualiser le contenu de CorpusDB :

```bash
python tools/explorer_server.py
```
Ouvrir ensuite le navigateur sur [http://localhost:8501](http://localhost:8501).

---

## 5. Ordre Logique des Pipelines (Historique de Construction)

En cas de re-génération complète à partir des données brutes :

1. **Staging Cour Suprême HTML** :
   ```bash
   python sources/coursupreme/scraper.py
   python sources/coursupreme/verif_completude.py
   ```
2. **Staging Conseil d'État** :
   ```bash
   python sources/conseildetat/scraper.py
   python sources/conseildetat/downloader.py
   ```
3. **Staging Revue Cour Suprême** :
   ```bash
   python sources/coursupreme/revue/guide_parser.py --guide v4 --clean
   python sources/coursupreme/revue/segment_legacy.py
   ```
4. **Intégration unifiée dans CorpusDB** :
   ```bash
   python scratch/ingest_revue_and_conseil.py
   python scratch/update_corpus_revue.py
   ```
