"""Calcul de l'offset guide→PDF par numéro de revue.

L'index du Guide de recherche (v4) donne la page IMPRIMÉE de chaque décision.
Les fichiers OCR sont nommés page-N où N est la page du fichier PDF.
L'offset = pdf_page - guide_page est constant au sein d'un même numéro,
mais varie d'un numéro à l'autre.

Trois méthodes de calcul, par ordre de fiabilité décroissante :

1. TEXT_MARKERS — Croise les décisions déjà segmentées par le segmenteur
   OCR (text_markers, qui a trouvé des marqueurs dans le texte) avec les
   entrées revue_index. La page OCR est la vérité terrain, la page index
   est la page imprimée → offset = ocr_page - index_page.

2. PAGE_FOOTERS — Scanne les dernières lignes de chaque page OCR à la
   recherche du motif strict « - N - » (N = page imprimée). Compare avec
   le numéro de page PDF pour déduire l'offset.

3. TEXT_SEARCH — Pour les issues sans aucune source fiable, cherche le
   numéro de décision (du guide) dans les pages OCR pour localiser la
   page physique, puis en déduit l'offset.

Usage :
    from offset_calculator import compute_all_offsets
    offsets = compute_all_offsets(conn, data_root)
    # offsets = {(year, num): OffsetResult(offset, confidence, method, samples)}
"""

import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Tuple

__all__ = ["OffsetConfidence", "OffsetResult", "compute_offset", "compute_all_offsets"]


class OffsetConfidence(Enum):
    HIGH = "HIGH"           # ≥5 concordant samples, ≥80% consensus
    MEDIUM = "MEDIUM"       # 2-4 concordant samples, or ≥60% consensus
    LOW = "LOW"             # 1 sample or <60% consensus
    FALLBACK = "FALLBACK"   # offset=0 assumed, no evidence
    NONE = "NONE"           # could not compute


@dataclass
class OffsetResult:
    offset: int
    confidence: OffsetConfidence
    method: str                # "text_markers" | "page_footers" | "text_search" | "fallback"
    samples: int               # number of concordant samples
    total_samples: int         # total samples evaluated
    consensus_pct: float       # % concordant / total

    def pdf_page(self, guide_page: int) -> int:
        """Convert a guide (printed) page to a PDF page number."""
        return guide_page + self.offset


# Strict page footer pattern: « - N - » only
_STRICT_FOOTER_RE = re.compile(r"^\s*-\s*(\d+)\s*-\s*$")


def _offset_from_text_markers(
    conn: sqlite3.Connection, year: int, num: int
) -> Optional[OffsetResult]:
    """Method 1: cross-reference text_markers decisions with index entries."""
    text_decs = conn.execute(
        "SELECT decision_number, pdf_start_page FROM revue_decisions "
        "WHERE issue_year=? AND issue_number=? AND source NOT LIKE '%index_guide' "
        "AND decision_number IS NOT NULL AND pdf_start_page IS NOT NULL",
        (year, num),
    ).fetchall()
    if not text_decs:
        return None

    idx = {}
    for r in conn.execute(
        "SELECT decision_number, start_page FROM revue_index "
        "WHERE issue_year=? AND issue_number=? AND start_page IS NOT NULL",
        (year, num),
    ):
        norm = (r["decision_number"] or "").lstrip("0") or "0"
        idx[norm] = r["start_page"]

    offsets = []
    for d in text_decs:
        norm = (d["decision_number"] or "").lstrip("0") or "0"
        if norm in idx:
            offsets.append(d["pdf_start_page"] - idx[norm])

    if not offsets:
        return None

    dist = Counter(offsets)
    best, cnt = dist.most_common(1)[0]
    total = len(offsets)
    pct = cnt / total * 100

    if cnt >= 5 and pct >= 80:
        conf = OffsetConfidence.HIGH
    elif cnt >= 2 and pct >= 60:
        conf = OffsetConfidence.MEDIUM
    elif cnt >= 1:
        conf = OffsetConfidence.LOW
    else:
        return None

    return OffsetResult(best, conf, "text_markers", cnt, total, round(pct, 1))


def _offset_from_page_footers(
    data_root: Path, year: int, num: int, max_pages: int = 150
) -> Optional[OffsetResult]:
    """Method 2: scan OCR page footers for strict « - N - » pattern."""
    pages_dir = data_root / "data" / "revue" / str(year) / f"issue_{num:02d}" / "pages"
    if not pages_dir.exists():
        return None

    page_dirs = sorted(
        pages_dir.glob("page-*"), key=lambda p: int(p.name.split("-")[1])
    )
    mappings = []
    for pd in page_dirs[:max_pages]:
        pdf_page = int(pd.name.split("-")[1])
        md = pd / "markdown.md"
        if not md.exists():
            continue
        text = md.read_text(encoding="utf-8").strip()
        lines = text.split("\n")
        for line in lines[-3:]:
            m = _STRICT_FOOTER_RE.match(line.strip())
            if m:
                printed = int(m.group(1))
                if 1 <= printed <= 2000:
                    mappings.append((pdf_page, printed))
                    break

    if not mappings:
        return None

    offsets = [pdf - pr for pdf, pr in mappings]
    dist = Counter(offsets)
    best, cnt = dist.most_common(1)[0]
    total = len(offsets)
    pct = cnt / total * 100

    # Reject if the best offset looks absurd (|offset| > 20)
    if abs(best) > 20:
        return None

    if cnt >= 5 and pct >= 80:
        conf = OffsetConfidence.HIGH
    elif cnt >= 2 and pct >= 60:
        conf = OffsetConfidence.MEDIUM
    elif cnt >= 1:
        conf = OffsetConfidence.LOW
    else:
        return None

    return OffsetResult(best, conf, "page_footers", cnt, total, round(pct, 1))


def _offset_from_text_search(
    conn: sqlite3.Connection, data_root: Path, year: int, num: int
) -> Optional[OffsetResult]:
    """Method 3: search for decision numbers in OCR text to find their page."""
    pages_dir = data_root / "data" / "revue" / str(year) / f"issue_{num:02d}" / "pages"
    if not pages_dir.exists():
        return None

    # Get index entries with start_page
    entries = conn.execute(
        "SELECT decision_number, start_page FROM revue_index "
        "WHERE issue_year=? AND issue_number=? "
        "AND decision_number IS NOT NULL AND start_page IS NOT NULL "
        "ORDER BY start_page LIMIT 20",
        (year, num),
    ).fetchall()
    if not entries:
        return None

    # Build a page text cache (limited to avoid memory explosion)
    page_dirs = sorted(
        pages_dir.glob("page-*"), key=lambda p: int(p.name.split("-")[1])
    )
    page_texts = {}
    for pd in page_dirs:
        pno = int(pd.name.split("-")[1])
        md = pd / "markdown.md"
        if md.exists():
            page_texts[pno] = md.read_text(encoding="utf-8")

    if not page_texts:
        return None

    offsets = []
    for entry in entries:
        dec_num = entry["decision_number"]
        guide_page = entry["start_page"]
        # Search for decision_number in pages near the expected range
        # Try offsets from -10 to +10 around guide_page
        for try_offset in range(-10, 11):
            pdf_page = guide_page + try_offset
            if pdf_page in page_texts and dec_num in page_texts[pdf_page]:
                offsets.append(try_offset)
                break

    if not offsets:
        return None

    dist = Counter(offsets)
    best, cnt = dist.most_common(1)[0]
    total = len(offsets)
    pct = cnt / total * 100

    if cnt >= 3 and pct >= 70:
        conf = OffsetConfidence.MEDIUM
    elif cnt >= 1:
        conf = OffsetConfidence.LOW
    else:
        return None

    return OffsetResult(best, conf, "text_search", cnt, total, round(pct, 1))


def compute_offset(
    conn: sqlite3.Connection, data_root: Path, year: int, num: int
) -> OffsetResult:
    """Compute offset for a single issue, trying all methods in order."""
    # Method 1: text_markers
    result = _offset_from_text_markers(conn, year, num)
    if result and result.confidence in (OffsetConfidence.HIGH, OffsetConfidence.MEDIUM):
        return result

    # Method 2: page footers
    result2 = _offset_from_page_footers(data_root, year, num)
    if result2 and result2.confidence in (OffsetConfidence.HIGH, OffsetConfidence.MEDIUM):
        return result2

    # Keep low-confidence text_markers if available
    if result:
        return result
    if result2:
        return result2

    # Method 3: text search
    result3 = _offset_from_text_search(conn, data_root, year, num)
    if result3:
        return result3

    # Fallback: assume offset=0
    return OffsetResult(0, OffsetConfidence.FALLBACK, "fallback", 0, 0, 0.0)


def compute_all_offsets(
    conn: sqlite3.Connection, data_root: Path
) -> Dict[Tuple[int, int], OffsetResult]:
    """Compute offsets for all issues that have index entries."""
    issues = conn.execute(
        "SELECT DISTINCT issue_year, issue_number FROM revue_index "
        "WHERE issue_year IS NOT NULL AND issue_number IS NOT NULL "
        "ORDER BY issue_year, issue_number"
    ).fetchall()

    results = {}
    for row in issues:
        y, n = row["issue_year"], row["issue_number"]
        results[(y, n)] = compute_offset(conn, data_root, y, n)

    return results


# --- CLI for testing ---
if __name__ == "__main__":
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[3]
    db_path = ROOT / "databases" / "coursupreme_revue.db"

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    offsets = compute_all_offsets(conn, ROOT)

    # Stats
    by_conf = Counter(r.confidence.value for r in offsets.values())
    by_method = Counter(r.method for r in offsets.values())

    print(f"Total issues: {len(offsets)}")
    print(f"By confidence: {dict(by_conf)}")
    print(f"By method: {dict(by_method)}")

    # Legacy-specific
    legacy = conn.execute(
        "SELECT DISTINCT issue_year, issue_number FROM revue_decisions "
        "WHERE source LIKE '%index_guide' ORDER BY issue_year, issue_number"
    ).fetchall()

    print(f"\n=== LEGACY ISSUES ({len(legacy)}) ===")
    for row in legacy:
        y, n = row["issue_year"], row["issue_number"]
        r = offsets.get((y, n))
        if r:
            print(
                f"  {y}/{n:02d}: offset={r.offset:+d}  "
                f"conf={r.confidence.value:<8s}  method={r.method:<14s}  "
                f"samples={r.samples}/{r.total_samples}"
            )
        else:
            print(f"  {y}/{n:02d}: NOT COMPUTED")

    conn.close()
