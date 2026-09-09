"""Reconnaissance technique de coursupreme.dz — Phase 1 du plan.

Utilise l'infrastructure JORADP (client TLS legacy + rate limiter global).
Sauvegarde le HTML brut dans reports/coursupreme_recon/ pour analyse hors ligne.
N'invente rien : tout ce qui est reporté a été réellement récupéré.
"""

import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from http_client import JoradpClient, JoradpClientConfig  # noqa: E402

BASE = "https://coursupreme.dz"
OUT = Path(__file__).resolve().parents[2] / "reports" / "coursupreme_recon"
OUT.mkdir(parents=True, exist_ok=True)

CONFIG = JoradpClientConfig(
    user_agent="AlgerianLegalCorpusBot/0.1 (academic legal research; polite crawler)"
)

CATEGORY_PAGES = {
    "themes": "/قرارات-مصنفة-حسب-المواضيع/",
    "penales": "/الغرف-الجزائية/",
    "civiles": "/الغرف-المدنية/",
    "indemnisation": "/لجنة-التعويض/",
    "reunies": "/الغرف-الاجتماعية/",
    "importantes": "/قرارات-مهمة/",
}


def fetch(client, url, label):
    t0 = time.time()
    resp = client.get(url)
    dt = time.time() - t0
    if resp is None:
        print(f"  [FAIL] {label}: {url}")
        return None
    size = len(resp.content)
    print(f"  [OK] {label}: HTTP {resp.status_code}, {size} octets, {dt:.1f}s")
    return resp


def slug_dir(url):
    """Nom de fichier stable pour une URL."""
    tail = unquote(urlparse(url).path).strip("/").replace("/", "_")
    tail = re.sub(r"[^\w\-\.]", "_", tail)
    return tail[:120] or "root"


def save_html(url, resp, subdir):
    d = OUT / subdir
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{slug_dir(url)}.html"
    p.write_bytes(resp.content)
    return p


def main():
    result = {"robots": None, "categories": {}, "decision_samples": []}

    with JoradpClient(CONFIG) as client:
        # 1. robots.txt
        print("== robots.txt ==")
        resp = fetch(client, f"{BASE}/robots.txt", "robots.txt")
        if resp is not None:
            text = resp.text
            (OUT / "robots.txt").write_text(text, encoding="utf-8")
            result["robots"] = text
            print(text if len(text) < 2000 else text[:2000] + "... [tronqué]")

        # 2. homepage : tous les liens
        print("\n== homepage ==")
        resp = fetch(client, f"{BASE}/", "homepage")
        if resp is not None:
            save_html(f"{BASE}/", resp, "listings")
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(resp.text, "html.parser")
            links = set()
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith(BASE) or href.startswith("/"):
                    links.add(href)
            decision_links = {l for l in links if "/decision/" in l}
            page_links = {l for l in links if "/page/" in l}
            print(f"  liens internes: {len(links)}, /decision/: {len(decision_links)}, pagination: {len(page_links)}")
            result["homepage"] = {
                "internal_links": len(links),
                "decision_links": sorted(decision_links),
                "page_links": sorted(page_links),
            }

        # 3. pages de catégories
        print("\n== catégories ==")
        from bs4 import BeautifulSoup

        for name, path in CATEGORY_PAGES.items():
            url = BASE + path
            resp = fetch(client, url, f"cat {name}")
            if resp is None:
                result["categories"][name] = {"url": url, "error": "fetch failed"}
                continue
            save_html(url, resp, "listings")
            soup = BeautifulSoup(resp.text, "html.parser")
            dec = {a["href"] for a in soup.find_all("a", href=True) if "/decision/" in a["href"]}
            pag = {a["href"] for a in soup.find_all("a", href=True) if re.search(r"/page/\d+/?$", a["href"])}
            nums = sorted(int(m.group(1)) for p in pag for m in [re.search(r"/page/(\d+)/?", p)] if m)
            result["categories"][name] = {
                "url": url,
                "http": resp.status_code,
                "decision_links_on_page": len(dec),
                "pagination_links": sorted(pag),
                "max_page_seen": nums[-1] if nums else None,
            }
            print(f"    décisions sur page: {len(dec)}, pages vues: {sorted(nums)[:10]}")

        # 4. vérification pagination : page 2 d'une catégorie
        print("\n== pagination (page 2 de 'civiles') ==")
        url2 = BASE + CATEGORY_PAGES["civiles"] + "page/2/"
        resp = fetch(client, url2, "civiles page/2")
        if resp is not None:
            save_html(url2, resp, "listings")
            soup = BeautifulSoup(resp.text, "html.parser")
            dec = {a["href"] for a in soup.find_all("a", href=True) if "/decision/" in a["href"]}
            print(f"    décisions sur page 2: {len(dec)}")
            result["pagination_check"] = {"url": url2, "decisions_on_page2": len(dec)}

        # 5. échantillon de décisions (2+ par catégorie)
        print("\n== échantillon de décisions ==")
        seen = []
        for name, path in CATEGORY_PAGES.items():
            resp = fetch(client, BASE + path, f"re-cat {name}")
            if resp is None:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            dec = [a["href"] for a in soup.find_all("a", href=True) if "/decision/" in a["href"]]
            for url in dec[:2]:
                if url in seen:
                    continue
                seen.append(url)
                r = fetch(client, url, f"decision [{name}]")
                if r is not None:
                    p = save_html(url, r, "decisions")
                    result["decision_samples"].append(
                        {"category": name, "url": url, "http": r.status_code, "bytes": len(r.content), "saved": p.name}
                    )

    (OUT / "recon_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nRésumé écrit: {OUT / 'recon_summary.json'}")
    print(f"Décisions échantillonnées: {len(result['decision_samples'])}")


if __name__ == "__main__":
    main()
