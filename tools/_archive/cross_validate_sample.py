"""
Vérification croisée sur échantillon d'années avant découverte massive.

Compare le HTML brut reçu par le client Python avec les attentes basées sur
les vérifications manuelles, pour détecter les écarts structurels avant de
lancer la découverte sur 64 ans.
"""

import sys
sys.path.append('tools')

from http_client import JoradpClient
from bs4 import BeautifulSoup
import re
from typing import Dict, List, Tuple


def analyze_index_structure(html_content: str, langue: str, annee: int) -> Dict[str, any]:
    """
    Analyse la structure d'un index annuel et retourne ses caractéristiques.
    """
    analysis = {
        "annee": annee,
        "langue": langue,
        "taille_octets": len(html_content),
        "contient_maxwin": "MaxWin" in html_content,
        "contient_form": "<form" in html_content.lower(),
        "contient_select": "<select" in html_content.lower(),
        "contient_liens": "<a" in html_content.lower(),
        "nombre_scripts": html_content.count("<script"),
        "nombre_forms": html_content.count("<form"),
        "nombre_selects": html_content.count("<select"),
        "encoding_anomalie": html_content.count('\x00') > 1000,  # UTF-16 suspect
    }
    
    # Analyse détaillée avec BeautifulSoup
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        forms = soup.find_all('form')
        analysis["forms_details"] = []
        for form in forms:
            analysis["forms_details"].append({
                "name": form.get('name', 'N/A'),
                "action": form.get('action', 'N/A'),
                "selects_count": len(form.find_all('select'))
            })
        
        # Compte les liens MaxWin
        maxwin_links = soup.find_all('a', href=True)
        maxwin_count = sum(1 for link in maxwin_links if 'MaxWin' in link.get('href', ''))
        analysis["maxwin_links_count"] = maxwin_count
        
        # Extrait les patterns d'URL si présents
        if maxwin_count > 0:
            maxwin_pattern = re.compile(r"MaxWin\(['\"](\d+)['\"]\)", re.IGNORECASE)
            matches = maxwin_pattern.findall(html_content)
            analysis["maxwin_values"] = matches[:10] if matches else []
        
    except Exception as e:
        analysis["bs4_error"] = str(e)
    
    return analysis


def test_sample_years() -> Dict[str, List[Dict]]:
    """
    Teste un échantillon représentatif d'années pour les deux langues.
    """
    sample_years = {
        "FR": [1962, 1980, 2000, 2020],
        "AR": [1964, 1983, 2000, 2020, 2026]  # Ajout de 2026 pour tester UTF-16
    }
    
    results = {"FR": [], "AR": []}
    
    with JoradpClient() as client:
        for langue, years in sample_years.items():
            print(f"\n{'='*80}")
            print(f"ANALYSE {langue} - Échantillon: {years}")
            print('='*80)
            
            for annee in years:
                langue_code = "F" if langue == "FR" else "A"
                url = f"https://www.joradp.dz/JRN/Z{langue_code}{annee}.htm"
                
                print(f"\nTest {langue} {annee}: {url}")
                
                # Force UTF-16 pour AR 2026 (connu), auto-détection pour autres
                force_encoding = "utf-16" if langue == "AR" and annee == 2026 else None
                response = client.get(url, force_encoding=force_encoding)
                
                if response:
                    analysis = analyze_index_structure(response.text, langue, annee)
                    results[langue].append(analysis)
                    
                    print(f"  [OK] HTTP {response.status_code}")
                    print(f"  Taille: {analysis['taille_octets']} octets")
                    print(f"  MaxWin: {analysis['contient_maxwin']} ({analysis['maxwin_links_count']} liens)")
                    print(f"  Formulaires: {analysis['nombre_forms']}")
                    print(f"  Selects: {analysis['nombre_selects']}")
                    print(f"  Encodage anormal: {analysis['encoding_anomalie']}")
                    
                    if analysis['forms_details']:
                        print(f"  Détails formulaires:")
                        for form_detail in analysis['forms_details']:
                            print(f"    - {form_detail}")
                else:
                    print(f"  [FAIL] Impossible de récupérer")
                    results[langue].append({
                        "annee": annee,
                        "langue": langue,
                        "error": "HTTP request failed"
                    })
    
    return results


def detect_anomalies(results: Dict[str, List[Dict]]) -> List[str]:
    """
    Détecte les anomalies structurelles dans les résultats.
    """
    anomalies = []
    
    for langue, analyses in results.items():
        print(f"\n{'='*80}")
        print(f"DÉTECTION D'ANOMALIES {langue}")
        print('='*80)
        
        for analysis in analyses:
            if "error" in analysis:
                anomalies.append(f"{langue} {analysis['annee']}: {analysis['error']}")
                continue
            
            annee = analysis['annee']
            
            # Anomalie 1: Encodage UTF-16 inattendu
            if analysis['encoding_anomalie'] and not (langue == "AR" and annee == 2026):
                anomalies.append(f"{langue} {annee}: Encodage UTF-16 inattendu (hors AR 2026)")
                print(f"  [ANOMALIE] Encodage UTF-16 inattendu")
            
            # Anomalie 2: Pas de MaxWin ni de formulaire
            if not analysis['contient_maxwin'] and analysis['nombre_forms'] == 0:
                anomalies.append(f"{langue} {annee}: Ni MaxWin ni formulaire détecté")
                print(f"  [ANOMALIE] Ni MaxWin ni formulaire")
            
            # Anomalie 3: Formulaires sans selects attendus
            if analysis['nombre_forms'] > 0 and analysis['nombre_selects'] == 0:
                anomalies.append(f"{langue} {annee}: Formulaires sans selects")
                print(f"  [ANOMALIE] Formulaires sans selects")
            
            # Anomalie 4: Structure incohérente avec l'année
            if langue == "AR" and annee <= 1993 and analysis['contient_maxwin']:
                # C'est normal pour AR legacy d'avoir MaxWin
                pass
            elif langue == "AR" and annee >= 1994 and not analysis['contient_maxwin'] and analysis['nombre_forms'] == 0:
                anomalies.append(f"{langue} {annee}: Structure inattendue pour AR post-1993")
                print(f"  [ANOMALIE] Structure inattendue pour AR post-1993")
    
    return anomalies


def generate_cross_validation_report(results: Dict[str, List[Dict]], anomalies: List[str]):
    """
    Génère un rapport de validation croisée.
    """
    print(f"\n{'='*80}")
    print("RAPPORT DE VALIDATION CROISÉE")
    print('='*80)
    
    print(f"\nAnnées testées:")
    for langue, analyses in results.items():
        years = [a['annee'] for a in analyses if 'error' not in a]
        print(f"  {langue}: {years}")
    
    print(f"\nAnomalies détectées: {len(anomalies)}")
    for anomaly in anomalies:
        print(f"  - {anomaly}")
    
    if not anomalies:
        print("  [OK] Aucune anomalie détectée")
    
    print(f"\nRecommandation:")
    if anomalies:
        print("  [ATTENTION] Des anomalies ont été détectées.")
        print("  Il faut ajuster le script de découverte avant de lancer la découverte massive.")
    else:
        print("  [OK] L'échantillon est cohérent.")
        print("  Le script de découverte peut être étendu à la plage complète 1962-2026.")


if __name__ == "__main__":
    print("=" * 80)
    print("PHASE 2 - VALIDATION CROISÉE SUR ÉCHANTILLON")
    print("=" * 80)
    print("Objectif: Détecter les écarts structurels avant découverte massive")
    print()
    
    results = test_sample_years()
    anomalies = detect_anomalies(results)
    generate_cross_validation_report(results, anomalies)