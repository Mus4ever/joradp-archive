"""Matching revue_index ↔ décisions HTML — Phase 7.

Niveaux (du plus fiable au plus faible) :
  L1 : numéro (sans zéros de tête) + année     → MATCH_EXACT
  L2 : numéro + chambre                         → MATCH_PROBABLE
  L3 : numéro seul                              → MATCH_PROBABLE
  L4 : similarité sujet/principe                → UNCERTAIN (hors scope numérique)

Verdicts : MATCH_EXACT | MATCH_PROBABLE | NEW | UNCERTAIN.
Aucune suppression automatique : la provenance est conservée
(sources = supreme_court_html + revue_YYYY_NN).
"""

import re
import sqlite3
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[3]
DECISIONS_DB = ROOT / "databases" / "coursupreme.db"
REVUE_DB = ROOT / "databases" / "coursupreme_revue.db"


def norm_number(num: Optional[str]) -> Optional[str]:
    """Numéro comparable : zéros de tête retirés."""
    if not num:
        return None
    num = str(num).strip().lstrip("0")
    return num or None


def load_html_index(db_path=DECISIONS_DB):
    """{norm_number: [(decision_id, year, chamber), ...]} — un numéro peut
    avoir plusieurs décisions (numérotation par série)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    index = {}
    for r in conn.execute(
        "SELECT id, decision_number, date, chamber FROM decisions "
        "WHERE decision_number IS NOT NULL AND status='telecharge'"):
        num = norm_number(r["decision_number"])
        if not num:
            continue
        year = int(r["date"][:4]) if r["date"] else None
        index.setdefault(num, []).append(
            {"id": r["id"], "year": year, "chamber": r["chamber"]})
    conn.close()
    return index


def match_entry(entry_num, entry_year, entry_chamber, html_index):
    """Retourne (verdict, level, decision_id ou None)."""
    num = norm_number(entry_num)
    if not num:
        return "UNCERTAIN", 0, None
    candidates = html_index.get(num, [])
    if not candidates:
        return "NEW", 3, None
    if entry_year:
        for c in candidates:
            if c["year"] == entry_year:
                return "MATCH_EXACT", 1, c["id"]
    if entry_chamber:
        for c in candidates:
            if c["chamber"] and entry_chamber in c["chamber"]:
                return "MATCH_PROBABLE", 2, c["id"]
    return "MATCH_PROBABLE", 3, candidates[0]["id"]


def run_matching(log=print) -> dict:
    """Matche toute la table revue_index, écrit revue_matches."""
    html_index = load_html_index()
    conn = sqlite3.connect(REVUE_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS revue_matches (
        entry_id INTEGER PRIMARY KEY,
        verdict TEXT, level INTEGER, decision_id INTEGER,
        sources TEXT)""")
    stats = {"MATCH_EXACT": 0, "MATCH_PROBABLE": 0, "NEW": 0, "UNCERTAIN": 0}
    rows = conn.execute(
        "SELECT id, decision_number, decision_year, chamber, issue_year, issue_number "
        "FROM revue_index WHERE decision_number IS NOT NULL").fetchall()
    for r in rows:
        verdict, level, did = match_entry(
            r["decision_number"], r["decision_year"], r["chamber"], html_index)
        if did:
            sources = "supreme_court_html+revue"
        else:
            src_issue = f"{r['issue_year'] or 'XXXX'}-{(r['issue_number'] or 0):02d}"
            sources = f"revue_{src_issue}"
        conn.execute(
            "INSERT OR REPLACE INTO revue_matches (entry_id, verdict, level, decision_id, sources) "
            "VALUES (?,?,?,?,?)", (r["id"], verdict, level, did, sources))
        stats[verdict] += 1
    conn.commit()
    conn.close()
    total = sum(stats.values())
    log(f"Matching : {total} entrées → {stats}")
    return stats


if __name__ == "__main__":
    run_matching()
