"""
Relance la découverte AR uniquement à partir de 1968 (FR déjà terminé)
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient
from database import JoradpDatabase
from discover import JoradpDiscoverer


def discover_ar_from(start_year: int = 1968):
    """
    Lance la découverte AR uniquement à partir de l'année spécifiée.
    """
    db = JoradpDatabase("joradp.db")
    with db:
        db.initialize_schema()
    
    with JoradpClient() as client:
        discoverer = JoradpDiscoverer(db, client)
        
        # Plage AR : 1964 à 2026 selon Project_Plan.md
        ar_range = range(start_year, 2027)  # 1968 à 2026 inclus
        
        print("=" * 80)
        print(f"DÉCOUVERTE AR - À partir de {start_year}")
        print("=" * 80)
        print(f"AR : {min(ar_range)} à {max(ar_range)} ({len(ar_range)} années)")
        print()
        
        ar_total = 0
        for annee in ar_range:
            print(f"\n--- AR {annee} ---")
            count = discoverer.discover_annual_index("AR", annee)
            ar_total += count
            print(f"AR {annee}: {count} numéros")
        
        print(f"\nTotal AR (depuis {start_year}): {ar_total} numéros")
        
        return ar_total


if __name__ == "__main__":
    print("RELANCE AR OPTIMISÉE")
    print("FR déjà terminé (65 années)")
    print("Relance AR à partir de 1968 (4 premières années déjà traitées)")
    print()
    
    total = discover_ar_from(1968)
    
    # Rapport de couverture
    print("\n" + "=" * 80)
    print("RAPPORT DE COUVERTURE FINAL")
    print("=" * 80)
    
    db = JoradpDatabase()
    with db:
        report = db.get_coverage_report()
        print(f"Total sources en base: {report['total_sources']}")
        print(f"  Téléchargées: {report['downloaded']}")
        print(f"  Validées: {report['validated']}")
        print(f"  Erreurs: {report['errors']}")
        
        # Statistiques par langue
        fr_count = sum(1 for cov in report['coverage_by_year_langue'] if cov['langue'] == 'FR')
        ar_count = sum(1 for cov in report['coverage_by_year_langue'] if cov['langue'] == 'AR')
        print(f"\nAnnées traitées:")
        print(f"  FR: {fr_count} années")
        print(f"  AR: {ar_count} années")