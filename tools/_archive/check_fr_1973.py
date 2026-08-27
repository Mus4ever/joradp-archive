"""
Vérification manuelle de l'index FR 1973
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient
from bs4 import BeautifulSoup
import re

url = "https://www.joradp.dz/JRN/ZF1973.htm"

print("VERIFICATION INDEX FR 1973")
print("=" * 80)
print(f"URL: {url}")
print()

with JoradpClient() as client:
    response = client.get(url)
    
    if response:
        print(f"HTTP {response.status_code}")
        
        # Extraction des numéros MaxWin
        soup = BeautifulSoup(response.text, 'html.parser')
        maxwin_pattern = r"MaxWin\(['\"](\d+)['\"]\)"
        
        numeros = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            matches = re.findall(maxwin_pattern, href)
            for numero in matches:
                numeros.append(numero)
        
        # Unique et tri
        numeros_uniques = sorted(set(numeros), key=int)
        
        print(f"Nombre de numéros uniques: {len(numeros_uniques)}")
        print(f"Range: {int(numeros_uniques[0])} à {int(numeros_uniques[-1])}")
        
        # Vérifie si 75 est dans la liste
        if '075' in numeros_uniques:
            print("[OK] Numéro 75 présent")
        else:
            print("[INFO] Numéro 75 absent dans l'index")
            
        # Affiche autour de 75
        nums_int = [int(n) for n in numeros_uniques]
        for i, n in enumerate(nums_int):
            if n == 74:
                print(f"Contexte: ...{nums_int[i-2] if i>=2 else ''}, {nums_int[i-1] if i>=1 else ''}, {n}, {nums_int[i+1] if i+1 < len(nums_int) else ''}, {nums_int[i+2] if i+2 < len(nums_int) else ''}...")
    else:
        print("Échec de la requête")