"""Segmentation des décisions du pilote OCR — Phase 6 + rapport qualité Phase 9.

Entrée  : data/revue/2023/issue_01/pages/page-N/markdown.md (OCR Mistral)
Sortie  : table revue_decisions (databases/coursupreme_revue.db)
          + revue_matches mis à jour (Phase 7 : revue vs HTML)
          + reports/revue_ocr_quality_report.{json,md}

Marqueurs OBSERVÉS dans l'OCR réel (jamais supposés) :
  début de décision : 'ملف رقم NNN قرار بتاريخ AAAA/MM/JJ'
    (les lignes du sommaire se terminent par '... NN' → exclues)
  champs : الموضوع: / الكلمات الأساسية: / المرجع القانوني: / المبدأ:
  fin    : 'فلهذه الأسباب' + 'قررت المحكمة العليا' (dispositif)
  chambre: sections '# N. الغرفة ...' du corps (pas les en-têtes répétés)
"""

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.append(str(ROOT / "tools"))

ISSUE_DIR = ROOT / "data" / "revue" / "2023" / "issue_01"
REPORTS = ROOT / "reports"

DECISION_START_RE = re.compile(
    r"^\s*#{0,4}\s*ملف\s+رقم\s+(\d+)\s+قرار\s+بتاريخ\s+(\d{4}/\d{2}/\d{2})\s*$")
SECTION_RE = re.compile(r"^\s*#\s*\d+\.\s*(الغرفة\s+\S+|غرفة\s+\S+)")
FIELD_RES = {
    "subject": re.compile(r"^\s*\**\s*الموضوع\s*\**\s*:?\s*(.*)"),
    "keywords": re.compile(r"^\s*\**\s*الكلمات الأساسية\s*\**\s*:?\s*(.*)"),
    "legal_references": re.compile(r"^\s*\**\s*المرجع القانوني\s*\**\s*:?\s*(.*)"),
    "principle": re.compile(r"^\s*\**\s*المبدأ\s*\**\s*:?\s*(.*)"),
}
DISPOSITION_RE = re.compile(r"قررت\s+المحكمة\s+العليا|تقضي\s+المحكمة\s+العليا")

# Chambres canoniques (correspondent au matching HTML)
CHAMBER_CANON = {
    "الغرفة المدنية": "الغرف المدنية",
    "الغرفة العقارية": "الغرف المدنية",
    "غرفة شؤون الأسرة والمواريث": "الغرف المدنية",
    "الغرفة التجارية والبحرية": "الغرف المدنية",
    "الغرفة الاجتماعية": "الغرف المدنية",
    "الغرفة الجنائية": "الغرف الجزائية",
    "غرفة الجنح والمخالفات": "الغرف الجزائية",
}


def norm_number(num: str) -> str:
    return num.lstrip("0") or "0"


def segment(pages_dir: Path):
    """Parcourt les pages dans l'ordre et assemble les décisions."""
    page_files = sorted(pages_dir.glob("page-*"),
                        key=lambda p: int(p.name.split("-")[1]))
    decisions = []
    current = None
    current_chamber = None

    def close(d):
        if d and d.get("decision_number"):
            decisions.append(d)

    for pf in page_files:
        pno = int(pf.name.split("-")[1])
        text = (pf / "markdown.md").read_text(encoding="utf-8")
        lines = text.split("\n")
        for line in lines:
            m = DECISION_START_RE.match(line)
            if m and not re.search(r"\.{2,}\s*\d+\s*$", line):  # pas un sommaire
                close(current)
                current = {
                    "decision_number": m.group(1),
                    "date": m.group(2).replace("/", "-"),
                    "start_page": pno,
                    "chamber_raw": current_chamber,
                    "subject": None, "keywords": None,
                    "legal_references": None, "principle": None,
                    "has_disposition": False,
                    "text_start": None, "text_end": None,
                    "source_page": pno,
                }
                current["text_start"] = (pno, lines.index(line))
                continue
            if current is None:
                sm = SECTION_RE.match(line)
                if sm:
                    current_chamber = re.sub(r"\s+", " ", sm.group(1)).strip()
                continue
            # champs de la décision courante
            for field, rx in FIELD_RES.items():
                fm = rx.match(line)
                if fm and not current.get(field):
                    current[field] = fm.group(1).strip().strip("*")
                    break
            else:
                if DISPOSITION_RE.search(line):
                    current["has_disposition"] = True
                sm = SECTION_RE.match(line)
                if sm:
                    current_chamber = re.sub(r"\s+", " ", sm.group(1)).strip()
        if current is not None:
            current["text_end"] = (pno, len(lines))
    close(current)
    for d in decisions:
        d["chamber"] = CHAMBER_CANON.get(d.get("chamber_raw") or "", None)
    return decisions


def main():
    from revue_store import RevueStore
    pages_dir = ISSUE_DIR / "pages"
    if not pages_dir.exists():
        print(f"OCR non ingéré : {pages_dir} absent")
        return

    decisions = segment(pages_dir)
    print(f"Décisions segmentées : {len(decisions)}")

    # --- offset guide → PDF (Phase 6 : vérification, pas de supposition) ----
    store = RevueStore()
    conn = store.connect()
    guide = {norm_number(r["decision_number"]): r["start_page"]
             for r in conn.execute(
                 "SELECT decision_number, start_page FROM revue_index "
                 "WHERE issue_year=2023 AND issue_number=1 AND start_page IS NOT NULL")}
    offsets = []
    for d in decisions:
        gp = guide.get(norm_number(d["decision_number"]))
        if gp:
            offsets.append(d["start_page"] - gp)
    offset_counts = Counter(offsets)

    # --- matching vs HTML (Phase 7, niveau 1 : numéro + date) ----------------
    import sqlite3
    dconn = sqlite3.connect(ROOT / "databases" / "coursupreme.db")
    dconn.row_factory = sqlite3.Row
    html = {}
    for r in dconn.execute(
            "SELECT id, decision_number, date FROM decisions WHERE status='telecharge'"):
        html.setdefault(norm_number(r["decision_number"]), []).append(
            {"id": r["id"], "date": r["date"]})
    matches = {"MATCH_EXACT": 0, "MATCH_PROBABLE": 0, "NEW": 0}
    for d in decisions:
        cands = html.get(norm_number(d["decision_number"]), [])
        if not cands:
            d["match"] = "NEW"
        elif any(c["date"] == d["date"] for c in cands):
            d["match"] = "MATCH_EXACT"
        else:
            d["match"] = "MATCH_PROBABLE"
        matches[d["match"]] += 1

    # --- stockage -------------------------------------------------------------
    conn.execute("""CREATE TABLE IF NOT EXISTS revue_decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decision_number TEXT, date TEXT, issue_year INTEGER, issue_number INTEGER,
        chamber TEXT, chamber_raw TEXT, subject TEXT, keywords TEXT,
        legal_references TEXT, principle TEXT, has_disposition INTEGER,
        pdf_start_page INTEGER, match_verdict TEXT, source TEXT,
        created_at TEXT DEFAULT (datetime('now')))""")
    conn.execute("DELETE FROM revue_decisions WHERE issue_year=2023 AND issue_number=1")
    for d in decisions:
        conn.execute(
            """INSERT INTO revue_decisions
               (decision_number, date, issue_year, issue_number, chamber, chamber_raw,
                subject, keywords, legal_references, principle, has_disposition,
                pdf_start_page, match_verdict, source)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (d["decision_number"], d["date"], 2023, 1, d["chamber"],
             d.get("chamber_raw"), d.get("subject"), d.get("keywords"),
             d.get("legal_references"), d.get("principle"),
             int(d["has_disposition"]), d["start_page"], d["match"],
             "revue_2023_01_ocr_mistral"))
    conn.commit()

    # --- rapport qualité (Phase 9) ---------------------------------------------
    n = len(decisions) or 1
    fields_missing = {f: sum(1 for d in decisions if not d.get(f))
                      for f in ("subject", "keywords", "legal_references", "principle")}
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pilote": {"issue": 1, "year": 2023, "source_pdf": "revue_2023_01.pdf",
                   "ocr_engine": "mistral_studio_manuel"},
        "ocr": {"pages_pdf": 335, "pages_ocr": len(list(pages_dir.glob("page-*"))),
                "taux_couverture_pct": round(
                    len(list(pages_dir.glob("page-*"))) / 335 * 100, 1)},
        "segmentation": {
            "decisions": len(decisions),
            "avec_numero": sum(1 for d in decisions if d.get("decision_number")),
            "avec_date": sum(1 for d in decisions if d.get("date")),
            "avec_chambre": sum(1 for d in decisions if d.get("chamber")),
            "avec_dispositif": sum(1 for d in decisions if d.get("has_disposition")),
            "champs_manquants": fields_missing,
        },
        "offset_guide_pdf": {
            "decisions_avec_page_guide": len(offsets),
            "distribution": {str(k): v for k, v in sorted(offset_counts.items())},
        },
        "matching": matches,
        "correspondance_revindex_v4": {
            "note": "les numéros du pilote 2023 figurent dans le guide v4 (éd. 2024)",
        },
    }
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "revue_ocr_quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Rapport qualité du pilote OCR — Revue 2023 n°01",
        f"\nGénéré : {report['generated_at']}\n",
        f"- Pages PDF : 335 | pages OCR : {report['ocr']['pages_ocr']} "
        f"({report['ocr']['taux_couverture_pct']} %)",
        f"- Décisions segmentées : **{len(decisions)}**",
        f"- avec numéro/date/chambre/dispositif : "
        f"{report['segmentation']['avec_numero']} / "
        f"{report['segmentation']['avec_date']} / "
        f"{report['segmentation']['avec_chambre']} / "
        f"{report['segmentation']['avec_dispositif']}",
        f"- champs manquants : {fields_missing}",
        f"- offset page guide → page PDF : "
        f"{dict(sorted(offset_counts.items()))}",
        f"- matching HTML : {matches}",
    ]
    (REPORTS / "revue_ocr_quality_report.md").write_text("\n".join(md), encoding="utf-8")

    print(json.dumps(report["segmentation"], ensure_ascii=False, indent=2))
    print("offset guide→PDF :", dict(sorted(offset_counts.items())))
    print("matching :", matches)
    print("Rapports : revue_ocr_quality_report.json/.md")


if __name__ == "__main__":
    main()
