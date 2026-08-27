"""
Vérifie le format réel des noms de fichiers
"""

from pathlib import Path

# Vérifie quelques fichiers existants
print("VERIFICATION FORMAT NOMS DE FICHIERS")
print("=" * 80)

downloads_dir = Path("downloads/AR")

# Vérifie un répertoire
if downloads_dir.exists():
    years = [d for d in downloads_dir.iterdir() if d.is_dir()]
    if years:
        sample_year = years[0]
        print(f"Année exemple: {sample_year.name}")
        
        pdfs = list(sample_year.glob("*.pdf"))
        if pdfs:
            sample_pdf = pdfs[0]
            print(f"Fichier exemple: {sample_pdf.name}")
            print(f"Format analysé: {sample_pdf.stem}")
else:
    print("Répertoire downloads/AR non trouvé")