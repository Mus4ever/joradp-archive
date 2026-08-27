"""
Script pour tester plusieurs années d'index arabe pour comprendre la structure
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient
from bs4 import BeautifulSoup
import re

years_to_test = [2025, 2024, 2023, 2020, 2010, 2000, 1994]

with JoradpClient() as client:
    for year in years_to_test:
        url = f"https://www.joradp.dz/JRN/ZA{year}.htm"
        print(f"\n{'='*60}")
        print(f"Test AR {year}: {url}")
        print('='*60)
        
        response = client.get(url)
        if response:
            print(f"[OK] HTTP 200, Taille: {len(response.text)} octets")
            
            # Cherche les liens MaxWin
            maxwin_pattern = re.compile(r"MaxWin\(['\"](\d+)['\"]\)", re.IGNORECASE)
            matches = maxwin_pattern.findall(response.text)
            print(f"MaxWin trouvés: {len(matches)}")
            if matches:
                print(f"Exemples: {matches[:10]}")
            
            # Cherche les liens javascript
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            maxwin_links = [l for l in links if 'MaxWin' in l.get('href', '')]
            print(f"Liens MaxWin: {len(maxwin_links)}")
            if maxwin_links:
                for i, link in enumerate(maxwin_links[:5]):
                    print(f"  {i}: {link.get('href')}")
        else:
            print("[FAIL] Impossible de récupérer")