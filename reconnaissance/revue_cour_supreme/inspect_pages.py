"""ÉTAPE 2 (suite) : visiter les sous-pages de numéros/guides trouvées sur la
page de téléchargement et en extraire les PDF réels.

Ne télécharge PAS les PDF : requêtes HEAD/GET des pages uniquement
(le GET des pages est nécessaire car les liens PDF sont dans le HTML).
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.append(str(ROOT / "tools"))

from bs4 import BeautifulSoup  # noqa: E402
from http_client import JoradpClient, JoradpClientConfig  # noqa: E402

BASE = "https://coursupreme.dz"
OUT = ROOT / "reports"
USER_AGENT = "AlgerianLegalCorpusBot/0.1 (academic legal research; polite crawler)"

# Sous-pages identifiées sur la page de téléchargement (09/09/2026)
SUBPAGES = [
    ("revue_special_civil", "مجلة-المحكمة-العليـا-عدد-خاص-المسوؤلي-2"),
    ("guide_recherche_v4", "دليل-البحث-في-مجلة-المحكمة-العليـا-الط-2"),
    ("guide_indemnisation_v2", "دليل-قرارات-لجنة-التعويض-المنشورة-في-م-2"),
    ("revue_2023_01", "مجلة-المحكمة-العليــا-العدد-01-2023"),
    ("revue_2022_02", "مجلة-المحكمة-العليــا-العدد-02-2022"),
    ("revue_2022_01", "مجلة-المحكمة-العليــا-العدد-01-2022"),
    ("revue_special_role", "مجلة-المحكمة-العليـا-عدد-خاص-دور-التش"),
    ("guide_recherche_v3", "دليل-البحث-في-مجلة-المحكمة-العليـا-الط"),
    ("guide_indemnisation_v1", "دليل-قرارات-لجنة-التعويض-المنشورة-في-م"),
    ("revue_2021_02", "مجلة-المحكمة-العليا-العدد-02-2021"),
]


def find_pdfs(html: str, page_url: str):
    """PDF dans une page : liens .pdf + iframes + embeds + boutons download."""
    soup = BeautifulSoup(html, "html.parser")
    found = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(page_url, a["href"])
        if ".pdf" in href.lower():
            found.add(href)
    for tag in soup.find_all(["iframe", "embed", "object"]):
        src = tag.get("src") or tag.get("data")
        if src and ".pdf" in src.lower():
            found.add(urljoin(page_url, src))
    # boutons/onclick avec URL pdf
    for m in re.finditer(r"[\"'](https?://[^\"']+?\.pdf[^\"']*)[\"']", html):
        found.add(m.group(1))
    for m in re.finditer(r"[\"'](/[^\"']*?\.pdf[^\"']*)[\"']", html):
        found.add(urljoin(page_url, m.group(1)))
    return found


def main():
    config = JoradpClientConfig(user_agent=USER_AGENT)
    results = {}

    with JoradpClient(config) as client:
        for label, slug in SUBPAGES:
            url = f"{BASE}/{slug}/"
            resp = client.get(url)
            if resp is None:
                results[label] = {"page": url, "statut": "ÉCHEC", "pdfs": []}
                print(f"[{label}] ÉCHEC")
                continue
            pdfs = find_pdfs(resp.text, url)
            (OUT / "revue_recon").mkdir(exist_ok=True)
            (OUT / "revue_recon" / f"{label}.html").write_bytes(resp.content)
            results[label] = {"page": url, "http": resp.status_code, "pdfs": sorted(pdfs)}
            print(f"[{label}] HTTP {resp.status_code}, {len(pdfs)} PDF: ")
            for p in sorted(pdfs):
                print(f"    {unquote(p)[:110]}")

    (OUT / "revue_recon" / "subpages_pdfs.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nRésultat : {OUT / 'revue_recon' / 'subpages_pdfs.json'}")


if __name__ == "__main__":
    main()
