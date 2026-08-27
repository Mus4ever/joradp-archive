"""
Examen manuel du texte arabe extrait pour vérifier l'ordre RTL réel
"""

import sys
sys.path.append('tools')

import pymupdf
from pathlib import Path
from database import JoradpDatabase

def examine_arabic_pdf(annee: int, numero: int):
    """Examine le texte d'un PDF arabe spécifique."""
    
    pdf_path = Path("downloads") / "AR" / str(annee) / f"AR{annee}{numero:03d}.pdf"
    
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return
    
    try:
        doc = pymupdf.open(pdf_path)
        
        print(f"AR {annee}-{numero} - {len(doc)} pages")
        print("=" * 80)
        
        # Examine les 2 premières pages
        for page_num in range(min(2, len(doc))):
            page = doc[page_num]
            text = page.get_text()
            
            print(f"\nPAGE {page_num + 1}:")
            print("-" * 80)
            print(f"Length: {len(text)} characters")
            
            # Preview sécurisé (évite les erreurs d'encodage)
            try:
                preview = text[:200]
                print(f"Preview (200 chars): {preview}")
            except:
                print("Preview: [Arabic text - encoding issue]")
            
            # Compte les caractères arabes
            arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
            print(f"Arabic chars: {arabic_chars}")
            
            # Compte les nombres
            import re
            numbers = re.findall(r'\d+', text)
            print(f"Numbers: {len(numbers)}")
            
            # Compte les mots français
            french_words = re.findall(r'[A-Za-z]{3,}', text)
            print(f"French words: {len(french_words)}")
            
            if french_words:
                print(f"French words sample: {french_words[:5]}")
        
        doc.close()
        
    except Exception as e:
        print(f"Error: {e}")

# Examine quelques échantillons représentatifs
print("EXAMEN MANUEL DU TEXTE ARABE")
print("=" * 80)

# Legacy (correct)
print("\nLEGACY 1964-1993 (supposé correct):")
examine_arabic_pdf(1991, 37)

# Ère complet (mixte)
print("\nÈRE COMPLET 1994-2009 (problèmes détectés):")
examine_arabic_pdf(1998, 21)

# Récent (problèmes détectés)
print("\nRÉCENT 2010-2026 (problèmes détectés):")
examine_arabic_pdf(2012, 69)