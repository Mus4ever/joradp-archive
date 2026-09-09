"""Volumétrie réelle de coursupreme.dz : parcours complet de la pagination
des 6 catégories officielles, comptage des URLs de décisions uniques.

- utilise la div.pagination (dernier numéro de page = borne haute fiable)
- ne télécharge QUE les pages de listing, jamais les décisions
- rate limit : celui du client JORADP (2 s global)
"""

import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from bs4 import BeautifulSoup  # noqa: E402
from http_client import JoradpClient, JoradpClientConfig  # noqa: E402

BASE = "https://coursupreme.dz"
OUT = Path(__file__).resolve().parents[2] / "reports" / "coursupreme_recon"

CATEGORIES = {
    "themes": "قرارات-مصنفة-حسب-المواضيع",
    "penales": "الغرف-الجزائية",
    "civiles": "الغرف-المدنية",
    "indemnisation": "لجنة-التعويض",
    "reunies": "الغرف-المجتمعة",
    "importantes": "قرارات-مهمة",
}

CONFIG = JoradpClientConfig(
    user_agent="AlgerianLegalCorpusBot/0.1 (academic legal research; polite crawler)"
)


def decision_urls(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    urls = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        if re.search(r"/decision/[^/]+/?$", href):
            urls.add(href.split("?")[0].rstrip("/") + "/")
    return urls


def max_page(html, base_url):
    """Dernière page annoncée par la div.pagination (0 si pagination absente)."""
    soup = BeautifulSoup(html, "html.parser")
    pag = soup.find("div", class_="pagination")
    if not pag:
        return 1
    nums = []
    for a in pag.find_all("a", class_="page-numbers", href=True):
        m = re.search(r"paged=(\d+)", urljoin(base_url, a["href"]))
        if m:
            nums.append(int(m.group(1)))
    return max(nums) if nums else 1


def main():
    report = {}
    all_urls = {}

    with JoradpClient(CONFIG) as client:
        for name, slug in CATEGORIES.items():
            page1_url = f"{BASE}/{slug}/"
            t0 = time.time()
            resp = client.get(page1_url)
            if resp is None:
                report[name] = {"url": page1_url, "error": "fetch failed page 1"}
                print(f"[FAIL] {name}: page 1")
                continue
            n_pages = max_page(resp.text, page1_url)
            urls = decision_urls(resp.text, page1_url)
            print(f"[{name}] page 1 : {len(urls)} décisions, pagination jusqu'à {n_pages} pages")
            # Format canonique /page/N/ (constat 09/09/2026) : ?paged=N renvoie
            # un 301 que le client ne suit pas ; /page/N/ répond directement 200.
            for p in range(2, n_pages + 1):
                url = f"{page1_url}page/{p}/"
                r = client.get(url)
                if r is None:
                    print(f"  [FAIL] {name} page {p}")
                    continue
                found = decision_urls(r.text, url)
                urls |= found
                if p % 10 == 0 or p == n_pages:
                    print(f"  [{name}] page {p}/{n_pages} : cumul {len(urls)}")
            report[name] = {
                "url": page1_url,
                "http": resp.status_code,
                "pages": n_pages,
                "unique_decisions": len(urls),
            }
            all_urls[name] = sorted(urls)

    total_unique = set()
    for urls in all_urls.values():
        total_unique |= set(urls)

    report["_TOTAL"] = {"unique_decisions_toutes_categories": len(total_unique)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "volumetrie.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "decision_urls_par_categorie.json").write_text(
        json.dumps(all_urls, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\n=== RÉSUMÉ VOLUMÉTRIE ===")
    for name, info in report.items():
        if name == "_TOTAL":
            continue
        if "error" in info:
            print(f"{name}: ERREUR ({info['error']})")
        else:
            print(f"{name}: {info['pages']} pages, {info['unique_decisions']} décisions uniques")
    print(f"TOTAL unique toutes catégories: {len(total_unique)}")
    print(f"Durée: {time.time() - t0:.0f}s (dernière catégorie)")


if __name__ == "__main__":
    main()
