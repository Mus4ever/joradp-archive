"""
Vérification SHA-256 par re-téléchargement indépendant
15-20 fichiers aléatoires répartis sur plusieurs décennies et les deux langues
"""

import sys
sys.path.append('tools')

import random
import hashlib
from pathlib import Path
from database import JoradpDatabase
from http_client import JoradpClient

db = JoradpDatabase()

print("VERIFICATION SHA-256 PAR RE-TELECHARGEMENT")
print("=" * 80)

with db:
    conn = db.connect()
    
    # Sélectionne 15-20 fichiers aléatoires répartis
    # 5 par décennie (1960s, 1980s, 2000s, 2020s) × 2 langues
    sample_files = []
    
    decades = [(1960, 1969), (1980, 1989), (2000, 2009), (2020, 2029)]
    languages = ['FR', 'AR']
    
    for (start_year, end_year), langue in [(d, l) for d in decades for l in languages]:
        # Sélectionne un fichier aléatoire dans cette décennie/langue
        query = """
            SELECT id, annee, numero, langue, url_complete, sha256
            FROM sources 
            WHERE langue = ? 
            AND annee BETWEEN ? AND ?
            AND statut = 'telecharge'
            AND sha256 IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 2
        """
        files = conn.execute(query, (langue, start_year, end_year)).fetchall()
        sample_files.extend(files)
    
    # Limite à 20 fichiers maximum
    sample_files = sample_files[:20]
    
    print(f"{len(sample_files)} fichiers sélectionnés pour vérification")
    print()

print("Re-téléchargement en cours...")
print("-" * 80)

mismatches = []
matches = []

with JoradpClient() as client:
    for source in sample_files:
        source_id, annee, numero, langue, url, original_sha256 = source
        
        # Télécharge à nouveau
        response = client.get(url)
        if not response:
            print(f"[ERROR] {langue} {annee}-{numero}: échec du re-téléchargement")
            continue
        
        # Calcule le nouveau SHA-256
        new_sha256 = hashlib.sha256(response.content).hexdigest()
        
        # Compare
        if new_sha256 == original_sha256:
            matches.append((langue, annee, numero))
            print(f"[MATCH] {langue} {annee}-{numero}")
        else:
            mismatches.append((langue, annee, numero, original_sha256, new_sha256))
            print(f"[MISMATCH] {langue} {annee}-{numero}")
            print(f"  Original: {original_sha256}")
            print(f"  Nouveau:  {new_sha256}")

print()
print("=" * 80)
print(f"RÉSULTAT: {len(matches)} matchs, {len(mismatches)} erreurs")

if mismatches:
    print("\nERREURS DETECTÉES:")
    for langue, annee, numero, orig, new in mismatches:
        print(f"  {langue} {annee}-{numero}: SHA-256 différent")
else:
    print("\nTous les fichiers correspondent - intégrité SHA-256 vérifiée")