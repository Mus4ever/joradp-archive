"""
Sonde d'exploration détaillée pour les trois sources :
1. droit.mjustice.gov.dz (FR & AR)
2. conseildetat.dz
3. conseil-etat-dz.org
"""

import ssl
import httpx
import truststore
from bs4 import BeautifulSoup
import json
import socket

def get_verified_client():
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.options |= 0x4  # SSL_OP_LEGACY_SERVER_CONNECT
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    return httpx.Client(
        verify=context,
        timeout=25.0,
        follow_redirects=True,
        headers={"User-Agent": "AlgerianLegalCorpusBot/0.1 (academic legal research; polite crawler)"}
    )

def inspect_old_domain():
    print("==================================================")
    print("INSPECTION 1: ANCIEN DOMAINE conseil-etat-dz.org")
    print("==================================================")
    
    # 1. DNS check
    domain = "conseil-etat-dz.org"
    try:
        ips = socket.gethostbyname_ex(domain)
        print(f"DNS resolution for {domain}: {ips}")
    except Exception as e:
        print(f"DNS resolution failed: {e}")

    # 2. HTTP (non-ssl)
    try:
        with httpx.Client(timeout=10.0, follow_redirects=False) as client:
            resp = client.get(f"http://{domain}/")
            print(f"HTTP http://{domain}/ status: {resp.status_code}")
            print(f"  Headers: {dict(resp.headers)}")
            if resp.is_redirect:
                print(f"  Redirects to: {resp.headers.get('location')}")
            else:
                print(f"  Body preview: {resp.text[:300]}")
    except Exception as e:
        print(f"HTTP request error: {e}")

    # 3. HTTPS without cert check
    try:
        with httpx.Client(verify=False, timeout=10.0, follow_redirects=False) as client:
            resp = client.get(f"https://{domain}/")
            print(f"HTTPS (unverified) status: {resp.status_code}")
            print(f"  Headers: {dict(resp.headers)}")
            if resp.is_redirect:
                print(f"  Redirects to: {resp.headers.get('location')}")
            else:
                print(f"  Body preview: {resp.text[:300]}")
    except Exception as e:
        print(f"HTTPS (unverified) request error: {e}")

def inspect_droit_mjustice():
    print("\n==================================================")
    print("INSPECTION 2: PORTAIL DU DROIT (droit.mjustice.gov.dz)")
    print("==================================================")
    
    with get_verified_client() as client:
        # Check robots.txt
        resp_robots = client.get("https://droit.mjustice.gov.dz/robots.txt")
        print(f"Robots.txt status: {resp_robots.status_code}")
        print("Robots.txt content:")
        print(resp_robots.text)
        print("---")
        
        # Check /fr and /ar homepages
        for lang, url in [("FR", "https://droit.mjustice.gov.dz/fr"), ("AR", "https://droit.mjustice.gov.dz/ar")]:
            resp = client.get(url)
            print(f"\nHomepage {lang} ({url}): status {resp.status_code}")
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Find all navigation links
            print(f"Navigation menu items ({lang}):")
            nav_links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True)
                if text and ("jurisprudence" in href.lower() or "jurisprudence" in text.lower() or 
                             "conseil" in href.lower() or "conseil" in text.lower() or
                             "قضاء" in text or "اجتهاد" in text or "مجلس الدولة" in text or
                             "arret" in href.lower() or "decision" in href.lower()):
                    nav_links.append((text, href))
            
            for text, href in set(nav_links):
                print(f"  - [{text}] -> {href}")

def inspect_conseildetat_dz():
    print("\n==================================================")
    print("INSPECTION 3: CONSEIL D'ÉTAT (conseildetat.dz)")
    print("==================================================")
    
    with get_verified_client() as client:
        # Check robots.txt
        resp_robots = client.get("https://conseildetat.dz/robots.txt")
        print(f"Robots.txt status: {resp_robots.status_code}")
        print("Robots.txt content:")
        print(resp_robots.text)
        print("---")
        
        resp = client.get("https://conseildetat.dz/")
        print(f"Homepage status: {resp.status_code}")
        soup = BeautifulSoup(resp.text, "html.parser")
        
        print("All navigation links on conseildetat.dz:")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if text:
                print(f"  - [{text}] -> {href}")

if __name__ == "__main__":
    inspect_old_domain()
    inspect_droit_mjustice()
    inspect_conseildetat_dz()
