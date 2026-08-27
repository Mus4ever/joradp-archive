"""
Vérifie le champ url_index_historique pour les années AR legacy
"""

import sys
sys.path.append('tools')

from database import JoradpDatabase

db = JoradpDatabase()
with db:
    conn = db.connect()
    
    print("VERIFICATION CHAMP url_index_historique")
    print("=" * 80)
    
    # AR 1964-1993 (période legacy)
    legacy_sources = conn.execute("""
        SELECT annee, COUNT(*) as total, 
               SUM(CASE WHEN url_index_historique IS NULL THEN 1 ELSE 0 END) as null_count
        FROM sources 
        WHERE langue = 'AR' AND annee BETWEEN 1964 AND 1993
        GROUP BY annee
        ORDER BY annee
    """).fetchall()
    
    print("AR 1964-1993 (période legacy avec pages historiques):")
    for row in legacy_sources:
        annee, total, null_count = row
        status = "[NULL]" if null_count == total else "[PARTIEL]" if null_count > 0 else "[REMPLI]"
        print(f"  {annee}: {total} sources, {null_count} nulls {status}")
    
    # AR 1994+ (période moderne)
    modern_sources = conn.execute("""
        SELECT annee, COUNT(*) as total, 
               SUM(CASE WHEN url_index_historique IS NULL THEN 1 ELSE 0 END) as null_count
        FROM sources 
        WHERE langue = 'AR' AND annee >= 1994
        GROUP BY annee
        ORDER BY annee
        LIMIT 5
    """).fetchall()
    
    print("\nAR 1994+ (période moderne sans pages historiques attendues):")
    for row in modern_sources:
        annee, total, null_count = row
        status = "[OK]" if null_count == total else "[ANOMALIE]"
        print(f"  {annee}: {total} sources, {null_count} nulls {status}")
    
    # FR (jamais de pages historiques)
    fr_sources = conn.execute("""
        SELECT annee, COUNT(*) as total, 
               SUM(CASE WHEN url_index_historique IS NULL THEN 1 ELSE 0 END) as null_count
        FROM sources 
        WHERE langue = 'FR'
        GROUP BY annee
        ORDER BY annee
        LIMIT 3
    """).fetchall()
    
    print("\nFR (jamais de pages historiques):")
    for row in fr_sources:
        annee, total, null_count = row
        status = "[OK]" if null_count == total else "[ANOMALIE]"
        print(f"  {annee}: {total} sources, {null_count} nulls {status}")