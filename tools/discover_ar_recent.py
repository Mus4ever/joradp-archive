"""
Découverte AR 2025-2026 avec encodage UTF-16 forcé
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient
from database import JoradpDatabase
from discover import JoradpDiscoverer

db = JoradpDatabase()
with db:
    db.initialize_schema()

with JoradpClient() as client:
    discoverer = JoradpDiscoverer(db, client)
    
    print("DÉCOUVERTE AR 2025-2026 - UTF-16 FORCÉ")
    print("=" * 80)
    
    for annee in [2025, 2026]:
        print(f"\n--- AR {annee} ---")
        langue_code = "A"
        index_url = f"https://www.joradp.dz/JRN/Z{langue_code}{annee}.htm"
        
        print(f"Découverte index AR {annee}: {index_url}")
        response = client.get(index_url, force_encoding="utf-16")
        
        if response:
            sources = discoverer.parse_annual_index(response.text, "AR", annee)
            print(f"  [OK] {len(sources)} numéros trouvés")
            
            for source in sources:
                discoverer.db.add_source(
                    annee=source["annee"],
                    numero=source["numero"],
                    langue=source["langue"],
                    type_source=source["type"],
                    url_complete=source["url_complete"]
                )
        else:
            print(f"  [FAIL] Impossible de récupérer l'index")

print("\n" + "=" * 80)
print("RAPPORT FINAL")
print("=" * 80)

db = JoradpDatabase()
with db:
    report = db.get_coverage_report()
    print(f"Total sources: {report['total_sources']}")
    
    ar_2025 = next((cov for cov in report['coverage_by_year_langue'] if cov['annee'] == 2025 and cov['langue'] == 'AR'), None)
    ar_2026 = next((cov for cov in report['coverage_by_year_langue'] if cov['annee'] == 2026 and cov['langue'] == 'AR'), None)
    
    print(f"AR 2025: {ar_2025['decouvert'] if ar_2025 else 0} numéros")
    print(f"AR 2026: {ar_2026['decouvert'] if ar_2026 else 0} numéros")