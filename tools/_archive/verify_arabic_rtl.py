"""
Vérification de l'ordre de lecture RTL pour le texte arabe natif
Échantillon 25 PDF arabes répartis sur toute la période
"""

import sys
sys.path.append('tools')

import pymupdf
from pathlib import Path
from database import JoradpDatabase
import re

class ArabicRTLVerifier:
    """Vérificateur de l'ordre de lecture RTL pour l'arabe."""
    
    def __init__(self, db: JoradpDatabase, downloads_dir: str = "downloads"):
        self.db = db
        self.downloads_dir = Path(downloads_dir)
    
    def extract_and_analyze_arabic(self, source_id: int, annee: int, numero: str) -> dict:
        """
        Extrait et analyse le texte arabe pour vérifier l'ordre RTL.
        
        Returns:
            dict: {page_count, text_samples, rtl_issues, order_correct}
        """
        pdf_path = self.downloads_dir / "AR" / str(annee) / f"AR{annee}{numero}.pdf"
        
        if not pdf_path.exists():
            return {"error": "PDF not found"}
        
        try:
            doc = pymupdf.open(pdf_path)
            page_count = len(doc)
            text_samples = []
            rtl_issues = []
            
            # Analyse les 3 premières pages
            for page_num in range(min(3, page_count)):
                page = doc[page_num]
                text = page.get_text()
                
                if len(text.strip()) > 100:  # Texte suffisant pour analyse
                    text_samples.append({
                        "page": page_num + 1,
                        "text": text[:500],  # Échantillon de 500 caractères
                        "length": len(text)
                    })
                    
                    # Heuristiques de détection de désordre RTL
                    issues = self.detect_rtl_issues(text)
                    if issues:
                        rtl_issues.extend([{"page": page_num + 1, "issue": issue} for issue in issues])
            
            doc.close()
            
            return {
                "page_count": page_count,
                "text_samples": text_samples,
                "rtl_issues": rtl_issues,
                "order_correct": len(rtl_issues) == 0
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def detect_rtl_issues(self, text: str) -> list:
        """
        Détecte des problèmes potentiels d'ordre RTL.
        
        Heuristiques:
        - Blocs français intercalés anormalement dans texte arabe
        - Numéros de page/article à positions anormales
        - Caractères arabe hors contexte logique
        """
        issues = []
        
        # Détection de blocs français anormaux
        french_words = re.findall(r'\b[A-Za-z]{3,}\b', text)
        if len(french_words) > 5:  # Beaucoup de mots français dans texte arabe
            issues.append(f"French words detected: {len(french_words)}")
        
        # Détection de numéros à positions suspectes
        numbers = re.findall(r'\d+', text)
        if len(numbers) > 10:
            issues.append(f"Many numbers detected: {len(numbers)}")
        
        # Détection de caractères arabe dans patterns suspectes
        arabic_chars = re.findall(r'[\u0600-\u06FF]', text)
        if len(arabic_chars) < 10 and len(text) > 100:
            issues.append(f"Few Arabic chars for text length: {len(arabic_chars)}")
        
        return issues
    
    def get_arabic_sample(self, count: int = 25) -> list:
        """
        Sélectionne un échantillon de PDF arabes répartis sur toute la période.
        
        Répartition: legacy 1964-1993, ère PDF complet 1994-2009, récent 2010-2026
        """
        with self.db:
            conn = self.db.connect()
            
            sample = []
            
            # Legacy 1964-1993 (8 PDF)
            query = """
                SELECT id, annee, numero
                FROM sources 
                WHERE langue = 'AR' 
                AND annee BETWEEN 1964 AND 1993
                AND statut = 'telecharge'
                ORDER BY RANDOM()
                LIMIT 8
            """
            sample.extend(conn.execute(query).fetchall())
            
            # Ère complet 1994-2009 (8 PDF)
            query = """
                SELECT id, annee, numero
                FROM sources 
                WHERE langue = 'AR' 
                AND annee BETWEEN 1994 AND 2009
                AND statut = 'telecharge'
                ORDER BY RANDOM()
                LIMIT 8
            """
            sample.extend(conn.execute(query).fetchall())
            
            # Récent 2010-2026 (9 PDF)
            query = """
                SELECT id, annee, numero
                FROM sources 
                WHERE langue = 'AR' 
                AND annee BETWEEN 2010 AND 2026
                AND statut = 'telecharge'
                ORDER BY RANDOM()
                LIMIT 9
            """
            sample.extend(conn.execute(query).fetchall())
            
            return sample


def main():
    """Vérification RTL sur échantillon 25 PDF arabes."""
    
    print("VERIFICATION ORDRE DE LECTURE RTL - ARABE")
    print("=" * 80)
    
    db = JoradpDatabase()
    verifier = ArabicRTLVerifier(db)
    
    # Sélectionne l'échantillon
    sample = verifier.get_arabic_sample(25)
    print(f"Échantillon sélectionné: {len(sample)} PDF arabes")
    print()
    
    # Analyse
    results = []
    for source in sample:
        source_id, annee, numero = source
        
        print(f"Analyse: AR {annee}-{numero}")
        result = verifier.extract_and_analyze_arabic(source_id, annee, numero)
        
        if not result.get("error"):
            results.append({
                "annee": annee,
                "numero": numero,
                **result
            })
            
            if result["order_correct"]:
                print(f"  OK: {result['page_count']} pages, ordre RTL correct")
            else:
                print(f"  ISSUE: {result['page_count']} pages, {len(result['rtl_issues'])} problèmes RTL")
                for issue in result['rtl_issues']:
                    print(f"    - {issue}")
        else:
            print(f"  ERROR: {result.get('error')}")
    
    print()
    print("=" * 80)
    print("ANALYSE GLOBALE")
    print("-" * 80)
    
    # Statistiques
    total_analyzed = len(results)
    correct_order = sum(1 for r in results if r["order_correct"])
    incorrect_order = total_analyzed - correct_order
    
    print(f"Total analysés: {total_analyzed}")
    print(f"Ordre RTL correct: {correct_order}")
    print(f"Ordre RTL incorrect: {incorrect_order}")
    
    # Par période
    print()
    print("PAR PÉRIODE:")
    periods = [
        ("Legacy 1964-1993", 1964, 1993),
        ("Ère complet 1994-2009", 1994, 2009),
        ("Récent 2010-2026", 2010, 2026)
    ]
    
    for period_name, start, end in periods:
        period_results = [r for r in results if start <= r["annee"] <= end]
        if period_results:
            correct = sum(1 for r in period_results if r["order_correct"])
            print(f"  {period_name}: {correct}/{len(period_results)} corrects")
    
    print()
    print("CONCLUSION:")
    if incorrect_order == 0:
        print("Tous les échantillons ont un ordre RTL correct.")
        print("Extension à l'ensemble des PDF arabes peut continuer.")
    else:
        print(f"{incorrect_order} échantillons ont des problèmes RTL.")
        print("Correction nécessaire avant extension complète.")

if __name__ == "__main__":
    main()