"""
Analyse complète du corpus Conseil d'État extrait des nœuds Drupal.
"""

import sys
import ssl
import httpx
import truststore
from bs4 import BeautifulSoup
import json
import re
from collections import Counter

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

def analyze_corpus():
    client = get_client()
    
    # Load from census or probe all jurisprudence nodes
    # We know jurisprudence nodes run from ~29, 44 to 365, plus arrets-selectionnes 30, 367-369
    decisions = []
    
    print("=== EXTRACTING FULL METADATA FOR ALL JURISPRUDENCE NODES ===", flush=True)
    
    # Let's check nodes 25 to 375
    for nid in range(25, 375):
        url = f"https://conseildetat.dz/node/{nid}"
        try:
            resp = client.get(url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                article = soup.find("article")
                if not article:
                    continue
                classes = article.get("class", [])
                node_type = "unknown"
                for c in classes:
                    if c in ("jurisprudence", "arrets-selectionnes", "publications-revue", "lmnshwrt-lmhdrt", "legislation"):
                        node_type = c
                        break
                        
                if node_type not in ("jurisprudence", "arrets-selectionnes", "publications-revue"):
                    continue
                    
                title = soup.title.string.strip() if soup.title else ""
                
                # Helper to extract field text
                def get_field(fname):
                    el = soup.find(class_=lambda x: x and f"field--name-{fname}" in x)
                    if el:
                        # get text
                        item = el.find(class_=lambda x: x and "field__item" in x)
                        if item:
                            return item.get_text(strip=True)
                        items = el.find_all(class_=lambda x: x and "field__item" in x)
                        if items:
                            return [it.get_text(strip=True) for it in items]
                    return None

                numm = get_field("field-numm-arr")
                date_val = get_field("field-date-arr")
                chamber = get_field("field-chamber-juris")
                sect = get_field("field-sect-jurisp")
                keywords = get_field("field-keywords-juris")
                adapt = get_field("field-adapt-juris")
                sujet = get_field("field-sujet")
                princ = get_field("field-princ-arret")
                
                # Check year
                year = "UNKNOWN"
                if date_val:
                    m = re.search(r'\b(19\d\d|20\d\d)\b', str(date_val))
                    if m:
                        year = m.group(1)
                        
                # Extract PDF links
                pdfs = []
                for a in article.find_all("a", href=True):
                    href = a["href"]
                    if ".pdf" in href.lower():
                        pdfs.append(href)
                        
                entry = {
                    "nid": nid,
                    "url": str(resp.url),
                    "type": node_type,
                    "title": title,
                    "decision_number": numm,
                    "date": date_val,
                    "year": year,
                    "chamber": chamber,
                    "section": sect,
                    "keywords": keywords,
                    "classification": adapt,
                    "subject": sujet,
                    "principle": princ,
                    "has_principle": bool(princ),
                    "pdfs": pdfs,
                    "pdf_count": len(pdfs)
                }
                decisions.append(entry)
        except Exception as e:
            pass

    print(f"\n=======================================================", flush=True)
    print(f"CORPUS ANALYSIS SUMMARY", flush=True)
    print(f"Total Jurisprudence/Revue Nodes: {len(decisions)}", flush=True)
    
    types_c = Counter(d["type"] for d in decisions)
    for t, c in types_c.items():
        print(f"  - Type '{t}': {c}", flush=True)
        
    juris_items = [d for d in decisions if d["type"] == "jurisprudence"]
    print(f"\nTotal 'jurisprudence' decisions: {len(juris_items)}", flush=True)
    
    years_c = Counter(d["year"] for d in juris_items)
    print("\nYears distribution for jurisprudence decisions:")
    for y in sorted(years_c.keys()):
        print(f"  - {y}: {years_c[y]} décisions", flush=True)
        
    chambers_c = Counter(str(d["chamber"]) for d in juris_items)
    print("\nChambers distribution:")
    for ch, c in chambers_c.most_common():
        print(f"  - {ch}: {c}", flush=True)
        
    principles_count = sum(1 for d in juris_items if d["has_principle"])
    print(f"\nDecisions with Principle (Mabda): {principles_count} / {len(juris_items)} ({principles_count/len(juris_items)*100:.1f}%)", flush=True)
    
    pdf_count = sum(d["pdf_count"] for d in juris_items)
    print(f"Total Attached PDFs for jurisprudence: {pdf_count} / {len(juris_items)}", flush=True)
    
    with open("reconnaissance/conseil_etat/conseildetat_jurisprudence_corpus.json", "w", encoding="utf-8") as f:
        json.dump(decisions, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    analyze_corpus()
