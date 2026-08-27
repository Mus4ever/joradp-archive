"""
Banc d'essai élargi sur 50 PDF stratifiés par décennie et langue
"""

import sys
from pathlib import Path
import json
import random
from collections import Counter

# Force UTF-8 pour Windows terminal
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(str(Path(__file__).parent))

from database import JoradpDatabase
from phase4_extractor import Phase4Extractor, PageClassification


def run_benchmark_50():
    print("=" * 80)
    print("BANC D'ESSAI ÉLARGI SUR 50 PDF STRATIFIÉS (PHASE 4)")
    print("=" * 80)
    
    db = JoradpDatabase("joradp.db")
    extractor = Phase4Extractor(downloads_dir="downloads")
    
    decades = [
        (1962, 1969),
        (1970, 1979),
        (1980, 1989),
        (1990, 1999),
        (2000, 2009),
        (2010, 2019),
        (2020, 2026)
    ]
    
    selected_sources = []
    with db:
        conn = db.connect()
        for start_y, end_y in decades:
            for langue in ["FR", "AR"]:
                # Pour chaque décennie & langue, prend 3 à 4 PDF aléatoires
                query = """
                    SELECT id, annee, numero, langue, url_complete 
                    FROM sources 
                    WHERE statut = 'telecharge' 
                      AND langue = ? 
                      AND annee BETWEEN ? AND ?
                    ORDER BY RANDOM()
                    LIMIT 4
                """
                rows = conn.execute(query, (langue, start_y, end_y)).fetchall()
                for r in rows:
                    selected_sources.append(dict(r))
                    
    # Limite à 50
    selected_sources = selected_sources[:50]
    print(f"Échantillon sélectionné : {len(selected_sources)} PDF couvrant 1962-2026 (FR & AR)")
    
    results = []
    total_pages_all = 0
    page_type_counts = Counter()
    doc_status_counts = Counter()
    
    for i, s in enumerate(selected_sources):
        langue = s["langue"]
        annee = s["annee"]
        numero = s["numero"]
        
        pdf_name_3d = f"{langue}{annee}{int(numero):03d}.pdf" if numero.isdigit() else f"{langue}{annee}{numero}.pdf"
        pdf_name_orig = f"{langue}{annee}{numero}.pdf"
        
        dir_path = Path("downloads") / langue / str(annee)
        pdf_path = dir_path / pdf_name_3d
        if not pdf_path.exists():
            pdf_path = dir_path / pdf_name_orig
            
        if not pdf_path.exists():
            continue
            
        res = extractor.extract_pdf_file(pdf_path, langue)
        if not res.get("success"):
            print(f"[{i+1}/{len(selected_sources)}] ERREUR sur {langue}{annee}-{numero}: {res.get('error')}")
            continue
            
        total_pages = res["total_pages"]
        total_pages_all += total_pages
        doc_status = res["overall_status"]
        doc_status_counts[doc_status] += 1
        
        for p in res["pages"]:
            page_type_counts[p["page_type"]] += 1
            
        results.append({
            "source_id": s["id"],
            "langue": langue,
            "annee": annee,
            "numero": numero,
            "total_pages": total_pages,
            "overall_status": doc_status,
            "types_count": res["types_count"]
        })
        
        print(f"[{i+1}/{len(selected_sources)}] {langue} {annee}-{numero} ({total_pages} p.) -> {doc_status}")
        
    print("\n" + "=" * 80)
    print("SYNTHÈSE STATISTIQUE DU BANC D'ESSAI (50 PDF)")
    print("=" * 80)
    print(f"Total documents testés : {len(results)}")
    print(f"Total pages analysées : {total_pages_all}")
    print("\n--- Répartition par Statut Document ---")
    for st, cnt in doc_status_counts.most_common():
        pct = (cnt / len(results)) * 100
        print(f"  - {st:<30}: {cnt:3d} ({pct:5.1f}%)")
        
    print("\n--- Répartition par Type de Page ---")
    for pt, cnt in page_type_counts.most_common():
        pct = (cnt / total_pages_all) * 100
        print(f"  - {pt:<24}: {cnt:5d} pages ({pct:5.1f}%)")
        
    # Enregistrement du rapport JSON
    report_path = Path("reports") / "phase4_benchmark_50.json"
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_documents": len(results),
            "total_pages": total_pages_all,
            "doc_status_distribution": dict(doc_status_counts),
            "page_type_distribution": dict(page_type_counts),
            "documents": results
        }, f, indent=2, ensure_ascii=False)
        
    print(f"\nRapport complet sauvegardé dans {report_path}")
    return results


if __name__ == "__main__":
    run_benchmark_50()
