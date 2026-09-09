"""OCR pilote du numéro 2023-01 — Phases 4-5.

Deux voies (le projet n'a pas de clé API en dur) :

1. API : MISTRAL_API_KEY définie → le script envoie le PDF à l'API Mistral OCR
   et structure la sortie par page.

2. Manuel (workflow établi du projet, utilisé pour JORADP) : uploader
   data/revue/revue_2023_01.pdf dans Mistral Studio (OCR), télécharger le
   résultat, puis ingérer :
       python sources/coursupreme/revue/ocr_pilot.py --from-file <resultat>

La sortie structurée réutilise le format JORADP :
    data/revue/2023/issue_01/
        raw/                    (sortie brute telle que reçue)
        pages/page-N/markdown.md
        markdown.md             (document complet)
        metadata.json
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

PILOT = ROOT / "data" / "revue" / "revue_2023_01.pdf"
OUT_DIR = ROOT / "data" / "revue" / "2023" / "issue_01"
ISSUE, YEAR = 1, 2023


def validate_pilot() -> bool:
    """Vérifications pré-OCR (Phase 4) : existence, SHA-256 en base, PUA."""
    import hashlib
    import sqlite3
    if not PILOT.exists():
        print(f"PDF pilote introuvable : {PILOT}")
        return False
    conn = sqlite3.connect(ROOT / "databases" / "coursupreme_revue.db")
    row = conn.execute(
        "SELECT sha256, pdf_pages FROM revue_resources WHERE issue_year=? AND issue_number=?",
        (YEAR, ISSUE)).fetchone()
    sha = hashlib.sha256(PILOT.read_bytes()).hexdigest()
    print(f"Pilote : {PILOT.name}")
    print(f"  pages : {row[1]} | SHA-256 base OK : {row[0] == sha}")
    from pypdf import PdfReader
    reader = PdfReader(str(PILOT))
    n = len(reader.pages)
    pua = sum(1 for ch in (reader.pages[i].extract_text() or "")
              for i in range(0, min(n, 10)) if False)  # noqa — voir ci-dessous
    pua = 0
    for i in range(0, min(n, 10)):
        t = reader.pages[i].extract_text() or ""
        pua += sum(1 for ch in t if 0xE000 <= ord(ch) <= 0xF8FF)
    print(f"  caractères PUA sur 10 pages : {pua} → OCR {'requis' if pua > 100 else 'optionnel'}")
    return True


def ocr_via_api() -> int:
    """Voie 1 : API Mistral OCR (nécessite MISTRAL_API_KEY)."""
    import os
    key = os.environ.get("MISTRAL_API_KEY")
    if not key:
        print("MISTRAL_API_KEY absente — voie manuelle disponible :")
        print(f"  1. Uploader {PILOT} dans Mistral Studio (OCR)")
        print("  2. Télécharger le résultat JSON")
        print(f"  3. python sources/coursupreme/revue/ocr_pilot.py --from-file <resultat.json>")
        return 1
    try:
        from mistralai import Mistral
    except ImportError:
        print("pip install mistralai d'abord")
        return 1
    client = Mistral(api_key=key)
    with open(PILOT, "rb") as f:
        uploaded = client.files.upload(file={"file_name": PILOT.name, "content": f})
    signed = client.files.get_signed_url(file_id=uploaded.id)
    result = client.ocr.process(document={"type": "document", "document_url": signed.url},
                                model="mistral-ocr-latest")
    return ingest_payload(result.model_dump(), source="mistral_api")


def ingest_payload(payload: dict, source: str) -> int:
    """Structure une sortie OCR (API ou manuelle) par page — Phase 5."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "raw").mkdir(exist_ok=True)
    pages = payload.get("pages") or []
    for i, p in enumerate(pages, 1):
        pd = OUT_DIR / "pages" / f"page-{i}"
        pd.mkdir(parents=True, exist_ok=True)
        (pd / "markdown.md").write_text(p.get("markdown", ""), encoding="utf-8")
    full_md = "\n\n---\n\n".join(p.get("markdown", "") for p in pages)
    (OUT_DIR / "markdown.md").write_text(full_md, encoding="utf-8")
    (OUT_DIR / "raw" / "ocr_response.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = {
        "issue": ISSUE, "year": YEAR, "source_pdf": PILOT.name,
        "ocr_engine": source, "pages": len(pages),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    (OUT_DIR / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Ingesté : {len(pages)} pages → {OUT_DIR}")
    return len(pages)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="OCR pilote 2023-01")
    ap.add_argument("--from-file", help="résultat OCR Mistral (JSON) téléchargé manuellement")
    args = ap.parse_args()

    if not validate_pilot():
        return
    if args.from_file:
        payload = json.loads(Path(args.from_file).read_text(encoding="utf-8"))
        # formats possibles : {pages: [...]} ou {data: {pages: [...]}} (studio)
        if "pages" not in payload and "data" in payload:
            payload = payload["data"]
        ingest_payload(payload, source="mistral_studio_manuel")
    else:
        ocr_via_api()


if __name__ == "__main__":
    main()
