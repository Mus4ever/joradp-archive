"""Parser du guide de recherche — Phase 3, approche géométrique.

extract_table() décale les cellules de données par rapport à l'en-tête
(cellules fusionnées). On utilise donc la GRILLE GÉOMÉTRIQUE de la table :
  1. find_tables() → grille de cellules (bboxes) par ligne/colonne ;
  2. la ligne d'en-tête est identifiée par son texte → mapping champ→colonne
     via le x-center des cellules d'en-tête ;
  3. les mots de la page (extract_words, ordre logique) sont assignés aux
     cellules par coordonnées (fallback par x-center si cellule fusionnée) ;
  4. chaque cellule → normalize_guide_text (bidi visuel→logique + NFKC,
     non destructif). raw_text de la page conservé.
"""

import sys
import time
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.append(str(ROOT / "tools"))

import pdfplumber  # noqa: E402

from arabic_normalize import normalize_guide_text  # noqa: E402
from revue_store import RevueStore  # noqa: E402

GUIDES = {
    "v4": ROOT / "data" / "revue" / "guide_دليل-البحث-الطبعة-الرابعة_b26b27fe.pdf",
    "v3": next((ROOT / "data" / "revue").glob("guide__D8_AF_D9_84*74e5019d.pdf"), None),
}

_HEADER_ALIASES = {
    "رقم القار": "decision_number",   # extraction : 'رقم القارر' (défaut mineur)
    "الصفحة": "start_page",
    "السنة": "decision_year",
    "العدد": "issue_number",
    "الغرفة": "chamber",
    "المرجع القانوني": "legal_reference",
    "المبدأ": "principle",
    "الموضوع": "subject",
}


def _xcenter(bbox):
    return (bbox[0] + bbox[2]) / 2


def _ycenter(bbox):
    return (bbox[1] + bbox[3]) / 2


def _match_header(text: str) -> Optional[str]:
    """Correspondance d'alias tolérante aux espaces parasites de l'extraction
    (ex. 'رقم الق ارر')."""
    if not text:
        return None
    compact = text.replace(" ", "")
    for alias, field in _HEADER_ALIASES.items():
        if alias.replace(" ", "") in compact:
            return field
    return None


def parse_page(page, log=None) -> list:
    """Retourne les entrées d'une page (liste de dicts) ou []."""
    tables = page.find_tables()
    if not tables:
        return []
    tbl = tables[0]
    grid = tbl.rows  # chaque row: .cells = [bbox ou None, ...]

    # --- 1. trouver la ligne d'en-tête et le mapping champ→x ---------------
    header_i, col_map = None, {}  # col_map: {champ: [x0,x1] de la colonne}
    words = page.extract_words()
    for ri, row in enumerate(grid):
        texts = []
        for cell in row.cells:
            if cell is None:
                texts.append("")
                continue
            crop = page.crop(cell).extract_text(x_tolerance=1.5) or ""
            texts.append(normalize_guide_text(crop) or "")
        joined = " ".join(texts)
        if _match_header(joined):
            header_i = ri
            for ci, cell in enumerate(row.cells):
                if cell is None:
                    continue
                t = normalize_guide_text(
                    page.crop(cell).extract_text(x_tolerance=1.5) or "")
                field = _match_header(t)
                if field:
                    col_map[field] = [cell[0], cell[2]]
            break
    if header_i is None or "decision_number" not in col_map:
        return []

    # frontières x entre colonnes (milieux entre colonnes adjacentes,
    # triées de gauche à droite = ordre visuel)
    ordered = sorted(col_map.items(), key=lambda kv: kv[1][0])

    def column_of(x: float) -> Optional[str]:
        for field, (x0, x1) in ordered:
            if x0 - 8 <= x <= x1 + 8:
                return field
        # fallback : colonne la plus proche
        best, bestd = None, 1e9
        for field, (x0, x1) in ordered:
            d = min(abs(x - x0), abs(x - x1))
            if d < bestd:
                best, bestd = field, d
        return best if bestd < 30 else None

    # --- 2. lignes de données : bandes y entre lignes de la grille ---------
    entries = []
    bounds = []  # (top, bottom) de chaque ligne de données
    for ri in range(header_i + 1, len(grid)):
        cells = grid[ri].cells
        tops = [c[1] for c in cells if c]
        bots = [c[3] for c in cells if c]
        if tops:
            bounds.append((min(tops), max(bots), ri))

    for bi, (top, bottom, ri) in enumerate(bounds):
        cell_words = {f: [] for f in col_map}
        for w in words:
            wy = (w["top"] + w["bottom"]) / 2
            if not (top - 2 <= wy <= bottom + 2):
                continue
            wx = (w["x0"] + w["x1"]) / 2
            f = column_of(wx)
            if f:
                cell_words[f].append(w)

        cells = {}
        for f, ws in cell_words.items():
            # regrouper par ligne y puis lire droite→gauche (RTL)
            lines = {}
            for w in ws:
                lines.setdefault(round(w["top"] / 4), []).append(w)
            txt = "\n".join(
                " ".join(w["text"] for w in sorted(l, key=lambda w: -w["x0"]))
                for _, l in sorted(lines.items())
            )
            cells[f] = normalize_guide_text(txt) if txt else None

        if not cells.get("decision_number"):
            if any(cells.values()):
                entries.append({
                    "source_pdf": "", "source_page": page.page_number,
                    "raw_text": str({k: v for k, v in cells.items() if v})[:2000],
                    "parser_status": "error",
                })
            continue

        num = cells["decision_number"].replace(" ", "")
        try:
            year = int(cells["decision_year"].split("-")[0]) if cells.get("decision_year") else None
        except (ValueError, AttributeError):
            year = None
        try:
            spage = int(cells["start_page"].replace(" ", "")) if cells.get("start_page") else None
        except (ValueError, AttributeError):
            spage = None

        entries.append({
            "decision_number": num,
            "decision_year": year,
            "issue_number": _to_int(cells.get("issue_number")),
            "issue_year": year,  # hypothèse documentée : numérotation par année
            "start_page": spage,
            "chamber": cells.get("chamber"),
            "subject": cells.get("subject"),
            "principle": cells.get("principle"),
            "legal_reference": cells.get("legal_reference"),
            "source_pdf": "",  # rempli par l'appelant
            "source_page": page.page_number,
            "raw_text": str({k: v for k, v in cells.items() if v})[:4000],
            "normalized_text": str({k: v for k, v in cells.items() if v})[:4000],
            "parser_status": "ok" if (year and spage) else "partial",
        })
    return entries


def _to_int(s):
    if not s:
        return None
    try:
        return int(s.replace(" ", ""))
    except ValueError:
        return None


def parse_guide(pdf_path: Path, store: RevueStore, max_pages: Optional[int] = None,
                log=print) -> dict:
    stats = {"pages": 0, "entrees": 0, "ok": 0, "partial": 0, "error": 0}
    entries = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        n_pages = len(pdf.pages) if not max_pages else min(len(pdf.pages), max_pages)
        log(f"Guide : {pdf_path.name} — {n_pages} pages")
        for pno in range(n_pages):
            page = pdf.pages[pno]
            stats["pages"] += 1
            page_entries = parse_page(page)
            for e in page_entries:
                e["source_pdf"] = pdf_path.name
            entries += page_entries
            for e in page_entries:
                stats[e["parser_status"]] += 1
            if pno % 25 == 0:
                log(f"  page {pno+1}/{n_pages} : {len(entries)} entrées cumulées")
            if len(entries) >= 400:
                stats["entrees"] += store.insert_entries(entries)
                entries = []
    if entries:
        stats["entrees"] += store.insert_entries(entries)
    return stats


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Parse guide → revue_index")
    ap.add_argument("--guide", choices=["v4", "v3"], default="v4")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    pdf_path = GUIDES[args.guide]
    store = RevueStore()
    t0 = time.time()
    with store:
        stats = parse_guide(pdf_path, store, max_pages=args.limit)
        print(f"Pages: {stats['pages']} | entrées: {stats['entrees']} "
              f"(ok {stats['ok']}, partial {stats['partial']}, error {stats['error']})")
        print(f"Index : {store.index_stats()}")
        print(f"Durée : {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
