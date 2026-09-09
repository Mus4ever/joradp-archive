"""Découverte des nœuds de jurisprudence sur conseildetat.dz.

Stratégie validée lors de la reconnaissance (09/09/2026) :
- Parcours séquentiel de /node/{nid} pour NID 25 à 575
- Filtrage par type d'article (classes CSS Drupal 11)
- Arrêt de sécurité après 40 codes 404 consécutifs
- Politesse : 2 secondes entre requêtes via JoradpClient
"""

import sys
from pathlib import Path
from typing import Dict, Optional

sys.path.append(str(Path(__file__).resolve().parents[2] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from bs4 import BeautifulSoup  # noqa: E402
from http_client import JoradpClient, JoradpClientConfig  # noqa: E402

from parser import DECISION_TYPES  # noqa: E402
from storage import DecisionStore  # noqa: E402

BASE = "https://conseildetat.dz"
USER_AGENT = "AlgerianLegalCorpusBot/0.1 (academic legal research; polite crawler)"

# Plage de NIDs à scanner (validée lors de la reconnaissance : 25 → 575)
NID_START = 25
NID_END = 575
MAX_CONSECUTIVE_404 = 40


def detect_node_type(html: str) -> Optional[str]:
    """Détecte le type de nœud depuis le HTML."""
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article")
    if not article:
        return None
    classes = article.get("class", [])
    for cls in classes:
        if cls in DECISION_TYPES:
            return cls
    return None


def discover_nodes(client: JoradpClient,
                   store: Optional[DecisionStore] = None,
                   nid_start: int = NID_START,
                   nid_end: int = NID_END,
                   log=print) -> Dict:
    """Parcourt /node/{nid} et enregistre les nœuds de jurisprudence.

    Retourne un résumé {scanned, found, new, by_type, errors, stopped_at}.
    """
    consecutive_404 = 0
    found = 0
    new = 0
    errors = 0
    by_type = {}
    stopped_at = nid_end

    log(f"=== DÉCOUVERTE conseildetat.dz — NIDs {nid_start} à {nid_end} ===")

    for nid in range(nid_start, nid_end + 1):
        url = f"{BASE}/node/{nid}"
        try:
            resp = client.get(url)
            if resp is None or resp.status_code == 404:
                consecutive_404 += 1
                if consecutive_404 >= MAX_CONSECUTIVE_404:
                    log(f"  [STOP] {MAX_CONSECUTIVE_404} codes 404 consécutifs à NID {nid} — arrêt")
                    stopped_at = nid
                    break
                continue

            # Réinitialiser le compteur 404
            consecutive_404 = 0

            node_type = detect_node_type(resp.text)
            if node_type and node_type in DECISION_TYPES:
                found += 1
                by_type[node_type] = by_type.get(node_type, 0) + 1

                if store is not None:
                    if store.add_discovered(url, nid=nid, node_type=node_type):
                        new += 1

                if found % 50 == 0 or found <= 5:
                    log(f"  NID {nid:>4d} : {node_type} (cumul: {found} trouvés, {new} nouveaux)")

        except Exception as e:
            errors += 1
            log(f"  NID {nid:>4d} : ERREUR {type(e).__name__}: {e}")

    scanned = stopped_at - nid_start + 1
    log(f"\n=== RÉSULTAT ===")
    log(f"  Scannés: {scanned} NIDs ({nid_start}–{stopped_at})")
    log(f"  Trouvés: {found} nœuds de décision")
    log(f"  Nouveaux en base: {new}")
    log(f"  Par type: {by_type}")
    log(f"  Erreurs: {errors}")

    return {
        "scanned": scanned,
        "found": found,
        "new": new,
        "by_type": by_type,
        "errors": errors,
        "stopped_at": stopped_at,
    }


def main():
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Découverte des décisions conseildetat.dz")
    ap.add_argument("--start", type=int, default=NID_START,
                     help=f"NID de départ (défaut: {NID_START})")
    ap.add_argument("--end", type=int, default=NID_END,
                     help=f"NID de fin (défaut: {NID_END})")
    ap.add_argument("--seed", type=str, default=None,
                     help="Chemin vers un fichier JSON de reconnaissance pour précharger les NIDs")
    args = ap.parse_args()

    config = JoradpClientConfig(
        base_url=BASE,
        user_agent=USER_AGENT,
        min_delay=2.0,
    )

    with DecisionStore() as store:
        before = store.counts_by_status()

        if args.seed:
            seed_path = Path(args.seed)
            if seed_path.exists():
                items = json.loads(seed_path.read_text(encoding="utf-8"))
                new = 0
                for it in items:
                    u = it.get("url") or f"{BASE}/node/{it['nid']}"
                    if store.add_discovered(u, nid=it.get("nid"), node_type=it.get("type", "jurisprudence")):
                        new += 1
                print(f"Seed chargé depuis {seed_path} : {len(items)} entrées, {new} nouvelles.")

        if not args.seed:
            with JoradpClient(config) as client:
                discover_nodes(client, store, nid_start=args.start, nid_end=args.end)

        after = store.counts_by_status()
        print(f"\nBase avant : {before}")
        print(f"Base après : {after}")
        print(f"Par type   : {store.counts_by_type()}")


if __name__ == "__main__":
    main()
