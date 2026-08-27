"""
Affiche le texte extrait réel pour les 3 cas suspects
Pour comparaison mot à mot avec les captures visuelles
"""

import sys
sys.path.append('tools')

import pymupdf
from pathlib import Path

def show_extracted_text_comparison(annee: int, numero: int):
    """Affiche le texte extrait pour comparaison avec capture."""
    
    pdf_path = Path("downloads") / "AR" / str(annee) / f"AR{annee}{numero:03d}.pdf"
    
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return
    
    try:
        doc = pymupdf.open(pdf_path)
        
        print(f"AR {annee}-{numero} - Page 1")
        print("=" * 80)
        print("TEXTE EXTRAIT BRUT (stocké en base):")
        print("-" * 80)
        
        page = doc[0]
        text = page.get_text()
        
        # Affiche le texte complet (UTF-8 explicit)
        import sys
        sys.stdout.reconfigure(encoding='utf-8')
        print(text)
        
        print()
        print("CAPTURE VISUELLE CORRESPONDANTE:")
        print(f"rtl_check_AR{annee}{numero}_page1.png")
        print()
        print("ANALYSE ORDRE RTL:")
        print("-" * 80)
        
        # Analyse détaillée
        import re
        arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        numbers = re.findall(r'\d+', text)
        french_words = re.findall(r'[A-Za-z]{3,}', text)
        
        print(f"Caractères arabes: {arabic_chars}")
        print(f"Nombres: {len(numbers)}")
        print(f"Mots français: {len(french_words)}")
        
        # Cherche des patterns typiques de désordre
        lines = text.split('\n')
        print(f"\nNombre de lignes: {len(lines)}")
        
        # Affiche les 5 premières lignes pour voir l'ordre
        print("\n5 PREMIÈRES LIGNES:")
        for i, line in enumerate(lines[:5]):
            print(f"Ligne {i+1}: {line[:100]}")
        
        doc.close()
        
    except Exception as e:
        print(f"Error: {e}")

print("TEXTE EXTRAIT RÉEL - CAS SUSPECTS 1-3")
print("=" * 80)

print("\nCAS 1: AR 2006-045")
show_extracted_text_comparison(2006, 45)

print("\n" + "=" * 80)
print("\nCAS 2: AR 2018-068")
show_extracted_text_comparison(2018, 68)

print("\n" + "=" * 80)
print("\nCAS 3: AR 2022-036")
show_extracted_text_comparison(2022, 36)