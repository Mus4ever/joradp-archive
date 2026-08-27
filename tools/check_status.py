"""
Vérification rapide du statut réel des sources
"""

import sys
sys.path.append('tools')

from database import JoradpDatabase

db = JoradpDatabase()

with db:
    conn = db.connect()
    
    result = conn.execute("""
        SELECT statut, COUNT(*) as count
        FROM sources 
        GROUP BY statut
    """).fetchall()
    
    print("STATUT RÉEL DES SOURCES:")
    print("=" * 80)
    
    for row in result:
        statut, count = row
        print(f"{statut}: {count}")
    
    print("=" * 80)
    
    total = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    print(f"Total: {total}")