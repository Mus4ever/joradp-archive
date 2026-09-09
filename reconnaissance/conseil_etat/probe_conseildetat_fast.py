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
        timeout=10.0,
        follow_redirects=True,
        headers={"User-Agent": "AlgerianLegalCorpusBot/0.1 (academic legal research; polite crawler)"}
    )

def main():
    client = get_client()
    url = "https://conseildetat.dz/"
    print(f"Fetching homepage: {url}", flush=True)
    resp = client.get(url)
    print(f"Status: {resp.status_code}, Length: {len(resp.text)}", flush=True)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Check language switcher
    lang_links = soup.select(".language-switcher-language-url a, a.language-link, nav.language-switcher a")
    print(f"\nLanguage Switcher links ({len(lang_links)}):", flush=True)
    for l in lang_links:
        print(f"  {l.get_text(strip=True)} -> {l.get('href')}", flush=True)
        
    # Check all menus
    print("\n--- Main Navigation Links on Homepage ---", flush=True)
    links = soup.find_all("a", href=True)
    for a in links:
        href = urljoin(url, a["href"])
        text = a.get_text(strip=True)
        if text:
            print(f"  [{text}] -> {unquote(href)}", flush=True)

if __name__ == "__main__":
    main()
