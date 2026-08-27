"""
Test de l'action réelle du formulaire AR 2026
Simule la soumission du formulaire pour voir l'URL générée
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient

print("=" * 80)
print("TEST DE L'ACTION DU FORMULAIRE AR 2026")
print("=" * 80)

# D'après l'analyse :
# - select name="znjo" 
# - onChange="Livejo(zFrm2,znjo,'arabe/2026/A20260')"
# - function Livejo: frm.action="../FTP/JO-"+zann+fld.value+".pdf"
# Donc pour zann='arabe/2026/A20260' et fld.value='061' -> ../FTP/JO-arabe/2026/A2026061.pdf

print("Analyse de la fonction Livejo:")
print("  Livejo(frm,fld,zann) avec fld.value='061' et zann='arabe/2026/A20260'")
print("  Résultat attendu: ../FTP/JO-arabe/2026/A2026061.pdf")
print()

with JoradpClient() as client:
    # Test quelques numéros pour voir le pattern réel
    test_numbers = ['061', '060', '059', '001', '062']
    
    for num in test_numbers:
        # Construction selon le pattern Livejo
        url_livejo = f"https://www.joradp.dz/FTP/JO-arabe/2026/A20260{num}.pdf"
        
        # Construction selon le pattern standard (vu dans les autres années)
        url_standard = f"https://www.joradp.dz/FTP/jo-arabe/2026/A2026{num}.pdf"
        
        print(f"Test numéro {num}:")
        print(f"  Pattern Livejo: {url_livejo}")
        response_livejo = client.get(url_livejo)
        if response_livejo:
            print(f"    [OK] HTTP {response_livejo.status_code} - Taille: {len(response_livejo.content)}")
        else:
            print(f"    [FAIL]")
        
        print(f"  Pattern standard: {url_standard}")
        response_standard = client.get(url_standard)
        if response_standard:
            print(f"    [OK] HTTP {response_standard.status_code} - Taille: {len(response_standard.content)}")
        else:
            print(f"    [FAIL]")
        print()
    
    print("=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print("Lequel des deux patterns fonctionne réellement ?")