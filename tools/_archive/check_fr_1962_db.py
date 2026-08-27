"""
Vérifie ce qui a été enregistré pour FR 1962
"""

import sys
sys.path.append('tools')

from database import JoradpDatabase

db = JoradpDatabase()
with db:
    conn = db.connect()
    sources = conn.execute("""
        SELECT numero FROM sources 
        WHERE annee = 1962 AND langue = 'FR'
        ORDER BY numero
    """).fetchall()
    
    numeros = [row[0] for row in sources]
    
    print("FR 1962 - NUMÉROS ENREGISTRÉS")
    print("=" * 80)
    print(f"Total: {len(numeros)}")
    print(f"\nTous les numéros: {numeros}")
    
    # Vérifie la continuité
    if numeros:
        nums_int = [int(n) for n in numeros]
        min_num = min(nums_int)
        max_num = max(nums_int)
        expected = max_num - min_num + 1
        
        print(f"\nRange: {min_num} à {max_num}")
        print(f"Attendu (continu): {expected}")
        print(f"Trouvé: {len(numeros)}")
        
        if expected != len(numeros):
            print(f"[INFO] {expected - len(numeros)} trous (normal pour 1962 = année de démarrage)")