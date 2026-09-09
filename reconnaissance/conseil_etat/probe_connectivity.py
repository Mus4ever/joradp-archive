"""
Sonde de connectivité et robots.txt pour la jurisprudence du Conseil d'État.
Teste la résolution DNS, le statut HTTP, les en-têtes, SSL et robots.txt.
"""

import sys
import ssl
import httpx
import truststore
from urllib.parse import urlparse

DOMAINS_TO_TEST = [
    "https://droit.mjustice.gov.dz/fr",
    "https://droit.mjustice.gov.dz/ar",
    "https://droit.mjustice.gov.dz/robots.txt",
    "https://conseildetat.dz/",
    "https://conseildetat.dz/robots.txt",
    "https://conseil-etat-dz.org/",
    "https://conseil-etat-dz.org/robots.txt",
]

def get_ssl_context():
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.options |= 0x4  # SSL_OP_LEGACY_SERVER_CONNECT
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    return context

def test_url(url: str):
    print(f"=== Testing: {url} ===")
    ctx = get_ssl_context()
    
    # Try with normal client first, with redirect follow
    try:
        with httpx.Client(verify=ctx, timeout=15.0, follow_redirects=False,
                          headers={"User-Agent": "AlgerianLegalCorpusBot/0.1 (academic legal research; polite crawler)"}) as client:
            resp = client.get(url)
            print(f"  HTTP Status: {resp.status_code}")
            print(f"  Final URL: {resp.url}")
            print(f"  Headers:")
            for k in ["server", "content-type", "location", "set-cookie", "content-length"]:
                if k in resp.headers:
                    print(f"    {k}: {resp.headers[k]}")
            
            if resp.is_redirect:
                print(f"  Redirect Location: {resp.headers.get('location')}")
                
            if "text" in resp.headers.get("content-type", ""):
                sample = resp.text[:500].replace("\n", " ")
                print(f"  Sample Text (first 500 chars): {sample[:200]}...")
            elif "robots.txt" in url:
                print(f"  Robots content:\n{resp.text[:1000]}")
    except httpx.ConnectError as e:
        print(f"  ConnectError: {e}")
    except httpx.ConnectTimeout as e:
        print(f"  ConnectTimeout: {e}")
    except ssl.SSLError as e:
        print(f"  SSLError: {e}")
        # Try unverified if needed to see if it's purely a cert issue
        try:
            with httpx.Client(verify=False, timeout=15.0, follow_redirects=False) as unverified_client:
                resp = unverified_client.get(url)
                print(f"  [UNVERIFIED SSL TEST] Status: {resp.status_code}")
        except Exception as e2:
            print(f"  [UNVERIFIED SSL TEST] Failed: {e2}")
    except Exception as e:
        print(f"  General Exception: {type(e).__name__}: {e}")
    print()

if __name__ == "__main__":
    for target in DOMAINS_TO_TEST:
        test_url(target)
