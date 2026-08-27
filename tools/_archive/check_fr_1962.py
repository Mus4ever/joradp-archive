"""
Vérification manuelle de l'index FR 1962
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient
from bs4 import BeautifulSoup
import re

url = "https://www.joradp.dz/JRN/ZF1962.htm"

print("VERIFICATION INDEX FR 1962")
print("=" * 80)
print(f"URL: {url}")
print()

with JoradpClient() as client:
    response = client.get(url)
    
    if response:
        print(f"HTTP {response.status_code}")
        print(f"Taille: {len(response.text)} octets")
        
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
        
        print(f"\nNombre de liens MaxWin: {len(numeros)}")
        print(f"Nombre de numéros uniques: {len(numeros_uniques)}")
        print(f"\nPremiers numéros: {numeros_uniques[:10]}")
        print(f"Derniers numéros: {numeros_uniques[-10:]}")
        
        if numeros_uniques:
            min_num = int(numeros_uniques[0])
            max_num = int(numeros_uniques[-1])
            print(f"\nRange: {min_num} à {max_num}")
            print(f"Total: {len(numeros_uniques)} numéros")
    else:
        print("Échec de la requête")