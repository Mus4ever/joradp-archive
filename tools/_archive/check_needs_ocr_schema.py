"""
Vérification du schéma needs_ocr au niveau page
Le plan exigeait explicitement needs_ocr au niveau page, pas document
"""

import sys
sys.path.append('tools')

from database import JoradpDatabase

print("VERIFICATION DU SCHÉMA NEEDS_OCR AU NIVEAU PAGE")
print("=" * 80)

db = JoradpDatabase()

with db:
    conn = db.connect()
    
    # Vérifie le schéma actuel de la table extractions
    print("SCHÉMA ACTUEL DE LA TABLE EXTRACTIONS:")
    print("-" * 80)
    
    columns = conn.execute("PRAGMA table_info(extractions)").fetchall()
    for col in columns:
        print(f"  {col[1]}: {col[2]}")
    
    print()
    
    # Vérifie s'il y a un champ needs_ocr
    has_needs_ocr = any(col[1] == 'needs_ocr' for col in columns)
    
    if has_needs_ocr:
        print("Champ needs_ocr: EXISTE")
    else:
        print("Champ needs_ocr: N'EXISTE PAS")
        print()
        print("EXTENSION DE SCHÉMA NÉCESSAIRE:")
        print("-" * 80)
        print("ALTER TABLE extractions ADD COLUMN needs_ocr BOOLEAN DEFAULT 0;")
        print()
        print("Justification:")
        print("- needs_ocr doit être au niveau page (pas document)")
        print("- Un PDF peut être mixte (certaines pages natives, d'autres scannées)")
        print("- Le schéma actuel ne permet pas cette distinction fine")
    
    print()
    print("EXEMPLE DE PDF MIXTE (si existe):")
    print("-" * 80)
    
    # Cherche un PDF potentiellement mixte
    # Utilise les données de l'échantillon déjà traité
    mixed_check = conn.execute("""
        SELECT e.source_id, e.page_numero, LENGTH(e.texte_natif) as chars
        FROM extractions e
        JOIN sources s ON e.source_id = s.id
        WHERE LENGTH(e.texte_natif) < 1161
        LIMIT 5
    """).fetchall()
    
    if mixed_check:
        print("Pages sous le seuil 1161 (potentiellement scannées):")
        for row in mixed_check:
            source_id, page_num, chars = row
            print(f"  Source {source_id}, Page {page_num}: {chars} chars")
    else:
        print("Aucune page sous le seuil détectée dans l'échantillon")