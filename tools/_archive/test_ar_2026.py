"""
Test spécifique pour vérifier la disponibilité de l'index AR 2026
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient
from bs4 import BeautifulSoup
import re

print("=" * 60)
print("Test AR 2026 - Vérification de disponibilité")
print("=" * 60)

with JoradpClient() as client:
    url = "https://www.joradp.dz/JRN/ZA2026.htm"
    print(f"URL testée: {url}")
    
    response = client.get(url)
    if response:
        print(f"[OK] HTTP {response.status_code}")
        print(f"Taille: {len(response.text)} octets")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        # Cherche les liens MaxWin
        maxwin_pattern = re.compile(r"MaxWin\(['\"](\d+)['\"]\)", re.IGNORECASE)
        matches = maxwin_pattern.findall(response.text)
        print(f"\nMaxWin trouvés: {len(matches)}")
        
        if matches:
            print(f"Premiers numéros: {matches[:15]}")
            print(f"Derniers numéros: {matches[-5:]}")
            
            # Vérifie avec BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            maxwin_links = [l for l in links if 'MaxWin' in l.get('href', '')]
            print(f"Liens MaxWin via BeautifulSoup: {len(maxwin_links)}")
            
            if maxwin_links:
                print("L'index AR 2026 est DISPONIBLE avec des numéros!")
            else:
                print("L'index AR 2026 est disponible mais sans liens MaxWin détectés")
        else:
            print("L'index AR 2026 est disponible mais SANS numéros MaxWin")
            print("C'est probablement un formulaire dynamique comme détecté précédemment")
            
            # Cherche les formulaires
            soup = BeautifulSoup(response.text, 'html.parser')
            forms = soup.find_all('form')
            print(f"Formulaires trouvés: {len(forms)}")
            
            for i, form in enumerate(forms):
                print(f"\nFormulaire {i}:")
                print(f"  Action: {form.get('action', 'N/A')}")
                print(f"  Name: {form.get('name', 'N/A')}")
                
                selects = form.find_all('select')
                for select in selects:
                    print(f"  Select: {select.get('name', 'N/A')}")
                    options = select.find_all('option')
                    print(f"    Options: {len(options)}")
                    for j, opt in enumerate(options[:5]):
                        print(f"      {j}: {opt.get('value', 'N/A')} -> {opt.get_text(strip=True)[:30]}")
    else:
        print("[FAIL] Impossible de récupérer l'index AR 2026")