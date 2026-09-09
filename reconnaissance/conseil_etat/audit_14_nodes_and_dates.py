"""
Audit précis :
1. Identifier les 14 nœuds omis dans le résumé de section 4 (NID, type, titre, url).
2. Analyser précisément les 4 arrêts sélectionnés (NIDs 30, 367, 368, 369) et tout arrêt post-2017.
"""

import sys
import json
from collections import Counter
import re
from bs4 import BeautifulSoup
import httpx
import truststore
import ssl

sys.stdout.reconfigure(encoding='utf-8')

def get_client():
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.options |= 0x4
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    return httpx.Client(
        verify=context,
        timeout=15.0,
        follow_redirects=True,
        headers={"User-Agent": "AlgerianLegalCorpusBot/0.1 (academic legal research; polite crawler)"}
    )

def audit_nodes():
    with open("reconnaissance/conseil_etat/census_conseildetat.json", "r", encoding="utf-8") as f:
        census = json.load(f)
        
    print(f"Total nodes in census: {len(census)}")
    
    types = Counter(n["type"] for n in census)
    print("\n--- Complete Breakdown of all 561 nodes by type ---")
    for t, c in types.most_common():
        print(f"  {t:<25}: {c}")
        
    sum_all = sum(types.values())
    print(f"Sum of types: {sum_all}")
    
    # 1. List the 14 nodes (actualites, album-photos, lmnshwrt-lmhdrt)
    other_types = ["actualites", "album-photos", "lmnshwrt-lmhdrt"]
    the_14 = [n for n in census if n["type"] in other_types]
    print(f"\n--- The 14 nodes ({len(the_14)}) ---")
    for item in the_14:
        print(f"  NID {item['nid']:3d} | Type: {item['type']:<18} | Title: {item['title'][:50]} | PDFs: {len(item.get('pdfs', []))}")

    # 2. Detailed audit of the 4 arrets-selectionnes + any other decision
    client = get_client()
    arrets_sel_nids = [n["nid"] for n in census if n["type"] == "arrets-selectionnes"]
    print(f"\n--- Detailed Audit of 'arrets-selectionnes' ({len(arrets_sel_nids)} nodes: {arrets_sel_nids}) ---")
    for nid in arrets_sel_nids:
        resp = client.get(f"https://conseildetat.dz/node/{nid}")
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.string.strip() if soup.title else ""
        body_txt = soup.find("article").get_text(strip=True, separator=" | ") if soup.find("article") else ""
        pdfs = [a.get("href") for a in soup.find_all("a", href=True) if ".pdf" in a.get("href", "").lower()]
        print(f"\n  NID {nid}:")
        print(f"    Titre : {title}")
        print(f"    URL   : {resp.url}")
        print(f"    PDFs  : {pdfs}")
        print(f"    Texte : {body_txt[:300]}")

    # 3. Check NID 380 (jurisprudence seen in census log)
    print("\n--- Checking NID 380 ---")
    resp = client.get("https://conseildetat.dz/node/380")
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, "html.parser")
        article = soup.find("article")
        print(f"  NID 380 Type: {article.get('class') if article else 'None'}")
        print(f"  NID 380 Title: {soup.title.string.strip() if soup.title else 'None'}")
        print(f"  NID 380 Text: {article.get_text(strip=True, separator=' | ')[:300] if article else 'None'}")

if __name__ == "__main__":
    audit_nodes()
