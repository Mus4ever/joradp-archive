"""
Récupère les vrais numéros de PDF arabes pour examen
"""

import sys
sys.path.append('tools')

from database import JoradpDatabase

db = JoradpDatabase()

with db:
    conn = db.connect()
    
    # Legacy
    print("LEGACY 1964-1993:")
    legacy = conn.execute("""
        SELECT annee, numero 
        FROM sources 
        WHERE langue = 'AR' 
        AND annee BETWEEN 1964 AND 1993
        AND statut = 'telecharge'
        ORDER BY RANDOM()
        LIMIT 1
    """).fetchone()
    print(f"Sample: AR {legacy[0]}-{legacy[1]}")
    
    # Ère complet
    print("\nÈRE COMPLET 1994-2009:")
    modern = conn.execute("""
        SELECT annee, numero 
        FROM sources 
        WHERE langue = 'AR' 
        AND annee BETWEEN 1994 AND 2009
        AND statut = 'telecharge'
        ORDER BY RANDOM()
        LIMIT 1
    """).fetchone()
    print(f"Sample: AR {modern[0]}-{modern[1]}")
    
    # Récent
    print("\nRÉCENT 2010-2026:")
    recent = conn.execute("""
        SELECT annee, numero 
        FROM sources 
        WHERE langue = 'AR' 
        AND annee BETWEEN 2010 AND 2026
        AND statut = 'telecharge'
        ORDER BY RANDOM()
        LIMIT 1
    """).fetchone()
    print(f"Sample: AR {recent[0]}-{recent[1]}")