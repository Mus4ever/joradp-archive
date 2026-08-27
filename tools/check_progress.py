"""
Vérification manuelle de l'avancement de la découverte
"""

import sys
sys.path.append('tools')

from database import JoradpDatabase

db = JoradpDatabase()
with db:
    report = db.get_coverage_report()
    
    print("=" * 80)
    print("ÉTAT ACTUEL DE LA DÉCOUVERTE")
    print("=" * 80)
    print(f"Total sources découvertes: {report['total_sources']}")
    print(f"  Téléchargées: {report['downloaded']}")
    print(f"  Validées: {report['validated']}")
    print(f"  Erreurs: {report['errors']}")
    print()
    
    # Statistiques par année
    print("Couverture par année/langue:")
    fr_years = []
    ar_years = []
    
    for cov in report['coverage_by_year_langue']:
        if cov['langue'] == 'FR':
            fr_years.append(cov['annee'])
        else:
            ar_years.append(cov['annee'])
    
    print(f"  FR: {len(fr_years)} années traitées ({min(fr_years) if fr_years else 'N/A'}-{max(fr_years) if fr_years else 'N/A'})")
    print(f"  AR: {len(ar_years)} années traitées ({min(ar_years) if ar_years else 'N/A'}-{max(ar_years) if ar_years else 'N/A'})")
    print()
    
    # Dernières années traitées
    print("Dernières années traitées:")
    for cov in sorted(report['coverage_by_year_langue'], key=lambda x: x['annee'], reverse=True)[:5]:
        print(f"  {cov['annee']} {cov['langue']}: {cov['decouvert']} numéros")