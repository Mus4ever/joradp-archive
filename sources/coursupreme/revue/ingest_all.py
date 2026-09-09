"""Ingestion + segmentation de TOUS les numéros OCRisés (batch).

Entrée : dossier de résultats Mistral Studio, dossiers nommés revue_YYYY_NN.pdf
Sortie : data/revue/{année}/issue_{NN}/ (copie + metadata.json)
         table revue_decisions (toutes issues)
         reports/revue_ocr_batch_report.{json,md}

Usage :
    python sources/coursupreme/revue/ingest_all.py                # tout
    python sources/coursupreme/revue/ingest_all.py --source DIR   # autre dossier
    python sources/coursupreme/revue/ingest_all.py --only 1989    # une année
"""

import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.append(str(ROOT / "tools"))

from segmenter import segment, norm_number  # noqa: E402
from revue_store import RevueStore  # noqa: E402

DEFAULT_SOURCE = Path(r"C:\Users\Gaming\OneDrive\Bureau\OcrMus")
REPORTS = ROOT / "reports"
FOLDER_RE = re.compile(r"^revue_(\d{4})_(\d{2})(?:\.pdf)?$", re.I)


def ingest_one(src: Path, year: int, number: int) -> dict:
    dst = ROOT / "data" / "revue" / str(year) / f"issue_{number:02d}"
    if not dst.exists():
        shutil.copytree(src, dst)
    n_pages = len(list((dst / "pages").glob("page-*")))
    meta = {
        "issue": number, "year": year, "source_pdf": f"revue_{year}_{number:02d}.pdf",
        "ocr_engine": "mistral_studio_manuel", "pages": n_pages,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "provenance_raw": str(src),
    }
    (dst / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"dst": str(dst), "pages_ocr": n_pages}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--only", help="année unique, ex. 1989")
    args = ap.parse_args()

    src_root = Path(args.source)
    folders = []
    for d in sorted(src_root.iterdir()):
        m = FOLDER_RE.match(d.name)
        if m and (d / "pages").exists():
            y, n = int(m.group(1)), int(m.group(2))
            if args.only and str(y) != args.only:
                continue
            folders.append((y, n, d))
    print(f"{len(folders)} numéros OCR à traiter")

    store = RevueStore()
    conn = store.connect()
    conn.execute("""CREATE TABLE IF NOT EXISTS revue_decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decision_number TEXT, date TEXT, issue_year INTEGER, issue_number INTEGER,
        chamber TEXT, chamber_raw TEXT, subject TEXT, keywords TEXT,
        legal_references TEXT, principle TEXT, has_disposition INTEGER,
        pdf_start_page INTEGER, match_verdict TEXT, source TEXT,
        created_at TEXT DEFAULT (datetime('now')))""")

    results = []
    for i, (year, number, src) in enumerate(folders, 1):
        ing = ingest_one(src, year, number)
        decisions = segment(Path(ing["dst"]) / "pages")
        conn.execute(
            "DELETE FROM revue_decisions WHERE issue_year=? AND issue_number=?",
            (year, number))
        for d in decisions:
            conn.execute(
                """INSERT INTO revue_decisions
                   (decision_number, date, issue_year, issue_number, chamber,
                    chamber_raw, subject, keywords, legal_references, principle,
                    has_disposition, pdf_start_page, match_verdict, source)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (d["decision_number"], d["date"], year, number, d.get("chamber"),
                 d.get("chamber_raw"), d.get("subject"), d.get("keywords"),
                 d.get("legal_references"), d.get("principle"),
                 int(d.get("has_disposition", False)), d.get("start_page"),
                 "PENDING", f"revue_{year}_{number:02d}_ocr_mistral"))
        conn.commit()
        # pages attendues (DB) vs OCR
        exp = conn.execute(
            "SELECT pdf_pages FROM revue_resources WHERE issue_year=? AND issue_number=?",
            (year, number)).fetchone()
        results.append({
            "year": year, "number": number,
            "pages_ocr": ing["pages_ocr"],
            "pages_attendues": exp["pdf_pages"] if exp else None,
            "decisions": len(decisions),
        })
        if i % 10 == 0 or i == len(folders):
            print(f"  [{i}/{len(folders)}] {year}-{number:02d}: "
                  f"{len(decisions)} décisions, {ing['pages_ocr']} pages")

    # --- matching vs HTML (niveau 1 : numéro + date) -------------------------
    import sqlite3
    dconn = sqlite3.connect(ROOT / "databases" / "coursupreme.db")
    html = {}
    for r in dconn.execute("SELECT decision_number, date FROM decisions WHERE status='telecharge'"):
        html.setdefault(norm_number(r[0]), []).append(r[1])
    stats = Counter()
    for num, date, verdict_placeholder in conn.execute(
            "SELECT decision_number, date, match_verdict FROM revue_decisions"):
        cands = html.get(norm_number(num), [])
        if not cands:
            verdict = "NEW"
        elif date in cands:
            verdict = "MATCH_EXACT"
        else:
            verdict = "MATCH_PROBABLE"
        stats[verdict] += 1
        if verdict_placeholder == "PENDING":
            conn.execute(
                "UPDATE revue_decisions SET match_verdict=? WHERE decision_number=? AND date=? AND match_verdict='PENDING'",
                (verdict, num, date))
    conn.commit()

    # --- rapport global --------------------------------------------------------
    total_dec = sum(r["decisions"] for r in results)
    total_ocr = sum(r["pages_ocr"] for r in results)
    issues_0 = [(r["year"], r["number"]) for r in results if r["decisions"] == 0]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "resume": {
            "issues_traites": len(results),
            "pages_ocr_total": total_ocr,
            "decisions_segmentees": total_dec,
            "moyenne_decisions_par_numero": round(total_dec / max(len(results), 1), 1),
            "matching_html": dict(stats),
            "issues_sans_decisions": issues_0,
        },
        "par_issue": results,
    }
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "revue_ocr_batch_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md = ["# OCR batch — toutes les revues", "",
          f"- Numéros traités : {len(results)}",
          f"- Pages OCR : {total_ocr}",
          f"- Décisions segmentées : **{total_dec}**",
          f"- Matching HTML : {dict(stats)}",
          f"- Numéros sans décision détectée : {issues_0}", "",
          "| numéro | pages OCR | attendues | décisions |", "|---|---:|---:|---:|"]
    for r in results:
        md.append(f"| {r['year']}-{r['number']:02d} | {r['pages_ocr']} | "
                  f"{r['pages_attendues'] or '?'} | {r['decisions']} |")
    (REPORTS / "revue_ocr_batch_report.md").write_text("\n".join(md), encoding="utf-8")

    print(f"\nTOTAL : {total_dec} décisions sur {len(results)} numéros, "
          f"{total_ocr} pages OCR")
    print(f"Matching HTML : {dict(stats)}")
    if issues_0:
        print(f"ATTENTION — numéros sans décision détectée : {issues_0}")
    print("Rapport : reports/revue_ocr_batch_report.json/.md")


if __name__ == "__main__":
    main()
