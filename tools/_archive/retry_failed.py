"""
Script pour retélécharger uniquement les sources en erreur
"""

import sys
sys.path.append('tools')

from database import JoradpDatabase
from http_client import JoradpClient
from download_optimized import OptimizedDownloader

db = JoradpDatabase()

print("RETOUÉCHARGEMENT DES SOURCES EN ERREUR")
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

if failed_sources:
    with JoradpClient() as client:
        downloader = OptimizedDownloader(db, client, max_workers=1)
        
        success_count = 0
        for source in failed_sources:
            source_id, annee, numero, langue, url = source
            
            # Nettoie le statut erreur pour permettre retéléchargement
            with db:
                conn2 = db.connect()
                conn2.execute("""
                    UPDATE sources 
                    SET statut = 'decouvert', erreur = NULL
                    WHERE id = ?
                """, (source_id,))
                conn2.commit()
            
            # Retélécharge
            result = downloader.download_source(source_id, url, annee, numero, langue)
            
            if result.final_status == "success":
                success_count += 1
                print(f"[OK] {langue} {annee}-{numero}")
            else:
                print(f"[FAIL] {langue} {annee}-{numero}: {result.error}")
        
        print("=" * 80)
        print(f"RETOUÉCHARGEMENT TERMINÉ: {success_count}/{len(failed_sources)} succès")
else:
    print("Aucune source en erreur à retélécharger")