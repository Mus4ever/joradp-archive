"""
Vérification si les PDF arabes et français sont séparés ou mixtes
Inspection réelle du corpus, pas basée sur les noms de fichiers
"""

import sys
sys.path.append('tools')

import pymupdf
from pathlib import Path
from database import JoradpDatabase
import re

def check_pdf_language_mixing(annee: int, numero: str, langue: str):
    """
    Vérifie si un PDF contient à la fois de l'arabe et du français.
    """
    prefix = "AR" if langue == "AR" else "FR"
    pdf_path = Path("downloads") / langue / str(annee) / f"{prefix}{annee}{int(numero):03d}.pdf"
    
    if not pdf_path.exists():
        return {"error": "PDF not found"}
    
    try:
        doc = pymupdf.open(pdf_path)
        
        arabic_chars_total = 0
        latin_chars_total = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
            latin_chars = sum(1 for c in text if 'a' <= c <= 'z' or 'A' <= c <= 'Z')
            
            arabic_chars_total += arabic_chars
            latin_chars_total += latin_chars
        
        doc.close()
        
        return {
            "annee": annee,
            "numero": numero,
            "langue": langue,
            "total_pages": len(doc),
            "arabic_chars_total": arabic_chars_total,
            "latin_chars_total": latin_chars_total,
            "is_bilingual": arabic_chars_total > 100 and latin_chars_total > 100
        }
        
    except Exception as e:
        return {"error": str(e)}


def main():
    """Vérification des PDF bilingues dans le corpus."""
    
    print("VERIFICATION PDF BILINGUES - INSPECTION RÉELLE DU CORPUS")
    print("=" * 80)
    
    db = JoradpDatabase()
    
    with db:
        conn = db.connect()
        
        # Échantillon de PDF arabes
        print("ÉCHANTILLON PDF ARABES:")
        print("-" * 80)
        
        arabic_sample = conn.execute("""
            SELECT annee, numero
            FROM sources 
            WHERE langue = 'AR' 
            AND statut = 'telecharge'
            ORDER BY RANDOM()
            LIMIT 10
        """).fetchall()
        
        arabic_results = []
        for annee, numero in arabic_sample:
            result = check_pdf_language_mixing(annee, numero, "AR")
            if not result.get("error"):
                arabic_results.append(result)
                print(f"AR {annee}-{numero}: Arabic={result['arabic_chars_total']}, Latin={result['latin_chars_total']}, Bilingual={result['is_bilingual']}")
        
        print()
        print("ÉCHANTILLON PDF FRANÇAIS:")
        print("-" * 80)
        
        french_sample = conn.execute("""
            SELECT annee, numero
            FROM sources 
            WHERE langue = 'FR' 
            AND statut = 'telecharge'
            ORDER BY RANDOM()
            LIMIT 10
        """).fetchall()
        
        french_results = []
        for annee, numero in french_sample:
            result = check_pdf_language_mixing(annee, numero, "FR")
            if not result.get("error"):
                french_results.append(result)
                print(f"FR {annee}-{numero}: Arabic={result['arabic_chars_total']}, Latin={result['latin_chars_total']}, Bilingual={result['is_bilingual']}")
        
        print()
        print("ANALYSE DES RÉSULTATS:")
        print("-" * 80)
        
        bilingual_arabic = sum(1 for r in arabic_results if r['is_bilingual'])
        bilingual_french = sum(1 for r in french_results if r['is_bilingual'])
        
        print(f"PDF arabes testés: {len(arabic_results)}")
        print(f"PDF arabes bilingues: {bilingual_arabic}")
        print(f"PDF français testés: {len(french_results)}")
        print(f"PDF français bilingues: {bilingual_french}")
        
        if bilingual_arabic > 0:
            print("\nEXEMPLES DE PDF ARABES BILINGUES:")
            for r in arabic_results:
                if r['is_bilingual']:
                    print(f"  AR {r['annee']}-{r['numero']}: {r['arabic_chars_total']} arabic, {r['latin_chars_total']} latin")
        
        if bilingual_french > 0:
            print("\nEXEMPLES DE PDF FRANÇAIS BILINGUES:")
            for r in french_results:
                if r['is_bilingual']:
                    print(f"  FR {r['annee']}-{r['numero']}: {r['arabic_chars_total']} arabic, {r['latin_chars_total']} latin")
        
        print()
        print("CONCLUSION:")
        if bilingual_arabic == 0 and bilingual_french == 0:
            print("Aucun PDF bilingue détecté dans l'échantillon")
            print("Les PDF arabes et français sont séparés par fichier")
        else:
            print(f"{bilingual_arabic + bilingual_filingual} PDF bilingues détectés")
            print("Certains PDF contiennent à la fois arabe et français")

if __name__ == "__main__":
    main()