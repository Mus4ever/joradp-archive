"""
Script pour examiner le fichier Journal.js
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient

with JoradpClient() as client:
    response = client.get('https://www.joradp.dz/JVS/Journal.js')
    if response:
        with open("journal_js.txt", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("Journal.js sauvegardé dans journal_js.txt")
        print(f"Taille: {len(response.text)} octets")
    else:
        print("FAIL")