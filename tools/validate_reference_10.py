"""
Script de validation approfondie pour les 10 PDF de référence
Génère un tableau détaillé page par page et extrait des exemples représentatifs.
"""

import sys
import os
from pathlib import Path
import json

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(str(Path(__file__).parent))

from phase4_extractor import Phase4Extractor, PageClassification
import pymupdf


def validate_10_reference_pdfs():
    extractor = Phase4Extractor(downloads_dir="downloads")
    
    test_cases = [
        ("AR", 2007, "003", "Multi-colonnes arabe standard"),
        ("AR", 2007, "016", "Multi-colonnes arabe standard"),
        ("AR", 2007, "034", "Multi-colonnes arabe"),
        ("AR", 2018, "072", "Arabe récent"),
        ("AR", 2012, "001", "Arabe récent dense"),
        ("AR", 2007, "019", "Multi-colonnes arabe + duplications potentielles"),
        ("AR", 2005, "042", "Corrupt font mapping (ToUnicode)"),
        ("AR", 2008, "001", "Corrupt / fragments"),
        ("AR", 2001, "037", "Scan image (0 texte natif)"),
        ("AR", 2002, "006", "Scan image (0 texte natif)"),
    ]
    
    results = []
    
    for langue, annee, numero, desc in test_cases:
        pdf_name_3d = f"{langue}{annee}{int(numero):03d}.pdf"
        pdf_name_orig = f"{langue}{annee}{numero}.pdf"
        
        dir_path = Path("downloads") / langue / str(annee)
        pdf_path = dir_path / pdf_name_3d
        if not pdf_path.exists():
            pdf_path = dir_path / pdf_name_orig
            
        if not pdf_path.exists():
            print(f"Fichier non trouvé: {pdf_path}")
            continue
            
        res = extractor.extract_pdf_file(pdf_path, langue)
        
        # Comptage exact par type
        counts = {
            "NATIVE_OK": 0,
            "NATIVE_RTL_REORDER": 0,
            "CORRUPT_MAPPING": 0,
            "SCAN_NO_TEXT": 0,
            "NEEDS_REVIEW": 0
        }
        
        methods_used = set()
        
        for p in res["pages"]:
            ptype = p["page_type"]
            counts[ptype] = counts.get(ptype, 0) + 1
            if p["methode"] == "needs_review":
                counts["NEEDS_REVIEW"] += 1
            methods_used.add(p["methode"])
            
        # Exemple représentatif (page 5 ou page 1)
        sample_page_num = min(5, res["total_pages"])
        sample_page = res["pages"][sample_page_num - 1]
        sample_text_snippet = sample_page["extracted_text"][:200].replace("\n", " ") if sample_page["extracted_text"] else "[AUCUN TEXTE EXTRAIT - SCAN OU OCR REQUIS]"
        
        results.append({
            "doc": f"{langue} {annee}-{numero}",
            "description": desc,
            "total_pages": res["total_pages"],
            "counts": counts,
            "methods": list(methods_used),
            "sample_page_num": sample_page_num,
            "sample_snippet": sample_text_snippet,
            "sample_stats": {
                "chars": sample_page["total_chars"],
                "arabic": sample_page["arabic_chars"],
                "latin": sample_page["latin_chars"],
                "arabic_ratio": sample_page["arabic_ratio"],
                "quality_score": sample_page["quality_score"]
            }
        })
        
    out_json = Path("reports") / "reference_10_validation.json"
    out_json.parent.mkdir(exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"Validation des 10 PDF terminée. Rapport sauvegardé dans {out_json}")
    return results

if __name__ == "__main__":
    validate_10_reference_pdfs()
