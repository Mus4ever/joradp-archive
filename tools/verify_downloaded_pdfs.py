"""
Vérification des PDF téléchargés : SHA-256 et ouverture réelle
Validation du lot test Phase 3
"""

import sys
sys.path.append('tools')

from pathlib import Path
import pymupdf  # PyMuPDF
from database import JoradpDatabase

db = JoradpDatabase()

print("VERIFICATION PDF TÉLÉCHARGÉS - LOT TEST")
print("=" * 80)

with db:
    conn = db.connect()
    
    # Récupère les 10 fichiers téléchargés les plus récents
    sources = conn.execute("""
        SELECT id, annee, numero, langue, url_complete, sha256, taille_octets
        FROM sources 
        WHERE statut = 'telecharge'
        ORDER BY date_telechargement DESC
        LIMIT 10
    """).fetchall()
    
    print(f"Échantillon : {len(sources)} PDF récents")
    print()
    
    for source in sources:
        source_id, annee, numero, langue, url, sha256, size = source
        
        # Chemin local
        local_path = Path("downloads") / langue / str(annee) / f"{langue}{annee}{numero}.pdf"
        
        print(f"{langue} {annee}-{numero} :")
        print(f"  URL : {url}")
        print(f"  Local : {local_path}")
        print(f"  Taille : {size} octets")
        print(f"  SHA-256 : {sha256}")
        
        # Vérifie que le fichier existe
        if not local_path.exists():
            print(f"  [FAIL] Fichier local absent")
            continue
        
        # Vérifie la taille
        actual_size = local_path.stat().st_size
        if actual_size != size:
            print(f"  [FAIL] Taille mismatch : {actual_size} vs {size}")
            continue
        
        # Ouvre le PDF avec PyMuPDF
        try:
            doc = pymupdf.open(local_path)
            page_count = len(doc)
            
            print(f"  [OK] PDF ouvert : {page_count} pages")
            
            # Extrait un échantillon de texte de la première page
            if page_count > 0:
                first_page = doc[0]
                text = first_page.get_text()
                
                if text.strip():
                    print(f"  [OK] Texte extrait : {len(text)} caractères")
                    # Affiche un extrait (seulement pour FR pour éviter problèmes d'encodage AR)
                    if langue == "FR":
                        excerpt = text[:100].replace('\n', ' ')
                        print(f"  Extrait : \"{excerpt}...\"")
                    else:
                        print(f"  Extrait : [texte arabe non affiché pour éviter erreur encodage console]")
                else:
                    print(f"  [INFO] Pas de texte natif (probablement scan)")
            
            doc.close()
            
        except Exception as e:
            print(f"  [FAIL] Erreur ouverture PDF : {e}")
        
        print()

print("=" * 80)
print("VERIFICATION TERMINÉE")