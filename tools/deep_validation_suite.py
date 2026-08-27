"""
Suite de vérification expérimentale approfondie pour la Phase 4 :
- Analyse empirique de 10 pages SCAN_NO_TEXT
- Analyse empirique et typographique de 10 pages CORRUPT_MAPPING
- Analyse comparative de 10 pages NATIVE_RTL_REORDER
- Mesures de performance réelles et reproductibles
"""

import sys
import os
import time
from pathlib import Path
import json
import pymupdf

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(str(Path(__file__).parent))

from database import JoradpDatabase
from phase4_extractor import Phase4Extractor, PageClassification


def deep_investigate_scans():
    """Analyse 10 pages de SCAN_NO_TEXT de différentes décennies."""
    print("\n" + "=" * 80)
    print("2. VALIDATION DES PAGES SCAN_NO_TEXT (10 ÉCHANTILLONS)")
    print("=" * 80)
    
    extractor = Phase4Extractor(downloads_dir="downloads")
    
    # 10 pages de test réparties sur 1963-2002
    test_scan_targets = [
        ("FR", 1963, "001", 1),
        ("FR", 1965, "027", 3),
        ("FR", 1970, "011", 2),
        ("FR", 1979, "028", 5),
        ("FR", 1986, "026", 4),
        ("FR", 1998, "052", 2),
        ("AR", 1965, "078", 1),
        ("AR", 1974, "086", 4),
        ("AR", 1981, "006", 5),
        ("AR", 2001, "037", 5),
    ]
    
    scan_results = []
    output_dir = Path("reports") / "scan_investigation"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for langue, annee, numero, page_num in test_scan_targets:
        pdf_name_3d = f"{langue}{annee}{int(numero):03d}.pdf" if numero.isdigit() else f"{langue}{annee}{numero}.pdf"
        pdf_path = Path("downloads") / langue / str(annee) / pdf_name_3d
        if not pdf_path.exists():
            pdf_path = Path("downloads") / langue / str(annee) / f"{langue}{annee}{numero}.pdf"
            
        if not pdf_path.exists():
            print(f"[SKIP] Fichier non trouvé: {pdf_path}")
            continue
            
        doc = pymupdf.open(pdf_path)
        page = doc[page_num - 1]
        
        # 1. Rendu visuel
        pix = page.get_pixmap(dpi=150)
        img_file = output_dir / f"scan_{langue}_{annee}_{numero}_p{page_num}.png"
        pix.save(img_file)
        
        # 2. Analyse des images
        images = page.get_images()
        image_details = []
        for img in images:
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_details.append({
                "xref": xref,
                "width": base_image["width"],
                "height": base_image["height"],
                "format": base_image["ext"],
                "size_bytes": len(base_image["image"])
            })
            
        # 3. Extraction brute du texte
        raw_text = page.get_text()
        raw_blocks = page.get_text("blocks")
        text_blocks = [b for b in raw_blocks if b[6] == 0]
        
        # 4. Diagnostic avec le routeur
        char_stats = extractor.analyze_characters(raw_text)
        page_type, methode, flags = extractor.detect_page_type(page, langue, raw_text, char_stats)
        
        doc.close()
        
        # Raison de la classification
        has_full_page_image = any(img["width"] > 1000 or img["height"] > 1000 for img in image_details)
        explanation = (
            f"La page contient {len(images)} image(s) pleine-page scannée(s) (ex: {image_details[0]['width']}x{image_details[0]['height']} px) "
            f"et exactement {char_stats['total_printable']} caractères de texte natif exploitable."
        )
        
        item = {
            "doc": f"{langue} {annee}-{numero}",
            "page_num": page_num,
            "images_count": len(images),
            "image_details": image_details,
            "has_full_page_image": has_full_page_image,
            "raw_text_length": len(raw_text),
            "total_printable_chars": char_stats["total_printable"],
            "arabic_chars": char_stats["arabic_chars"],
            "latin_chars": char_stats["latin_chars"],
            "text_blocks_count": len(text_blocks),
            "classified_type": page_type,
            "methode": methode,
            "explanation": explanation,
            "image_path": str(img_file)
        }
        scan_results.append(item)
        
        print(f"[{item['doc']} p.{page_num}] {page_type} -> Images: {len(images)}, Caractères natifs: {char_stats['total_printable']}")
        print(f"  Raison: {explanation}")
        
    return scan_results


def deep_investigate_corrupt_mapping():
    """Analyse 10 pages de CORRUPT_MAPPING."""
    print("\n" + "=" * 80)
    print("3. VALIDATION DES PAGES CORRUPT_MAPPING (10 ÉCHANTILLONS)")
    print("=" * 80)
    
    extractor = Phase4Extractor(downloads_dir="downloads")
    
    # Échantillon de documents arabes 2003-2005 connus pour ToUnicode corrompu
    corrupt_targets = [
        ("AR", 2005, "042", 1),
        ("AR", 2005, "042", 5),
        ("AR", 2005, "042", 10),
        ("AR", 2005, "049", 2),
        ("AR", 2005, "049", 6),
        ("AR", 2003, "032", 3),
        ("AR", 2003, "032", 8),
        ("AR", 2005, "050", 4),
        ("AR", 2005, "050", 12),
        ("AR", 2004, "015", 3),
    ]
    
    output_dir = Path("reports") / "corrupt_investigation"
    output_dir.mkdir(parents=True, exist_ok=True)
    corrupt_results = []
    
    for langue, annee, numero, page_num in corrupt_targets:
        pdf_name_3d = f"{langue}{annee}{int(numero):03d}.pdf" if numero.isdigit() else f"{langue}{annee}{numero}.pdf"
        pdf_path = Path("downloads") / langue / str(annee) / pdf_name_3d
        if not pdf_path.exists():
            pdf_path = Path("downloads") / langue / str(annee) / f"{langue}{annee}{numero}.pdf"
            
        if not pdf_path.exists():
            continue
            
        doc = pymupdf.open(pdf_path)
        if page_num > len(doc):
            doc.close()
            continue
            
        page = doc[page_num - 1]
        
        # Rendu visuel
        pix = page.get_pixmap(dpi=150)
        img_file = output_dir / f"corrupt_{langue}_{annee}_{numero}_p{page_num}.png"
        pix.save(img_file)
        
        # Analyse des polices (fonts)
        fonts = page.get_fonts()
        font_info = []
        for f in fonts:
            font_info.append({
                "xref": f[0],
                "name": f[3],
                "type": f[2],
                "encoding": f[4],
                "to_unicode": f[5]
            })
            
        # Extraction du texte
        raw_text = page.get_text()
        raw_dict = page.get_text("dict")
        
        char_stats = extractor.analyze_characters(raw_text)
        page_type, methode, flags = extractor.detect_page_type(page, langue, raw_text, char_stats)
        
        # Analyse de la cause
        # Est-ce un encodage propriétaire sans table ToUnicode conforme ?
        sample_extracted = raw_text[:250].replace("\n", " ")
        
        # Détection de la cause racine
        if char_stats["arabic_chars"] == 0 and char_stats["latin_chars"] > 100:
            root_cause = "Mauvais mapping ToUnicode / Police arabe encodée avec table de glyphes latins Windows-1252"
        elif char_stats["arabic_ratio"] < 0.40:
            root_cause = "Mélange corrompu de glyphes non-standards et fragments de caractères"
        else:
            root_cause = "Police non-standard"
            
        doc.close()
        
        item = {
            "doc": f"{langue} {annee}-{numero}",
            "page_num": page_num,
            "fonts": font_info,
            "total_chars": char_stats["total_chars"],
            "arabic_chars": char_stats["arabic_chars"],
            "latin_chars": char_stats["latin_chars"],
            "arabic_ratio": char_stats["arabic_ratio"],
            "classified_type": page_type,
            "methode": methode,
            "root_cause": root_cause,
            "text_sample": sample_extracted,
            "image_path": str(img_file)
        }
        corrupt_results.append(item)
        
        print(f"[{item['doc']} p.{page_num}] {page_type} -> Arabe: {char_stats['arabic_chars']}, Latin: {char_stats['latin_chars']}, Ratio: {char_stats['arabic_ratio']:.1%}")
        print(f"  Cause racine : {root_cause}")
        print(f"  Texte extrait (corrompu) : {sample_extracted[:100]}...")
        
    return corrupt_results


def deep_investigate_rtl_reorder():
    """Analyse comparative de 10 pages NATIVE_RTL_REORDER."""
    print("\n" + "=" * 80)
    print("4. VALIDATION DES PAGES NATIVE_RTL_REORDER (10 ÉCHANTILLONS)")
    print("=" * 80)
    
    extractor = Phase4Extractor(downloads_dir="downloads")
    
    rtl_targets = [
        ("AR", 2007, "003", 5),
        ("AR", 2007, "016", 5),
        ("AR", 2007, "019", 4),
        ("AR", 2007, "034", 5),
        ("AR", 2012, "001", 5),
        ("AR", 2018, "072", 5),
        ("AR", 2010, "079", 3),
        ("AR", 2016, "021", 4),
        ("AR", 2017, "071", 6),
        ("AR", 2026, "025", 2),
    ]
    
    output_dir = Path("reports") / "rtl_investigation"
    output_dir.mkdir(parents=True, exist_ok=True)
    rtl_results = []
    
    for langue, annee, numero, page_num in rtl_targets:
        pdf_name_3d = f"{langue}{annee}{int(numero):03d}.pdf" if numero.isdigit() else f"{langue}{annee}{numero}.pdf"
        pdf_path = Path("downloads") / langue / str(annee) / pdf_name_3d
        if not pdf_path.exists():
            pdf_path = Path("downloads") / langue / str(annee) / f"{langue}{annee}{numero}.pdf"
            
        if not pdf_path.exists():
            continue
            
        doc = pymupdf.open(pdf_path)
        if page_num > len(doc):
            doc.close()
            continue
            
        page = doc[page_num - 1]
        
        # 1. Rendu visuel
        pix = page.get_pixmap(dpi=150)
        img_file = output_dir / f"rtl_{langue}_{annee}_{numero}_p{page_num}.png"
        pix.save(img_file)
        
        # 2. Extraction par défaut
        text_default = page.get_text()
        
        # 3. Extraction par blocs bruts
        blocks_raw = page.get_text("blocks")
        text_blocks = "\n".join([b[4] for b in blocks_raw if b[6] == 0])
        
        # 4. Extraction réordonnée RTL
        text_rtl, layout_info = extractor.extract_arabic_rtl_reordered(page)
        
        char_stats = extractor.analyze_characters(text_rtl)
        
        doc.close()
        
        # Comparaison et vérification
        # L'extraction RTL doit débuter par l'entête puis la colonne de droite
        snippet_default = text_default[:150].replace("\n", " ")
        snippet_rtl = text_rtl[:150].replace("\n", " ")
        
        item = {
            "doc": f"{langue} {annee}-{numero}",
            "page_num": page_num,
            "total_chars": char_stats["total_chars"],
            "arabic_chars": char_stats["arabic_chars"],
            "arabic_ratio": char_stats["arabic_ratio"],
            "columns_detected": layout_info.get("columns", 1),
            "duplicate_detected": layout_info.get("duplicate_detected", False),
            "snippet_default": snippet_default,
            "snippet_rtl": snippet_rtl,
            "image_path": str(img_file)
        }
        rtl_results.append(item)
        
        print(f"[{item['doc']} p.{page_num}] Colonnes: {item['columns_detected']} | Doublons filtrés: {item['duplicate_detected']} | Ratio Arabe: {char_stats['arabic_ratio']:.1%}")
        print(f"  Ordre RTL propre : {snippet_rtl[:100]}...")
        
    return rtl_results


def benchmark_real_performance():
    """Mesure réelle et reproductible des performances (RAM, CPU, débit)."""
    print("\n" + "=" * 80)
    print("5. MESURE RÉELLE DES PERFORMANCES DU PIPELINE")
    print("=" * 80)
    
    import psutil
    
    extractor = Phase4Extractor(downloads_dir="downloads")
    
    # Sélectionner 50 PDF récents complets
    db = JoradpDatabase("joradp.db")
    with db:
        conn = db.connect()
        sample_sources = conn.execute("""
            SELECT id, annee, numero, langue 
            FROM sources 
            WHERE statut = 'telecharge' 
            ORDER BY annee DESC, numero ASC 
            LIMIT 50
        """).fetchall()
        
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / (1024 * 1024)
    cpu_before = psutil.cpu_percent(interval=None)
    
    start_time = time.perf_counter()
    total_pages = 0
    total_chars = 0
    
    for s in sample_sources:
        langue = s["langue"]
        annee = s["annee"]
        numero = s["numero"]
        pdf_name_3d = f"{langue}{annee}{int(numero):03d}.pdf" if numero.isdigit() else f"{langue}{annee}{numero}.pdf"
        pdf_path = Path("downloads") / langue / str(annee) / pdf_name_3d
        if not pdf_path.exists():
            pdf_path = Path("downloads") / langue / str(annee) / f"{langue}{annee}{numero}.pdf"
        if not pdf_path.exists():
            continue
            
        res = extractor.extract_pdf_file(pdf_path, langue)
        if res.get("success"):
            total_pages += res["total_pages"]
            for p in res["pages"]:
                total_chars += p["total_chars"]
                
    end_time = time.perf_counter()
    total_time = end_time - start_time
    
    mem_after = process.memory_info().rss / (1024 * 1024)
    cpu_after = psutil.cpu_percent(interval=None)
    
    pdf_per_sec = len(sample_sources) / total_time if total_time > 0 else 0
    pages_per_sec = total_pages / total_time if total_time > 0 else 0
    
    perf_metrics = {
        "pdf_count": len(sample_sources),
        "total_pages": total_pages,
        "total_chars": total_chars,
        "total_time_seconds": round(total_time, 3),
        "pdf_per_second": round(pdf_per_sec, 2),
        "pages_per_second": round(pages_per_sec, 2),
        "ram_before_mb": round(mem_before, 2),
        "ram_after_mb": round(mem_after, 2),
        "ram_increase_mb": round(mem_after - mem_before, 2),
        "cpu_usage_pct": cpu_after
    }
    
    print(f"PDF testés         : {len(sample_sources)}")
    print(f"Pages traitées     : {total_pages:,}")
    print(f"Caractères extraits: {total_chars:,}")
    print(f"Temps mesuré       : {total_time:.3f} secondes")
    print(f"Débit PDF          : {pdf_per_sec:.1f} PDF / seconde")
    print(f"Débit Pages        : {pages_per_sec:.1f} Pages / seconde")
    print(f"Empreinte RAM      : {mem_after:.1f} MB (Delta: +{mem_after - mem_before:.1f} MB)")
    
    return perf_metrics


def main():
    scans = deep_investigate_scans()
    corrupt = deep_investigate_corrupt_mapping()
    rtl = deep_investigate_rtl_reorder()
    perf = benchmark_real_performance()
    
    full_report = {
        "scans_investigation": scans,
        "corrupt_mapping_investigation": corrupt,
        "rtl_investigation": rtl,
        "performance_benchmark": perf
    }
    
    out_file = Path("reports") / "phase4_deep_validation_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2, ensure_ascii=False)
        
    print(f"\nRapport complet d'investigation sauvegardé dans {out_file}")

if __name__ == "__main__":
    main()
