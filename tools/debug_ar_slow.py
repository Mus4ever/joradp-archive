"""
Diagnostic du problème de lenteur AR
Teste une année AR spécifique pour voir où ça bloque
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient
from database import JoradpDatabase
from discover import JoradpDiscoverer
import time

db = JoradpDatabase()
with db:
    db.initialize_schema()

with JoradpClient() as client:
    discoverer = JoradpDiscoverer(db, client)
    
    print("TEST DIAGNOSTIC AR 1968")
    print("=" * 80)
    
    start_time = time.time()
    count = discoverer.discover_annual_index("AR", 1968)
    elapsed = time.time() - start_time
    
    print(f"\nTemps écoulé: {elapsed:.2f} secondes")
    print(f"Numéros trouvés: {count}")
    
    if elapsed > 10:
        print("[PROBLÈME] Trop lent pour une seule année!")
    else:
        print("[OK] Temps normal")