"""
Analyze extraction results and identify problems
Compare different PyMuPDF methods and identify root causes
"""

import sys
sys.path.append('tools')

import json
from pathlib import Path
from difflib import SequenceMatcher

def analyze_single_pdf(results_path: Path):
    """Analyze extraction results for a single PDF."""
    
    with open(results_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    report = []
    
    for pdf_result in data:
        pdf_id = Path(pdf_result["pdf_path"]).stem
        page_num = pdf_result["page_num"]
        
        report.append(f"\n{'='*80}")
        report.append(f"PDF: {pdf_id}, Page: {page_num}")
        report.append(f"{'='*80}")
        
        methods = pdf_result["extraction_methods"]
        
        # Check if it's a scanned PDF (0 chars)
        default_chars = methods.get("default", {}).get("length", 0)
        if default_chars == 0:
            report.append(f"CLASSIFICATION: SCANNED PDF (no native text)")
            report.append(f"RECOMMENDATION: NEEDS_OCR")
            continue
        
        report.append(f"CLASSIFICATION: NATIVE TEXT PDF")
        
        # Compare method outputs
        report.append(f"\nMethod Comparison:")
        report.append(f"  Default: {methods.get('default', {}).get('length', 0)} chars")
        report.append(f"  Blocks: {methods.get('blocks', {}).get('length', 0)} chars")
        report.append(f"  Words: {methods.get('words', {}).get('length', 0)} chars")
        report.append(f"  Sorted: {methods.get('sorted', {}).get('length', 0)} chars")
        
        # Check for duplicates by comparing text similarity
        default_text = methods.get("default", {}).get("text", "")
        sorted_text = methods.get("sorted", {}).get("text", "")
        
        if default_text and sorted_text:
            similarity = SequenceMatcher(None, default_text, sorted_text).ratio()
            report.append(f"\nText Similarity (default vs sorted): {similarity:.2%}")
            
            if similarity < 0.8:
                report.append(f"  ALERT: Low similarity suggests reordering")
            elif similarity > 0.95:
                report.append(f"  OK: High similarity, similar ordering")
        
        # Check for character issues
        arabic_chars = methods.get("default", {}).get("arabic_chars", 0)
        latin_chars = methods.get("default", {}).get("latin_chars", 0)
        
        report.append(f"\nCharacter Analysis:")
        report.append(f"  Arabic: {arabic_chars} chars")
        report.append(f"  Latin: {latin_chars} chars")
        report.append(f"  Ratio: {latin_chars/arabic_chars if arabic_chars > 0 else 0:.2%}")
        
        # Check block structure
        blocks = methods.get("blocks", {}).get("blocks", [])
        if blocks:
            report.append(f"\nBlock Structure:")
            report.append(f"  Total blocks: {len(blocks)}")
            
            # Analyze block coordinates for ordering
            y_coords = [b[1] for b in blocks if len(b) > 1]
            if y_coords:
                y_coords_sorted = sorted(y_coords)
                if y_coords == y_coords_sorted:
                    report.append(f"  Block ordering: Top-to-bottom (correct)")
                else:
                    report.append(f"  ALERT: Block ordering may be incorrect")
        
        # Preliminary diagnosis
        report.append(f"\nPRELIMINARY DIAGNOSIS:")
        
        if default_chars > 0 and arabic_chars > 0:
            if similarity > 0.9:
                report.append(f"  => Likely correct extraction (high similarity)")
                report.append(f"  => RECOMMENDATION: Use default or blocks method")
            else:
                report.append(f"  => Potential ordering issue (low similarity)")
                report.append(f"  => RECOMMENDATION: Investigate block coordinates")
        
        if latin_chars > arabic_chars * 0.5:
            report.append(f"  => High Latin content (bilingual document)")
            report.append(f"  => Normal for technical/legal documents")
    
    return "\n".join(report)


def main():
    """Analyze all extraction results."""
    
    results_path = Path("extraction_diagnosis") / "diagnosis_results.json"
    
    if not results_path.exists():
        print(f"ERROR: Results file not found: {results_path}")
        return
    
    print("ANALYZING EXTRACTION RESULTS")
    print("=" * 80)
    
    report = analyze_single_pdf(results_path)
    
    # Save report
    report_path = Path("extraction_diagnosis") / "analysis_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("Report saved to:", report_path)
    print("Next: Manual inspection of text files vs rendered pages")

if __name__ == "__main__":
    main()