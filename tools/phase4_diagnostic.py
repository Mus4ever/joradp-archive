"""
Diagnostic et validation du routeur intelligent Phase 4
Teste sur les 10 PDF problématiques de référence + échantillons supplémentaires.
"""

import sys
import io
from pathlib import Path
import json

# Force UTF-8 pour Windows terminal
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Ajout du dossier tools au path
sys.path.append(str(Path(__file__).parent))

from database import JoradpDatabase
from phase4_extractor import Phase4Extractor, PageClassification
import pymupdf


def run_known_cases_diagnostic():
    print("=" * 80)
    print("DIAGNOSTIC DU ROUTEUR INTELLIGENT PHASE 4 - ÉCHANTILLON DE RÉFÉRENCE")
    print("=" * 80)
    
    extractor = Phase4Extractor(downloads_dir="downloads")
    
    test_cases = [
        ("AR", 2007, "003", "Multi-colonnes arabe standard"),
        ("AR", 2007, "016", "Multi-colonnes arabe standard"),
        ("AR", 2007, "019", "Multi-colonnes arabe + duplications potentielles"),
        ("AR", 2007, "034", "Multi-colonnes arabe"),
        ("AR", 2012, "001", "Arabe récent dense"),
        ("AR", 2018, "072", "Arabe récent"),
        ("AR", 2005, "042", "Corrupt font mapping (problème ToUnicode)"),
        ("AR", 2008, "001", "Corrupt / fragments parasites"),
        ("AR", 2001, "037", "Scan image (0 texte natif)"),
        ("AR", 2002, "006", "Scan image (0 texte natif)"),
        ("FR", 2026, "001", "Français récent natif"),
        ("FR", 1973, "001", "Français historique / scan"),
    ]
    
    results_summary = []
    
    for langue, annee, numero, description in test_cases:
        pdf_name_3d = f"{langue}{annee}{int(numero):03d}.pdf"
        pdf_name_orig = f"{langue}{annee}{numero}.pdf"
        
        dir_path = Path("downloads") / langue / str(annee)
        pdf_path = dir_path / pdf_name_3d
        if not pdf_path.exists():
            pdf_path = dir_path / pdf_name_orig
            if not pdf_path.exists():
                print(f"[SKIP] {langue} {annee}-{numero} non trouvé dans {dir_path}")
                continue
                
        print(f"\n--- Test: {langue} {annee}-{numero} ({description}) ---")
        print(f"Fichier: {pdf_path.name}")
        
        res = extractor.extract_pdf_file(pdf_path, langue)
        if not res.get("success"):
            print(f"  [ERREUR] {res.get('error')}")
            continue
            
        print(f"  Pages totales: {res['total_pages']}")
        print(f"  Statut global détecté: {res['overall_status']}")
        print(f"  Répartition des pages: {res['types_count']}")
        
        sample_page_idx = min(4, res['total_pages'] - 1)
        sample_page = res['pages'][sample_page_idx]
        print(f"  > Détail Page {sample_page['page_num']}:")
        print(f"    - Type: {sample_page['page_type']}")
        print(f"    - Méthode: {sample_page['methode']}")
        print(f"    - Caractères: {sample_page['total_chars']} (Arabe: {sample_page['arabic_chars']}, Latin: {sample_page['latin_chars']}, Chiffres: {sample_page['digit_chars']})")
        print(f"    - Ratio Arabe: {sample_page['arabic_ratio']:.1%}")
        print(f"    - Lettres latines suspectes: {sample_page['suspect_latin_count']}")
        print(f"    - Score qualité: {sample_page['quality_score']}")
        print(f"    - Flags: {sample_page['quality_flags']}")
        
        # Encodage sécurisé de l'aperçu pour affichage
        sample_text = sample_page['extracted_text'].strip()
        if sample_text:
            preview = sample_text[:120].replace("\n", " ")
        else:
            preview = "[AUCUN TEXTE EXTRAIT - SCAN OU OCR REQUIS]"
        print(f"    - Aperçu texte (longueur {len(sample_text)}): {preview[:80]}...")
        
        results_summary.append({
            "langue": langue,
            "annee": annee,
            "numero": numero,
            "description": description,
            "total_pages": res['total_pages'],
            "overall_status": res['overall_status'],
            "types_count": res['types_count'],
            "sample_page_type": sample_page['page_type'],
            "sample_page_chars": sample_page['total_chars']
        })
        
    print("\n" + "=" * 80)
    print("RÉSUMÉ DU DIAGNOSTIC SUR ÉCHANTILLON")
    print("=" * 80)
    print(f"{'Document':<16} | {'Description':<32} | {'Pages':<6} | {'Statut Global':<28} | {'Échantillon':<18}")
    print("-" * 110)
    for r in results_summary:
        doc_id = f"{r['langue']} {r['annee']}-{r['numero']}"
        print(f"{doc_id:<16} | {r['description'][:32]:<32} | {r['total_pages']:<6} | {r['overall_status']:<28} | {r['sample_page_type']:<18}")

    return results_summary


if __name__ == "__main__":
    run_known_cases_diagnostic()
