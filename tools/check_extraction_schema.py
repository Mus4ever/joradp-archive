"""
Examine la structure de la table extractions existante
"""

import sys
sys.path.append('tools')

from database import JoradpDatabase

db = JoradpDatabase()

print("STRUCTURE DE LA TABLE EXTRACTIONS")
print("=" * 80)

with db:
    conn = db.connect()
    
    # Récupère le schéma de la table
    schema = conn.execute("""
        SELECT sql 
        FROM sqlite_master 
        WHERE type='table' AND name='extractions'
    """).fetchone()
    
    if schema:
        print("Schema SQL:")
        print(schema[0])
    else:
        print("La table 'extractions' n'existe pas encore")
    
    print()
    
    # Vérifie si la table existe
    table_exists = conn.execute("""
        SELECT COUNT(*) 
        FROM sqlite_master 
        WHERE type='table' AND name='extractions'
    """).fetchone()[0]
    
    if table_exists:
        print("Table 'extractions' existe - structure:")
        columns = conn.execute("PRAGMA table_info(extractions)").fetchall()
        for col in columns:
            print(f"  {col[1]}: {col[2]}")
    else:
        print("Table 'extractions' doit être créée")