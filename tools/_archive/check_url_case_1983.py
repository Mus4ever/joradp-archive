"""
Vérification de la casse d'URL pour 1983 (période legacy)
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient

# Teste un PDF legacy AR 1983
test_urls = [
    "https://www.joradp.dz/FTP/Jo-Arabe/1983/A1983001.pdf",  # Casse mixte (documentée)
    "https://www.joradp.dz/FTP/JO-ARABE/1983/A1983001.pdf",  # Tout majuscules
    "https://www.joradp.dz/FTP/jo-arabe/1983/A1983001.pdf",  # Tout minuscules
]

print("VERIFICATION CASSE URL LEGACY 1983")
print("=" * 80)

with JoradpClient() as client:
    for test_url in test_urls:
        test_response = client.get(test_url)
        if test_response:
            print(f"[OK] {test_url} -> HTTP {test_response.status_code}, {len(test_response.content)} octets")
        else:
            print(f"[FAIL] {test_url}")