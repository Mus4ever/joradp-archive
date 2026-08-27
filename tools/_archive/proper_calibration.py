"""
Calibration PROPRE du seuil needs_ocr
Échantillon dédié 30 PDF scannés + 30 PDF natifs (étiquetés à l'avance)
"""

import sys
sys.path.append('tools')

import pymupdf
from pathlib import Path
from database import JoradpDatabase
import statistics

class ProperOCRCalibrator:
    """Calibrateur PROPRE avec échantillon dédié étiqueté à l'avance."""
    
    def __init__(self, db: JoradpDatabase, downloads_dir: str = "downloads"):
        self.db = db
        self.downloads_dir = Path(downloads_dir)
    
    def analyze_pdf_chars_per_page(self, source_id: int, annee: int, numero: str, langue: str) -> dict:
        """Analyse un PDF et retourne les caractères par page."""
        pdf_path = self.downloads_dir / langue / str(annee) / f"{langue}{annee}{numero}.pdf"
        
        if not pdf_path.exists():
            return {"error": "PDF not found"}
        
        try:
            doc = pymupdf.open(pdf_path)
            chars_per_page = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                chars_per_page.append(len(text.strip()))
            
            doc.close()
            
            return {
                "total_pages": len(chars_per_page),
                "chars_per_page": chars_per_page,
                "avg_chars_per_page": statistics.mean(chars_per_page) if chars_per_page else 0,
                "median_chars_per_page": statistics.median(chars_per_page) if chars_per_page else 0,
                "min_chars_per_page": min(chars_per_page) if chars_per_page else 0,
                "max_chars_per_page": max(chars_per_page) if chars_per_page else 0
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_known_scanned_samples(self, count: int = 30) -> list:
        """
        Sélectionne 30 PDF connus comme scannés (étiquetés à l'avance).
        
        Critère: années 1960-1995 (historiquement des scans)
        """
        with self.db:
            conn = self.db.connect()
            
            query = """
                SELECT id, annee, numero, langue
                FROM sources 
                WHERE annee BETWEEN 1960 AND 1995
                AND statut = 'telecharge'
                ORDER BY RANDOM()
                LIMIT ?
            """
            return conn.execute(query, (count,)).fetchall()
    
    def get_known_native_samples(self, count: int = 30) -> list:
        """
        Sélectionne 30 PDF connus comme texte natif (étiquetés à l'avance).
        
        Critère: années 2015-2026 (historiquement texte natif)
        """
        with self.db:
            conn = self.db.connect()
            
            query = """
                SELECT id, annee, numero, langue
                FROM sources 
                WHERE annee BETWEEN 2015 AND 2026
                AND statut = 'telecharge'
                ORDER BY RANDOM()
                LIMIT ?
            """
            return conn.execute(query, (count,)).fetchall()
    
    def calculate_threshold_performance(self, threshold: int, scanned_results: list, native_results: list) -> dict:
        """
        Calcule le taux d'erreur pour un seuil donné.
        
        Returns:
            dict: {false_positives, false_negatives, accuracy, error_rate}
        """
        # Scanned = should be < threshold
        false_positives = sum(1 for r in scanned_results if r['avg_chars_per_page'] >= threshold)
        
        # Native = should be >= threshold
        false_negatives = sum(1 for r in native_results if r['avg_chars_per_page'] < threshold)
        
        total = len(scanned_results) + len(native_results)
        accuracy = (total - false_positives - false_negatives) / total
        error_rate = (false_positives + false_negatives) / total
        
        return {
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "accuracy": accuracy,
            "error_rate": error_rate
        }


def main():
    """Calibration PROPRE avec échantillon dédié."""
    
    print("CALIBRATION PROPRE DU SEUIL NEEDS_OCR")
    print("=" * 80)
    print("Échantillon dédié: 30 PDF scannés + 30 PDF natifs (étiquetés à l'avance)")
    print()
    
    db = JoradpDatabase()
    calibrator = ProperOCRCalibrator(db)
    
    # Échantillon 30 PDF scannés (étiquetés à l'avance: 1960-1995)
    print("ÉCHANTILLON SCANNÉS (étiquetés à l'avance: 1960-1995)")
    print("-" * 80)
    
    scanned_samples = calibrator.get_known_scanned_samples(30)
    scanned_results = []
    
    for source in scanned_samples:
        source_id, annee, numero, langue = source
        result = calibrator.analyze_pdf_chars_per_page(source_id, annee, numero, langue)
        
        if not result.get("error"):
            scanned_results.append(result)
            print(f"{langue} {annee}-{numero}: {result['avg_chars_per_page']:.0f} chars/page (pages: {result['total_pages']})")
    
    print()
    print("STATISTIQUES SCANNÉS:")
    if scanned_results:
        avg = statistics.mean([r['avg_chars_per_page'] for r in scanned_results])
        median = statistics.median([r['avg_chars_per_page'] for r in scanned_results])
        max_val = max([r['max_chars_per_page'] for r in scanned_results])
        print(f"Moyenne: {avg:.0f} chars/page")
        print(f"Médiane: {median:.0f} chars/page")
        print(f"Maximum: {max_val:.0f} chars/page")
    
    print()
    print("ÉCHANTILLON TEXTE NATIF (étiquetés à l'avance: 2015-2026)")
    print("-" * 80)
    
    native_samples = calibrator.get_known_native_samples(30)
    native_results = []
    
    for source in native_samples:
        source_id, annee, numero, langue = source
        result = calibrator.analyze_pdf_chars_per_page(source_id, annee, numero, langue)
        
        if not result.get("error"):
            native_results.append(result)
            print(f"{langue} {annee}-{numero}: {result['avg_chars_per_page']:.0f} chars/page (pages: {result['total_pages']})")
    
    print()
    print("STATISTIQUES TEXTE NATIF:")
    if native_results:
        avg = statistics.mean([r['avg_chars_per_page'] for r in native_results])
        median = statistics.median([r['avg_chars_per_page'] for r in native_results])
        min_val = min([r['min_chars_per_page'] for r in native_results])
        print(f"Moyenne: {avg:.0f} chars/page")
        print(f"Médiane: {median:.0f} chars/page")
        print(f"Minimum: {min_val:.0f} chars/page")
    
    print()
    print("CALIBRATION DU SEUIL 1161 SUR ÉCHANTILLON DÉDIÉ")
    print("-" * 80)
    
    if scanned_results and native_results:
        performance = calibrator.calculate_threshold_performance(1161, scanned_results, native_results)
        
        print(f"Seuil testé: 1161 caractères/page")
        print(f"Faux positifs (scannés classés natifs): {performance['false_positives']}/{len(scanned_results)}")
        print(f"Faux négatifs (natifs classés scannés): {performance['false_negatives']}/{len(native_results)}")
        print(f"Précision: {performance['accuracy']:.2%}")
        print(f"Taux d'erreur: {performance['error_rate']:.2%}")
        
        if performance['error_rate'] == 0:
            print("\nSeuil 1161: PARFAIT sur cet échantillon (0% erreur)")
        else:
            print(f"\nSeuil 1161: {performance['error_rate']:.2%} erreur - ajustement nécessaire")
            
            # Suggère un meilleur seuil
            max_scanned = max([r['max_chars_per_page'] for r in scanned_results])
            min_native = min([r['min_chars_per_page'] for r in native_results])
            
            if min_native > max_scanned:
                suggested = (max_scanned + min_native) / 2
                print(f"Seuil suggéré alternatif: {suggested:.0f} chars/page")

if __name__ == "__main__":
    main()