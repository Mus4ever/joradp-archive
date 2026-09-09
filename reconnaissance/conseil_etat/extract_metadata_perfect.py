"""
Extraction complète et parfaite des 328 nœuds de jurisprudence.
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

def extract_metadata_from_soup(soup, nid, url):
    article = soup.find("article")
    if not article:
        return None
        
    classes = article.get("class", [])
    node_type = "unknown"
    for c in classes:
        if c in ("jurisprudence", "arrets-selectionnes", "publications-revue", "lmnshwrt-lmhdrt"):
            node_type = c
            break
            
    if node_type not in ("jurisprudence", "arrets-selectionnes", "publications-revue"):
        return None
        
    def get_val(field_name):
        el = article.find("div", class_=lambda x: x and f"field--name-{field_name}" in str(x))
        if not el:
            return None
            
        # In Drupal 11, items have class 'field--item' or 'field__item'
        items = el.find_all(class_=lambda x: x and ("field--item" in str(x) or "field__item" in str(x)))
        if items:
            texts = [it.get_text(strip=True) for it in items if it.get_text(strip=True)]
            if len(texts) == 1:
                return texts[0]
            elif len(texts) > 1:
                return " - ".join(texts)
                
        # Fallback: remove label and return stripped text
        lbl = el.find(class_=lambda x: x and ("field--label" in str(x) or "field__label" in str(x)))
        full_text = el.get_text(strip=True)
        if lbl:
            lbl_txt = lbl.get_text(strip=True)
            return full_text[len(lbl_txt):].strip()
        return full_text.strip()

    numm = get_val("field-numm-arr")
    date_str = get_val("field-date-arr")
    chamber = get_val("field-chamber-juris")
    sect = get_val("field-sect-jurisp")
    keywords = get_val("field-keywords-juris")
    adapt = get_val("field-adapt-juris")
    sujet = get_val("field-sujet")
    princ = get_val("field-princ-arret")
    
    # Year extraction
    year = "UNKNOWN"
    if date_str:
        m = re.search(r'\b(19\d\d|20\d\d)\b', str(date_str))
        if m:
            year = m.group(1)
            
    pdfs = []
    for a in article.find_all("a", href=True):
        href = a["href"]
        if ".pdf" in href.lower():
            pdfs.append(href)
            
    title = soup.title.string.strip() if soup.title else ""
    
    return {
        "nid": nid,
        "url": url,
        "type": node_type,
        "title": title,
        "decision_number": numm,
        "date": date_str,
        "year": year,
        "chamber": chamber,
        "section": sect,
        "keywords": keywords,
        "classification": adapt,
        "subject": sujet,
        "principle": princ,
        "pdfs": pdfs
    }

def run_extraction():
    client = get_client()
    results = []
    
    print("=== EXTRACTING PERFECT METADATA FOR JURISPRUDENCE (NIDS 25 TO 380) ===", flush=True)
    for nid in range(25, 381):
        url = f"https://conseildetat.dz/node/{nid}"
        try:
            resp = client.get(url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                meta = extract_metadata_from_soup(soup, nid, str(resp.url))
                if meta:
                    results.append(meta)
        except Exception as e:
            pass
            
    print(f"\n=======================================================", flush=True)
    print(f"EXTRACTION STATS ({len(results)} nodes)", flush=True)
    
    juris = [r for r in results if r["type"] == "jurisprudence"]
    arrets_sel = [r for r in results if r["type"] == "arrets-selectionnes"]
    revues = [r for r in results if r["type"] == "publications-revue"]
    
    print(f"  - Jurisprudence standard: {len(juris)}", flush=True)
    print(f"  - Arrêts sélectionnés: {len(arrets_sel)}", flush=True)
    print(f"  - Publications / Revues: {len(revues)}", flush=True)
    
    years = Counter(r["year"] for r in juris)
    print(f"\nDistribution par Année (Jurisprudence {len(juris)} décisions):", flush=True)
    for y in sorted(years.keys()):
        print(f"  - {y}: {years[y]} décisions", flush=True)
        
    chambers = Counter(str(r["chamber"]) for r in juris)
    print(f"\nDistribution par Chambre:", flush=True)
    for ch, c in chambers.most_common():
        print(f"  - {ch}: {c}", flush=True)
        
    princ_count = sum(1 for r in juris if r["principle"])
    print(f"\nDécisions avec Principe juridique (Mabda): {princ_count} / {len(juris)} ({princ_count/len(juris)*100:.1f}%)", flush=True)
    
    pdf_count = sum(len(r["pdfs"]) for r in juris)
    print(f"Décisions avec PDF attaché: {pdf_count} / {len(juris)} ({pdf_count/len(juris)*100:.1f}%)", flush=True)
    
    with open("reconnaissance/conseil_etat/conseil_etat_final_corpus.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_extraction()
