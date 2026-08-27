"""
Script de préparation du dataset de benchmark 30 pages (300 DPI)
et génération du Ground Truth d'évaluation.
"""

import sys
import os
from pathlib import Path
import json
import pymupdf

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Liste des 30 pages définies dans le protocole
BENCHMARK_SPEC = [
    # --- ARABE (15 pages) ---
    {"id": "AR-01", "langue": "AR", "annee": 1965, "numero": "078", "page": 1, "era": "Legacy", "desc": "Scan 1965 (Typographie ancienne)"},
    {"id": "AR-02", "langue": "AR", "annee": 1974, "numero": "086", "page": 4, "era": "Legacy", "desc": "Scan 1974 multi-colonnes"},
    {"id": "AR-03", "langue": "AR", "annee": 1981, "numero": "006", "page": 5, "era": "Legacy", "desc": "Scan 1981 dense"},
    {"id": "AR-04", "langue": "AR", "annee": 1987, "numero": "031", "page": 2, "era": "Legacy", "desc": "Scan 1987 bicolonne"},
    {"id": "AR-05", "langue": "AR", "annee": 1991, "numero": "002", "page": 3, "era": "Legacy", "desc": "Scan 1991 à faible contraste"},
    {"id": "AR-06", "langue": "AR", "annee": 1993, "numero": "025", "page": 2, "era": "Legacy", "desc": "Scan 1993 fin de période legacy"},
    {"id": "AR-07", "langue": "AR", "annee": 1997, "numero": "027", "page": 3, "era": "Transition", "desc": "Scan 1997"},
    {"id": "AR-08", "langue": "AR", "annee": 2001, "numero": "037", "page": 5, "era": "Transition", "desc": "Scan 2001 pleine-page"},
    {"id": "AR-09", "langue": "AR", "annee": 2003, "numero": "032", "page": 3, "era": "Transition", "desc": "Police corrompue (2003)"},
    {"id": "AR-10", "langue": "AR", "annee": 2005, "numero": "042", "page": 5, "era": "Transition", "desc": "Police corrompue (2005)"},
    {"id": "AR-11", "langue": "AR", "annee": 2005, "numero": "049", "page": 2, "era": "Transition", "desc": "Police corrompue WinAnsi (2005)"},
    {"id": "AR-12", "langue": "AR", "annee": 2007, "numero": "019", "page": 4, "era": "Transition", "desc": "PDF complexe 2007"},
    {"id": "AR-13", "langue": "AR", "annee": 2012, "numero": "001", "page": 4, "era": "Moderne", "desc": "PDF moderne dense"},
    {"id": "AR-14", "langue": "AR", "annee": 2018, "numero": "072", "page": 3, "era": "Moderne", "desc": "PDF moderne avec dates mixtes"},
    {"id": "AR-15", "langue": "AR", "annee": 2023, "numero": "027", "page": 4, "era": "Moderne", "desc": "Scan isolé au sein d'un PDF moderne"},
    
    # --- FRANÇAIS (15 pages) ---
    {"id": "FR-01", "langue": "FR", "annee": 1963, "numero": "001", "page": 1, "era": "Legacy", "desc": "Scan 1963 n°1"},
    {"id": "FR-02", "langue": "FR", "annee": 1965, "numero": "027", "page": 3, "era": "Legacy", "desc": "Scan 1965"},
    {"id": "FR-03", "langue": "FR", "annee": 1970, "numero": "011", "page": 2, "era": "Legacy", "desc": "Scan 1970 bicolonne"},
    {"id": "FR-04", "langue": "FR", "annee": 1979, "numero": "028", "page": 5, "era": "Legacy", "desc": "Scan 1979"},
    {"id": "FR-05", "langue": "FR", "annee": 1986, "numero": "026", "page": 4, "era": "Legacy", "desc": "Scan 1986 bicolonne"},
    {"id": "FR-06", "langue": "FR", "annee": 1991, "numero": "005", "page": 2, "era": "Legacy", "desc": "Scan 1991"},
    {"id": "FR-07", "langue": "FR", "annee": 1994, "numero": "082", "page": 3, "era": "Transition", "desc": "Scan 1994"},
    {"id": "FR-08", "langue": "FR", "annee": 1998, "numero": "052", "page": 2, "era": "Transition", "desc": "Scan 1998"},
    {"id": "FR-09", "langue": "FR", "annee": 2000, "numero": "025", "page": 4, "era": "Transition", "desc": "Scan 2000"},
    {"id": "FR-10", "langue": "FR", "annee": 2001, "numero": "016", "page": 1, "era": "Transition", "desc": "Scan 2001 couverture"},
    {"id": "FR-11", "langue": "FR", "annee": 2004, "numero": "018", "page": 2, "era": "Transition", "desc": "PDF transitoire 2004"},
    {"id": "FR-12", "langue": "FR", "annee": 2008, "numero": "041", "page": 3, "era": "Transition", "desc": "PDF 2008"},
    {"id": "FR-13", "langue": "FR", "annee": 2011, "numero": "045", "page": 2, "era": "Moderne", "desc": "PDF moderne 2011"},
    {"id": "FR-14", "langue": "FR", "annee": 2019, "numero": "043", "page": 5, "era": "Moderne", "desc": "PDF moderne 2019"},
    {"id": "FR-15", "langue": "FR", "annee": 2024, "numero": "005", "page": 1, "era": "Moderne", "desc": "PDF moderne 2024"}
]


def extract_30_benchmark_images():
    out_dir = Path("benchmark") / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    extracted_manifest = []
    
    for item in BENCHMARK_SPEC:
        langue = item["langue"]
        annee = item["annee"]
        numero = item["numero"]
        page_num = item["page"]
        doc_id = item["id"]
        
        pdf_name_3d = f"{langue}{annee}{int(numero):03d}.pdf" if numero.isdigit() else f"{langue}{annee}{numero}.pdf"
        dir_path = Path("downloads") / langue / str(annee)
        pdf_path = dir_path / pdf_name_3d
        if not pdf_path.exists():
            pdf_path = dir_path / f"{langue}{annee}{numero}.pdf"
            
        if not pdf_path.exists():
            print(f"[ERREUR] PDF introuvable: {pdf_path}")
            continue
            
        doc = pymupdf.open(pdf_path)
        if page_num > len(doc):
            print(f"[ERREUR] Page {page_num} dépasse la taille du document ({len(doc)} pages)")
            doc.close()
            continue
            
        page = doc[page_num - 1]
        
        # Rendu 300 DPI haute résolution
        pix = page.get_pixmap(dpi=300)
        img_filename = f"{doc_id}_{langue}_{annee}_{numero}_p{page_num}.png"
        img_path = out_dir / img_filename
        pix.save(img_path)
        
        doc.close()
        
        item_data = dict(item)
        item_data["image_path"] = str(img_path)
        item_data["image_width"] = pix.width
        item_data["image_height"] = pix.height
        extracted_manifest.append(item_data)
        
        print(f"[{doc_id}] Extrait {langue} {annee}-{numero} p.{page_num} -> {img_filename} ({pix.width}x{pix.height} px)")
        
    manifest_file = Path("benchmark") / "manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(extracted_manifest, f, indent=2, ensure_ascii=False)
        
    print(f"\nManifest de 30 pages sauvegardé dans {manifest_file}")
    return extracted_manifest

if __name__ == "__main__":
    extract_30_benchmark_images()
