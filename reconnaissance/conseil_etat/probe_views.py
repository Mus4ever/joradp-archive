"""
Sonde approfondie des vues et fichiers sur conseildetat.dz
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

def test_jurisprudence_direct():
    client = get_client()
    url = "https://conseildetat.dz/ar/الإجتهاد-القضائي"
    print(f"=== TESTING DIRECT VIEW: {url} ===", flush=True)
    resp = client.get(url)
    print(f"Status: {resp.status_code}, Final URL: {resp.url}", flush=True)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    rows = soup.select(".view-content .views-row, table.views-table tbody tr, .views-view-grid .views-col, .node")
    print(f"Direct page rows found: {len(rows)}", flush=True)
    
    for i, r in enumerate(rows[:5]):
        print(f"  Row #{i+1}: {r.get_text(strip=True, separator=' | ')[:200]}", flush=True)
        for a in r.find_all("a", href=True):
            print(f"    Link: [{a.get_text(strip=True)}] -> {a['href']}", flush=True)
            
    pager = soup.select("nav.pager, ul.pager__items, .pagination")
    if pager:
        print(f"Pager found: {pager[0].get_text(strip=True, separator=' ')}", flush=True)
        for a in pager[0].find_all("a", href=True):
            print(f"  Pager link: {a.get_text(strip=True)} -> {a['href']}", flush=True)

def test_selected_decisions_correct_url():
    client = get_client()
    # Correct spelling from menu: القرارات-المختارة
    url = "https://conseildetat.dz/ar/القرارات-المختارة"
    print(f"\n=== TESTING SELECTED DECISIONS (القرارات-المختارة): {url} ===", flush=True)
    resp = client.get(url)
    print(f"Status: {resp.status_code}, Final URL: {resp.url}", flush=True)
    soup = BeautifulSoup(resp.text, "html.parser")
    print(f"Title: {soup.title.string.strip() if soup.title else 'None'}", flush=True)
    
    rows = soup.select(".view-content .views-row, table.views-table tbody tr, .views-view-grid .views-col, .node")
    print(f"Rows found: {len(rows)}", flush=True)
    for i, r in enumerate(rows[:5]):
        print(f"  Row #{i+1}: {r.get_text(strip=True, separator=' | ')[:200]}", flush=True)
        for a in r.find_all("a", href=True):
            print(f"    Link: [{a.get_text(strip=True)}] -> {a['href']}", flush=True)
            
    pager = soup.select("nav.pager, ul.pager__items, .pagination")
    if pager:
        print(f"Pager found: {pager[0].get_text(strip=True, separator=' ')}", flush=True)
        for a in pager[0].find_all("a", href=True):
            print(f"  Pager link: {a.get_text(strip=True)} -> {a['href']}", flush=True)

def probe_magazine_pdfs():
    client = get_client()
    print(f"\n=== PROBING KNOWN MAGAZINE PDF PATTERNS IN SITES/DEFAULT/FILES/ ===", flush=True)
    # Let's test pattern like revuen-1-2000.pdf, revuen-1.pdf, revue-01.pdf, etc.
    patterns = [
        "https://conseildetat.dz/sites/default/files/magazines_pdf/revuen-13-2015.pdf",
    ]
    for n in range(1, 25):
        for y in range(1998, 2026):
            patterns.append(f"https://conseildetat.dz/sites/default/files/magazines_pdf/revuen-{n}-{y}.pdf")
            patterns.append(f"https://conseildetat.dz/sites/default/files/magazines_pdf/revue-{n}-{y}.pdf")
            patterns.append(f"https://conseildetat.dz/sites/default/files/magazines_pdf/revue-n-{n}-{y}.pdf")
            patterns.append(f"https://conseildetat.dz/sites/default/files/magazines_pdf/revue{n}-{y}.pdf")
        patterns.append(f"https://conseildetat.dz/sites/default/files/magazines_pdf/revuen-{n}.pdf")
        patterns.append(f"https://conseildetat.dz/sites/default/files/magazines_pdf/revue-{n}.pdf")

    # Let's test a few sample HEAD requests
    sample_tests = [
        "https://conseildetat.dz/sites/default/files/magazines_pdf/revuen-13-2015.pdf",
        "https://conseildetat.dz/sites/default/files/magazines_pdf/revuen-1-2001.pdf",
        "https://conseildetat.dz/sites/default/files/magazines_pdf/revuen-2-2002.pdf",
        "https://conseildetat.dz/sites/default/files/magazines_pdf/revuen-12-2014.pdf",
        "https://conseildetat.dz/sites/default/files/magazines_pdf/revuen-14-2016.pdf",
    ]
    for target in sample_tests:
        try:
            r = client.head(target)
            print(f"HEAD {target} -> Status: {r.status_code}, Length: {r.headers.get('content-length')}", flush=True)
        except Exception as e:
            print(f"HEAD {target} -> Error: {e}", flush=True)

if __name__ == "__main__":
    test_jurisprudence_direct()
    test_selected_decisions_correct_url()
    probe_magazine_pdfs()
