"""
Script pour examiner la structure de l'index arabe en détail
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient
from bs4 import BeautifulSoup
import re

with JoradpClient() as client:
    response = client.get('https://www.joradp.dz/JRN/ZA2026.htm')
    if response:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Cherche les formulaires
        print("Formulaires trouvés:", len(soup.find_all('form')))
        for i, form in enumerate(soup.find_all('form')):
            print(f"\n--- Formulaire {i} ---")
            print(f"Action: {form.get('action', 'N/A')}")
            print(f"Name: {form.get('name', 'N/A')}")
            print(f"Target: {form.get('target', 'N/A')}")
            
            # Cherche les selects
            for select in form.find_all('select'):
                print(f"\nSelect: {select.get('name', 'N/A')}")
                print(f"OnChange: {select.get('onchange', 'N/A')}")
                for j, option in enumerate(select.find_all('option')[:15]):
                    print(f"  Option {j}: {option.get('value', 'N/A')} -> {option.get_text(strip=True)[:50]}")
        
        # Cherche tous les scripts
        print(f"\nScripts trouvés: {len(soup.find_all('script'))}")
        for i, script in enumerate(soup.find_all('script')):
            src = script.get('src', 'inline')
            print(f"Script {i}: {src}")
            if script.string and len(script.string) < 500:
                print(f"  Contenu: {script.string[:200]}")
        
        # Cherche les liens
        print(f"\nLiens trouvés: {len(soup.find_all('a'))}")
        for i, link in enumerate(soup.find_all('a')[:20]):
            href = link.get('href', '')
            text = link.get_text(strip=True)[:50]
            if href or text:
                print(f"  {i}: {href} -> {text}")
    else:
        print("FAIL")