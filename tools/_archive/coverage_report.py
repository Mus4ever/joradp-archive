"""
Génère un rapport de couverture détaillé depuis la base de données.
"""

import json
from database import JoradpDatabase
from datetime import datetime


def generate_coverage_report(db_path: str = "joradp.db", output_file: str = "rapport_couverture.json"):
    """Génère un rapport de couverture détaillé."""
    
    db = JoradpDatabase(db_path)
    with db:
        db.initialize_schema()
        
        # Rapport de base
        report = db.get_coverage_report()
        
        # Analyse par année et langue
        conn = db.connect()
        cursor = conn.cursor()
        
        # Statistiques par année
        cursor.execute("""
            SELECT annee, langue, COUNT(*) as total,
                   SUM(CASE WHEN statut = 'decouvert' THEN 1 ELSE 0 END) as decouvert,
                   SUM(CASE WHEN statut = 'telecharge' THEN 1 ELSE 0 END) as telecharge,
                   SUM(CASE WHEN statut = 'valide' THEN 1 ELSE 0 END) as valide,
                   SUM(CASE WHEN statut = 'erreur' THEN 1 ELSE 0 END) as erreur
            FROM sources
            GROUP BY annee, langue
            ORDER BY annee DESC, langue
        """)
        
        yearly_stats = []
        for row in cursor.fetchall():
            yearly_stats.append({
                "annee": row["annee"],
                "langue": row["langue"],
                "total": row["total"],
                "decouvert": row["decouvert"],
                "telecharge": row["telecharge"],
                "valide": row["valide"],
                "erreur": row["erreur"]
            })
        
        # Statistiques par type de source
        cursor.execute("""
            SELECT type, COUNT(*) as total
            FROM sources
            GROUP BY type
        """)
        
        type_stats = []
        for row in cursor.fetchall():
            type_stats.append({
                "type": row["type"],
                "total": row["total"]
            })
        
        # Sources en attente de téléchargement
        pending = db.get_pending_downloads()
        
        # Complète le rapport
        report["generated_at"] = datetime.now().isoformat()
        report["yearly_statistics"] = yearly_stats
        report["type_statistics"] = type_stats
        report["pending_downloads"] = len(pending)
        report["pending_samples"] = pending[:5]  # Premier exemple
        
        # Sauvegarde en JSON
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # Affichage console
        print("=" * 60)
        print("RAPPORT DE COUVERTURE JORADP")
        print("=" * 60)
        print(f"Date: {report['generated_at']}")
        print(f"Base de données: {db_path}")
        print()
        print("STATISTIQUES GLOBALES:")
        print(f"  Total sources: {report['total_sources']}")
        print(f"  Téléchargées: {report['downloaded']}")
        print(f"  Validées: {report['validated']}")
        print(f"  Erreurs: {report['errors']}")
        print(f"  En attente: {report['pending_downloads']}")
        print()
        print("STATISTIQUES PAR ANNÉE:")
        for stat in yearly_stats:
            print(f"  {stat['annee']} {stat['langue']}: {stat['total']} total ({stat['decouvert']} découvert, {stat['telecharge']} téléchargé)")
        print()
        print("STATISTIQUES PAR TYPE:")
        for stat in type_stats:
            print(f"  {stat['type']}: {stat['total']}")
        print()
        print(f"Rapport détaillé sauvegardé: {output_file}")
        
        return report


if __name__ == "__main__":
    generate_coverage_report()