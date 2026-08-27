"""
Test rapide de la découverte AR optimisée sur une seule année
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient
from database import JoradpDatabase
from discover import JoradpDiscoverer
import time

# Nettoie la base pour test
import os
if os.path.exists("test_ar.db"):
    os.remove("test_ar.db")

db = JoradpDatabase("test_ar.db")
with db:
    db.initialize_schema()

with JoradpClient() as client:
    discoverer = JoradpDiscoverer(db, client)
    
    print("TEST AR 1968 - VERSION OPTIMISÉE")
    print("=" * 80)
    
    start_time = time.time()
    count = discoverer.discover_annual_index("AR", 1968)
    elapsed = time.time() - start_time
    
    print(f"\nTemps écoulé: {elapsed:.2f} secondes")
    print(f"Numéros trouvés: {count}")
    
    if elapsed < 5:
        print("[OK] Performance acceptable")
    else:
        print("[SLOW] Encore trop lent")
    
    # Nettoyage
    os.remove("test_ar.db")