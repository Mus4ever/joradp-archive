"""
Sonde d'exploration approfondie de https://conseildetat.dz/ (et www.conseildetat.dz).
Inspecte l'arbre des menus, les rubriques de jurisprudence, les publications,
les vues Drupal, les formulaires de recherche, et la pagination.
"""

import sys
import ssl
import httpx
import truststore
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote

sys.stdout.reconfigure(encoding='utf-8')

def get_client():
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.options |= 0x4
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    return httpx.Client(
        verify=context,
        timeout=25.0,
        follow_redirects=True,
        headers={"User-Agent": "AlgerianLegalCorpusBot/0.1 (academic legal research; polite crawler)"}
    )

def explore_conseildetat():
    client = get_client()
    base_url = "https://conseildetat.dz"
    
    # 1. Inspect Homepages and language switchers
    pages_to_check = [
        "https://conseildetat.dz/",
        "https://conseildetat.dz/ar",
        "https://conseildetat.dz/fr",
        "https://conseildetat.dz/fr/documentations/publications/magazines-ce",
        "https://conseildetat.dz/ar/%D8%A7%D9%84%D8%A5%D8%AC%D8%AA%D9%87%D8%A7%D8%AF-%D8%A7%D9%84%D9%82%D8%B6%D8%A7%D8%A6%D9%8A/%D8%A7%D9%84%D9%88%D8%AB%D8%A7%D8%A6%D9%82",
    ]
    
    discovered_urls = set()
    
    for url in pages_to_check:
        try:
            print(f"\n==========================================")
            print(f"GET: {url}")
            print(f"Decoded URL: {unquote(url)}")
            print(f"==========================================")
            resp = client.get(url)
            print(f"Status: {resp.status_code}")
            print(f"Final URL: {resp.url} (Decoded: {unquote(str(resp.url))})")
            
            soup = BeautifulSoup(resp.text, "html.parser")
            print(f"Page Title: {soup.title.string if soup.title else 'No Title'}")
            
            # Find all links
            for a in soup.find_all("a", href=True):
                href = urljoin(str(resp.url), a["href"])
                text = a.get_text(strip=True)
                discovered_urls.add((text, href))
                
        except Exception as e:
            print(f"Error requesting {url}: {e}")
            
    print(f"\n=== ALL UNIQUE LINKS DISCOVERED ON CONSEILDETAT.DZ ({len(discovered_urls)}) ===")
    for text, href in sorted(discovered_urls, key=lambda x: x[1]):
        decoded = unquote(href)
        print(f"  [{text}] -> {decoded}")

if __name__ == "__main__":
    explore_conseildetat()
