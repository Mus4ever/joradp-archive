"""
Vérification de continuité de séquence pour toutes les années
Détecte les trous entre numéros (ex: 001, 002, 004 -> trou en 003)
"""

import sys
sys.path.append('tools')

from database import JoradpDatabase

db = JoradpDatabase()
with db:
    conn = db.connect()
    
    # Récupère toutes les années/langues
    years_langs = conn.execute("""
        SELECT annee, langue FROM sources 
        GROUP BY annee, langue 
        ORDER BY annee, langue
    """).fetchall()
    
    print("VERIFICATION DE CONTINUITE DE SEQUENCE")
    print("=" * 80)
    
    total_issues = 0
    
    for annee, langue in years_langs:
        sources = conn.execute("""
            SELECT numero FROM sources 
            WHERE annee = ? AND langue = ?
            ORDER BY numero
        """, (annee, langue)).fetchall()
        
        numeros = [row[0] for row in sources]
        
        if not numeros:
            continue
        
        # Convertit en entiers pour analyse
        nums_int = [int(n) for n in numeros]
        min_num = min(nums_int)
        max_num = max(nums_int)
        expected = max_num - min_num + 1
        actual = len(numeros)
        
        if expected != actual:
            missing = []
            for i in range(min_num, max_num + 1):
                if str(i).zfill(3) not in numeros:
                    missing.append(i)
            
            print(f"{annee} {langue}: {missing} ({len(missing)} trous)")
            total_issues += 1
    
    if total_issues == 0:
        print("[OK] Toutes les séquences sont continues")
    else:
        print(f"\n[PROBLEME] {total_issues} années/langues avec des trous")
    
    print(f"\nTotal années/langues vérifiées: {len(years_langs)}")