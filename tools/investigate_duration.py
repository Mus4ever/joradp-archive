"""
Investigation de l'anomalie de durée (1.82x plus lent que prévu)
Hypothèses à tester:
1. Le rate limiter global est-il vraiment 2 secondes ?
2. Y a-t-il des délais supplémentaires non comptés ?
3. Y a-t-il des retries invisibles ?
"""

import sys
sys.path.append('tools')

from database import JoradpDatabase
import statistics

db = JoradpDatabase()

print("INVESTIGATION ANOMALIE DURÉE (1.82x)")
print("=" * 80)

with db:
    conn = db.connect()
    
    # Vérifie si la base enregistre les durées individuelles
    print("1. DONNÉES DE DURÉE DISPONIBLES")
    print("-" * 80)
    
    # La base ne stocke pas les durées individuelles, mais on peut les estimer
    # via la distribution des timestamps
    
    print("La base de données ne stocke pas les durées individuelles.")
    print("Investigation via code et logs...")
    print()
    
    # Vérifie s'il y a des retries dans les erreurs
    print("2. RETRIES INVISIBLES")
    print("-" * 80)
    
    retries = conn.execute("""
        SELECT COUNT(*) 
        FROM sources 
        WHERE erreur LIKE '%retry%' OR erreur LIKE '%attempt%'
    """).fetchone()[0]
    
    print(f"Sources avec retry mentionné dans erreur: {retries}")
    
    # Vérifie le rate limiter dans le code
    print()
    print("3. RATE LIMITER CODE ANALYSIS")
    print("-" * 80)
    
    # Le rate limiter est dans tools/rate_limiter.py
    print("Rate limiter: tools/rate_limiter.py")
    print("Configuration: min_delay = 2.0 secondes")
    print("Implementation: singleton global, thread-safe")
    print()
    
    # Analyse la distribution des téléchargements par heure
    print("4. DISTRIBUTION TEMPORELLE PAR HEURE")
    print("-" * 80)
    
    hourly = conn.execute("""
        SELECT 
            strftime('%H', date_telechargement) as hour,
            COUNT(*) as count
        FROM sources 
        WHERE date_telechargement IS NOT NULL
        GROUP BY hour
        ORDER BY hour
    """).fetchall()
    
    for row in hourly:
        hour, count = row
        print(f"{hour}h: {count} téléchargements")
    
    print()
    print("5. CALCUL DU VÉRITABLE DÉLAI MOYEN")
    print("-" * 80)
    
    # Si on a 10432 téléchargements en 634.6 minutes
    # Délai moyen = 634.6 * 60 / 10432 = 3.65 secondes
    total_minutes = 634.6
    total_files = 10432
    avg_delay = (total_minutes * 60) / total_files
    
    print(f"Durée totale: {total_minutes} minutes")
    print(f"Nombre de fichiers: {total_files}")
    print(f"Délai moyen réel: {avg_delay:.2f} secondes")
    print(f"Délai théorique: 2.00 secondes")
    print(f"Surcoût: {avg_delay - 2.00:.2f} secondes par fichier")
    print(f"Ratio: {avg_delay / 2.00:.2f}x")
    
    print()
    print("6. HYPOTHÈSES DE CAUSE")
    print("-" * 80)
    print("H1: Rate limiter global plus lent que prévu")
    print("H2: Délai de validation PDF significatif")
    print("H3: Délai d'écriture disque (.part -> .pdf)")
    print("H4: Délai de base de données (SHA-256 calcul + UPDATE)")
    print("H5: Latence réseau variable (> 2s sur certains fichiers)")
    print()
    print("7. RECOMMANDATION")
    print("-" * 80)
    print("Il faut instrumenter le code pour mesurer:")
    print("- Délai réel entre requêtes HTTP")
    print("- Durée de téléchargement réseau")
    print("- Durée de validation PDF")
    print("- Durée des opérations base de données")
    print("Pour identifier précisément où se trouve le surcoût de 1.65s/fichier")

print("=" * 80)