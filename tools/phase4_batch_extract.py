"""
Script d'extraction massive par lots - Phase 4 (JORADP)
Traite l'ensemble du corpus (10 432 PDF) avec reprise automatique,
stockage granulaire dans page_extractions et suivi dans sources.
"""

import sys
import os
import time
import argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple
import sqlite3

# Force UTF-8 console output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(str(Path(__file__).parent))

from database import JoradpDatabase
from phase4_extractor import Phase4Extractor, PageClassification


def process_single_pdf_worker(task_info: Tuple[int, int, str, str, str, str]) -> Dict[str, Any]:
    """Worker fonction pour exécuter l'extraction d'un PDF dans un sous-processus."""
    source_id, annee, numero, langue, type_source, downloads_dir = task_info
    
    extractor = Phase4Extractor(downloads_dir=downloads_dir)
    
    pdf_name_3d = f"{langue}{annee}{int(numero):03d}.pdf" if numero.isdigit() else f"{langue}{annee}{numero}.pdf"
    pdf_name_orig = f"{langue}{annee}{numero}.pdf"
    
    dir_path = Path(downloads_dir) / langue / str(annee)
    pdf_path = dir_path / pdf_name_3d
    if not pdf_path.exists():
        pdf_path = dir_path / pdf_name_orig
        
    if not pdf_path.exists():
        return {
            "source_id": source_id,
            "success": False,
            "error": f"Fichier introuvable: {pdf_path}"
        }
        
    res = extractor.extract_pdf_file(pdf_path, langue)
    if not res.get("success"):
        return {
            "source_id": source_id,
            "success": False,
            "error": res.get("error")
        }
        
    return {
        "source_id": source_id,
        "success": True,
        "total_pages": res["total_pages"],
        "overall_status": res["overall_status"],
        "types_count": res["types_count"],
        "pages": res["pages"]
    }


class BatchExtractor:
    """Orchestrateur d'extraction par lots pour JORADP."""
    
    def __init__(self, db_path: str = "joradp.db", downloads_dir: str = "downloads", num_workers: int = 4):
        self.db_path = db_path
        self.downloads_dir = downloads_dir
        self.num_workers = num_workers

    def get_pending_sources(self, langue: str = None, annee_min: int = None, annee_max: int = None, limit: int = None) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        query = "SELECT id, annee, numero, langue, type FROM sources WHERE statut = 'telecharge' AND (extraction_statut IS NULL OR extraction_statut = 'non_extrait')"
        params = []
        
        if langue:
            query += " AND langue = ?"
            params.append(langue)
        if annee_min is not None:
            query += " AND annee >= ?"
            params.append(annee_min)
        if annee_max is not None:
            query += " AND annee <= ?"
            params.append(annee_max)
            
        query += " ORDER BY annee DESC, numero ASC"
        
        if limit:
            query += f" LIMIT {limit}"
            
        sources = [dict(row) for row in conn.execute(query, params).fetchall()]
        conn.close()
        return sources

    def save_batch_results(self, batch_results: List[Dict[str, Any]]):
        """Enregistre un lot complet de résultats en une seule transaction SQLite."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        cursor = conn.cursor()
        
        import json
        for res in batch_results:
            source_id = res["source_id"]
            if not res.get("success"):
                cursor.execute("UPDATE sources SET extraction_statut = 'erreur_technique', erreur = ? WHERE id = ?",
                               (res.get("error"), source_id))
                continue
                
            overall_status = res["overall_status"]
            cursor.execute("UPDATE sources SET extraction_statut = ?, date_extraction = CURRENT_TIMESTAMP WHERE id = ?",
                           (overall_status, source_id))
                           
            for p in res.get("pages", []):
                flags_json = json.dumps(p.get("quality_flags", {}), ensure_ascii=False)
                cursor.execute("""
                    INSERT INTO page_extractions 
                    (source_id, page_numero, page_type, total_chars, arabic_chars, latin_chars,
                     digit_chars, arabic_ratio, suspect_latin_count, has_images, texte_extrait,
                     methode_extraction, quality_score, quality_flags, date_extraction)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(source_id, page_numero) DO UPDATE SET
                        page_type = excluded.page_type,
                        total_chars = excluded.total_chars,
                        arabic_chars = excluded.arabic_chars,
                        latin_chars = excluded.latin_chars,
                        digit_chars = excluded.digit_chars,
                        arabic_ratio = excluded.arabic_ratio,
                        suspect_latin_count = excluded.suspect_latin_count,
                        has_images = excluded.has_images,
                        texte_extrait = excluded.texte_extrait,
                        methode_extraction = excluded.methode_extraction,
                        quality_score = excluded.quality_score,
                        quality_flags = excluded.quality_flags,
                        date_extraction = CURRENT_TIMESTAMP
                """, (source_id, p["page_num"], p["page_type"], p["total_chars"],
                      p["arabic_chars"], p["latin_chars"], p["digit_chars"],
                      p["arabic_ratio"], p["suspect_latin_count"], p["has_images"],
                      p["extracted_text"], p["methode"], p["quality_score"], flags_json))
                      
        conn.commit()
        conn.close()

    def run(self, langue: str = None, annee_min: int = None, annee_max: int = None, limit: int = None, batch_size: int = 50, dry_run: bool = False):
        print("=" * 80)
        print("EXTRACTION MASSIVE PAR LOTS - PHASE 4 (JORADP)")
        print("=" * 80)
        
        sources = self.get_pending_sources(langue=langue, annee_min=annee_min, annee_max=annee_max, limit=limit)
        total_sources = len(sources)
        
        if total_sources == 0:
            print("Aucune source en attente d'extraction.")
            return
            
        print(f"Sources à traiter : {total_sources} PDF (Workers : {self.num_workers}, Lot : {batch_size})")
        if dry_run:
            print("[MODE DRY-RUN] Aucune écriture dans la base de données ne sera effectuée.")
            
        start_time = time.time()
        processed_count = 0
        total_pages_count = 0
        errors_count = 0
        
        tasks = [(s["id"], s["annee"], s["numero"], s["langue"], s["type"], self.downloads_dir) for s in sources]
        
        # Traitement par lots pour gérer la mémoire et enregistrer au fur et à mesure
        for i in range(0, total_sources, batch_size):
            batch_tasks = tasks[i:i + batch_size]
            batch_results = []
            
            if self.num_workers > 1:
                with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
                    futures = [executor.submit(process_single_pdf_worker, t) for t in batch_tasks]
                    for future in as_completed(futures):
                        res = future.result()
                        batch_results.append(res)
            else:
                for t in batch_tasks:
                    batch_results.append(process_single_pdf_worker(t))
                    
            if not dry_run:
                self.save_batch_results(batch_results)
                
            # Calcul des métriques du lot
            for r in batch_results:
                if r.get("success"):
                    total_pages_count += r.get("total_pages", 0)
                else:
                    errors_count += 1
            processed_count += len(batch_results)
            
            elapsed = time.time() - start_time
            rate_docs = processed_count / elapsed if elapsed > 0 else 0
            rate_pages = total_pages_count / elapsed if elapsed > 0 else 0
            
            print(f"Progression : {processed_count}/{total_sources} PDF ({(processed_count/total_sources)*100:.1f}%) | "
                  f"Pages : {total_pages_count:,} | Erreurs : {errors_count} | "
                  f"Vitesse : {rate_docs:.1f} PDF/s ({rate_pages:.0f} p/s)")

        total_elapsed = time.time() - start_time
        print("\n" + "=" * 80)
        print("EXTRACTION TERMINÉE AVEC SUCCÈS")
        print("=" * 80)
        print(f"Total documents traités : {processed_count}")
        print(f"Total pages extraites   : {total_pages_count:,}")
        print(f"Erreurs techniques      : {errors_count}")
        print(f"Temps total écoulé      : {total_elapsed:.1f} secondes ({total_elapsed/60:.1f} min)")


def main():
    parser = argparse.ArgumentParser(description="Extraction massive de texte JORADP - Phase 4")
    parser.add_argument("--langue", choices=["FR", "AR"], help="Filtrer par langue")
    parser.add_argument("--annee-min", type=int, help="Année minimum")
    parser.add_argument("--annee-max", type=int, help="Année maximum")
    parser.add_argument("--limit", type=int, help="Nombre max de PDF à traiter")
    parser.add_argument("--batch-size", type=int, default=50, help="Taille des lots (défaut: 50)")
    parser.add_argument("--workers", type=int, default=4, help="Nombre de workers parallèles (défaut: 4)")
    parser.add_argument("--dry-run", action="store_true", help="Tester sans enregistrer dans la DB")
    
    args = parser.parse_args()
    
    extractor = BatchExtractor(num_workers=args.workers)
    extractor.run(
        langue=args.langue,
        annee_min=args.annee_min,
        annee_max=args.annee_max,
        limit=args.limit,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
