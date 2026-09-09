"""Segmentation des numéros LEGACY (1990-2004) guidée par l'index du guide.

Constat (09/09/2026, OCR réel) : dans les anciens numéros, la Cour s'appelle
« المجلس الأعلى », il n'y a pas de marqueur « ملف رقم N قرار بتاريخ », les
dates sont rédigées en toutes lettres. En revanche le guide v4 indexe ces
numéros avec la page de début de chaque décision (offset guide→PDF = 0,
vérifié : 2023 et 1991).

Méthode : chaque entrée revue_index (issue_year, issue_number) devient une
décision de revue_decisions, avec numéro/année/chambre/sujet/principe/
référence légale du guide et pdf_start_page. source = '..._index_guide'
(provenance honnête : métadonnées du guide, texte à aligner plus tard).

Usage : python segment_legacy.py
"""

import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.append(str(ROOT / "tools"))

from revue_store import RevueStore  # noqa: E402
from segmenter import norm_number  # noqa: E402


def main():
    store = RevueStore()
    conn = store.connect()
    dconn_ok = True

    # 1. numéros legacy = issues de l'inventaire sans aucune décision détectée
    #    (GROUP BY ... HAVING n=0 ne voit jamais les groupes vides → LEFT JOIN)
    issues = conn.execute("""
        SELECT r.issue_year, r.issue_number, COUNT(d.id) n
        FROM revue_resources r
        LEFT JOIN revue_decisions d
          ON d.issue_year = r.issue_year AND d.issue_number = r.issue_number
        WHERE r.resource_type = 'REVUE'
        GROUP BY r.issue_year, r.issue_number
        HAVING n = 0 AND r.issue_year IS NOT NULL""").fetchall()
    print(f"{len(issues)} numéros legacy à couvrir par l'index")

    # 2. index HTML pour le matching
    import sqlite3
    html = {}
    dconn = sqlite3.connect(ROOT / "databases" / "coursupreme.db")
    for r in dconn.execute(
            "SELECT decision_number, date FROM decisions WHERE status='telecharge'"):
        html.setdefault(norm_number(r[0]), []).append(r[1])

    inserted = 0
    match_stats = Counter()
    for row in issues:
        year, number = row["issue_year"], row["issue_number"]
        entries = conn.execute(
            "SELECT decision_number, decision_year, start_page, chamber, subject, "
            "principle, legal_reference FROM revue_index "
            "WHERE issue_year=? AND issue_number=? AND decision_number IS NOT NULL "
            "AND start_page IS NOT NULL ORDER BY start_page",
            (year, number)).fetchall()
        for e in entries:
            cands = html.get(norm_number(e["decision_number"]), [])
            if not cands:
                verdict = "NEW"
            elif any(c and c.startswith(str(e["decision_year"] or "")) for c in cands):
                verdict = "MATCH_EXACT"
            else:
                verdict = "MATCH_PROBABLE"
            match_stats[verdict] += 1
            conn.execute(
                """INSERT INTO revue_decisions
                   (decision_number, date, issue_year, issue_number, chamber,
                    chamber_raw, subject, keywords, legal_references, principle,
                    has_disposition, pdf_start_page, match_verdict, source)
                   VALUES (?,?,?,?,?,?,?,?,?,?,0,?,?,?)""",
                (e["decision_number"], None, year, number,
                 e["chamber"], e["chamber"], e["subject"], None,
                 e["legal_reference"], e["principle"], e["start_page"],
                 verdict, f"revue_{year}_{number:02d}_index_guide"))
            inserted += 1
    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM revue_decisions").fetchone()[0]
    by_source = dict(conn.execute(
        "SELECT CASE WHEN source LIKE '%index_guide' THEN 'index_guide' "
        "ELSE 'text_markers' END s, COUNT(*) FROM revue_decisions GROUP BY s").fetchall())
    print(f"Entrées index insérées : {inserted}")
    print(f"Total revue_decisions : {total} ({by_source})")
    print(f"Matching (legacy, numéro+année) : {dict(match_stats)}")


if __name__ == "__main__":
    main()
