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

def inspect_page(client, name, url):
    print(f"\n==================================================================", flush=True)
    print(f"PAGE: {name}", flush=True)
    print(f"URL: {url} (Decoded: {unquote(url)})", flush=True)
    print(f"==================================================================", flush=True)
    try:
        resp = client.get(url)
        print(f"Status: {resp.status_code}, Final URL: {resp.url}", flush=True)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Check title
        print(f"Title: {soup.title.string.strip() if soup.title else 'None'}", flush=True)
        
        # Forms / Filters
        forms = soup.find_all("form")
        print(f"\nForms found: {len(forms)}", flush=True)
        for i, f in enumerate(forms):
            action = f.get("action", "")
            method = f.get("method", "GET").upper()
            form_id = f.get("id", "")
            print(f"  Form #{i+1} [id={form_id}, method={method}, action={action}]", flush=True)
            inputs = f.find_all(["input", "select", "textarea"])
            for inp in inputs:
                name_attr = inp.get("name")
                type_attr = inp.get("type", inp.name)
                val = inp.get("value", "")
                if inp.name == "select":
                    options = [opt.get_text(strip=True) for opt in inp.find_all("option")]
                    print(f"    Select: name='{name_attr}', options={options[:5]} (total {len(options)})", flush=True)
                else:
                    print(f"    Input: name='{name_attr}', type='{type_attr}', val='{val}'", flush=True)
                    
        # Pagination
        pager = soup.select(".pager, .pagination, nav.pager, ul.pager__items, .pager__item")
        print(f"\nPagination elements found: {len(pager)}", flush=True)
        for p in pager:
            print(f"  Pager text: {p.get_text(strip=True, separator=' ')}", flush=True)
            for a in p.find_all("a", href=True):
                print(f"    Pager link: {a.get_text(strip=True)} -> {a['href']}", flush=True)
                
        # Main content / items listing
        # Look for views rows, articles, tables, lists
        views_rows = soup.select(".view-content .views-row, .views-view-grid .views-row, table.views-table tbody tr, .node--type-decision, .node")
        print(f"\nListing items found (rows/nodes): {len(views_rows)}", flush=True)
        
        for i, row in enumerate(views_rows[:5]):
            print(f"\n  --- Sample Item #{i+1} ---", flush=True)
            # Find links
            links = row.find_all("a", href=True)
            for l in links:
                print(f"    Link: [{l.get_text(strip=True)}] -> {unquote(urljoin(str(resp.url), l['href']))}", flush=True)
            # Sample text
            print(f"    Text: {row.get_text(strip=True, separator=' | ')[:300]}", flush=True)

        # Check for PDF links
        pdf_links = [a for a in soup.find_all("a", href=True) if a["href"].lower().endswith(".pdf") or ".pdf" in a["href"].lower()]
        print(f"\nPDF links on page: {len(pdf_links)}", flush=True)
        for pdf in pdf_links[:5]:
            print(f"  PDF: [{pdf.get_text(strip=True)}] -> {unquote(urljoin(str(resp.url), pdf['href']))}", flush=True)
            
        return soup, resp
    except Exception as e:
        print(f"Error inspecting {url}: {e}", flush=True)
        return None, None

def main():
    client = get_client()
    
    # 1. conseildetat.dz - Jurisprudence / Documents
    inspect_page(client, "Conseil d'État - Ijtihad Qada'i (Jurisprudence)", 
                 "https://conseildetat.dz/ar/%D8%A7%D9%84%D8%A5%D8%AC%D8%AA%D9%87%D8%A7%D8%AF-%D8%A7%D9%84%D9%82%D8%B6%D8%A7%D8%A6%D9%8A/%D8%A7%D9%84%D9%88%D8%AB%D8%A7%D8%A6%D9%82")
    
    # 2. conseildetat.dz - Selected Decisions
    inspect_page(client, "Conseil d'État - Qararat Mokhtara (Selected Decisions)", 
                 "https://conseildetat.dz/ar/%D8%A7%D9%84%D9%82%D8%B1%D8%A7%D8%A1%D8%A7%D8%AA-%D8%A7%D9%84%D9%85%D8%AE%D8%AA%D8%A7%D8%B1%D8%A9")

    # 3. conseildetat.dz - Magazines / Revues
    inspect_page(client, "Conseil d'État - Majallat (Revues)", 
                 "https://conseildetat.dz/ar/%D9%85%D8%AC%D9%84%D8%A7%D8%AA-%D9%85%D8%AC%D9%84%D8%B3-%D8%A7%D9%84%D8%AF%D9%88%D9%84%D8%A9")
                 
    # 4. conseildetat.dz - French homepage & pages
    inspect_page(client, "Conseil d'État - Version Française", 
                 "https://conseildetat.dz/fr")
                 
    # 5. droit.mjustice.gov.dz - French & Arabic Jurisprudence sections
    inspect_page(client, "Portail Droit - Jurisprudence Accueil FR", 
                 "https://droit.mjustice.gov.dz/fr/content/arrets-des-cours-rendus-en-matiere-commerciale-et-sociale")

if __name__ == "__main__":
    main()
