"""
Debug spécifique pour AR 2025 qui échoue
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient
from bs4 import BeautifulSoup

with JoradpClient() as client:
    response = client.get("https://www.joradp.dz/JRN/ZA2025.htm")
    if response:
        print(f"Taille: {len(response.text)}")
        print(f"Contient 'form': {'form' in response.text.lower()}")
        print(f"Contient 'MaxWin': {'MaxWin' in response.text}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        forms = soup.find_all('form')
        print(f"Formulaires trouvés: {len(forms)}")
        
        for i, form in enumerate(forms):
            print(f"\nFormulaire {i}:")
            print(f"  Name: {form.get('name', 'N/A')}")
            print(f"  Action: {form.get('action', 'N/A')}")
            
            selects = form.find_all('select')
            print(f"  Selects: {len(selects)}")
            
            for j, select in enumerate(selects):
                print(f"  Select {j}:")
                print(f"    Name: {select.get('name', 'N/A')}")
                options = select.find_all('option')
                print(f"    Options: {len(options)}")
                for k, option in enumerate(options[:5]):
                    value = option.get('value', 'N/A')
                    text = option.get_text(strip=True)[:30]
                    print(f"      {k}: value={value}, text={text}")
        
        # Cherche les liens MaxWin
        links = soup.find_all('a', href=True)
        maxwin_links = [l for l in links if 'MaxWin' in l.get('href', '')]
        print(f"\nLiens MaxWin: {len(maxwin_links)}")
        for i, link in enumerate(maxwin_links[:5]):
            print(f"  {i}: {link.get('href')}")