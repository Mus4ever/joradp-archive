import sys
import ssl
import httpx
import truststore
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
import json

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

def probe_all_nodes():
    client = get_client()
    found_nodes = []
    
    print("=== SCANNING NODES 1 TO 150 ON CONSEILDETAT.DZ ===", flush=True)
    for nid in range(1, 151):
        url = f"https://conseildetat.dz/node/{nid}"
        try:
            resp = client.get(url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                title = soup.title.string.strip() if soup.title else "No Title"
                article = soup.find("article")
                classes = article.get("class", []) if article else []
                canonical = soup.find("link", rel="canonical")
                canonical_href = canonical.get("href") if canonical else str(resp.url)
                
                # Check for PDF links in node
                pdfs = [a.get("href") for a in soup.find_all("a", href=True) if ".pdf" in a.get("href", "").lower()]
                
                node_info = {
                    "nid": nid,
                    "title": title,
                    "classes": classes,
                    "canonical": canonical_href,
                    "pdfs": pdfs
                }
                found_nodes.append(node_info)
                print(f"  [FOUND] NID {nid:3d} | Classes: {classes} | Title: {title[:40]} | Canonical: {canonical_href} | PDFs: {len(pdfs)}", flush=True)
            elif resp.status_code != 404:
                print(f"  [STATUS {resp.status_code}] NID {nid}", flush=True)
        except Exception as e:
            print(f"  [ERROR] NID {nid}: {e}", flush=True)

    print(f"\nTotal nodes found: {len(found_nodes)}", flush=True)
    
    # Save to json
    with open("reconnaissance/conseil_etat/conseildetat_nodes.json", "w", encoding="utf-8") as f:
        json.dump(found_nodes, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    probe_all_nodes()
