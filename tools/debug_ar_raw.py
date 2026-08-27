"""
Script pour examiner l'index arabe en mode brut (sans BeautifulSoup)
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient
import re

with JoradpClient() as client:
    response = client.get('https://www.joradp.dz/JRN/ZA2026.htm')
    if response:
        html = response.text
        print(f"Taille: {len(html)} octets")
        print(f"Encodage: {response.encoding}")
        
        # Cherche MaxWin directement
        maxwin_pattern = re.compile(r"MaxWin\(['\"](\d+)['\"]\)", re.IGNORECASE)
        matches = maxwin_pattern.findall(html)
        print(f"\nMaxWin trouvés: {len(matches)}")
        if matches:
            print(f"Premiers: {matches[:20]}")
        
        # Cherche les motifs javascript:MaxWin
        js_pattern = re.compile(r"javascript:MaxWin\(['\"](\d+)['\"]\)", re.IGNORECASE)
        js_matches = js_pattern.findall(html)
        print(f"\njavascript:MaxWin trouvés: {len(js_matches)}")
        if js_matches:
            print(f"Premiers: {js_matches[:20]}")
        
        # Cherche les motifs de liens <a>
        link_pattern = re.compile(r"<a[^>]*href=['\"]([^'\"]*)['\"][^>]*>", re.IGNORECASE)
        links = link_pattern.findall(html)
        print(f"\nLiens trouvés: {len(links)}")
        for i, link in enumerate(links[:30]):
            print(f"  {i}: {link}")
        
        # Sauvegarde pour examen
        with open("debug_ar_raw.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("\nSauvegardé dans debug_ar_raw.html")
        
        # Extrait un échantillon du HTML (sans affichage console pour éviter unicode errors)
        print("\nEchantillon HTML sauvegarde (premiers 2000 caracteres)")
    else:
        print("FAIL")