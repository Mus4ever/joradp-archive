"""
Extrait le HTML brut AR 1967 avec les liens MaxWin pour documentation
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient

url = "https://www.joradp.dz/JRN/ZA1967.htm"

print("EXTRACTION HTML BRUT AR 1967 - MAXWIN")
print("=" * 80)

with JoradpClient() as client:
    response = client.get(url)
    
    if response:
        html = response.text
        
        # Sauvegarde le HTML brut pour inspection
        with open("ar_1967_raw.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        print(f"HTML brut sauvegardé: ar_1967_raw.html ({len(html)} octets)")
        
        # Extrait et affiche les lignes contenant MaxWin
        print("\nEXTRAIT DES LIENS MAXWIN (premiers 20):")
        print("-" * 80)
        
        lines = html.split('\n')
        maxwin_lines = []
        
        for line in lines:
            if 'MaxWin' in line:
                maxwin_lines.append(line.strip())
        
        for i, line in enumerate(maxwin_lines[:20]):
            print(f"{i+1:2d}. {line}")
        
        if len(maxwin_lines) > 20:
            print(f"... et {len(maxwin_lines) - 20} autres lignes MaxWin")
        
        print(f"\nTotal lignes MaxWin: {len(maxwin_lines)}")
        
        # Compte les numéros uniques
        import re
        maxwin_pattern = r"MaxWin\(['\"](\d+)['\"]\)"
        all_matches = re.findall(maxwin_pattern, html)
        unique_numbers = sorted(set(all_matches), key=int)
        
        print(f"Numéros uniques extraits: {len(unique_numbers)}")
        print(f"Premiers: {unique_numbers[:10]}")
        print(f"Derniers: {unique_numbers[-10:]}")
        print(f"Range: {unique_numbers[0]} à {unique_numbers[-1]}")
    else:
        print("Échec de la requête")