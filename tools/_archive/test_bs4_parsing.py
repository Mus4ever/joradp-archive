"""
Test de parsing BeautifulSoup sur le HTML AR 2026
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient
from bs4 import BeautifulSoup
import re

with JoradpClient() as client:
    response = client.get("https://www.joradp.dz/JRN/ZA2026.htm", force_encoding="utf-16")
    if response:
        html = response.text
        print(f"Taille HTML: {len(html)}")
        print(f"Contient 'option': {'option' in html.lower()}")
        print(f"Contient 'form': {'form' in html.lower()}")
        print()
        
        # Test avec BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        forms = soup.find_all('form')
        print(f"Formulaires trouvés: {len(forms)}")
        
        for i, form in enumerate(forms):
            print(f"\nFormulaire {i}:")
            print(f"  Name: {form.get('name', 'N/A')}")
            
            selects = form.find_all('select')
            print(f"  Selects: {len(selects)}")
            
            for j, select in enumerate(selects):
                print(f"  Select {j}:")
                print(f"    Name: {select.get('name', 'N/A')}")
                
                options = select.find_all('option')
                print(f"    Options: {len(options)}")
                
                for k, option in enumerate(options[:10]):
                    value = option.get('value', 'N/A')
                    text = option.get_text(strip=True)
                    print(f"      {k}: value={value}, text={text}")