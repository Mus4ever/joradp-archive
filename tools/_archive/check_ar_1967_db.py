"""
Vérifie ce qui a été réellement enregistré pour AR 1967 dans la base
"""

import sys
sys.path.append('tools')

from database import JoradpDatabase

db = JoradpDatabase()
with db:
    conn = db.connect()
    # Récupère les numéros AR 1967
    sources = conn.execute("""
        SELECT numero FROM sources 
        WHERE annee = 1967 AND langue = 'AR'
        ORDER BY numero
    """).fetchall()
    
    numeros = [row[0] for row in sources]
    
    print("AR 1967 - NUMÉROS ENREGISTRÉS DANS LA BASE")
    print("=" * 80)
    print(f"Total enregistré: {len(numeros)}")
    print(f"Premiers: {numeros[:10]}")
    print(f"Derniers: {numeros[-10:]}")
    
    # Vérifie la continuité
    if numeros:
        nums_int = [int(n) for n in numeros]
        min_num = min(nums_int)
        max_num = max(nums_int)
        expected = max_num - min_num + 1
        
        print(f"\nRange: {min_num} à {max_num}")
        print(f"Attendu: {expected} numéros")
        print(f"Trouvé: {len(numeros)} numéros")
        
        if expected != len(numeros):
            missing = []
            for i in range(min_num, max_num + 1):
                if str(i).zfill(3) not in numeros:
                    missing.append(i)
            
            print(f"Numéros manquants: {missing}")
    
    # Compare avec FR 1967
    fr_sources = conn.execute("""
        SELECT numero FROM sources 
        WHERE annee = 1967 AND langue = 'FR'
        ORDER BY numero
    """).fetchall()
    
    fr_numeros = [row[0] for row in fr_sources]
    print(f"\nFR 1967 pour comparaison: {len(fr_numeros)} numéros")