"""Segmentation des numéros LEGACY (1990-2004) — V2 avec extraction de texte OCR.

Constat (09/09/2026, OCR réel) : dans les anciens numéros, la Cour s'appelle
« المجلس الأعلى », il n'y a pas de marqueur « ملف رقم N قرار بتاريخ », les
dates sont rédigées en toutes lettres. En revanche le guide v4 indexe ces
numéros avec la page de début de chaque décision.

V2 (10/09/2026) : utilise offset_calculator pour convertir les pages du
guide en pages PDF, puis extrait le texte OCR pour chaque décision.

Pipeline :
1. Calculer l'offset guide→PDF pour chaque issue Legacy
2. Pour chaque décision dans revue_index :
   - Convertir guide_start_page → pdf_start_page via l'offset
   - Lire le texte OCR de pdf_start_page à pdf_end_page (page avant la décision suivante)
   - Stocker le texte dans revue_decision_texts
3. Mettre à jour pdf_start_page dans revue_decisions avec la page PDF corrigée

Usage : python sources/coursupreme/revue/segment_legacy.py [--dry-run]
"""

import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.append(str(ROOT / "tools"))

from offset_calculator import compute_all_offsets, OffsetConfidence  # noqa: E402
from revue_store import RevueStore  # noqa: E402
from segmenter import norm_number  # noqa: E402


def read_pages(pages_dir: Path, start_page: int, end_page: int) -> str:
    """Read and concatenate markdown content from page-{start} to page-{end} (inclusive)."""
    parts = []
    for pno in range(start_page, end_page + 1):
        md = pages_dir / f"page-{pno}" / "markdown.md"
        if md.exists():
            parts.append(md.read_text(encoding="utf-8"))
    return "\n\n".join(parts)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="No DB writes, just report")
    args = ap.parse_args()

    store = RevueStore()
    conn = store.connect()

    # Ensure schema is up to date (creates revue_decision_texts if needed)
    store.initialize_schema()

    # 1. Identify legacy issues (issues with index_guide decisions)
    legacy_issues = conn.execute("""
        SELECT DISTINCT issue_year, issue_number
        FROM revue_decisions WHERE source LIKE '%index_guide'
        ORDER BY issue_year, issue_number
    """).fetchall()
    print(f"Legacy issues to process: {len(legacy_issues)}")

    # 2. Compute offsets for all issues
    print("Computing offsets...")
    offsets = compute_all_offsets(conn, ROOT)

    # Store offsets in revue_offsets
    if not args.dry_run:
        for (y, n), result in offsets.items():
            conn.execute("""
                INSERT OR REPLACE INTO revue_offsets
                (issue_year, issue_number, offset_value, confidence, method,
                 samples, total_samples, consensus_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (y, n, result.offset, result.confidence.value, result.method,
                  result.samples, result.total_samples, result.consensus_pct))
        conn.commit()

    # 3. HTML matching index
    html = {}
    dconn = sqlite3.connect(ROOT / "databases" / "coursupreme.db")
    for r in dconn.execute(
            "SELECT decision_number, date FROM decisions WHERE status='telecharge'"):
        html.setdefault(norm_number(r[0]), []).append(r[1])

    # 4. Process each legacy issue
    stats = {
        "issues_processed": 0,
        "decisions_total": 0,
        "texts_extracted": 0,
        "texts_empty": 0,
        "by_confidence": Counter(),
        "match_stats": Counter(),
        "chars_total": 0,
    }

    for row in legacy_issues:
        year, number = row["issue_year"], row["issue_number"]
        offset_result = offsets.get((year, number))
        if not offset_result:
            print(f"  SKIP {year}/{number:02d}: no offset available")
            continue

        offset = offset_result.offset
        confidence = offset_result.confidence
        method = offset_result.method

        pages_dir = ROOT / "data" / "revue" / str(year) / f"issue_{number:02d}" / "pages"
        if not pages_dir.exists():
            print(f"  SKIP {year}/{number:02d}: no OCR pages directory")
            continue

        # Get max available page
        all_page_dirs = sorted(
            pages_dir.glob("page-*"), key=lambda p: int(p.name.split("-")[1])
        )
        max_pdf_page = int(all_page_dirs[-1].name.split("-")[1]) if all_page_dirs else 0

        # Get index entries sorted by start_page
        entries = conn.execute("""
            SELECT decision_number, decision_year, start_page, chamber, subject,
                   principle, legal_reference
            FROM revue_index
            WHERE issue_year=? AND issue_number=? AND decision_number IS NOT NULL
            AND start_page IS NOT NULL
            ORDER BY start_page
        """, (year, number)).fetchall()

        if not entries:
            continue

        # Get existing decision IDs for this issue (from legacy source)
        existing_decisions = conn.execute("""
            SELECT id, decision_number, pdf_start_page
            FROM revue_decisions
            WHERE issue_year=? AND issue_number=? AND source LIKE '%index_guide'
            ORDER BY pdf_start_page
        """, (year, number)).fetchall()

        # Build a map: (decision_number, pdf_start_page) → decision_id
        # For duplicates, we keep all IDs in a list keyed by decision_number
        dec_by_page = {}   # (decision_number, pdf_start_page) → id
        dec_by_num = {}    # decision_number → [id, ...]
        for d in existing_decisions:
            key = d["decision_number"]
            dec_by_page[(key, d["pdf_start_page"])] = d["id"]
            dec_by_num.setdefault(key, []).append(d["id"])

        # Track which decision IDs have been used (for duplicate handling)
        used_ids = set()

        # Process each index entry
        issue_extracted = 0
        for i, entry in enumerate(entries):
            guide_page = entry["start_page"]
            pdf_start = guide_page + offset

            # Compute pdf_end: next decision's start page - 1, or max page
            if i + 1 < len(entries):
                next_guide = entries[i + 1]["start_page"]
                pdf_end = (next_guide + offset) - 1
            else:
                pdf_end = max_pdf_page

            # Clamp to valid range
            pdf_start = max(1, min(pdf_start, max_pdf_page))
            pdf_end = max(pdf_start, min(pdf_end, max_pdf_page))

            # Extract text
            full_text = read_pages(pages_dir, pdf_start, pdf_end)
            char_count = len(full_text.strip())
            page_count = pdf_end - pdf_start + 1

            # Match verdict
            dec_num = entry["decision_number"]
            cands = html.get(norm_number(dec_num), [])
            if not cands:
                verdict = "NEW"
            elif any(c and c.startswith(str(entry["decision_year"] or "")) for c in cands):
                verdict = "MATCH_EXACT"
            else:
                verdict = "MATCH_PROBABLE"

            stats["match_stats"][verdict] += 1
            stats["by_confidence"][confidence.value] += 1
            stats["decisions_total"] += 1

            if char_count > 0:
                stats["texts_extracted"] += 1
                stats["chars_total"] += char_count
            else:
                stats["texts_empty"] += 1

            if not args.dry_run:
                # Find the decision_id: try exact (num, page) match first,
                # then take the first unused ID for this decision_number
                decision_id = dec_by_page.get((dec_num, guide_page))
                if decision_id is None:
                    # Fallback: take the first unused ID for this number
                    candidates = dec_by_num.get(dec_num, [])
                    for cid in candidates:
                        if cid not in used_ids:
                            decision_id = cid
                            break

                if decision_id and decision_id not in used_ids:
                    used_ids.add(decision_id)
                    conn.execute("""
                        UPDATE revue_decisions
                        SET pdf_start_page=?, match_verdict=?, chamber=?, chamber_raw=?,
                            subject=?, legal_references=?, principle=?
                        WHERE id=?
                    """, (pdf_start, verdict, entry["chamber"], entry["chamber"],
                          entry["subject"], entry["legal_reference"], entry["principle"],
                          decision_id))

                    # Insert or replace text
                    conn.execute("""
                        INSERT OR REPLACE INTO revue_decision_texts
                        (decision_id, full_text, pdf_start_page, pdf_end_page,
                         page_count, offset_used, offset_confidence, offset_method, char_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (decision_id, full_text, pdf_start, pdf_end,
                          page_count, offset, confidence.value, method, char_count))

                    issue_extracted += 1
                else:
                    # Decision not found in existing records — skip
                    # This can happen with duplicates
                    pass

        if not args.dry_run:
            conn.commit()

        stats["issues_processed"] += 1
        if stats["issues_processed"] % 5 == 0 or stats["issues_processed"] == len(legacy_issues):
            print(f"  [{stats['issues_processed']}/{len(legacy_issues)}] "
                  f"{year}/{number:02d}: {issue_extracted} texts, "
                  f"offset={offset:+d} ({confidence.value})")

    # 5. Final report
    print(f"\n{'='*60}")
    print(f"SEGMENT LEGACY V2 — RESULTS")
    print(f"{'='*60}")
    print(f"Issues processed: {stats['issues_processed']}/{len(legacy_issues)}")
    print(f"Decisions total:  {stats['decisions_total']}")
    print(f"Texts extracted:  {stats['texts_extracted']} "
          f"({stats['texts_extracted']/max(stats['decisions_total'],1)*100:.1f}%)")
    print(f"Texts empty:      {stats['texts_empty']}")
    print(f"Total characters: {stats['chars_total']:,}")
    print(f"Avg chars/text:   {stats['chars_total']/max(stats['texts_extracted'],1):,.0f}")
    print(f"\nBy confidence: {dict(stats['by_confidence'])}")
    print(f"Matching HTML:  {dict(stats['match_stats'])}")

    if not args.dry_run:
        # Verify
        text_count = conn.execute("SELECT COUNT(*) FROM revue_decision_texts").fetchone()[0]
        non_empty = conn.execute(
            "SELECT COUNT(*) FROM revue_decision_texts WHERE char_count > 0"
        ).fetchone()[0]
        print(f"\nDB verification:")
        print(f"  revue_decision_texts: {text_count} rows")
        print(f"  Non-empty texts:      {non_empty}")

    dconn.close()
    store.close()


if __name__ == "__main__":
    main()
