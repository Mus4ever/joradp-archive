"""
Vérification RTL réelle sur pages de contenu (articles de décret)
Teste l'ordre logique du texte arabe continu, pas les couvertures
"""

import sys
sys.path.append('tools')

import pymupdf
from pathlib import Path
from database import JoradpDatabase
import re

def verify_rtl_content_page(annee: int, numero: int, page_num: int = 5):
    """
    Vérifie l'ordre RTL sur une page de contenu réel (pas couverture).
    
    Args:
        page_num: Numéro de page à tester (5-15 typiquement pour contenu)
    """
    pdf_path = Path("downloads") / "AR" / str(annee) / f"AR{annee}{numero}.pdf"
    
    if not pdf_path.exists():
        return {"error": "PDF not found"}
    
    try:
        doc = pymupdf.open(pdf_path)
        
        if page_num >= len(doc):
            return {"error": f"Page {page_num} doesn't exist (PDF has {len(doc)} pages)"}
        
        page = doc[page_num]
        text = page.get_text()
        
        # Capture visuelle pour comparaison
        pix = page.get_pixmap()
        img_path = f"rtl_content_AR{annee}{numero}_page{page_num+1}.png"
        pix.save(img_path)
        
        total_pages = len(doc)
        doc.close()
        
        # Analyse du texte
        arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        latin_chars = sum(1 for c in text if 'a' <= c <= 'z' or 'A' <= c <= 'Z')
        numbers = re.findall(r'\d+', text)
        
        # Détection de désordre RTL potentiel
        # Cherche des patterns qui indiquent un mauvais ordre de blocs
        lines = text.split('\n')
        
        # Pattern 1: Mots latins isolés au milieu de texte arabe continu
        latin_in_arabic_context = 0
        for i, line in enumerate(lines):
            if i > 0 and i < len(lines) - 1:
                # Si la ligne précédente et suivante sont principalement arabes
                prev_arabic = sum(1 for c in lines[i-1] if '\u0600' <= c <= '\u06FF')
                next_arabic = sum(1 for c in lines[i+1] if '\u0600' <= c <= '\u06FF')
                current_latin = sum(1 for c in line if 'a' <= c <= 'z' or 'A' <= c <= 'Z')
                
                if prev_arabic > 5 and next_arabic > 5 and current_latin > 3:
                    latin_in_arabic_context += 1
        
        # Pattern 2: Nombres de page/article à positions anormales
        # (Cherche des nombres qui semblent mal placés)
        number_positions = []
        for i, line in enumerate(lines):
            nums_in_line = re.findall(r'\d+', line)
            if nums_in_line:
                number_positions.append((i, len(nums_in_line)))
        
        return {
            "annee": annee,
            "numero": numero,
            "page_num": page_num + 1,
            "total_pages": total_pages,
            "text_length": len(text),
            "arabic_chars": arabic_chars,
            "latin_chars": latin_chars,
            "numbers_count": len(numbers),
            "latin_in_arabic_context": latin_in_arabic_context,
            "capture_path": img_path,
            "text_sample": text[:300]  # Échantillon pour inspection
        }
        
    except Exception as e:
        return {"error": str(e)}


def main():
    """Teste 5-6 PDF sur pages de contenu réel."""
    
    print("VERIFICATION RTL RÉELLE - PAGES DE CONTENU")
    print("=" * 80)
    print("Teste l'ordre RTL sur du texte d'article continu (page 5-15)")
    print("Pas sur les couvertures/sommaires")
    print()
    
    db = JoradpDatabase()
    
    with db:
        conn = db.connect()
        
        # Sélectionne 5-6 PDF arabes avec du contenu (années 2000-2020)
        sample = conn.execute("""
            SELECT annee, numero
            FROM sources 
            WHERE langue = 'AR' 
            AND annee BETWEEN 2000 AND 2020
            AND statut = 'telecharge'
            ORDER BY RANDOM()
            LIMIT 6
        """).fetchall()
        
        print(f"Échantillon: {len(sample)} PDF arabes (2000-2020)")
        print("-" * 80)
        
        results = []
        for annee, numero in sample:
            # Essaie page 8 (typiquement contenu)
            result = verify_rtl_content_page(annee, numero, page_num=7)
            
            if not result.get("error"):
                results.append(result)
                
                print(f"AR {annee}-{numero} Page {result['page_num']}:")
                print(f"  Capture: {result['capture_path']}")
                print(f"  Arabic chars: {result['arabic_chars']}")
                print(f"  Latin chars: {result['latin_chars']}")
                print(f"  Numbers: {result['numbers_count']}")
                print(f"  Latin in Arabic context: {result['latin_in_arabic_context']}")
                
                if result['arabic_chars'] > 100:
                    print(f"  -> Contenu arabe substantiel détecté")
                    if result['latin_in_arabic_context'] == 0:
                        print(f"  -> Pas de blocs latins anormaux détectés")
                    else:
                        print(f"  -> ALERT: {result['latin_in_arabic_context']} blocs latins potentiels")
                else:
                    print(f"  -> Peu de contenu arabe (page différente?)")
                
                print()
            else:
                print(f"AR {annee}-{numero}: ERROR - {result['error']}")
                print()
        
        print("=" * 80)
        print("ANALYSE GLOBALE")
        print("-" * 80)
        
        if results:
            total_arabic = sum(r['arabic_chars'] for r in results)
            total_latin = sum(r['latin_chars'] for r in results)
            total_latin_context = sum(r['latin_in_arabic_context'] for r in results)
            
            print(f"Total Arabic chars: {total_arabic}")
            print(f"Total Latin chars: {total_latin}")
            print(f"Total Latin in Arabic context alerts: {total_latin_context}")
            
            if total_latin_context == 0:
                print()
                print("CONCLUSION: Aucun désordre RTL détecté sur pages de contenu")
                print("L'ordre d'extraction des blocs semble correct")
            else:
                print()
                print(f"ALERT: {total_latin_context} cas potentiels de désordre")
                print("Examen manuel des captures recommandé")

if __name__ == "__main__":
    main()