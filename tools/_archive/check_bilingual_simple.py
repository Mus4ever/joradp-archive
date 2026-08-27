"""
Vérification simple des PDF bilingues - échantillon direct
"""

import sys
sys.path.append('tools')

import pymupdf
from pathlib import Path

def check_pdf_mixing(pdf_path: Path):
    """Vérifie si un PDF contient à la fois de l'arabe et du français."""
    
    if not pdf_path.exists():
        return {"error": "PDF not found"}
    
    try:
        doc = pymupdf.open(pdf_path)
        
        arabic_chars_total = 0
        latin_chars_total = 0
        total_pages = len(doc)
        
        for page_num in range(total_pages):
            page = doc[page_num]
            text = page.get_text()
            
            arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
            latin_chars = sum(1 for c in text if 'a' <= c <= 'z' or 'A' <= c <= 'Z')
            
            arabic_chars_total += arabic_chars
            latin_chars_total += latin_chars
        
        doc.close()
        
        return {
            "pdf_path": str(pdf_path),
            "total_pages": total_pages,
            "arabic_chars_total": arabic_chars_total,
            "latin_chars_total": latin_chars_total,
            "is_bilingual": arabic_chars_total > 100 and latin_chars_total > 100
        }
        
    except Exception as e:
        return {"error": str(e)}


print("VERIFICATION PDF BILINGUES - ÉCHANTILLON DIRECT")
print("=" * 80)

# Échantillon PDF arabes
print("ÉCHANTILLON PDF ARABES:")
print("-" * 80)

arabic_pdfs = [
    "downloads/AR/2007/AR2007003.pdf",
    "downloads/AR/2007/AR2007016.pdf",
    "downloads/AR/2007/AR2007034.pdf",
    "downloads/AR/2018/AR2018072.pdf",
    "downloads/AR/2012/AR2012001.pdf",
]

arabic_results = []
for pdf_path in arabic_pdfs:
    result = check_pdf_mixing(Path(pdf_path))
    if not result.get("error"):
        arabic_results.append(result)
        print(f"{Path(pdf_path).name}: Arabic={result['arabic_chars_total']}, Latin={result['latin_chars_total']}, Bilingual={result['is_bilingual']}")
    else:
        print(f"{Path(pdf_path).name}: ERROR - {result['error']}")

print()
print("ÉCHANTILLON PDF FRANÇAIS:")
print("-" * 80)

french_pdfs = [
    "downloads/FR/2007/FR2007001.pdf",
    "downloads/FR/2007/FR2007002.pdf",
    "downloads/FR/2007/FR2007003.pdf",
    "downloads/FR/2018/FR2018001.pdf",
    "downloads/FR/2012/FR2012001.pdf",
]

french_results = []
for pdf_path in french_pdfs:
    result = check_pdf_mixing(Path(pdf_path))
    if not result.get("error"):
        french_results.append(result)
        print(f"{Path(pdf_path).name}: Arabic={result['arabic_chars_total']}, Latin={result['latin_chars_total']}, Bilingual={result['is_bilingual']}")
    else:
        print(f"{Path(pdf_path).name}: ERROR - {result['error']}")

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
            print(f"  {Path(r['pdf_path']).name}: {r['arabic_chars_total']} arabic, {r['latin_chars_total']} latin")

if bilingual_french > 0:
    print("\nEXEMPLES DE PDF FRANÇAIS BILINGUES:")
    for r in french_results:
        if r['is_bilingual']:
            print(f"  {Path(r['pdf_path']).name}: {r['arabic_chars_total']} arabic, {r['latin_chars_total']} latin")

print()
print("CONCLUSION:")
if bilingual_arabic == 0 and bilingual_french == 0:
    print("Aucun PDF bilingue détecté dans l'échantillon")
    print("Les PDF arabes et français sont séparés par fichier")
else:
    print(f"{bilingual_arabic + bilingual_french} PDF bilingues détectés")
    print("Certains PDF contiennent à la fois arabe et français")