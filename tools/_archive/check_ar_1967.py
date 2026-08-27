"""
Vérification manuelle de l'index AR 1967 pour expliquer l'écart FR=107 vs AR=74
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient
from bs4 import BeautifulSoup

url = "https://www.joradp.dz/JRN/ZA1967.htm"

print("VERIFICATION INDEX AR 1967")
print("=" * 80)
print(f"URL: {url}")
print()

with JoradpClient() as client:
    response = client.get(url)
    
    if response:
        print(f"HTTP {response.status_code}")
        print(f"Taille: {len(response.text)} octets")
        print(f"Contient MaxWin: {'MaxWin' in response.text}")
        
        # Extraction des numéros MaxWin
        soup = BeautifulSoup(response.text, 'html.parser')
        maxwin_pattern = r"MaxWin\(['\"](\d+)['\"]\)"
        
        numeros = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            import re
            matches = re.findall(maxwin_pattern, href)
            for numero in matches:
                numeros.append(numero)
        
        # Unique et tri
        numeros_uniques = sorted(set(numeros), key=int)
        
        print(f"\nNombre de liens MaxWin: {len(numeros)}")
        print(f"Nombre de numéros uniques: {len(numeros_uniques)}")
        print(f"\nPremiers numéros: {numeros_uniques[:10]}")
        print(f"Derniers numéros: {numeros_uniques[-10:]}")
        
        # Vérification de continuité
        if numeros_uniques:
            min_num = int(numeros_uniques[0])
            max_num = int(numeros_uniques[-1])
            expected_count = max_num - min_num + 1
            actual_count = len(numeros_uniques)
            
            print(f"\nRange: {min_num} à {max_num}")
            print(f"Attendu (continu): {expected_count} numéros")
            print(f"Trouvé: {actual_count} numéros")
            
            if expected_count != actual_count:
                print(f"[ANOMALIE] {expected_count - actual_count} trous dans la séquence")
                
                # Trouve les trous
                missing = []
                for i in range(min_num, max_num + 1):
                    if str(i).zfill(3) not in [n.zfill(3) for n in numeros_uniques]:
                        missing.append(i)
                
                if missing:
                    print(f"Numéros manquants: {missing[:20]}")
                    if len(missing) > 20:
                        print(f"... et {len(missing) - 20} autres")
            else:
                print("[OK] Séquence continue")
    else:
        print("Échec de la requête")