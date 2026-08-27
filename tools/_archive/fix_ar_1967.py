"""
Correction de la découverte AR 1967 (manque 33 numéros : 075-107)
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient
from database import JoradpDatabase
from discover import JoradpDiscoverer

# Nettoie AR 1967 existant
db = JoradpDatabase()
with db:
    conn = db.connect()
    deleted = conn.execute("""
        DELETE FROM sources 
        WHERE annee = 1967 AND langue = 'AR'
    """).rowcount
    conn.commit()
    print(f"Supprimé {deleted} entrées AR 1967 existantes")

# Redécouvre AR 1967
with JoradpClient() as client:
    discoverer = JoradpDiscoverer(db, client)
    
    print("\nREDÉCOUVERTE AR 1967")
    print("=" * 80)
    count = discoverer.discover_annual_index("AR", 1967)
    print(f"AR 1967: {count} numéros découverts")

# Vérification
with db:
    conn = db.connect()
    sources = conn.execute("""
        SELECT numero FROM sources 
        WHERE annee = 1967 AND langue = 'AR'
        ORDER BY numero
    """).fetchall()
    
    numeros = [row[0] for row in sources]
    print(f"\nVérification: {len(numeros)} numéros enregistrés")
    print(f"Premiers: {numeros[:5]}")
    print(f"Derniers: {numeros[-5:]}")