"""
Sonde pour trouver la borne supérieure des nœuds sur conseildetat.dz
Scanne de NID 151 jusqu'à ce que 50 codes 404 consécutifs soient rencontrés.
"""

import sys
import ssl
import httpx
import truststore
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
import json
import time
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

def get_client():
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.options |= 0x4
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    return httpx.Client(
        verify=context,
        timeout=10.0,
        follow_redirects=True,
        headers={"User-Agent": "AlgerianLegalCorpusBot/0.1 (academic legal research; polite crawler)"}
    )

def scan_upper():
    client = get_client()
    consecutive_404 = 0
    max_consecutive_404 = 40
    
    found_nodes = []
    type_counts = Counter()
    
    print("=== SCANNING FROM NID 151 UPWARDS ON CONSEILDETAT.DZ ===", flush=True)
    nid = 151
    while consecutive_404 < max_consecutive_404 and nid <= 2000:
        url = f"https://conseildetat.dz/node/{nid}"
        try:
            resp = client.get(url)
            if resp.status_code == 200:
                consecutive_404 = 0
                soup = BeautifulSoup(resp.text, "html.parser")
                article = soup.find("article")
                node_type = "unknown"
                if article:
                    classes = article.get("class", [])
                    for c in classes:
                        if c not in ("node", "full", "clearfix", "contextual-region"):
                            node_type = c
                            break
                title = soup.title.string.strip() if soup.title else ""
                pdfs = [a.get("href") for a in soup.find_all("a", href=True) if ".pdf" in a.get("href", "").lower()]
                
                type_counts[node_type] += 1
                found_nodes.append({
                    "nid": nid,
                    "type": node_type,
                    "title": title,
                    "url": str(resp.url),
                    "pdfs": pdfs
                })
                
                if nid % 25 == 0 or node_type != "jurisprudence":
                    print(f"  [FOUND] NID {nid:4d} | Type: {node_type:<20} | Title: {title[:35]} | PDFs: {len(pdfs)}", flush=True)
            elif resp.status_code == 404:
                consecutive_404 += 1
            else:
                print(f"  [STATUS {resp.status_code}] NID {nid}", flush=True)
        except Exception as e:
            print(f"  [ERROR] NID {nid}: {e}", flush=True)
            
        nid += 1
        time.sleep(0.02)
        
    print(f"\nScan ended at NID {nid-1} after {consecutive_404} consecutive 404s.", flush=True)
    print(f"Total additional nodes found: {len(found_nodes)}", flush=True)
    print(f"Content types found:", flush=True)
    for k, v in type_counts.most_common():
        print(f"  - {k:<25}: {v}", flush=True)
        
    with open("reconnaissance/conseil_etat/upper_nodes.json", "w", encoding="utf-8") as f:
        json.dump(found_nodes, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    scan_upper()
