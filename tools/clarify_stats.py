"""
Clarification des statistiques - page vs document
Vérifie si les chiffres sont des moyennes par page ou par document
"""

import sys
sys.path.append('tools')

import pymupdf
from pathlib import Path
from database import JoradpDatabase
import statistics

def analyze_pdf_detail(annee: int, numero: int, langue: str):
    """Analyse détaillée d'un PDF pour clarifier les stats."""
    
    pdf_path = Path("downloads") / langue / str(annee) / f"{langue}{annee}{numero:03d}.pdf"
    
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return
    
    try:
        doc = pymupdf.open(pdf_path)
        
        print(f"{langue} {annee}-{numero} - {len(doc)} pages")
        print("=" * 80)
        
        chars_per_page = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            chars_per_page.append(len(text.strip()))
        
        doc.close()
        
        # Stats par page
        avg_page = statistics.mean(chars_per_page) if chars_per_page else 0
        median_page = statistics.median(chars_per_page) if chars_per_page else 0
        min_page = min(chars_per_page) if chars_per_page else 0
        max_page = max(chars_per_page) if chars_per_page else 0
        
        print("STATISTIQUES PAR PAGE:")
        print(f"Moyenne: {avg_page:.0f} chars/page")
        print(f"Médiane: {median_page:.0f} chars/page")
        print(f"Minimum: {min_page:.0f} chars/page")
        print(f"Maximum: {max_page:.0f} chars/page")
        
        print()
        print("DISTRIBUTION DES PAGES:")
        for i, chars in enumerate(chars_per_page[:10]):  # Premières 10 pages
            status = "NATIVE" if chars >= 1161 else "SCAN"
            print(f"Page {i+1}: {chars} chars - {status}")
        
        # Compte pages natives vs scannées
        native_pages = sum(1 for c in chars_per_page if c >= 1161)
        scanned_pages = sum(1 for c in chars_per_page if c < 1161)
        
        print()
        print("CLASSIFICATION AU SEUIL 1161:")
        print(f"Pages natives: {native_pages}/{len(chars_per_page)} ({native_pages*100//len(chars_per_page)}%)")
        print(f"Pages scannées: {scanned_pages}/{len(chars_per_page)} ({scanned_pages*100//len(chars_per_page)}%)")
        
        # Est-ce mixte ?
        if native_pages > 0 and scanned_pages > 0:
            print("PDF MIXTE: contient à la fois pages natives et scannées")
        elif native_pages == len(chars_per_page):
            print("PDF 100% NATIF")
        elif scanned_pages == len(chars_per_page):
            print("PDF 100% SCANNÉ")
        
    except Exception as e:
        print(f"Error: {e}")

print("CLARIFICATION DES STATISTIQUES - PAGE VS DOCUMENT")
print("=" * 80)

# Teste quelques PDF de la période 2000 "mixte"
print("\nTEST PDF 2000 (supposé mixte):")
analyze_pdf_detail(2002, 33, "AR")

print("\nTEST PDF 2003 (supposé natif):")
analyze_pdf_detail(2003, 14, "FR")

print("\nTEST PDF 2009 (supposé natif):")
analyze_pdf_detail(2009, 7, "FR")