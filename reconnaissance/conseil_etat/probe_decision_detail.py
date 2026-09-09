"""
Sonde d'analyse détaillée de la structure d'une décision du Conseil d'État.
Inspecte les nœuds 'jurisprudence' et 'arrets-selectionnes'.
"""

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
        timeout=15.0,
        follow_redirects=True,
        headers={"User-Agent": "AlgerianLegalCorpusBot/0.1 (academic legal research; polite crawler)"}
    )

def inspect_decision_node(nid, url=None):
    client = get_client()
    target_url = url or f"https://conseildetat.dz/node/{nid}"
    print(f"\n=======================================================", flush=True)
    print(f"INSPECTING DECISION NODE #{nid} : {target_url}", flush=True)
    print(f"=======================================================", flush=True)
    
    resp = client.get(target_url)
    print(f"HTTP Status: {resp.status_code}, Final URL: {unquote(str(resp.url))}", flush=True)
    if resp.status_code != 200:
        return
        
    soup = BeautifulSoup(resp.text, "html.parser")
    article = soup.find("article")
    if not article:
        print("No article element found.", flush=True)
        return
        
    print(f"Article tag classes: {article.get('class')}", flush=True)
    
    # 1. Look for fields (Drupal field classes)
    fields = article.find_all(class_=lambda x: x and "field" in x)
    print(f"\nDrupal fields found: {len(fields)}", flush=True)
    for f in fields:
        f_classes = f.get("class", [])
        # Check label and item
        label = f.find(class_=lambda x: x and "field__label" in x)
        label_text = label.get_text(strip=True) if label else "NO_LABEL"
        items = f.find_all(class_=lambda x: x and "field__item" in x)
        items_text = [it.get_text(strip=True) for it in items]
        print(f"  Field: {f_classes} | Label: '{label_text}' | Items: {items_text[:2]}", flush=True)
        
    # 2. Look for PDFs
    pdf_links = [a for a in article.find_all("a", href=True) if ".pdf" in a["href"].lower()]
    print(f"\nPDF attachments in article: {len(pdf_links)}", flush=True)
    for p in pdf_links:
        print(f"  PDF: [{p.get_text(strip=True)}] -> {unquote(urljoin(str(resp.url), p['href']))}", flush=True)
        
    # 3. Text preview
    print(f"\nArticle full text preview (first 500 chars):", flush=True)
    print(article.get_text(strip=True, separator="\n")[:500], flush=True)

if __name__ == "__main__":
    # Test a few representative nodes
    # Node 29: jurisprudence
    inspect_decision_node(29)
    # Node 30: arrets-selectionnes
    inspect_decision_node(30)
    # Node 44: jurisprudence
    inspect_decision_node(44)
    # Node 61: jurisprudence (older)
    inspect_decision_node(61)
