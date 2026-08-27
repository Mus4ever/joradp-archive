"""
Découverte automatique sur la plage complète 1962-2026.

Lance la découverte pour :
- FR : 1962 à 2026
- AR : 1964 à 2026 (pas d'AR en 1962-1963)
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient
from database import JoradpDatabase
from discover import JoradpDiscoverer


def discover_full_range(test_mode=False):
    """
    Lance la découverte sur la plage complète des années disponibles.
    
    Args:
        test_mode: Si True, ne traite qu'un petit échantillon pour test
    """
    db = JoradpDatabase("joradp.db")
    with db:
        db.initialize_schema()
    
    with JoradpClient() as client:
        discoverer = JoradpDiscoverer(db, client)
        
        # Plages selon le mode
        if test_mode:
            fr_range = [2025, 2024]  # Test sur 2 années récentes
            ar_range = [2025, 2024]
            print("MODE TEST : Échantillon réduit")
        else:
            fr_range = range(1962, 2027)  # 1962 à 2026 inclus
            ar_range = range(1964, 2027)  # 1964 à 2026 inclus (pas d'AR 1962-1963)
            print("MODE COMPLET : Plage historique 1962-2026")
        
        print("=" * 80)
        print("DÉCOUVERTE AUTOMATIQUE - PLAGE COMPLÈTE")
        print("=" * 80)
        print(f"FR : {min(fr_range)} à {max(fr_range)} ({len(fr_range)} années)")
        print(f"AR : {min(ar_range)} à {max(ar_range)} ({len(ar_range)} années)")
        print(f"Total : {len(fr_range) + len(ar_range)} années à traiter")
        print()
        
        # Découverte FR
        print("=" * 80)
        print("DÉCOUVERTE FRANÇAIS")
        print("=" * 80)
        fr_total = 0
        for annee in fr_range:
            print(f"\n--- FR {annee} ---")
            count = discoverer.discover_annual_index("FR", annee)
            fr_total += count
            print(f"FR {annee}: {count} numéros")
        
        print(f"\nTotal FR: {fr_total} numéros")
        
        # Découverte AR
        print("\n" + "=" * 80)
        print("DÉCOUVERTE ARABE")
        print("=" * 80)
        ar_total = 0
        for annee in ar_range:
            print(f"\n--- AR {annee} ---")
            count = discoverer.discover_annual_index("AR", annee)
            ar_total += count
            print(f"AR {annee}: {count} numéros")
        
        print(f"\nTotal AR: {ar_total} numéros")
        
        # Total global
        print("\n" + "=" * 80)
        print("RÉSULTAT GLOBAL")
        print("=" * 80)
        print(f"Total FR: {fr_total} numéros")
        print(f"Total AR: {ar_total} numéros")
        print(f"TOTAL: {fr_total + ar_total} numéros découverts")
        
        return fr_total + ar_total


if __name__ == "__main__":
    import sys
    
    # Permet de choisir le mode via argument
    test_mode = "--test" in sys.argv or "-t" in sys.argv
    
    if test_mode:
        print("DÉMARRAGE EN MODE TEST - Échantillon réduit")
        total = discover_full_range(test_mode=True)
    else:
        print("DÉMARRAGE EN MODE COMPLET - PLAGE 1962-2026")
        print("Attention: cela peut prendre plusieurs heures (délai de 2s entre requêtes)")
        print("Utilise --test pour le mode test")
        total = discover_full_range(test_mode=False)
    
    # Rapport de couverture
    print("\n" + "=" * 80)
    print("RAPPORT DE COUVERTURE")
    print("=" * 80)
    
    db = JoradpDatabase()
    with db:
        report = db.get_coverage_report()
        print(f"Total sources en base: {report['total_sources']}")
        print(f"  Téléchargées: {report['downloaded']}")
        print(f"  Validées: {report['validated']}")
        print(f"  Erreurs: {report['errors']}")
        print(f"\nCouverture par année/langue (échantillon):")
        for cov in report['coverage_by_year_langue'][:10]:  # Premiers 10
            print(f"  {cov['annee']} {cov['langue']}: {cov['decouvert']} découvert")