"""
Extension du schéma pour ajouter needs_ocr au niveau page
"""

import sys
sys.path.append('tools')

from database import JoradpDatabase

db = JoradpDatabase()

print("EXTENSION DU SCHÉMA - AJOUT NEEDS_OCR AU NIVEAU PAGE")
print("=" * 80)

with db:
    conn = db.connect()
    
    # Vérifie si la colonne existe déjà
    columns = conn.execute("PRAGMA table_info(extractions)").fetchall()
    has_needs_ocr = any(col[1] == 'needs_ocr' for col in columns)
    
    if has_needs_ocr:
        print("Champ needs_ocr existe déjà")
    else:
        print("Ajout du champ needs_ocr...")
        conn.execute("ALTER TABLE extractions ADD COLUMN needs_ocr BOOLEAN DEFAULT 0")
        conn.commit()
        print("Schéma étendu avec succès")
        
        # Vérifie
        columns = conn.execute("PRAGMA table_info(extractions)").fetchall()
        print("\nNouveau schéma:")
        for col in columns:
            print(f"  {col[1]}: {col[2]}")

print("=" * 80)
print("Extension terminée - needs_ocr maintenant disponible au niveau page")