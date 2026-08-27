"""
Script de debug pour examiner la structure des index annuels.
"""

from http_client import JoradpClient
from bs4 import BeautifulSoup
import re


def debug_index(url: str):
    """Examine le contenu d'un index annuel."""
    with JoradpClient() as client:
        response = client.get(url)
        if not response:
            print(f"FAIL: Impossible de récupérer {url}")
            return
        
        print(f"OK: Récupéré {url}")
        print(f"Taille: {len(response.text)} octets")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        # Sauvegarde pour examen manuel
        with open("debug_index.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("Contenu sauvegardé dans debug_index.html")
        
        # Analyse avec BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Cherche tous les scripts
        print(f"\nScripts trouvés: {len(soup.find_all('script'))}")
        for i, script in enumerate(soup.find_all('script')):
            if script.string:
                print(f"\n--- Script {i} ---")
                # Montre les premières lignes
                lines = script.string.split('\n')[:10]
                for line in lines:
                    print(line)
                
                # Cherche MaxWin
                maxwin_matches = re.findall(r"MaxWin\(['\"](\d+)['\"]\)", script.string)
                if maxwin_matches:
                    print(f"MaxWin trouvés: {maxwin_matches[:10]}")  # Premiers 10
        
        # Cherche les liens
        print(f"\nLiens trouvés: {len(soup.find_all('a'))}")
        for i, link in enumerate(soup.find_all('a')[:20]):
            href = link.get('href', '')
            text = link.get_text(strip=True)[:50]
            print(f"  {i}: {href} -> {text}")


if __name__ == "__main__":
    print("=" * 60)
    print("Debug Index FR 2026")
    print("=" * 60)
    debug_index("https://www.joradp.dz/JRN/ZF2026.htm")
    
    print("\n" + "=" * 60)
    print("Debug Index AR 2026")
    print("=" * 60)
    debug_index("https://www.joradp.dz/JRN/ZA2026.htm")