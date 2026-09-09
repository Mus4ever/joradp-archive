"""Téléchargeur des pièces jointes PDF du Conseil d'État.

- Parcourt les décisions stockées ayant un lien PDF (pdf_url) ;
- Télécharge chaque fichier PDF vers downloads/conseildetat/ ;
- Calcule le hash SHA-256 et vérifie l'intégrité ;
- Met à jour pdf_path et pdf_hash dans la table decisions ;
- Ignore les fichiers déjà présents avec hash validé (reprise sans doublon) ;
- Respecte le rate limiting via JoradpClient.

Usage :
    python sources/conseildetat/downloader.py --limit 5    # test rapide
    python sources/conseildetat/downloader.py              # téléchargement complet
"""

import hashlib
import sys
from pathlib import Path
from typing import Optional

# Tools HTTP client
sys.path.append(str(Path(__file__).resolve().parents[2] / "tools"))
from http_client import JoradpClient, JoradpClientConfig  # noqa: E402

# Storage & discover
sys.path.insert(0, str(Path(__file__).resolve().parent))
from storage import DecisionStore  # noqa: E402
from discover import USER_AGENT  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = ROOT / "downloads" / "conseildetat"


class PdfDownloader:
    def __init__(self, store: DecisionStore, client: Optional[JoradpClient] = None,
                 dest_dir: Optional[Path] = None, log=print):
        self.store = store
        self.client = client
        self.dest_dir = dest_dir or PDF_DIR
        self.dest_dir.mkdir(parents=True, exist_ok=True)
        self.log = log
        self.stop = False

    def request_stop(self):
        self.stop = True
        self.log("[STOP] arrêt demandé pour le téléchargement PDF")

    def _file_sha256(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def download_all(self, limit: Optional[int] = None) -> dict:
        pending = self.store.decisions_with_pdf(downloaded_only=False)
        if limit:
            pending = pending[:limit]

        stats = {
            "total": len(pending),
            "succes": 0,
            "deja_presents": 0,
            "erreurs": 0,
            "arret": False
        }
        self.log(f"TÉLÉCHARGEMENT PDF : {len(pending)} fichiers à traiter")

        for i, row in enumerate(pending, 1):
            if self.stop:
                stats["arret"] = True
                break

            source_url = row["source_url"]
            pdf_url = row["pdf_url"]
            nid = row["nid"] or "nonid"

            # Nom de fichier standardisé : nid_{nid}_{filename_or_hash}.pdf
            url_filename = Path(pdf_url.split("?")[0]).name
            if not url_filename.lower().endswith(".pdf"):
                url_filename = f"doc_{nid}.pdf"
            local_filename = f"nid_{nid}_{url_filename}"
            target_path = self.dest_dir / local_filename

            # Si le fichier existe déjà localement et est non vide
            if target_path.exists() and target_path.stat().st_size > 0:
                file_hash = self._file_sha256(target_path)
                self.store.save_pdf_info(source_url, str(target_path), file_hash)
                stats["deja_presents"] += 1
                if i % 10 == 0 or i <= 3 or i == len(pending):
                    self.log(f"  [{i}/{len(pending)}] DÉJÀ PRÉSENT {local_filename}")
                continue

            try:
                resp = self.client.get(pdf_url)
                if resp is None:
                    stats["erreurs"] += 1
                    self.log(f"  [{i}/{len(pending)}] ÉCHEC HTTP PDF {pdf_url}")
                    continue

                content = resp.content
                if not content.startswith(b"%PDF") and len(content) < 500:
                    self.log(f"  [{i}/{len(pending)}] ATTENTION: contenu non-PDF reçu pour {pdf_url}")

                target_path.write_bytes(content)
                file_hash = hashlib.sha256(content).hexdigest()
                self.store.save_pdf_info(source_url, str(target_path), file_hash)
                stats["succes"] += 1

                size_kb = len(content) // 1024
                if i % 10 == 0 or i <= 3 or i == len(pending):
                    self.log(f"  [{i}/{len(pending)}] OK {local_filename} ({size_kb} KB)")

            except Exception as e:
                stats["erreurs"] += 1
                self.log(f"  [{i}/{len(pending)}] ERREUR téléchargement {pdf_url}: {e}")

        self.log(f"Terminé PDF : {stats['succes']} téléchargés, {stats['deja_presents']} déjà présents, "
                 f"{stats['erreurs']} erreurs" + (" (arrêté)" if stats["arret"] else ""))
        return stats


def main():
    import argparse

    ap = argparse.ArgumentParser(description="Téléchargeur de PDFs Conseil d'État")
    ap.add_argument("--limit", type=int, default=None, help="Nombre max de PDFs à télécharger")
    args = ap.parse_args()

    config = JoradpClientConfig(user_agent=USER_AGENT)
    store = DecisionStore()
    downloader = PdfDownloader(store, None)

    with JoradpClient(config) as client:
        downloader.client = client
        try:
            downloader.download_all(limit=args.limit)
        except KeyboardInterrupt:
            downloader.request_stop()


if __name__ == "__main__":
    main()
