"""
FINAL RTL VALIDATION - Empirical validation on 25 representative Arabic PDFs
Distributed across periods: 1964-1993, 1994-2009, 2010-2026
"""

import sys
sys.path.append('tools')

import pymupdf
from pathlib import Path
from database import JoradpDatabase
import json
from datetime import datetime

def select_rtl_samples():
    """Select 25 Arabic PDFs representative distributed by period."""
    
    db = JoradpDatabase()
    
    with db:
        conn = db.connect()
        
        samples = []
        
        # Period 1: 1964-1993 (8 PDF)
        period1 = conn.execute("""
            SELECT annee, numero
            FROM sources 
            WHERE langue = 'AR' 
            AND annee BETWEEN 1964 AND 1993
            AND statut = 'telecharge'
            ORDER BY RANDOM()
            LIMIT 8
        """).fetchall()
        
        for annee, numero in period1:
            samples.append({"annee": annee, "numero": numero, "period": "1964-1993"})
        
        # Period 2: 1994-2009 (9 PDF)
        period2 = conn.execute("""
            SELECT annee, numero
            FROM sources 
            WHERE langue = 'AR' 
            AND annee BETWEEN 1994 AND 2009
            AND statut = 'telecharge'
            ORDER BY RANDOM()
            LIMIT 9
        """).fetchall()
        
        for annee, numero in period2:
            samples.append({"annee": annee, "numero": numero, "period": "1994-2009"})
        
        # Period 3: 2010-2026 (8 PDF)
        period3 = conn.execute("""
            SELECT annee, numero
            FROM sources 
            WHERE langue = 'AR' 
            AND annee BETWEEN 2010 AND 2026
            AND statut = 'telecharge'
            ORDER BY RANDOM()
            LIMIT 8
        """).fetchall()
        
        for annee, numero in period3:
            samples.append({"annee": annee, "numero": numero, "period": "2010-2026"})
        
        return samples


def analyze_page(annee: int, numero: int, page_num: int = 5):
    """
    Analyze a real content page.
    Returns extracted text, capture and metadata.
    """
    
    pdf_path = Path("downloads") / "AR" / str(annee) / f"AR{annee}{int(numero):03d}.pdf"
    
    if not pdf_path.exists():
        return {"error": "PDF not found"}
    
    try:
        doc = pymupdf.open(pdf_path)
        
        # Try page 5, if not available try page 3, then page 2
        if page_num >= len(doc):
            page_num = min(2, len(doc) - 1)
        if page_num >= len(doc):
            page_num = min(1, len(doc) - 1)
        
        page = doc[page_num]
        text = page.get_text()
        
        # Visual capture
        pix = page.get_pixmap()
        img_path = Path("rtl_validation") / f"sample_AR{annee}{int(numero):03d}_page{page_num+1}.png"
        img_path.parent.mkdir(exist_ok=True)
        pix.save(img_path)
        
        # Metadata
        arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        latin_chars = sum(1 for c in text if 'a' <= c <= 'z' or 'A' <= c <= 'Z')
        numbers = len([c for c in text if c.isdigit()])
        
        # Heuristic alerts
        lines = text.split('\n')
        latin_in_arabic_context = 0
        
        for i, line in enumerate(lines):
            if i > 0 and i < len(lines) - 1:
                prev_arabic = sum(1 for c in lines[i-1] if '\u0600' <= c <= '\u06FF')
                next_arabic = sum(1 for c in lines[i+1] if '\u0600' <= c <= '\u06FF')
                current_latin = sum(1 for c in line if 'a' <= c <= 'z' or 'A' <= c <= 'Z')
                
                if prev_arabic > 5 and next_arabic > 5 and current_latin > 3:
                    latin_in_arabic_context += 1
        
        total_pages = len(doc)
        doc.close()
        
        actual_page_num = page_num + 1
        return {
            "annee": annee,
            "numero": numero,
            "page_num": actual_page_num,
            "total_pages": total_pages,
            "text": text,
            "img_path": str(img_path),
            "arabic_chars": arabic_chars,
            "latin_chars": latin_chars,
            "numbers": numbers,
            "latin_in_arabic_context": latin_in_arabic_context,
            "heuristic_alert": latin_in_arabic_context > 0
        }
        
    except Exception as e:
        return {"error": str(e)}


def generate_html_report(samples, results):
    """Generate HTML visual validation report."""
    
    html_path = Path("rtl_validation") / "final_rtl_review.html"
    html_path.parent.mkdir(exist_ok=True)
    
    # HTML template
    html_parts = []
    
    # Header
    html_parts.append('<!DOCTYPE html>')
    html_parts.append('<html lang="fr">')
    html_parts.append('<head>')
    html_parts.append('<meta charset="UTF-8">')
    html_parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    html_parts.append('<title>Final RTL Validation Report</title>')
    html_parts.append('<style>')
    html_parts.append('body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }')
    html_parts.append('.header { background-color: #333; color: white; padding: 20px; margin-bottom: 20px; }')
    html_parts.append('.summary { background-color: white; padding: 20px; margin-bottom: 20px; border-radius: 5px; }')
    html_parts.append('.sample { background-color: white; padding: 20px; margin-bottom: 20px; border-radius: 5px; border: 1px solid #ddd; }')
    html_parts.append('.sample-header { background-color: #f0f0f0; padding: 10px; margin: -20px -20px 20px -20px; border-radius: 5px 5px 0 0; }')
    html_parts.append('.comparison { display: flex; gap: 20px; }')
    html_parts.append('.left { flex: 1; }')
    html_parts.append('.right { flex: 1; }')
    html_parts.append('.page-image { max-width: 100%; border: 1px solid #ddd; }')
    html_parts.append('.extracted-text { background-color: #f9f9f9; padding: 15px; border: 1px solid #ddd; border-radius: 5px; font-family: monospace; white-space: pre-wrap; word-wrap: break-word; max-height: 600px; overflow-y: auto; }')
    html_parts.append('.metadata { margin-top: 20px; padding: 10px; background-color: #f0f0f0; border-radius: 5px; }')
    html_parts.append('.alert { color: #d9534f; font-weight: bold; }')
    html_parts.append('.pass { color: #5cb85c; font-weight: bold; }')
    html_parts.append('.review { color: #f0ad4e; font-weight: bold; }')
    html_parts.append('.verdict { margin-top: 15px; padding: 10px; border-radius: 5px; font-weight: bold; }')
    html_parts.append('.verdict-pass { background-color: #dff0d8; color: #3c763d; }')
    html_parts.append('.verdict-fail { background-color: #f2dede; color: #a94442; }')
    html_parts.append('.verdict-review { background-color: #fcf8e3; color: #8a6d3b; }')
    html_parts.append('</style>')
    html_parts.append('</head>')
    html_parts.append('<body>')
    
    # Header section
    html_parts.append('<div class="header">')
    html_parts.append('<h1>Final RTL Validation Report</h1>')
    html_parts.append(f'<p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>')
    html_parts.append('</div>')
    
    # Summary section
    html_parts.append('<div class="summary">')
    html_parts.append('<h2>Summary</h2>')
    html_parts.append(f'<p>Total samples: {len(samples)}</p>')
    html_parts.append('<p>Period distribution:</p>')
    html_parts.append('<ul>')
    
    # Distribution by period
    period_counts = {}
    for sample in samples:
        period = sample["period"]
        period_counts[period] = period_counts.get(period, 0) + 1
    
    for period, count in sorted(period_counts.items()):
        html_parts.append(f'<li>{period}: {count} samples</li>')
    
    html_parts.append('</ul>')
    
    # Validation results
    pass_count = sum(1 for r in results if r.get("verdict") == "PASS")
    fail_count = sum(1 for r in results if r.get("verdict") == "FAIL")
    review_count = sum(1 for r in results if r.get("verdict") == "REVIEW_REQUIRED")
    
    html_parts.append('<p>Validation results:</p>')
    html_parts.append('<ul>')
    html_parts.append(f'<li>PASS: {pass_count}</li>')
    html_parts.append(f'<li>FAIL: {fail_count}</li>')
    html_parts.append(f'<li>REVIEW_REQUIRED: {review_count}</li>')
    html_parts.append('</ul>')
    html_parts.append('</div>')
    
    # Sample details
    for i, (sample, result) in enumerate(zip(samples, results)):
        if result.get("error"):
            html_parts.append('<div class="sample">')
            html_parts.append('<div class="sample-header">')
            html_parts.append(f'<h3>Sample {i+1}: AR {sample["annee"]}-{sample["numero"]} (ERROR)</h3>')
            html_parts.append('</div>')
            html_parts.append(f'<p class="alert">Error: {result["error"]}</p>')
            html_parts.append('</div>')
            continue
        
        verdict = result.get("verdict", "REVIEW_REQUIRED")
        verdict_class = f"verdict-{verdict.lower()}"
        
        html_parts.append('<div class="sample">')
        html_parts.append('<div class="sample-header">')
        html_parts.append(f'<h3>Sample {i+1}: AR {sample["annee"]}-{sample["numero"]} (Page {result["page_num"]})</h3>')
        html_parts.append(f'<p>Period: {sample["period"]}</p>')
        html_parts.append('</div>')
        
        html_parts.append('<div class="comparison">')
        html_parts.append('<div class="left">')
        html_parts.append('<h4>Rendered PDF Page</h4>')
        img_filename = Path(result["img_path"]).name
        html_parts.append(f'<img src="{img_filename}" class="page-image" alt="AR {sample["annee"]}-{sample["numero"]} page {result["page_num"]}">')
        html_parts.append('</div>')
        html_parts.append('<div class="right">')
        html_parts.append('<h4>Extracted Text (PyMuPDF)</h4>')
        html_parts.append(f'<div class="extracted-text">{result["text"]}</div>')
        html_parts.append('</div>')
        html_parts.append('</div>')
        
        html_parts.append('<div class="metadata">')
        html_parts.append(f'<p><strong>PDF ID:</strong> AR {sample["annee"]}-{sample["numero"]}</p>')
        html_parts.append(f'<p><strong>Year:</strong> {sample["annee"]}</p>')
        html_parts.append(f'<p><strong>Issue:</strong> {sample["numero"]}</p>')
        html_parts.append(f'<p><strong>Page:</strong> {result["page_num"]} / {result["total_pages"]}</p>')
        html_parts.append(f'<p><strong>Arabic characters:</strong> {result["arabic_chars"]}</p>')
        html_parts.append(f'<p><strong>Latin characters:</strong> {result["latin_chars"]}</p>')
        html_parts.append(f'<p><strong>Numbers:</strong> {result["numbers"]}</p>')
        alert_text = 'YES' if result['heuristic_alert'] else 'NO'
        html_parts.append(f'<p><strong>Heuristic alerts:</strong> {alert_text} ({result["latin_in_arabic_context"]} Latin-in-Arabic contexts)</p>')
        html_parts.append('</div>')
        
        html_parts.append(f'<div class="verdict {verdict_class}">')
        html_parts.append(f'Preliminary verdict: {verdict}')
        html_parts.append('</div>')
        html_parts.append('</div>')
    
    # Conclusion section
    html_parts.append('<div class="summary">')
    html_parts.append('<h2>Conclusion</h2>')
    html_parts.append('<p><strong>Validation Method:</strong> Visual comparison of rendered PDF pages vs PyMuPDF extracted text</p>')
    html_parts.append('<p><strong>RTL Review Rule:</strong> Latin technical words, company names, abbreviations, numbers, dates, and isolated Latin characters are NOT considered RTL failures. These are legitimate mixed-language content.</p>')
    html_parts.append('<p><strong>Real RTL Failure:</strong> Block-order corruption that changes the logical reading sequence of Arabic text (wrong column blocks, scrambled paragraphs, reversed article sequence).</p>')
    html_parts.append('<p><strong>Recommendation:</strong> Manual visual inspection of the above samples to verify RTL ordering correctness.</p>')
    html_parts.append('</div>')
    html_parts.append('</body>')
    html_parts.append('</html>')
    
    # Write HTML file
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_parts))
    
    return html_path


def main():
    """Final RTL validation on 25 representative Arabic PDFs."""
    
    print("FINAL RTL VALIDATION - EMPIRICAL VALIDATION")
    print("=" * 80)
    print("Sampling 25 Arabic PDFs across periods: 1964-1993, 1994-2009, 2010-2026")
    print()
    
    # Select samples
    print("Step 1: Selecting representative samples...")
    samples = select_rtl_samples()
    print(f"Selected {len(samples)} samples")
    
    # Distribution by period
    period_counts = {}
    for sample in samples:
        period = sample["period"]
        period_counts[period] = period_counts.get(period, 0) + 1
    
    print("Period distribution:")
    for period, count in sorted(period_counts.items()):
        print(f"  {period}: {count} samples")
    
    print()
    print("Step 2: Analyzing content pages (page 5)...")
    
    results = []
    for i, sample in enumerate(samples):
        print(f"Processing sample {i+1}/{len(samples)}: AR {sample['annee']}-{sample['numero']}")
        
        # Try page 5 (typical content)
        result = analyze_page(sample['annee'], sample['numero'], page_num=4)
        
        if not result.get("error"):
            # Preliminary verdict based on heuristic
            if result['heuristic_alert']:
                result['verdict'] = 'REVIEW_REQUIRED'
            else:
                result['verdict'] = 'PASS'
        
        results.append(result)
    
    print()
    print("Step 3: Generating HTML visual review report...")
    html_path = generate_html_report(samples, results)
    print(f"Report generated: {html_path}")
    
    print()
    print("Step 4: Summary statistics...")
    
    pass_count = sum(1 for r in results if r.get("verdict") == "PASS")
    fail_count = sum(1 for r in results if r.get("verdict") == "FAIL")
    review_count = sum(1 for r in results if r.get("verdict") == "REVIEW_REQUIRED")
    error_count = sum(1 for r in results if r.get("error"))
    
    print(f"PASS: {pass_count}")
    print(f"FAIL: {fail_count}")
    print(f"REVIEW_REQUIRED: {review_count}")
    print(f"ERROR: {error_count}")
    
    print()
    print("=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)
    print(f"Report: {html_path}")
    print("Next step: Manual visual inspection of the HTML report")
    print("Do NOT start mass extraction until RTL validation is approved")

if __name__ == "__main__":
    main()