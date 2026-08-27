"""
Examen détaillé du HTML brut reçu par le client Python pour AR 2026
Comparaison avec les notes de Phase 0
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient

print("=" * 80)
print("EXAMEN DU HTML BRUT AR 2026 - CLIENT PYTHON")
print("=" * 80)

with JoradpClient() as client:
    url = "https://www.joradp.dz/JRN/ZA2026.htm"
    print(f"URL: {url}")
    print(f"User-Agent: {client.config.user_agent}")
    print()
    
    response = client.get(url)
    if response:
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        print(f"Taille: {len(response.text)} octets")
        print(f"Encoding: {response.encoding}")
        print()
        
        # Sauvegarde le HTML brut complet
        with open("ar_2026_python_client.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("HTML brut sauvegardé: ar_2026_python_client.html")
        print()
        
        # Affiche les premières lignes du HTML brut (sans affichage console pour éviter unicode errors)
        print("=" * 80)
        print("PREMIÈRES LIGNES DU HTML BRUT (caractères 0-2000)")
        print("=" * 80)
        print("(Sauvegardé dans ar_2026_python_client.html pour examen manuel)")
        print()
        
        # Cherche des motifs spécifiques
        print("=" * 80)
        print("RECHERCHE DE MOTIFS SPÉCIFIQUES")
        print("=" * 80)
        
        # MaxWin
        if "MaxWin" in response.text:
            print("[OK] Motif 'MaxWin' trouvé dans le HTML")
            # Extrait les occurrences
            import re
            maxwin_pattern = re.compile(r"MaxWin\(['\"](\d+)['\"]\)", re.IGNORECASE)
            matches = maxwin_pattern.findall(response.text)
            print(f"    Occurrences: {len(matches)}")
            if matches:
                print(f"    Exemples: {matches[:10]}")
        else:
            print("[INFO] Motif 'MaxWin' NON trouvé dans le HTML")
        
        # Formulaire
        if "<form" in response.text.lower():
            print("[OK] Balise <form> trouvée dans le HTML")
        else:
            print("[INFO] Balise <form> NON trouvée dans le HTML")
        
        # Select
        if "<select" in response.text.lower():
            print("[OK] Balise <select> trouvée dans le HTML")
        else:
            print("[INFO] Balise <select> NON trouvée dans le HTML")
        
        # Liens
        link_count = response.text.count("<a")
        print(f"[INFO] Nombre de balises <a>: {link_count}")
        
        # JavaScript
        if "<script" in response.text.lower():
            print("[OK] Balise <script> trouvée dans le HTML")
            script_count = response.text.count("<script")
            print(f"    Nombre de balises <script>: {script_count}")
        else:
            print("[INFO] Balise <script> NON trouvée dans le HTML")
        
        print()
        print("=" * 80)
        print("COMPARAISON AVEC NOTES PHASE 0")
        print("=" * 80)
        print("Phase 0 notait: 'les index 2026 arabe et français exposent les numéros")
        print("directement dans le HTML ; par exemple l'arabe contient MaxWin('001'), etc.'")
        print()
        print("Réalité client Python:")
        if "MaxWin" in response.text:
            print("  - Les motifs MaxWin SONT présents -> Concordance avec Phase 0")
        else:
            print("  - Les motifs MaxWin sont ABSENTS -> ÉCART avec Phase 0")
            print("  - Possibilités: mauvaise page vérifiée, contenu changé, ou")
            print("    différence client/navigateur (session, cookie, en-tête)")
    else:
        print("[FAIL] Impossible de récupérer la page")