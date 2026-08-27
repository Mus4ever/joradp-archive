"""
Prototype RTL-aware block ordering for Arabic PDF extraction
Uses coordinate-based sorting to fix block ordering issues
"""

import sys
sys.path.append('tools')

import pymupdf
from pathlib import Path

def extract_rtl_blocks(pdf_path: Path, page_num: int = 4):
    """
    Extract text with RTL-aware block ordering.
    
    Algorithm:
    1. Extract blocks with coordinates
    2. Sort by Y coordinate (top-to-bottom)
    3. For blocks on same Y line: sort by X in RTL order (right-to-left)
    4. Detect column boundaries based on X coordinate gaps
    5. Order columns right-to-left
    """
    
    if not pdf_path.exists():
        return {"error": "PDF not found"}
    
    try:
        doc = pymupdf.open(pdf_path)
        
        if page_num >= len(doc):
            doc.close()
            return {"error": f"Page {page_num+1} doesn't exist (PDF has {len(doc)} pages)"}
        
        page = doc[page_num]
        
        # Extract blocks with coordinates
        blocks = page.get_text("blocks")
        
        # Filter text blocks (type 0)
        text_blocks = [b for b in blocks if b[6] == 0]
        
        if not text_blocks:
            doc.close()
            return {"error": "No text blocks found"}
        
        # Sort blocks by Y coordinate (top-to-bottom)
        text_blocks.sort(key=lambda b: b[1])
        
        # Group blocks by Y coordinate (same line)
        line_groups = []
        current_line = []
        current_y = text_blocks[0][1]
        y_tolerance = 5  # Tolerance for same line
        
        for block in text_blocks:
            if abs(block[1] - current_y) <= y_tolerance:
                current_line.append(block)
            else:
                if current_line:
                    line_groups.append(current_line)
                current_line = [block]
                current_y = block[1]
        
        if current_line:
            line_groups.append(current_line)
        
        # Sort each line RTL (right-to-left)
        rtl_ordered_lines = []
        for line in line_groups:
            # Sort by X coordinate descending (right-to-left)
            line_sorted = sorted(line, key=lambda b: b[0], reverse=True)
            rtl_ordered_lines.extend(line_sorted)
        
        # Extract text in RTL order
        rtl_text = "\n".join([b[4] for b in rtl_ordered_lines])
        
        doc.close()
        
        return {
            "text": rtl_text,
            "length": len(rtl_text),
            "block_count": len(text_blocks),
            "line_count": len(line_groups),
            "arabic_chars": sum(1 for c in rtl_text if '\u0600' <= c <= '\u06FF'),
            "latin_chars": sum(1 for c in rtl_text if 'a' <= c <= 'z' or 'A' <= c <= 'Z')
        }
        
    except Exception as e:
        return {"error": str(e)}


def test_rtl_ordering():
    """Test RTL block ordering on problematic PDFs."""
    
    print("RTL BLOCK ORDERING PROTOTYPE TEST")
    print("=" * 80)
    
    # Test on previously problematic PDFs
    test_pdfs = [
        ("AR", 2007, 3),
        ("AR", 2007, 16),
        ("AR", 2007, 34),
        ("AR", 2018, 72),
        ("AR", 2012, 1),
    ]
    
    results = []
    
    for langue, annee, numero in test_pdfs:
        print(f"\nTesting {langue} {annee}-{numero}")
        
        pdf_path = Path("downloads") / langue / str(annee) / f"{langue}{annee}{int(numero):03d}.pdf"
        
        if not pdf_path.exists():
            print(f"  SKIPPED: PDF not found")
            continue
        
        # Test RTL ordering
        rtl_result = extract_rtl_blocks(pdf_path, page_num=4)
        
        if not rtl_result.get("error"):
            results.append(rtl_result)
            
            # Save RTL ordered text
            output_path = Path("extraction_diagnosis") / f"{langue}{annee}{int(numero):03d}_page5_rtl.txt"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"RTL Block Ordering\n")
                f.write(f"Length: {rtl_result['length']}\n")
                f.write(f"Blocks: {rtl_result['block_count']}\n")
                f.write(f"Lines: {rtl_result['line_count']}\n")
                f.write(f"Arabic: {rtl_result['arabic_chars']}\n")
                f.write(f"Latin: {rtl_result['latin_chars']}\n")
                f.write("\n" + "="*80 + "\n")
                f.write(rtl_result['text'])
            
            print(f"  RTL ordered: {rtl_result['length']} chars")
            print(f"  Blocks: {rtl_result['block_count']}")
            print(f"  Lines: {rtl_result['line_count']}")
        else:
            print(f"  ERROR: {rtl_result['error']}")
    
    print()
    print("=" * 80)
    print(f"Successfully processed {len(results)} PDFs with RTL ordering")
    print("RTL ordered text saved to extraction_diagnosis/")
    print("Next: Manual comparison with default extraction")

if __name__ == "__main__":
    test_rtl_ordering()