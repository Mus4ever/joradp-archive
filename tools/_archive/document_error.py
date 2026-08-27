"""
Documentation précise de l'erreur enregistrée
"""

import sys
sys.path.append('tools')

from database import JoradpDatabase

db = JoradpDatabase()

print("DOCUMENTATION DE L'ERREUR ENREGISTRÉE")
print("=" * 80)

with db:
    conn = db.connect()
    
    # Récupère toutes les sources avec erreur
    errors = conn.execute("""
        SELECT id, annee, numero, langue, url_complete, erreur, date_telechargement
        FROM sources 
        WHERE erreur IS NOT NULL
        ORDER BY date_telechargement
    """).fetchall()
    
    print(f"Nombre d'erreurs enregistrées: {len(errors)}")
    print()
    
    if errors:
        for row in errors:
            source_id, annee, numero, langue, url, erreur, date = row
            print(f"Source ID: {source_id}")
            print(f"Fichier: {langue} {annee}-{numero}")
            print(f"URL: {url}")
            print(f"Erreur: {erreur}")
            print(f"Date: {date}")
            print("-" * 80)
    else:
        print("Aucune erreur enregistrée dans la base actuelle")
    
    # Vérifie s'il y a des champs erreur NULL mais statut 'erreur'
    legacy_errors = conn.execute("""
        SELECT COUNT(*) 
        FROM sources 
        WHERE statut = 'erreur'
    """).fetchone()[0]
    
    print(f"\nSources avec statut 'erreur': {legacy_errors}")
    
    # Vérifie l'historique du téléchargement via les dates
    print("\nANALYSE TEMPORELLE DU TÉLÉCHARGEMENT:")
    print("-" * 80)
    
    temporal = conn.execute("""
        SELECT 
            DATE(date_telechargement) as date,
            COUNT(*) as count
        FROM sources 
        WHERE date_telechargement IS NOT NULL
        GROUP BY DATE(date_telechargement)
        ORDER BY date
    """).fetchall()
    
    for row in temporal:
        date, count = row
        print(f"{date}: {count} téléchargements")

print("=" * 80)