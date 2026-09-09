"""
Sonde pour interroger la base de jurisprudence et les revues sur conseildetat.dz
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

def probe_jurisprudence_search():
    client = get_client()
    url = "https://conseildetat.dz/ar/الإجتهاد-القضائي/الوثائق"
    
    print(f"=== PROBING JURISPRUDENCE SEARCH ON {url} ===", flush=True)
    
    # Let's test a GET query with no filters or submit the exposed form
    # Let's inspect the exact form markup on the page
    resp = client.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    view = soup.select(".view, .view-id-jurisprudence, .view-id-ijtihad")
    print(f"Views classes found: {[v.get('class') for v in view]}", flush=True)
    
    # Check if there are results by default or after submitting
    # Check exposed filter form ID and inputs
    form = soup.find("form", id=lambda x: x and "views-exposed-form" in x)
    if form:
        print(f"Exposed form ID: {form.get('id')}, Action: {form.get('action')}, Method: {form.get('method')}", flush=True)
        data = {}
        for inp in form.find_all(["input", "select"]):
            name = inp.get("name")
            if name:
                if inp.name == "select":
                    # test with all/first option
                    val = inp.find("option").get("value", "All")
                    data[name] = val
                elif inp.get("type") == "submit":
                    continue
                else:
                    data[name] = inp.get("value", "")
        print(f"Default form payload: {data}", flush=True)
        
        # Try GET with this payload or empty
        res_resp = client.get(url, params=data)
        res_soup = BeautifulSoup(res_resp.text, "html.parser")
        
        # Check rows in result
        rows = res_soup.select(".view-content .views-row, table.views-table tbody tr, .views-view-grid .views-col, .node")
        print(f"Rows found with default query: {len(rows)}", flush=True)
        
        # Check if there is a pager
        pager = res_soup.select("nav.pager, ul.pager__items, .pagination")
        if pager:
            print(f"Pager found: {pager[0].get_text(strip=True, separator=' ')}", flush=True)
            for a in pager[0].find_all("a"):
                print(f"  Pager link: {a.get_text(strip=True)} -> {a.get('href')}", flush=True)
        else:
            print("No pager found.", flush=True)
            
        # Try searching by selecting specific chambers
        chamber_select = form.find("select", attrs={"name": "field_chamber_juris_value"})
        if chamber_select:
            options = chamber_select.find_all("option")
            print(f"\nTesting Chamber Options ({len(options)} options):", flush=True)
            for opt in options:
                opt_val = opt.get("value")
                opt_text = opt.get_text(strip=True)
                if not opt_val or opt_val == "_none" or opt_val == "All":
                    continue
                query = dict(data)
                query["field_chamber_juris_value"] = opt_val
                q_resp = client.get(url, params=query)
                q_soup = BeautifulSoup(q_resp.text, "html.parser")
                q_rows = q_soup.select(".view-content .views-row, table.views-table tbody tr, .views-view-grid .views-col")
                q_pager = q_soup.select("nav.pager, ul.pager__items")
                pager_info = q_pager[0].get_text(strip=True, separator=' ') if q_pager else "No pager"
                print(f"  Chamber '{opt_text}' (val={opt_val}): {len(q_rows)} rows visible, Pager: {pager_info}", flush=True)
                
                # Print details of first row if available
                if q_rows:
                    first_row = q_rows[0]
                    links = [a.get("href") for a in first_row.find_all("a", href=True)]
                    print(f"    First item links: {links}", flush=True)
                    print(f"    First item text: {first_row.get_text(strip=True, separator=' | ')[:200]}", flush=True)

def probe_magazines():
    client = get_client()
    url = "https://conseildetat.dz/ar/مجلات-مجلس-الدولة"
    print(f"\n=== PROBING MAGAZINES / REVUES ON {url} ===", flush=True)
    
    resp = client.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    form = soup.find("form", id=lambda x: x and "views-exposed-form" in x)
    
    if form:
        year_select = form.find("select", attrs={"name": "year_enhanced_filter"})
        if year_select:
            options = year_select.find_all("option")
            print(f"Found {len(options)} year options in filter:", flush=True)
            for opt in options:
                val = opt.get("value")
                text = opt.get_text(strip=True)
                if not val or val == "All" or val == "_none":
                    continue
                q_resp = client.get(url, params={"year_enhanced_filter": val})
                q_soup = BeautifulSoup(q_resp.text, "html.parser")
                rows = q_soup.select(".view-content .views-row, table.views-table tbody tr, .views-view-grid .views-col, .node")
                pdf_links = [a.get("href") for a in q_soup.find_all("a", href=True) if ".pdf" in a.get("href", "").lower()]
                print(f"  Year {text} (val={val}): {len(rows)} items, {len(pdf_links)} PDF links -> {pdf_links[:3]}", flush=True)

if __name__ == "__main__":
    probe_jurisprudence_search()
    probe_magazines()
