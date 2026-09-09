"""
Recensement exhaustif des nœuds Drupal sur conseildetat.dz
Scanne par lots pour mesurer le volume réel exact, les types de contenu,
la distribution des dates et les fichiers PDF attachés.
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

def full_census():
    client = get_client()
    consecutive_404 = 0
    max_consecutive_404 = 50  # stop after 50 consecutive 404s
    
    results = []
    type_counts = Counter()
    years_counts = Counter()
    pdf_count = 0
    
    print("=== STARTING FULL CENSUS OF NODES ON CONSEILDETAT.DZ ===", flush=True)
    
    nid = 1
    max_nid = 1000  # safety cap
    
    while nid <= max_nid and consecutive_404 < max_consecutive_404:
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
                
                # Extract date if jurisprudence
                date_field = soup.find(class_=lambda x: x and "field--name-field-date-arr" in x)
                date_str = ""
                year = "UNKNOWN"
                if date_field:
                    date_item = date_field.find(class_=lambda x: x and "field__item" in x)
                    if date_item:
                        date_str = date_item.get_text(strip=True)
                        # extract 4 digit year
                        import re
                        m = re.search(r'\b(19\d\d|20\d\d)\b', date_str)
                        if m:
                            year = m.group(1)
                            
                # Check PDF
                pdf_links = [a.get("href") for a in soup.find_all("a", href=True) if ".pdf" in a.get("href", "").lower()]
                if pdf_links:
                    pdf_count += len(pdf_links)
                    
                type_counts[node_type] += 1
                if year != "UNKNOWN":
                    years_counts[year] += 1
                    
                item = {
                    "nid": nid,
                    "url": str(resp.url),
                    "type": node_type,
                    "title": title,
                    "date": date_str,
                    "year": year,
                    "pdfs": pdf_links
                }
                results.append(item)
                
                if nid % 20 == 0 or node_type in ("jurisprudence", "arrets-selectionnes", "publications-revue"):
                    print(f"  NID {nid:3d}: Type={node_type:<20} | Year={year:<5} | Title={title[:35]} | PDFs={len(pdf_links)}", flush=True)
            else:
                consecutive_404 += 1
        except Exception as e:
            print(f"  Error on NID {nid}: {e}", flush=True)
            
        nid += 1
        time.sleep(0.05)  # small polite interval
        
    print(f"\n=======================================================", flush=True)
    print(f"CENSUS COMPLETED", flush=True)
    print(f"Total Nodes Found: {len(results)} (scanned up to NID {nid-1})", flush=True)
    print(f"Content Types Breakdown:", flush=True)
    for k, v in type_counts.most_common():
        print(f"  - {k:<25}: {v}", flush=True)
        
    print(f"\nYears Breakdown for Jurisprudence:", flush=True)
    for y in sorted(years_counts.keys()):
        print(f"  - {y}: {years_counts[y]}", flush=True)
        
    print(f"\nTotal PDF attachments found: {pdf_count}", flush=True)
    print(f"=======================================================", flush=True)
    
    # Save full census JSON
    with open("reconnaissance/conseil_etat/census_conseildetat.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    full_census()
