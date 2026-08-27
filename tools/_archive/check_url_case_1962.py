"""
Vérification de la casse d'URL réelle pour FR 1962
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient
from bs4 import BeautifulSoup
import re

url = "https://www.joradp.dz/JRN/ZF1962.htm"

print("VERIFICATION CASSE URL FR 1962")
print("=" * 80)

with JoradpClient() as client:
    response = client.get(url)
    
    if response:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Cherche les liens JavaScript qui contiennent les URLs
        for script in soup.find_all('script'):
            if script.string:
                # Cherche les patterns d'URL dans le JavaScript
                ftp_patterns = re.findall(r'/FTP/[^/]+/1962/[^\s\']+\.pdf', script.string)
                for pattern in ftp_patterns:
                    print(f"Pattern trouvé: {pattern}")
        
        # Cherche spécifiquement le premier numéro pour tester l'URL réelle
        maxwin_pattern = r"MaxWin\(['\"](\d+)['\"]\)"
        first_match = None
        for link in soup.find_all('a', href=True):
            href = link['href']
            matches = re.findall(maxwin_pattern, href)
            if matches:
                first_match = matches[0]
                break
        
        if first_match:
            print(f"\nPremier numéro: {first_match}")
            
            # Teste différentes casses
            test_urls = [
                f"https://www.joradp.dz/FTP/JO-FRANCAIS/1962/F1962{first_match.zfill(3)}.pdf",
                f"https://www.joradp.dz/FTP/Jo-Francais/1962/F1962{first_match.zfill(3)}.pdf",
                f"https://www.joradp.dz/FTP/jo-francais/1962/F1962{first_match.zfill(3)}.pdf",
            ]
            
            print("\nTest des différentes casses:")
            for test_url in test_urls:
                test_response = client.get(test_url)
                if test_response:
                    print(f"  [OK] {test_url} -> HTTP {test_response.status_code}")
                else:
                    print(f"  [FAIL] {test_url}")
    else:
        print("Échec de la requête")