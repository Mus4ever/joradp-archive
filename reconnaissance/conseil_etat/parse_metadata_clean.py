"""
Parser précis des métadonnées des décisions du Conseil d'État depuis le HTML.
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

def inspect_node_dom(nid=44):
    client = get_client()
    url = f"https://conseildetat.dz/node/{nid}"
    resp = client.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    article = soup.find("article")
    
    print(f"=== DOM OF NODE #{nid} ===", flush=True)
    # Print all child elements in article
    for child in article.find_all(recursive=False):
        print(f"Direct Child: <{child.name} class='{child.get('class')}'>", flush=True)
        
    for f in article.find_all(class_=lambda x: x and "field--" in str(x)):
        classes = f.get("class", [])
        name_class = [c for c in classes if c.startswith("field--name-")]
        text = f.get_text(strip=True, separator=" ")
        print(f"  Field class: {name_class} -> text: '{text[:100]}'", flush=True)

if __name__ == "__main__":
    inspect_node_dom(44)
    inspect_node_dom(61)
