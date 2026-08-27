"""
Vérifie si les PDF finaux existent pour les sources en erreur
"""

import sys
sys.path.append('tools')

from pathlib import Path
from database import JoradpDatabase

db = JoradpDatabase()

print("VERIFICATION PDF FINAUX POUR SOURCES EN ERREUR")
print("=" * 80)

with db:
    conn = db.connect()
    
    # Récupère les sources en erreur
    failed_sources = conn.execute("""
        SELECT id, annee, numero, langue, url_complete 
        FROM sources 
        WHERE statut = 'erreur'
        ORDER BY annee, langue, numero
    """).fetchall()
    
    print(f"Sources en erreur: {len(failed_sources)}")
    print()
    
    pdf_exists_count = 0
    part_exists_count = 0
    neither_exists_count = 0
    
    for source in failed_sources:
        source_id, annee, numero, langue, url = source
        
        # Chemins
        pdf_path = Path("downloads") / langue / str(annee) / f"{langue}{annee}{numero}.pdf"
        part_path = pdf_path.with_suffix(".pdf.part")
        
        pdf_exists = pdf_path.exists()
        part_exists = part_path.exists()
        
        if pdf_exists:
            pdf_exists_count += 1
            print(f"[PDF EXISTS] {langue} {annee}-{numero}")
        elif part_exists:
            part_exists_count += 1
            print(f"[PART EXISTS] {langue} {annee}-{numero}")
        else:
            neither_exists_count += 1
            print(f"[MISSING] {langue} {annee}-{numero}")
    
    print()
    print("=" * 80)
    print(f"PDF finaux existent: {pdf_exists_count}")
    print(f".part files existent: {part_exists_count}")
    print(f"Aucun fichier: {neither_exists_count}")
    
    # Si les PDF finaux existent, les valider et marquer comme téléchargés
    if pdf_exists_count > 0:
        print(f"\n{pdf_exists_count} PDF finaux existent - validation en cours...")
        
        import pymupdf
        import hashlib
        
        validated_count = 0
        for source in failed_sources:
            source_id, annee, numero, langue, url = source
            
            pdf_path = Path("downloads") / langue / str(annee) / f"{langue}{annee}{numero}.pdf"
            
            if pdf_path.exists():
                # Validation PyMuPDF
                try:
                    doc = pymupdf.open(pdf_path)
                    page_count = len(doc)
                    doc.close()
                    
                    if page_count > 0:
                        # SHA-256
                        sha256_hash = hashlib.sha256()
                        with open(pdf_path, "rb") as f:
                            for chunk in iter(lambda: f.read(4096), b""):
                                sha256_hash.update(chunk)
                        sha256 = sha256_hash.hexdigest()
                        
                        size = pdf_path.stat().st_size
                        
                        # Met à jour la base
                        with db:
                            conn2 = db.connect()
                            conn2.execute("""
                                UPDATE sources 
                                SET statut = 'telecharge', sha256 = ?, taille_octets = ?, erreur = NULL
                                WHERE id = ?
                            """, (sha256, size, source_id))
                            conn2.commit()
                        
                        validated_count += 1
                        print(f"[VALIDATED] {langue} {annee}-{numero}")
                except Exception as e:
                    print(f"[INVALID] {langue} {annee}-{numero}: {e}")
        
        print(f"\nValidation terminée: {validated_count}/{pdf_exists_count} PDF validés")