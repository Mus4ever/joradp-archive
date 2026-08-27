"""
Diagnose PDF extraction problems - technical investigation
Test different PyMuPDF extraction methods and identify root causes
"""

import sys
sys.path.append('tools')

import pymupdf
from pathlib import Path
import json
from datetime import datetime

def test_extraction_methods(pdf_path: Path, page_num: int = 4):
    """
    Test all PyMuPDF extraction methods on a single page.
    Returns results for comparison.
    """
    
    if not pdf_path.exists():
        return {"error": "PDF not found"}
    
    try:
        doc = pymupdf.open(pdf_path)
        
        if page_num >= len(doc):
            doc.close()
            return {"error": f"Page {page_num+1} doesn't exist (PDF has {len(doc)} pages)"}
        
        page = doc[page_num]
        
        # Capture visual
        pix = page.get_pixmap()
        img_path = Path("extraction_diagnosis") / f"{pdf_path.stem}_page{page_num+1}.png"
        img_path.parent.mkdir(exist_ok=True)
        pix.save(img_path)
        
        results = {
            "pdf_path": str(pdf_path),
            "page_num": page_num + 1,
            "total_pages": len(doc),
            "img_path": str(img_path),
            "extraction_methods": {}
        }
        
        # Method 1: Default get_text()
        try:
            text_default = page.get_text()
            results["extraction_methods"]["default"] = {
                "text": text_default,
                "length": len(text_default),
                "arabic_chars": sum(1 for c in text_default if '\u0600' <= c <= '\u06FF'),
                "latin_chars": sum(1 for c in text_default if 'a' <= c <= 'z' or 'A' <= c <= 'Z')
            }
        except Exception as e:
            results["extraction_methods"]["default"] = {"error": str(e)}
        
        # Method 2: get_text("blocks")
        try:
            blocks = page.get_text("blocks")
            blocks_text = "\n".join([b[4] for b in blocks if b[6] == 0])  # Only text blocks
            results["extraction_methods"]["blocks"] = {
                "text": blocks_text,
                "length": len(blocks_text),
                "block_count": len(blocks),
                "arabic_chars": sum(1 for c in blocks_text if '\u0600' <= c <= '\u06FF'),
                "latin_chars": sum(1 for c in blocks_text if 'a' <= c <= 'z' or 'A' <= c <= 'Z'),
                "blocks": blocks[:10]  # First 10 blocks for inspection
            }
        except Exception as e:
            results["extraction_methods"]["blocks"] = {"error": str(e)}
        
        # Method 3: get_text("words")
        try:
            words = page.get_text("words")
            words_text = " ".join([w[4] for w in words])
            results["extraction_methods"]["words"] = {
                "text": words_text,
                "length": len(words_text),
                "word_count": len(words),
                "arabic_chars": sum(1 for c in words_text if '\u0600' <= c <= '\u06FF'),
                "latin_chars": sum(1 for c in words_text if 'a' <= c <= 'z' or 'A' <= c <= 'Z'),
                "words": words[:20]  # First 20 words for inspection
            }
        except Exception as e:
            results["extraction_methods"]["words"] = {"error": str(e)}
        
        # Method 4: get_text("dict")
        try:
            text_dict = page.get_text("dict")
            dict_text = "\n".join([block["text"] for block in text_dict["blocks"]])
            results["extraction_methods"]["dict"] = {
                "text": dict_text,
                "length": len(dict_text),
                "block_count": len(text_dict["blocks"]),
                "arabic_chars": sum(1 for c in dict_text if '\u0600' <= c <= '\u06FF'),
                "latin_chars": sum(1 for c in dict_text if 'a' <= c <= 'z' or 'A' <= c <= 'Z'),
                "dict_structure": {
                    "block_count": len(text_dict["blocks"]),
                    "width": text_dict["width"],
                    "height": text_dict["height"]
                }
            }
        except Exception as e:
            results["extraction_methods"]["dict"] = {"error": str(e)}
        
        # Method 5: get_text(sort=True)
        try:
            text_sorted = page.get_text(sort=True)
            results["extraction_methods"]["sorted"] = {
                "text": text_sorted,
                "length": len(text_sorted),
                "arabic_chars": sum(1 for c in text_sorted if '\u0600' <= c <= '\u06FF'),
                "latin_chars": sum(1 for c in text_sorted if 'a' <= c <= 'z' or 'A' <= c <= 'Z')
            }
        except Exception as e:
            results["extraction_methods"]["sorted"] = {"error": str(e)}
        
        doc.close()
        
        return results
        
    except Exception as e:
        return {"error": str(e)}


def diagnose_problematic_pdfs():
    """Select and diagnose 10 problematic PDFs."""
    
    print("PDF EXTRACTION PROBLEM DIAGNOSIS")
    print("=" * 80)
    print("Testing different PyMuPDF extraction methods on selected PDFs")
    print()
    
    # Start with known cases from previous validation
    problematic_pdfs = [
        ("AR", 2007, 3),   # Previously tested
        ("AR", 2007, 16),  # Previously tested with alerts
        ("AR", 2007, 34),  # Previously tested with alerts
        ("AR", 2018, 72),  # Previously tested
        ("AR", 2012, 1),   # Previously tested
        ("AR", 2001, 37),  # Random from 2001
        ("AR", 2002, 6),   # Random from 2002
        ("AR", 2003, 41),  # Random from 2003
        ("AR", 2011, 19),  # Random from 2011
        ("AR", 2007, 19),  # Try 19, will skip if not exists
    ]
    
    results = []
    
    for i, (langue, annee, numero) in enumerate(problematic_pdfs):
        print(f"Processing {i+1}/10: {langue} {annee}-{numero}")
        
        pdf_path = Path("downloads") / langue / str(annee) / f"{langue}{annee}{int(numero):03d}.pdf"
        
        if not pdf_path.exists():
            print(f"  SKIPPED: PDF not found")
            continue
        
        result = test_extraction_methods(pdf_path, page_num=4)
        
        if not result.get("error"):
            results.append(result)
            
            # Save individual method outputs
            base_name = f"{langue}{annee}{int(numero):03d}_page5"
            
            for method_name, method_data in result["extraction_methods"].items():
                if "error" in method_data:
                    print(f"  - {method_name}: ERROR - {method_data['error']}")
                    continue
                
                output_path = Path("extraction_diagnosis") / f"{base_name}_{method_name}.txt"
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"Method: {method_name}\n")
                    f.write(f"Length: {method_data['length']}\n")
                    f.write(f"Arabic chars: {method_data['arabic_chars']}\n")
                    f.write(f"Latin chars: {method_data['latin_chars']}\n")
                    f.write("\n" + "="*80 + "\n")
                    f.write(method_data['text'])
            
            # Print summary
            for method_name, method_data in result["extraction_methods"].items():
                if "error" in method_data:
                    print(f"  - {method_name}: ERROR")
                elif "length" in method_data:
                    print(f"  - {method_name}: {method_data['length']} chars")
        else:
            print(f"  ERROR: {result['error']}")
        
        print()
    
    # Save comprehensive results
    results_path = Path("extraction_diagnosis") / "diagnosis_results.json"
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"Results saved to: {results_path}")
    print(f"Individual method outputs saved to: extraction_diagnosis/")
    
    return results


def main():
    """Main diagnostic function."""
    
    results = diagnose_problematic_pdfs()
    
    print()
    print("=" * 80)
    print("DIAGNOSIS COMPLETE")
    print("=" * 80)
    print(f"Tested {len(results)} PDFs")
    print("Next: Manual inspection of extraction outputs vs rendered pages")
    print("Goal: Identify root causes and determine correct extraction strategy")

if __name__ == "__main__":
    main()