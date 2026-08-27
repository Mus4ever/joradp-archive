"""
Extraction de texte natif avec PyMuPDF (fitz) page par page
Phase 4 - Extraction sur échantillon 50 PDF avant extension complète
"""

import sys
sys.path.append('tools')

import pymupdf
from pathlib import Path
from database import JoradpDatabase
import statistics

class NativeTextExtractor:
    """Extracteur de texte natif avec PyMuPDF."""
    
    def __init__(self, db: JoradpDatabase, downloads_dir: str = "downloads"):
        self.db = db
        self.downloads_dir = Path(downloads_dir)
    
    def extract_pdf(self, source_id: int, annee: int, numero: str, langue: str) -> dict:
        """
        Extrait le texte natif d'un PDF page par page.
        
        Returns:
            dict: {total_pages, total_chars, chars_per_page, pages_with_text, needs_ocr_candidates}
        """
        pdf_path = self.downloads_dir / langue / str(annee) / f"{langue}{annee}{numero}.pdf"
        
        if not pdf_path.exists():
            return {"error": "PDF not found"}
        
        try:
            doc = pymupdf.open(pdf_path)
            total_pages = len(doc)
            total_chars = 0
            chars_per_page = []
            pages_with_text = 0
            needs_ocr_candidates = []
            
            for page_num in range(total_pages):
                page = doc[page_num]
                text = page.get_text()
                
                # Stocke l'extraction dans la base
                with self.db:
                    conn = self.db.connect()
                    conn.execute("""
                        INSERT INTO extractions 
                        (source_id, page_numero, texte_natif, methode_extraction)
                        VALUES (?, ?, ?, ?)
                    """, (source_id, page_num + 1, text, "native_pymupdf"))
                    conn.commit()
                
                char_count = len(text.strip())
                total_chars += char_count
                chars_per_page.append(char_count)
                
                if char_count > 0:
                    pages_with_text += 1
                else:
                    needs_ocr_candidates.append(page_num + 1)
            
            doc.close()
            
            # Calcul des métriques
            avg_chars_per_page = statistics.mean(chars_per_page) if chars_per_page else 0
            median_chars_per_page = statistics.median(chars_per_page) if chars_per_page else 0
            
            return {
                "total_pages": total_pages,
                "total_chars": total_chars,
                "chars_per_page": chars_per_page,
                "avg_chars_per_page": avg_chars_per_page,
                "median_chars_per_page": median_chars_per_page,
                "pages_with_text": pages_with_text,
                "needs_ocr_candidates": needs_ocr_candidates,
                "success": True
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_sample_pdfs(self, sample_size: int = 50) -> list:
        """
        Sélectionne un échantillon de PDF pour test.
        
        Répartis: FR/AR, toutes décennies
        """
        with self.db:
            conn = self.db.connect()
            
            # Sélectionne 25 FR + 25 AR répartis sur les décennies
            decades = [(1960, 1969), (1970, 1979), (1980, 1989), (1990, 1999), (2000, 2009), (2010, 2019), (2020, 2029)]
            languages = ['FR', 'AR']
            
            sample = []
            for (start_year, end_year), langue in [(d, l) for d in decades for l in languages]:
                # Sélectionne quelques fichiers par décennie/langue
                query = """
                    SELECT id, annee, numero, langue
                    FROM sources 
                    WHERE langue = ? 
                    AND annee BETWEEN ? AND ?
                    AND statut = 'telecharge'
                    ORDER BY RANDOM()
                    LIMIT 3
                """
                files = conn.execute(query, (langue, start_year, end_year)).fetchall()
                sample.extend(files)
            
            # Limite à sample_size
            return sample[:sample_size]


def main():
    """Test sur échantillon 50 PDF."""
    
    print("EXTRACTION DE TEXTE NATIF - ÉCHANTILLON 50 PDF")
    print("=" * 80)
    
    db = JoradpDatabase()
    extractor = NativeTextExtractor(db)
    
    # Sélectionne l'échantillon
    sample = extractor.get_sample_pdfs(50)
    print(f"Échantillon sélectionné: {len(sample)} PDF")
    print()
    
    # Extraction
    results = []
    for source in sample:
        source_id, annee, numero, langue = source
        
        print(f"Extraction: {langue} {annee}-{numero}")
        result = extractor.extract_pdf(source_id, annee, numero, langue)
        
        if result.get("success"):
            results.append({
                "langue": langue,
                "annee": annee,
                "numero": numero,
                **result
            })
            print(f"  OK: {result['total_pages']} pages, {result['total_chars']} caractères")
        else:
            print(f"  ERROR: {result.get('error')}")
    
    print()
    print("=" * 80)
    print("ANALYSE DES RÉSULTATS")
    print("-" * 80)
    
    # Statistiques globales
    total_pages = sum(r['total_pages'] for r in results)
    total_chars = sum(r['total_chars'] for r in results)
    avg_chars_per_page = statistics.mean([r['avg_chars_per_page'] for r in results])
    median_chars_per_page = statistics.median([r['median_chars_per_page'] for r in results])
    
    print(f"Total pages extraites: {total_pages}")
    print(f"Total caractères extraits: {total_chars:,}")
    print(f"Moyenne caractères/page: {avg_chars_per_page:.0f}")
    print(f"Médiane caractères/page: {median_chars_per_page:.0f}")
    
    print()
    print("DISTRIBUTION PAR LANGUE:")
    for langue in ['FR', 'AR']:
        langue_results = [r for r in results if r['langue'] == langue]
        if langue_results:
            total = sum(r['total_chars'] for r in langue_results)
            avg = statistics.mean([r['avg_chars_per_page'] for r in langue_results])
            print(f"  {langue}: {len(langue_results)} PDF, {total:,} caractères, {avg:.0f}/page")
    
    print()
    print("DISTRIBUTION PAR DÉCENNIE:")
    decades = [(1960, 1969), (1970, 1979), (1980, 1989), (1990, 1999), (2000, 2009), (2010, 2019), (2020, 2029)]
    for start, end in decades:
        decade_results = [r for r in results if start <= r['annee'] <= end]
        if decade_results:
            total = sum(r['total_chars'] for r in decade_results)
            avg = statistics.mean([r['avg_chars_per_page'] for r in decade_results])
            print(f"  {start}s: {len(decade_results)} PDF, {total:,} caractères, {avg:.0f}/page")
    
    print()
    print("CONCLUSION:")
    print("Échantillon traité avec succès. Analyse pour seuil needs_OCR à suivre.")

if __name__ == "__main__":
    main()