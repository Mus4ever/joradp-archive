"""Téléchargement robuste des PDF de la revue — Phase 2.

Réutilise l'infrastructure JORADP : http_client (rate limiter global 2 s,
retries backoff), validation PDF magie + taille, écriture .part puis
os.replace atomique, SHA-256, statuts SQLite, reprise intégrale.

Usage :
    python sources/coursupreme/revue/downloader.py                # tout en attente
    python sources/coursupreme/revue/downloader.py --only-guides  # guides d'abord
    python sources/coursupreme/revue/downloader.py --limit 2      # pilote
"""

import hashlib
import os
import sys
import time
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.append(str(ROOT / "tools"))
sys.path.insert(0, str(HERE))

from http_client import JoradpClient, JoradpClientConfig  # noqa: E402

from revue_store import RevueStore  # noqa: E402

# Même User-Agent que le scraper décisions (constante de sources/coursupreme/discover.py)
USER_AGENT = "AlgerianLegalCorpusBot/0.1 (academic legal research; polite crawler)"

DATA_DIR = ROOT / "data" / "revue"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_pdf(path: Path) -> tuple:
    """Validation minimale : magie %PDF, non vide, taille raisonnable."""
    with open(path, "rb") as f:
        head = f.read(4)
    if head != b"%PDF":
        return False, "magic bytes absents"
    size = path.stat().st_size
    if size == 0:
        return False, "fichier vide"
    if size < 10_000:
        return False, f"taille suspecte ({size} octets)"
    return True, "ok"


def logical_name(row) -> str:
    """Nom de fichier logique et stable : type_année_numéro.pdf.
    Pour les ressources sans numéro/année (guides...), un suffixe court
    dérivé du SHA-256 de l'URL garantit l'unicité (évite les collisions
    de slugs encodés)."""
    import re
    t = {"REVUE": "revue", "SPECIAL_ISSUE": "special",
         "GUIDE": "guide", "INDEX": "index", "OTHER": "autre"}.get(row["resource_type"], "autre")
    suffix = hashlib.sha256(row["url"].encode()).hexdigest()[:8]
    if row["issue_year"] and row["issue_number"]:
        return f"{t}_{row['issue_year']}_{row['issue_number']:02d}.pdf"
    if row["issue_year"]:
        return f"{t}_{row['issue_year']}_{suffix}.pdf"
    slug = Path(row["pdf_url"].split("?")[0]).stem
    slug = re.sub(r"[^\w\-]", "_", slug)[:40]
    return f"{t}_{slug}_{suffix}.pdf"


def count_pages(path: Path) -> Optional[int]:
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(path)).pages)
    except Exception:
        return None


def download_all(store: RevueStore, limit: Optional[int] = None,
                 only_guides: bool = False, log=print) -> dict:
    rows = store.pending_pdfs()
    if only_guides:
        rows = [r for r in rows if r["resource_type"] in ("GUIDE", "INDEX")]
    if limit:
        rows = rows[:limit]

    log(f"TÉLÉCHARGEMENT : {len(rows)} PDF en attente")
    stats = {"succes": 0, "erreurs": 0, "total": len(rows)}

    config = JoradpClientConfig(user_agent=USER_AGENT)
    with JoradpClient(config) as client:
        for i, row in enumerate(rows, 1):
            name = logical_name(row)
            dest = DATA_DIR / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            part = dest.with_suffix(".pdf.part")

            # reprise : déjà téléchargé et valide ?
            if dest.exists():
                ok, msg = validate_pdf(dest)
                if ok:
                    store.mark_downloaded(row["url"], str(dest), dest.stat().st_size,
                                          sha256_file(dest), count_pages(dest))
                    log(f"  [{i}/{len(rows)}] [SKIP] {name} (déjà présent)")
                    stats["succes"] += 1
                    continue
                dest.unlink()  # corrompu : retélécharge

            t0 = time.time()
            try:
                resp = client.get(row["pdf_url"])
                if resp is None:
                    raise RuntimeError("échec HTTP après retries")
                if resp.content[:4] != b"%PDF":
                    raise RuntimeError(f"pas un PDF ({resp.headers.get('content-type', '?')})")
                with open(part, "wb") as f:
                    f.write(resp.content)
                ok, msg = validate_pdf(part)
                if not ok:
                    raise RuntimeError(f"validation : {msg}")
                os.replace(part, dest)
                size = dest.stat().st_size
                sha = sha256_file(dest)
                pages = count_pages(dest)
                store.mark_downloaded(row["url"], str(dest), size, sha, pages)
                stats["succes"] += 1
                log(f"  [{i}/{len(rows)}] [OK] {name} : {size/1e6:.1f} Mo, "
                    f"{pages or '?'} pages, {time.time()-t0:.0f}s")
            except Exception as e:
                if part.exists():
                    part.unlink()
                store.mark_error(row["url"], f"{type(e).__name__}: {e}")
                stats["erreurs"] += 1
                log(f"  [{i}/{len(rows)}] [FAIL] {name} : {e}")

    log(f"Terminé : {stats['succes']} succès, {stats['erreurs']} erreurs")
    return stats


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Télécharge les PDF de la revue")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only-guides", action="store_true")
    args = ap.parse_args()

    store = RevueStore()
    download_all(store, limit=args.limit, only_guides=args.only_guides)
    print("Statuts :", store.counts_by_status())


if __name__ == "__main__":
    main()
