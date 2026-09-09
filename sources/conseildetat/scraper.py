"""Scraper des décisions du Conseil d'État (conseildetat.dz).

- télécharge les URLs en statut 'decouvert'/'erreur' (reprise intégrale) ;
- parse chaque page Drupal 11 et persiste décision + HTML brut (RAW conservé) ;
- rate limiting via JoradpClient (2 s de politesse) ;
- Ctrl+C gracieux : les décisions déjà traitées sont conservées en base SQLite.

Usage :
    python sources/conseildetat/scraper.py --limit 10     # phase pilote
    python sources/conseildetat/scraper.py                # extraction complète
"""

import sys
from pathlib import Path
from typing import Optional

# Chemin vers tools/
sys.path.append(str(Path(__file__).resolve().parents[2] / "tools"))
from http_client import JoradpClient, JoradpClientConfig  # noqa: E402

# Modules locaux conseildetat
sys.path.insert(0, str(Path(__file__).resolve().parent))
from parser import parse_decision  # noqa: E402
from storage import DecisionStore  # noqa: E402
from discover import USER_AGENT  # noqa: E402


class DecisionScraper:
    def __init__(self, store: DecisionStore, client: Optional[JoradpClient] = None, log=print):
        self.store = store
        self.client = client
        self.log = log
        self.stop = False

    def request_stop(self):
        self.stop = True
        self.log("[STOP] arrêt demandé — reprise possible au prochain lancement")

    def scrape(self, limit: Optional[int] = None) -> dict:
        pending = self.store.pending(limit=limit)
        stats = {"a_faire": len(pending), "succes": 0, "erreurs": 0, "arret": False}
        self.log(f"SCRAPING CONSEIL D'ÉTAT : {len(pending)} décisions en attente")

        for i, row in enumerate(pending, 1):
            if self.stop:
                stats["arret"] = True
                break
            url = row["source_url"]
            nid = row["nid"]
            try:
                resp = self.client.get(url)
                if resp is None:
                    self.store.mark_error(url, "échec HTTP après retries")
                    stats["erreurs"] += 1
                    self.log(f"  [{i}/{len(pending)}] ÉCHEC HTTP {url}")
                    continue

                decision = parse_decision(resp.content, source_url=url, nid=nid)
                self.store.save_decision(decision, resp.content)
                stats["succes"] += 1

                num = decision.decision_number or "?"
                date = decision.date or decision.date_raw or "?"
                ch = decision.chamber or decision.node_type or "?"
                pdf_flag = " [PDF]" if decision.pdf_url else ""
                if i % 10 == 0 or i <= 3 or i == len(pending):
                    msg = f"  [{i}/{len(pending)}] OK n°{num} du {date} ({ch}){pdf_flag}"
                    try:
                        self.log(msg)
                    except UnicodeEncodeError:
                        self.log(msg.encode("ascii", "replace").decode("ascii"))

            except ValueError as e:
                # Page non décision ou format inattendu
                self.store.mark_error(url, f"parse: {e}")
                stats["erreurs"] += 1
                self.log(f"  [{i}/{len(pending)}] VALEUR: {str(e)[:100]}")
            except Exception as e:
                self.store.mark_error(url, f"exception: {type(e).__name__}: {e}")
                stats["erreurs"] += 1
                self.log(f"  [{i}/{len(pending)}] EXCEPTION {type(e).__name__}: {e}")

        self.log(f"Terminé : {stats['succes']} succès, {stats['erreurs']} erreurs"
                 + (" (arrêté)" if stats["arret"] else ""))
        return stats


def main():
    import argparse

    ap = argparse.ArgumentParser(description="Scraper conseildetat.dz")
    ap.add_argument("--limit", type=int, default=None,
                    help="Nombre maximum de décisions à scraper (pilote : 10)")
    args = ap.parse_args()

    config = JoradpClientConfig(user_agent=USER_AGENT)
    store = DecisionStore()
    scraper = DecisionScraper(store, None)

    with JoradpClient(config) as client:
        scraper.client = client
        try:
            scraper.scrape(limit=args.limit)
        except KeyboardInterrupt:
            scraper.request_stop()

    print("Statuts finaux :", store.counts_by_status())


if __name__ == "__main__":
    main()
