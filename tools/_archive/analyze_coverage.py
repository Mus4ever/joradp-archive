"""
Analyse détaillée de la couverture pour identifier les trous et anomalies
"""

import sys
sys.path.append('tools')

from database import JoradpDatabase

db = JoradpDatabase()
with db:
    report = db.get_coverage_report()
    
    print("=" * 80)
    print("ANALYSE DE COUVERTURE - TROUS ET ANOMALIES")
    print("=" * 80)
    
    # Statistiques globales
    print(f"\nSTATISTIQUES GLOBALES:")
    print(f"  Total sources: {report['total_sources']}")
    print(f"  Années FR traitées: {sum(1 for cov in report['coverage_by_year_langue'] if cov['langue'] == 'FR')}")
    print(f"  Années AR traitées: {sum(1 for cov in report['coverage_by_year_langue'] if cov['langue'] == 'AR')}")
    
    # Analyse par decennie
    print(f"\nANALYSE PAR DECENNIE:")
    
    fr_by_decade = {}
    ar_by_decade = {}
    
    for cov in report['coverage_by_year_langue']:
        decade = (cov['annee'] // 10) * 10
        key = f"{decade}s"
        
        if cov['langue'] == 'FR':
            if key not in fr_by_decade:
                fr_by_decade[key] = {'count': 0, 'total': 0}
            fr_by_decade[key]['count'] += cov['decouvert']
            fr_by_decade[key]['total'] += 1
        else:
            if key not in ar_by_decade:
                ar_by_decade[key] = {'count': 0, 'total': 0}
            ar_by_decade[key]['count'] += cov['decouvert']
            ar_by_decade[key]['total'] += 1
    
    for decade in sorted(fr_by_decade.keys()):
        avg = fr_by_decade[decade]['count'] / fr_by_decade[decade]['total']
        print(f"  FR {decade}: {fr_by_decade[decade]['count']} numéros ({fr_by_decade[decade]['total']} années, avg {avg:.1f}/an)")
    
    for decade in sorted(ar_by_decade.keys()):
        avg = ar_by_decade[decade]['count'] / ar_by_decade[decade]['total']
        print(f"  AR {decade}: {ar_by_decade[decade]['count']} numéros ({ar_by_decade[decade]['total']} années, avg {avg:.1f}/an)")
    
    # Recherche d'annees manquantes attendues
    print(f"\nANNEES ATTENDUES vs REELLES:")
    
    expected_fr = set(range(1962, 2027))
    expected_ar = set(range(1964, 2027))
    
    actual_fr = {cov['annee'] for cov in report['coverage_by_year_langue'] if cov['langue'] == 'FR'}
    actual_ar = {cov['annee'] for cov in report['coverage_by_year_langue'] if cov['langue'] == 'AR'}
    
    missing_fr = expected_fr - actual_fr
    missing_ar = expected_ar - actual_ar
    
    if missing_fr:
        print(f"  FR manquantes: {sorted(missing_fr)}")
    else:
        print(f"  FR: [OK] Toutes les années 1962-2026 présentes")
    
    if missing_ar:
        print(f"  AR manquantes: {sorted(missing_ar)}")
    else:
        print(f"  AR: [OK] Toutes les années 1964-2026 présentes")
    
    # Anomalies : annees avec tres peu de numeros
    print(f"\nANOMALIES POTENTIELLES (moins de 30 numeros):")
    
    for cov in report['coverage_by_year_langue']:
        if cov['decouvert'] < 30:
            print(f"  {cov['annee']} {cov['langue']}: seulement {cov['decouvert']} numeros")
    
    # Sources avec statut erreur
    error_sources = db.get_pending_downloads()
    error_count = sum(1 for s in error_sources if s.get('erreur'))
    
    if error_count > 0:
        print(f"\nERREURS: {error_count} sources en erreur")
    else:
        print(f"\nERREURS: [OK] Aucune erreur")
    
    print(f"\nCONCLUSION:")
    print(f"  Couverture FR: {len(actual_fr)}/{len(expected_fr)} années ({len(actual_fr)*100//len(expected_fr)}%)")
    print(f"  Couverture AR: {len(actual_ar)}/{len(expected_ar)} années ({len(actual_ar)*100//len(expected_ar)}%)")
    print(f"  Total sources: {report['total_sources']}")
    
    if not missing_fr and not missing_ar and error_count == 0:
        print(f"  [OK] Couverture complete sans anomalies majeures")