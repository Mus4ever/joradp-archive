"""
Examen manuel des cas RTL avec alertes
Affiche le texte extrait pour comparaison avec captures
"""

import sys
sys.path.append('tools')

import pymupdf
from pathlib import Path

def examine_rtl_alert(annee: int, numero: int, page_num: int = 7):
    """Examen détaillé d'un cas RTL avec alerte."""
    
    pdf_path = Path("downloads") / "AR" / str(annee) / f"AR{annee}{numero:03d}.pdf"
    
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return
    
    try:
        doc = pymupdf.open(pdf_path)
        
        if page_num >= len(doc):
            doc.close()
            print(f"Page {page_num+1} doesn't exist (PDF has {len(doc)} pages)")
            return
        
        page = doc[page_num]
        text = page.get_text()
        doc.close()
        
        print(f"AR {annee}-{numero} Page {page_num+1}:")
        print("=" * 80)
        print(f"Capture: rtl_content_AR{annee}{numero}_page{page_num+1}.png")
        print()
        print("TEXTE EXTRAIT (500 premiers caractères):")
        print("-" * 80)
        
        # Configure UTF-8 pour l'affichage
        import sys
        sys.stdout.reconfigure(encoding='utf-8')
        print(text[:500])
        
        print()
        print("ANALYSE MANUELLE:")
        print("-" * 80)
        
        import re
        lines = text.split('\n')
        
        # Affiche quelques lignes pour voir l'ordre
        print("10 PREMIÈRES LIGNES:")
        for i, line in enumerate(lines[:10]):
            print(f"Ligne {i+1}: {line[:80]}")
        
        # Cherche des patterns spécifiques
        arabic_lines = [i for i, line in enumerate(lines) if sum(1 for c in line if '\u0600' <= c <= '\u06FF') > 5]
        latin_lines = [i for i, line in enumerate(lines) if sum(1 for c in line if 'a' <= c <= 'z' or 'A' <= c <= 'Z') > 3]
        
        print()
        print(f"Lignes avec arabe substantiel: {len(arabic_lines)}")
        print(f"Lignes avec latin substantiel: {len(latin_lines)}")
        
        # Vérifie si les lignes latines sont intercalées anormalement
        if latin_lines:
            print()
            print("POSITIONS DES LIGNES LATINES:")
            for line_num in latin_lines[:5]:
                print(f"  Ligne {line_num+1}: {lines[line_num][:60]}")
        
    except Exception as e:
        print(f"Error: {e}")

print("EXAMEN MANUEL DES CAS RTL AVEC ALERTES")
print("=" * 80)

# Les cas avec alertes
alert_cases = [
    (2007, 16),  # 3 blocs latins potentiels
    (2007, 34),  # 2 blocs latins potentiels
]

for annee, numero in alert_cases:
    examine_rtl_alert(annee, numero)

print()
print("=" * 80)
print("Un cas normal pour comparaison:")
examine_rtl_alert(2007, 3)  # 0 blocs latins