"""
Script de validation empirique de la Phase 4 :
Mesure l'élimination des doublons de fragments et l'intégrité de l'ordre de lecture RTL
sur les 10 PDF du diagnostic initial.
"""
import sys, os, json, re
from pathlib import Path
import pymupdf

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE / "tools"))

from phase4_extractor import Phase4Extractor

def count_duplicate_fragments(lines):
    """Compte les répétitions exactes de lignes consécutives ou ombrées (shadow-text)."""
    consecutive_dups = 0
    shadow_dups = 0
    
    prev = ""
    for l in lines:
        s = l.strip()
        if not s:
            continue
        if s == prev:
            consecutive_dups += 1
        words = s.split()
        n = len(words)
        if n >= 2 and n % 2 == 0 and words[:n//2] == words[n//2:]:
            shadow_dups += 1
        prev = s
        
    return consecutive_dups, shadow_dups


def run_phase4_dedup_validation():
    extractor = Phase4Extractor(downloads_dir=str(BASE / "downloads"))
    
    diag_pdfs = [
        ("AR", 2007, "003", 5),
        ("AR", 2007, "016", 5),
        ("AR", 2007, "019", 5),
        ("AR", 2007, "034", 5),
        ("AR", 2018, "072", 5),
        ("AR", 2012, "001", 5),
        ("AR", 2003, "041", 5),
        ("AR", 2011, "019", 5),
        ("AR", 2001, "037", 5),
        ("AR", 2002, "006", 5),
    ]
    
    print("=" * 95)
    print("VALIDATION DE DÉDUPLICATION ET D'EXTRACTION RTL — PHASE 4 (10 PDFS DU DIAGNOSTIC)")
    print("=" * 95)
    print(f"{'Document':<18} | {'Classification':<16} | {'Doublons Avant':<16} | {'Doublons Après':<16} | {'Réduction'}")
    print("-" * 95)
    
    summary = []
    
    for langue, annee, num, page_idx in diag_pdfs:
        num_str = str(num).zfill(3)
        pdf_path = BASE / "downloads" / langue / str(annee) / f"{langue}{annee}{num_str}.pdf"
        doc_id = f"{langue} {annee}-{num_str} p.{page_idx}"
        
        if not pdf_path.exists():
            print(f"{doc_id:<18} | Fichier absent ({pdf_path.name})")
            continue
            
        doc = pymupdf.open(str(pdf_path))
        if len(doc) < page_idx:
            page_idx = 1
        page = doc[page_idx - 1]
        
        # 1. Extraction brute non corrigée (page.get_text())
        raw_text = page.get_text()
        raw_lines = [l for l in raw_text.splitlines() if l.strip()]
        raw_c_dup, raw_s_dup = count_duplicate_fragments(raw_lines)
        total_raw_dups = raw_c_dup + raw_s_dup
        
        # 2. Détection et extraction Phase 4
        char_stats = extractor.analyze_characters(raw_text)
        page_type, methode, q_flags = extractor.detect_page_type(page, langue, raw_text, char_stats)
        
        if methode == "rtl_reorder":
            clean_text, stats = extractor.extract_arabic_rtl_reordered(page)
        elif methode == "needs_ocr":
            clean_text = "[ROUTÉ VERS OCR - SCAN PUR]"
        else:
            clean_text = raw_text
            
        clean_lines = [l for l in clean_text.splitlines() if l.strip()]
        clean_c_dup, clean_s_dup = count_duplicate_fragments(clean_lines)
        total_clean_dups = clean_c_dup + clean_s_dup
        
        doc.close()
        
        reduc = f"-{total_raw_dups - total_clean_dups}" if total_raw_dups > 0 else "0 (Déjà propre)"
        print(f"{doc_id:<18} | {methode:<16} | {total_raw_dups:2d} (cons:{raw_c_dup}, shad:{raw_s_dup}) | {total_clean_dups:2d} (cons:{clean_c_dup}, shad:{clean_s_dup}) | {reduc}")
        
        summary.append({
            "doc": doc_id,
            "methode": methode,
            "raw_dups": total_raw_dups,
            "clean_dups": total_clean_dups
        })
        
    print("-" * 95)
    total_before = sum(s["raw_dups"] for s in summary)
    total_after = sum(s["clean_dups"] for s in summary)
    print(f"TOTAL DOUBLONS PARASITES : {total_before} avant fix -> {total_after} après fix (Élimination : {(total_before - total_after)/total_before * 100:.1f}%)" if total_before > 0 else "Aucun doublon")
    print("=" * 95)

if __name__ == "__main__":
    run_phase4_dedup_validation()
