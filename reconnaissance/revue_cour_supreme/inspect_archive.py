"""Reconnaissance de la revue de la Cour suprême (مجلة المحكمة العليا).
ÉTAPE 1-2 : cartographie de la page de téléchargement + inventaire.

- parcourt la page https://coursupreme.dz/تحميل-مجلة-المحكمة-العليا/ et sa
  pagination éventuelle ;
- extrait les liens PDF et les liens vers guides/index ;
- NE TÉLÉCHARGE AUCUN PDF (sauf en-têtes si demandé explicitement) ;
- écrit reports/revue_cour_supreme_inventory.json.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.append(str(ROOT / "tools"))

from bs4 import BeautifulSoup  # noqa: E402
from http_client import JoradpClient, JoradpClientConfig  # noqa: E402

BASE = "https://coursupreme.dz"
PAGE_URL = f"{BASE}/تحميل-مجلة-المحكمة-العليا/"
OUT = ROOT / "reports"
USER_AGENT = "AlgerianLegalCorpusBot/0.1 (academic legal research; polite crawler)"


def last_page_number(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    pag = soup.find("div", class_="pagination")
    if not pag:
        return 1
    nums = []
    for a in pag.find_all("a", class_="page-numbers", href=True):
        m = re.search(r"(?:paged=|/page/)(\d+)", a["href"])
        if m:
            nums.append(int(m.group(1)))
    return max(nums) if nums else 1


def extract_items(html: str, page_url: str):
    """Items de la page : liens PDF, titres, liens guides/index."""
    soup = BeautifulSoup(html, "html.parser")
    pdfs, guides = [], []
    for a in soup.find_all("a", href=True):
        href = urljoin(page_url, a["href"])
        title = a.get_text(" ", strip=True)
        if href.lower().endswith(".pdf") or ".pdf?" in href.lower():
            # contexte : titre du parent proche
            ctx = title
            if not ctx:
                p = a.find_parent(["h1", "h2", "h3", "h4", "h5", "h6", "li", "article", "div"])
                ctx = p.get_text(" ", strip=True)[:120] if p else ""
            pdfs.append({"url": href, "titre_lien": title, "contexte": ctx})
        elif any(k in title for k in ("دليل", "فهرس", "فهارس")) or \
             any(k in href for k in ("dail", "fihris", "index", "guide")):
            guides.append({"url": href, "titre": title})
    return pdfs, guides


def main():
    config = JoradpClientConfig(user_agent=USER_AGENT)
    all_pdfs, all_guides, pages = [], [], 0

    with JoradpClient(config) as client:
        resp = client.get(PAGE_URL)
        if resp is None:
            print("ÉCHEC page principale")
            return
        (OUT / "revue_recon").mkdir(exist_ok=True)
        (OUT / "revue_recon" / "page1.html").write_bytes(resp.content)
        n_pages = last_page_number(resp.text)
        print(f"Page principale : HTTP {resp.status_code}, pagination={n_pages}")

        pdfs, guides = extract_items(resp.text, PAGE_URL)
        all_pdfs += pdfs
        all_guides += guides
        pages = 1

        for p in range(2, n_pages + 1):
            url = f"{PAGE_URL}page/{p}/"
            r = client.get(url)
            if r is None:
                print(f"  page {p}: ÉCHEC")
                continue
            pdfs, guides = extract_items(r.text, url)
            all_pdfs += pdfs
            all_guides += guides
            pages += 1
            print(f"  page {p}/{n_pages}: +{len(pdfs)} PDF")

    # déduplication par URL
    seen = set()
    uniq = []
    for p in all_pdfs:
        if p["url"] not in seen:
            seen.add(p["url"])
            uniq.append(p)

    inventory = {
        "source": PAGE_URL,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "listing_pages": pages,
        "pdf_links_total": len(all_pdfs),
        "pdf_links_unique": len(uniq),
        "guides": all_guides,
        "issues": [
            {"url": p["url"], "titre_lien": p["titre_lien"],
             "contexte": p["contexte"][:150], "pages": None,
             "size_bytes": None, "text_type": "UNKNOWN", "status": "ACCESSIBLE"}
            for p in uniq
        ],
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "revue_cour_supreme_inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\nPDF uniques : {len(uniq)} sur {pages} pages de listing")
    print(f"Guides/index trouvés : {len(all_guides)}")
    for g in all_guides[:10]:
        print(f"  - {g['titre'][:50]} : {g['url'][:90]}")
    print(f"\nInventaire : {OUT / 'revue_cour_supreme_inventory.json'}")
    print("\nÉchantillon des PDF :")
    for p in uniq[:15]:
        print(f"  {p['titre_lien'][:40]:42s} {p['contexte'][:60]:62s} {p['url'][:80]}")


if __name__ == "__main__":
    main()
