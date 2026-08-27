"""
Test ultra-simple : vérifie si MaxWin fonctionne pour AR 1968
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient
import time

print("TEST ULTRA-SIMPLE AR 1968")
print("=" * 80)

with JoradpClient() as client:
    url = "https://www.joradp.dz/JRN/ZA1968.htm"
    
    start_time = time.time()
    response = client.get(url)
    elapsed = time.time() - start_time
    
    print(f"Temps de requête: {elapsed:.2f} secondes")
    
    if response:
        print(f"HTTP {response.status_code}")
        print(f"Taille: {len(response.text)} octets")
        print(f"Contient MaxWin: {'MaxWin' in response.text}")
        
        maxwin_count = response.text.count("MaxWin")
        print(f"Nombre de MaxWin: {maxwin_count}")
    else:
        print("Échec de la requête")