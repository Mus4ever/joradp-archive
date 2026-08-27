"""
Calibration empirique du seuil needs_ocr
Échantillon 30 PDF scannés vs 30 PDF texte natif
"""

import sys
sys.path.append('tools')

import pymupdf
from pathlib import Path
from database import JoradpDatabase
import statistics

class OCRThresholdCalibrator:
    """Calibrateur empirique du seuil needs_ocr."""
    
    def __init__(self, db: JoradpDatabase, downloads_dir: str = "downloads"):
        self.db = db
        self.downloads_dir = Path(downloads_dir)
    
    def analyze_pdf_for_threshold(self, source_id: int, annee: int, numero: str, langue: str) -> dict:
        """
        Analyse un PDF pour déterminer s'il est scanné ou texte natif.
        
        Returns:
            dict: {total_pages, total_chars, chars_per_page, is_scan_candidate}
        """
        pdf_path = self.downloads_dir / langue / str(annee) / f"{langue}{annee}{numero}.pdf"
        
        if not pdf_path.exists():
            return {"error": "PDF not found"}
        
        try:
            doc = pymupdf.open(pdf_path)
            total_pages = len(doc)
            total_chars = 0
            chars_per_page = []
            
            for page_num in range(total_pages):
                page = doc[page_num]
                text = page.get_text()
                char_count = len(text.strip())
                total_chars += char_count
                chars_per_page.append(char_count)
            
            doc.close()
            
            # Métriques
            avg_chars_per_page = statistics.mean(chars_per_page) if chars_per_page else 0
            median_chars_per_page = statistics.median(chars_per_page) if chars_per_page else 0
            min_chars_per_page = min(chars_per_page) if chars_per_page else 0
            max_chars_per_page = max(chars_per_page) if chars_per_page else 0
            
            # Heuristique simple pour l'échantillon
            is_scan_candidate = avg_chars_per_page < 100  # À calibrer
            
            return {
                "total_pages": total_pages,
                "total_chars": total_chars,
                "chars_per_page": chars_per_page,
                "avg_chars_per_page": avg_chars_per_page,
                "median_chars_per_page": median_chars_per_page,
                "min_chars_per_page": min_chars_per_page,
                "max_chars_per_page": max_chars_per_page,
                "is_scan_candidate": is_scan_candidate
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_scan_samples(self, count: int = 30) -> list:
        """Sélectionne des PDF probablement scannés (années 1960-1999)."""
        with self.db:
            conn = self.db.connect()
            
            # Sélectionne des PDF des années 1960-1999 (probablement scannés)
            query = """
                SELECT id, annee, numero, langue
                FROM sources 
                WHERE annee BETWEEN 1960 AND 1999
                AND statut = 'telecharge'
                ORDER BY RANDOM()
                LIMIT ?
            """
            return conn.execute(query, (count,)).fetchall()
    
    def get_native_samples(self, count: int = 30) -> list:
        """Sélectionne des PDF probablement texte natif (années 2010-2026)."""
        with self.db:
            conn = self.db.connect()
            
            # Sélectionne des PDF des années 2010-2026 (probablement texte natif)
            query = """
                SELECT id, annee, numero, langue
                FROM sources 
                WHERE annee BETWEEN 2010 AND 2026
                AND statut = 'telecharge'
                ORDER BY RANDOM()
                LIMIT ?
            """
            return conn.execute(query, (count,)).fetchall()


def main():
    """Calibration empirique du seuil needs_ocr."""
    
    print("CALIBRATION EMPIRIQUE DU SEUIL NEEDS_OCR")
    print("=" * 80)
    
    db = JoradpDatabase()
    calibrator = OCRThresholdCalibrator(db)
    
    # Échantillon 30 PDF scannés (années 1960-1999)
    print("ÉCHANTILLON SCANNÉS (années 1960-1999)")
    print("-" * 80)
    
    scan_samples = calibrator.get_scan_samples(30)
    scan_results = []
    
    for source in scan_samples:
        source_id, annee, numero, langue = source
        result = calibrator.analyze_pdf_for_threshold(source_id, annee, numero, langue)
        
        if not result.get("error"):
            scan_results.append(result)
            print(f"{langue} {annee}-{numero}: {result['avg_chars_per_page']:.0f} chars/page")
    
    print()
    print("STATISTIQUES SCANNÉS:")
    print("-" * 80)
    
    if scan_results:
        scan_avg = statistics.mean([r['avg_chars_per_page'] for r in scan_results])
        scan_median = statistics.median([r['avg_chars_per_page'] for r in scan_results])
        scan_max = max([r['max_chars_per_page'] for r in scan_results])
        
        print(f"Moyenne: {scan_avg:.0f} chars/page")
        print(f"Médiane: {scan_median:.0f} chars/page")
        print(f"Maximum: {scan_max:.0f} chars/page")
    
    print()
    print("ÉCHANTILLON TEXTE NATIF (années 2010-2026)")
    print("-" * 80)
    
    native_samples = calibrator.get_native_samples(30)
    native_results = []
    
    for source in native_samples:
        source_id, annee, numero, langue = source
        result = calibrator.analyze_pdf_for_threshold(source_id, annee, numero, langue)
        
        if not result.get("error"):
            native_results.append(result)
            print(f"{langue} {annee}-{numero}: {result['avg_chars_per_page']:.0f} chars/page")
    
    print()
    print("STATISTIQUES TEXTE NATIF:")
    print("-" * 80)
    
    if native_results:
        native_avg = statistics.mean([r['avg_chars_per_page'] for r in native_results])
        native_median = statistics.median([r['avg_chars_per_page'] for r in native_results])
        native_min = min([r['min_chars_per_page'] for r in native_results])
        
        print(f"Moyenne: {native_avg:.0f} chars/page")
        print(f"Médiane: {native_median:.0f} chars/page")
        print(f"Minimum: {native_min:.0f} chars/page")
    
    print()
    print("CALIBRATION DU SEUIL:")
    print("-" * 80)
    
    if scan_results and native_results:
        # Trouve un seuil qui sépare les deux distributions
        scan_max = max([r['avg_chars_per_page'] for r in scan_results])
        native_min = min([r['avg_chars_per_page'] for r in native_results])
        
        print(f"Maximum scannés: {scan_max:.0f} chars/page")
        print(f"Minimum texte natif: {native_min:.0f} chars/page")
        
        if native_min > scan_max:
            suggested_threshold = (scan_max + native_min) / 2
            print(f"Seuil suggéré: {suggested_threshold:.0f} chars/page")
            print(f"< {suggested_threshold:.0f} = scanné (needs_ocr)")
            print(f">= {suggested_threshold:.0f} = texte natif")
        else:
            print("OVERLAP DETECTÉ - Les distributions se chevauchent")
            print("Un seuil simple ne suffira pas, analyse plus fine nécessaire")

if __name__ == "__main__":
    main()