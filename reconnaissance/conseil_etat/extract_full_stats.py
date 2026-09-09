"""
Extraction complète et calcul des statistiques réelles sur les 323 décisions du Conseil d'État.
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

def extract_all():
    client = get_client()
    decisions = []
    
    print("=== EXTRACTING PRECISE METADATA (NIDS 25 TO 370) ===", flush=True)
    for nid in range(25, 370):
        url = f"https://conseildetat.dz/node/{nid}"
        try:
            resp = client.get(url)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            article = soup.find("article")
            if not article:
                continue
            classes = article.get("class", [])
            node_type = "unknown"
            for c in classes:
                if c in ("jurisprudence", "arrets-selectionnes", "publications-revue", "lmnshwrt-lmhdrt"):
                    node_type = c
                    break
            if node_type not in ("jurisprudence", "arrets-selectionnes", "publications-revue"):
                continue

            def get_text_by_class(cls_name):
                el = soup.find(class_=lambda x: x and cls_name in str(x))
                if el:
                    item = el.find(class_=lambda x: x and "field__item" in str(x))
                    if item:
                        return item.get_text(strip=True)
                return None

            numm = get_text_by_class("field--name-field-numm-arr")
            date_str = get_text_by_class("field--name-field-date-arr")
            chamber = get_text_by_class("field--name-field-chamber-juris")
            section = get_text_by_class("field--name-field-sect-jurisp")
            keywords = get_text_by_class("field--name-field-keywords-juris")
            adapt = get_text_by_class("field--name-field-adapt-juris")
            sujet = get_text_by_class("field--name-field-sujet")
            principle = get_text_by_class("field--name-field-princ-arret")

            # Extract year
            year = "UNKNOWN"
            if date_str:
                m = re.search(r'\b(19\d\d|20\d\d)\b', date_str)
                if m:
                    year = m.group(1)

            # PDF
            pdfs = [a.get("href") for a in article.find_all("a", href=True) if ".pdf" in a.get("href", "").lower()]

            entry = {
                "nid": nid,
                "url": str(resp.url),
                "type": node_type,
                "decision_number": numm,
                "date": date_str,
                "year": year,
                "chamber": chamber,
                "section": section,
                "keywords": keywords,
                "classification": adapt,
                "subject": sujet,
                "principle": principle,
                "pdfs": pdfs
            }
            decisions.append(entry)
        except Exception as e:
            pass

    print(f"\n=======================================================", flush=True)
    print(f"EXTRACTION COMPLETE: {len(decisions)} nodes", flush=True)
    
    juris = [d for d in decisions if d["type"] == "jurisprudence"]
    arrets_sel = [d for d in decisions if d["type"] == "arrets-selectionnes"]
    revues = [d for d in decisions if d["type"] == "publications-revue"]
    
    print(f"  - Jurisprudence standard: {len(juris)}", flush=True)
    print(f"  - Arrêts sélectionnés: {len(arrets_sel)}", flush=True)
    print(f"  - Publications / Revues: {len(revues)}", flush=True)
    
    years = Counter(d["year"] for d in juris)
    print(f"\nDistribution par Année (Jurisprudence):", flush=True)
    for y in sorted(years.keys()):
        print(f"  - {y}: {years[y]} décisions", flush=True)
        
    chambers = Counter(str(d["chamber"]) for d in juris)
    print(f"\nDistribution par Chambre:", flush=True)
    for ch, c in chambers.most_common():
        print(f"  - {ch}: {c}", flush=True)
        
    with_princ = sum(1 for d in juris if d["principle"])
    with_pdf = sum(1 for d in juris if d["pdfs"])
    print(f"\nComplétude:", flush=True)
    print(f"  - Décisions avec Principe (Mabda): {with_princ} / {len(juris)} ({with_princ/len(juris)*100:.1f}%)", flush=True)
    print(f"  - Décisions avec PDF: {with_pdf} / {len(juris)} ({with_pdf/len(juris)*100:.1f}%)", flush=True)
    
    with open("reconnaissance/conseil_etat/conseil_etat_full_stats.json", "w", encoding="utf-8") as f:
        json.dump(decisions, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    extract_all()
