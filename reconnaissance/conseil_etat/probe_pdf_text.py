"""
Inspection du contenu textuel des 3 PDF téléchargés (sample_node_28, 30, 44).
"""

import sys
import os
import re

sys.stdout.reconfigure(encoding='utf-8')

def inspect_pdf_file(filepath):
    print(f"\n=======================================================", flush=True)
    print(f"INSPECTING PDF FILE: {filepath}", flush=True)
    print(f"=======================================================", flush=True)
    
    with open(filepath, "rb") as f:
        content = f.read()
        
    print(f"File size: {len(content)} bytes ({len(content)/(1024*1024):.2f} MB)", flush=True)
    
    # Check PDF version
    header = content[:20]
    print(f"PDF Header: {header}", flush=True)
    
    # Check objects and streams
    pages_count = len(re.findall(rb'/Type\s*/Page\b', content))
    fonts_count = len(re.findall(rb'/Type\s*/Font\b', content))
    images_count = len(re.findall(rb'/Subtype\s*/Image\b', content))
    
    print(f"Pages detected: {pages_count}", flush=True)
    print(f"Fonts detected: {fonts_count}", flush=True)
    print(f"Images detected: {images_count}", flush=True)
    
    # Look for readable text strings in the raw stream if uncompressed
    arabic_chars = len(re.findall(rb'[\xd8\xd9][\x80-\xbf]', content))
    print(f"UTF-8 Arabic byte patterns: {arabic_chars}", flush=True)
    
    if fonts_count > 0 and images_count <= pages_count:
        print("Verdict: NATIVE DIGITAL PDF (Contains vector fonts/text)", flush=True)
    elif images_count >= pages_count and fonts_count == 0:
        print("Verdict: SCANNED PDF / IMAGE-BASED (Requires OCR)", flush=True)
    else:
        print("Verdict: HYBRID / MIXED PDF", flush=True)

if __name__ == "__main__":
    for fname in ["sample_node_28.pdf", "sample_node_30.pdf", "sample_node_44.pdf"]:
        p = f"reconnaissance/conseil_etat/samples/{fname}"
        if os.path.exists(p):
            inspect_pdf_file(p)
