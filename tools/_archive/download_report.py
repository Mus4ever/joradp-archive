"""
Rapport détaillé du téléchargement Phase 3
"""

import sys
sys.path.append('tools')

from database import JoradpDatabase

db = JoradpDatabase()

print("RAPPORT DE TÉLÉCHARGEMENT PHASE 3")
print("=" * 80)

with db:
    conn = db.connect()
    
    # Statistiques globales
    stats = conn.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN statut = 'telecharge' THEN 1 ELSE 0 END) as telecharge,
            SUM(CASE WHEN statut = 'erreur' THEN 1 ELSE 0 END) as erreur,
            SUM(CASE WHEN statut = 'decouvert' THEN 1 ELSE 0 END) as decouvert
        FROM sources
    """).fetchone()
    
    total, telecharge, erreur, decouvert = stats
    
    print(f"Total sources: {total}")
    print(f"Téléchargées: {telecharge} ({telecharge*100//total}%)")
    print(f"Erreurs: {erreur} ({erreur*100//total}%)")
    print(f"Restantes: {decouvert} ({decouvert*100//total}%)")
    print()
    
    # Sources en erreur
    if erreur > 0:
        print("SOURCES EN ERREUR:")
        print("-" * 80)
        
        errors = conn.execute("""
            SELECT annee, numero, langue, url_complete, erreur
            FROM sources 
            WHERE statut = 'erreur'
            ORDER BY annee DESC, langue, numero
            LIMIT 20
        """).fetchall()
        
        for row in errors:
            annee, numero, langue, url, err = row
            print(f"{langue} {annee}-{numero}: {err}")
            print(f"  URL: {url}")
            print()
        
        if erreur > 20:
            print(f"... et {erreur - 20} autres erreurs")
    
    # Sources restantes
    if decouvert > 0:
        print(f"\nSOURCES RESTANTES ({decouvert}):")
        print("-" * 80)
        
        remaining = conn.execute("""
            SELECT annee, numero, langue, url_complete
            FROM sources 
            WHERE statut = 'decouvert'
            ORDER BY annee, langue, numero
            LIMIT 10
        """).fetchall()
        
        for row in remaining:
            annee, numero, langue, url = row
            print(f"{langue} {annee}-{numero}")
        
        if decouvert > 10:
            print(f"... et {decouvert - 10} autres")
    
    # Statistiques par année
    print("\nSTATISTIQUES PAR ANNÉE:")
    print("-" * 80)
    
    year_stats = conn.execute("""
        SELECT annee, langue,
               COUNT(*) as total,
               SUM(CASE WHEN statut = 'telecharge' THEN 1 ELSE 0 END) as telecharge,
               SUM(CASE WHEN statut = 'erreur' THEN 1 ELSE 0 END) as erreur
        FROM sources 
        GROUP BY annee, langue
        ORDER BY annee DESC, langue
    """).fetchall()
    
    for row in year_stats:
        annee, langue, total, telecharge, erreur = row
        if erreur > 0:
            print(f"{annee} {langue}: {telecharge}/{total} ({erreur} erreurs)")
        elif telecharge < total:
            print(f"{annee} {langue}: {telecharge}/{total} ({total - telecharge} restantes)")
    
    print("\n" + "=" * 80)
    print(f"TÉLÉCHARGEMENT: {'TERMINÉ' if decouvert == 0 else 'INCOMPLET'}")
    print(f"TAUX DE SUCCÈS: {telecharge*100//total}%")