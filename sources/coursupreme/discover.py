"""Découverte des URLs de décisions sur coursupreme.dz.

Méthode validée (voir docs/coursupreme.md) :
- 6 catégories officielles (slugs réels extraits du HTML de la page d'accueil) ;
- pagination canonique /page/N/ (le format ?paged=N renvoie un 301) ;
- dernière page lue dans div.pagination (aucun probing au-delà) ;
- arrêt de sécurité si une page ne liste plus aucune décision.
"""

import re
import sys
from pathlib import Path
from typing import Dict, Iterable, Optional, Set
from urllib.parse import urljoin

sys.path.append(str(Path(__file__).resolve().parents[2] / "tools"))

from bs4 import BeautifulSoup  # noqa: E402
from http_client import JoradpClient, JoradpClientConfig  # noqa: E402

from parser import is_decision_url  # noqa: E402
from storage import DecisionStore  # noqa: E402

BASE = "https://coursupreme.dz"

# Slugs réels (extraits du HTML de la page d'accueil, 09/09/2026).
CATEGORIES = {
    "themes": "قرارات-مصنفة-حسب-المواضيع",
    "penales": "الغرف-الجزائية",
    "civiles": "الغرف-المدنية",
    "indemnisation": "لجنة-التعويض",
    "reunies": "الغرف-المجتمعة",
    "importantes": "قرارات-مهمة",
}

USER_AGENT = "AlgerianLegalCorpusBot/0.1 (academic legal research; polite crawler)"


def normalize_url(href: str, base_url: str = BASE) -> str:
    """URL absolue canonique d'une décision : sans query, sans fragment,
    slash final — clé de déduplication stable."""
    url = urljoin(base_url, href)
    url = url.split("#")[0].split("?")[0]
    if not url.endswith("/"):
        url += "/"
    return url


def extract_decision_urls(html: str, base_url: str) -> Set[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls = set()
    for a in soup.find_all("a", href=True):
        url = normalize_url(a["href"], base_url)
        if is_decision_url(url):
            urls.add(url)
    return urls


def last_page_number(html: str) -> int:
    """Dernière page annoncée par div.pagination (1 si absente)."""
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


def discover_category(client: JoradpClient, name: str, slug: str,
                      store: Optional[DecisionStore] = None,
                      log=print) -> Dict:
    """Parcourt toute la pagination d'une catégorie et enregistre les URLs.

    Retourne un résumé {pages, nouvelles, total_uniques, erreurs}.
    """
    page1_url = f"{BASE}/{slug}/"
    resp = client.get(page1_url)
    if resp is None:
        log(f"[{name}] ÉCHEC page 1 — catégorie abandonnée")
        return {"pages": 0, "nouvelles": 0, "total_uniques": 0, "erreurs": 1}

    n_pages = last_page_number(resp.text)
    urls = extract_decision_urls(resp.text, page1_url)
    errors = 0
    pages_fetched = 1

    for p in range(2, n_pages + 1):
        url = f"{page1_url}page/{p}/"
        r = client.get(url)
        if r is None:
            errors += 1
            log(f"[{name}] page {p}/{n_pages} : ÉCHEC réseau")
            continue
        found = extract_decision_urls(r.text, url)
        if not found:
            # Sécurité : page sans décision = fin réelle ou page vide → on stoppe.
            log(f"[{name}] page {p}/{n_pages} : 0 décision, arrêt de la catégorie")
            break
        urls |= found
        pages_fetched += 1
        if p % 10 == 0:
            log(f"[{name}] page {p}/{n_pages} : cumul {len(urls)} URLs")

    nouvelles = 0
    if store is not None:
        nouvelles = store.add_discovered_batch((u, name) for u in sorted(urls))

    log(f"[{name}] terminé : {pages_fetched} pages lues, {len(urls)} URLs uniques, "
        f"{nouvelles} nouvelles en base")
    return {"pages": pages_fetched, "nouvelles": nouvelles,
            "total_uniques": len(urls), "erreurs": errors}


def discover_all(store: DecisionStore, categories: Optional[Iterable[str]] = None,
                 log=print) -> Dict[str, Dict]:
    config = JoradpClientConfig(user_agent=USER_AGENT)
    summary = {}
    with JoradpClient(config) as client:
        wanted = categories or CATEGORIES.keys()
        for name in wanted:
            summary[name] = discover_category(client, name, CATEGORIES[name], store, log)
    return summary


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Découverte des décisions coursupreme.dz")
    ap.add_argument("--categories", nargs="*", help="Sous-ensemble : themes penales civiles "
                    "indemnisation reunies importantes")
    args = ap.parse_args()

    with DecisionStore() as store:
        before = store.counts_by_status()
        discover_all(store, categories=args.categories)
        after = store.counts_by_status()
        print("\nBase avant :", before)
        print("Base après :", after)
