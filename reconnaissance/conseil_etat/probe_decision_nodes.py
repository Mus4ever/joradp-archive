"""
Sonde pour inspecter la recherche interne et les nœuds de décisions sur conseildetat.dz
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
        timeout=15.0,
        follow_redirects=True,
        headers={"User-Agent": "AlgerianLegalCorpusBot/0.1 (academic legal research; polite crawler)"}
    )

def probe_drupal_search():
    client = get_client()
    keywords = ["قرار", "المبدأ", "الغرفة", "إلغاء", "صفقة"]
    
    print("=== TESTING DRUPAL NODE SEARCH (/ar/search/node) ===", flush=True)
    for kw in keywords:
        url = "https://conseildetat.dz/ar/search/node"
        try:
            resp = client.get(url, params={"keys": kw})
            soup = BeautifulSoup(resp.text, "html.parser")
            results = soup.select(".search-results li, .search-result, ol.search-results > li")
            print(f"Keyword '{kw}': Status {resp.status_code}, Found {len(results)} results in HTML", flush=True)
            for r in results[:3]:
                link = r.find("a")
                if link:
                    print(f"  - [{link.get_text(strip=True)}] -> {unquote(urljoin(str(resp.url), link['href']))}", flush=True)
                snippet = r.find(class_=lambda x: x and "snippet" in x)
                if snippet:
                    print(f"    Snippet: {snippet.get_text(strip=True)[:150]}", flush=True)
        except Exception as e:
            print(f"Error searching '{kw}': {e}", flush=True)

def probe_node_ranges():
    client = get_client()
    print("\n=== PROBING SAMPLE NODE IDS (/node/1 to /node/30) ===", flush=True)
    for node_id in range(1, 31):
        url = f"https://conseildetat.dz/node/{node_id}"
        try:
            resp = client.get(url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                title = soup.title.string.strip() if soup.title else "No Title"
                article = soup.find("article")
                node_type = article.get("class") if article else "No article tag"
                print(f"  Node #{node_id} ({resp.url}): {title} | Type: {node_type}", flush=True)
            elif resp.status_code == 403:
                print(f"  Node #{node_id}: 403 Forbidden", flush=True)
        except Exception as e:
            pass

if __name__ == "__main__":
    probe_drupal_search()
    probe_node_ranges()
