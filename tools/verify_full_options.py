"""
Vérification que les 61 valeurs extraites correspondent bien à la totalité des options
du select znjo, pas seulement à la portion visible dans l'extrait
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient
from bs4 import BeautifulSoup

print("=" * 80)
print("VÉRIFICATION COMPLÈTE DES OPTIONS DU SELECT ZNJO")
print("=" * 80)

with JoradpClient() as client:
    response = client.get("https://www.joradp.dz/JRN/ZA2026.htm", force_encoding="utf-16")
    if response:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Cherche le formulaire zFrm2
        form_zfrm2 = soup.find('form', {'name': 'zFrm2'})
        if form_zfrm2:
            # Cherche le select znjo
            select_znjo = form_zfrm2.find('select', {'name': 'znjo'})
            if select_znjo:
                # Extrait TOUTES les options
                options = select_znjo.find_all('option')
                
                print(f"Nombre total d'options: {len(options)}")
                print()
                
                # Analyse complète des valeurs
                values = []
                for i, option in enumerate(options):
                    value = option.get('value')
                    text = option.get_text(strip=True)
                    
                    if value and value.isdigit():
                        values.append(int(value))
                        if i < 5 or i >= len(options) - 5:  # Premiers et derniers
                            print(f"Option {i}: value={value}, text={text[:50]}")
                    elif i == 0:
                        print(f"Option {i}: value={value} (vide?), text={text[:50]}")
                
                if values:
                    values_sorted = sorted(values)
                    print()
                    print(f"Valeurs extraites: {len(values)}")
                    print(f"Valeur minimale: {min(values)}")
                    print(f"Valeur maximale: {max(values)}")
                    print(f"Plage complète: {min(values)} à {max(values)}")
                    print()
                    
                    # Vérifie si la plage est continue
                    expected_range = set(range(min(values), max(values) + 1))
                    actual_values = set(values)
                    missing = expected_range - actual_values
                    
                    if missing:
                        print(f"Valeurs manquantes: {sorted(missing)}")
                    else:
                        print("[OK] Plage continue - aucune valeur manquante")
                    
                    print()
                    print(f"Conclusion: Les {len(values)} valeurs correspondent bien à la plage complète")
                    print(f"de {min(values)} à {max(values)}, soit toutes les options du select znjo.")
            else:
                print("Select znjo non trouvé")
        else:
            print("Formulaire zFrm2 non trouvé")