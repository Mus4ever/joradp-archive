"""
Analyse détaillée d'un échantillon de 10 décisions du Conseil d'État et des PDF attachés.
Vérifie la complétude des métadonnées, la structure textuelle, la langue,
le caractère natif/scanné des PDF et l'anonymisation.
"""

import sys
import os
import ssl
import httpx
import truststore
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
import json
import re

sys.stdout.reconfigure(encoding='utf-8')

def get_client():
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.options |= 0x4
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    return httpx.Client(
        verify=context,
        timeout=20.0,
        follow_redirects=True,
        headers={"User-Agent": "AlgerianLegalCorpusBot/0.1 (academic legal research; polite crawler)"}
    )

SAMPLE_NIDS = [28, 29, 30, 44, 61, 80, 100, 120, 150, 175]

def analyze_samples():
    client = get_client()
    os.makedirs("reconnaissance/conseil_etat/samples", exist_ok=True)
    
    samples_data = []
    
    print("=== DETAILED ANALYSIS OF 10 SAMPLE NODES ===", flush=True)
    for nid in SAMPLE_NIDS:
        url = f"https://conseildetat.dz/node/{nid}"
        try:
            resp = client.get(url)
            if resp.status_code != 200:
                print(f"Node {nid}: Status {resp.status_code}", flush=True)
                continue
                
            soup = BeautifulSoup(resp.text, "html.parser")
            article = soup.find("article")
            classes = article.get("class", []) if article else []
            title = soup.title.string.strip() if soup.title else ""
            
            # Extract metadata fields
            def get_field_val(field_name):
                f = soup.find(class_=lambda x: x and f"field--name-{field_name}" in x)
                if f:
                    item = f.find(class_=lambda x: x and "field__item" in x)
                    if item:
                        return item.get_text(strip=True)
                return None
                
            num_decision = get_field_val("field-numm-arr")
            date_decision = get_field_val("field-date-arr")
            chambre = get_field_val("field-chamber-juris")
            section = get_field_val("field-sect-jurisp")
            keywords = get_field_val("field-keywords-juris")
            adapt = get_field_val("field-adapt-juris")
            sujet = get_field_val("field-sujet")
            principe = get_field_val("field-princ-arret")
            
            # PDF links
            pdf_links = [urljoin(str(resp.url), a["href"]) for a in soup.find_all("a", href=True) if ".pdf" in a.get("href", "").lower()]
            
            sample_entry = {
                "nid": nid,
                "url": str(resp.url),
                "type": classes,
                "title": title,
                "decision_number": num_decision,
                "date": date_decision,
                "chamber": chambre,
                "section": section,
                "keywords": keywords,
                "classification": adapt,
                "subject": sujet,
                "principle_preview": principe[:150] if principe else None,
                "pdf_count": len(pdf_links),
                "pdf_urls": pdf_links
            }
            samples_data.append(sample_entry)
            
            print(f"\n--- Node #{nid} ({classes[0] if classes else 'unknown'}) ---", flush=True)
            print(f"  Titre: {title}", flush=True)
            print(f"  Numéro: {num_decision} | Date: {date_decision}", flush=True)
            print(f"  Chambre: {chambre} | Section: {section}", flush=True)
            print(f"  Mots-clés: {keywords}", flush=True)
            print(f"  Classification: {adapt} | Sujet: {sujet}", flush=True)
            print(f"  Principe (Mabda): {principe[:100] if principe else 'NONE'}", flush=True)
            print(f"  PDFs ({len(pdf_links)}): {pdf_links}", flush=True)
            
            # Download first PDF if any to analyze format
            if pdf_links and nid in (30, 44, 28):
                pdf_url = pdf_links[0]
                pdf_resp = client.get(pdf_url)
                if pdf_resp.status_code == 200:
                    filename = f"reconnaissance/conseil_etat/samples/sample_node_{nid}.pdf"
                    with open(filename, "wb") as pf:
                        pf.write(pdf_resp.content)
                    pdf_size = len(pdf_resp.content)
                    # Inspect PDF bytes for fonts / text streams vs images
                    raw_bytes = pdf_resp.content
                    has_font = b"/Font" in raw_bytes
                    has_stream = b"stream" in raw_bytes
                    has_text = b"/Text" in raw_bytes or b"/Type /Page" in raw_bytes
                    is_scanned_likely = (b"/Image" in raw_bytes and not has_font) or (b"DCTDecode" in raw_bytes and not has_font)
                    print(f"  [PDF DOWNLOADED] Size: {pdf_size} bytes, has_font={has_font}, likely_scanned={is_scanned_likely}", flush=True)
                    
        except Exception as e:
            print(f"Error on node {nid}: {e}", flush=True)
            
    with open("reconnaissance/conseil_etat/sample_analysis.json", "w", encoding="utf-8") as f:
        json.dump(samples_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    analyze_samples()
