"""
Script de découverte automatique des sources JORADP.

Parcourt les index annuels pour découvrir les PDF complets et les pages historiques,
enregistre tout dans SQLite et produit un rapport de couverture.
"""

import re
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup

from http_client import JoradpClient, JoradpClientConfig
from database import JoradpDatabase


class JoradpDiscoverer:
    """Découvreur automatique de sources JORADP."""
    
    def __init__(self, db: JoradpDatabase, client: JoradpClient):
        self.db = db
        self.client = client
        
    def parse_annual_index(self, html_content: str, langue: str, annee: int) -> List[Dict[str, Any]]:
        """
        Extrait les numéros depuis un index annuel.
        
        Args:
            html_content: Contenu HTML de l'index annuel
            langue: 'FR' ou 'AR'
            annee: Année de l'index
            
        Returns:
            Liste des numéros découverts avec leurs URL
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        sources = []
        
        # Cherche les appels MaxWin qui contiennent les numéros
        # Format: javascript:MaxWin('001'), javascript:MaxWin('002'), etc.
        maxwin_pattern = re.compile(r"MaxWin\(['\"](\d+)['\"]\)")
        
        # Cherche d'abord dans les liens (javascript:MaxWin('001'))
        for link in soup.find_all('a', href=True):
            href = link['href']
            matches = maxwin_pattern.findall(href)
            for numero in matches:
                numero_formate = numero.zfill(3)  # 001, 002, etc.
                
                # Construit l'URL du PDF complet selon la convention
                if langue == "FR":
                    # Note: l'index FR utilise JO-FRANCAIS (majuscules)
                    url_complete = f"https://www.joradp.dz/FTP/JO-FRANCAIS/{annee}/F{annee}{numero_formate}.pdf"
                else:  # AR
                    # Note: l'index AR utilise jo-arabe (minuscules)
                    url_complete = f"https://www.joradp.dz/FTP/jo-arabe/{annee}/A{annee}{numero_formate}.pdf"
                
                sources.append({
                    "annee": annee,
                    "numero": numero_formate,
                    "langue": langue,
                    "type": "pdf_complet",
                    "url_complete": url_complete
                })
        
        # Cherche aussi dans les scripts inline (backup)
        if not sources:
            for script in soup.find_all('script'):
                if script.string:
                    matches = maxwin_pattern.findall(script.string)
                    for numero in matches:
                        numero_formate = numero.zfill(3)
                        
                        if langue == "FR":
                            url_complete = f"https://www.joradp.dz/FTP/JO-FRANCAIS/{annee}/F{annee}{numero_formate}.pdf"
                        else:
                            url_complete = f"https://www.joradp.dz/FTP/jo-arabe/{annee}/A{annee}{numero_formate}.pdf"
                        
                        sources.append({
                            "annee": annee,
                            "numero": numero_formate,
                            "langue": langue,
                            "type": "pdf_complet",
                            "url_complete": url_complete
                        })
        
        # Pour les années AR récentes sans MaxWin (cas rare selon validation)
        # on tente l'extraction par formulaire comme fallback
        if not sources and langue == "AR":
            print(f"  [INFO] Pas de MaxWin détecté, tentative par formulaire")
            sources = self._discover_ar_sequential(html_content, annee)
        
        return sources
    
    def _discover_ar_sequential(self, html_content: str, annee: int) -> List[Dict[str, Any]]:
        """
        Extraction des numéros depuis le formulaire AR pour les années avec formulaire dynamique.
        
        Extrait directement les numéros du second formulaire (zFrm2) qui contient la liste.
        Utilise BeautifulSoup pour gérer l'encodage UTF-16 correctement.
        """
        sources = []
        print(f"  [INFO] Extraction des numéros depuis le formulaire AR {annee}")
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Cherche le formulaire zFrm2
            form_zfrm2 = soup.find('form', {'name': 'zFrm2'})
            if not form_zfrm2:
                print(f"  [WARN] Formulaire zFrm2 non trouvé")
                return sources
            
            # Cherche le select znjo
            select_znjo = form_zfrm2.find('select', {'name': 'znjo'})
            if not select_znjo:
                print(f"  [WARN] Select znjo non trouvé")
                return sources
            
            # Extrait les valeurs des options
            options = select_znjo.find_all('option')
            numeros = []
            
            for option in options:
                value = option.get('value')
                if value and value.isdigit():
                    numeros.append(value)
            
            if numeros:
                # Tri décroissant comme dans le formulaire
                numeros = sorted(set(numeros), key=int, reverse=True)
                print(f"  [INFO] {len(numeros)} numéros trouvés dans le formulaire")
                
                for numero in numeros:
                    numero_formate = str(numero).zfill(3)
                    url = f"https://www.joradp.dz/FTP/jo-arabe/{annee}/A{annee}{numero_formate}.pdf"
                    
                    sources.append({
                        "annee": annee,
                        "numero": numero_formate,
                        "langue": "AR",
                        "type": "pdf_complet",
                        "url_complete": url
                    })
            else:
                print(f"  [WARN] Aucun numéro trouvé dans les options")
                
        except Exception as e:
            print(f"  [ERROR] Erreur lors de l'extraction: {e}")
        
        return sources
    
    def parse_historical_index(self, html_content: str, langue: str, annee: int, numero: str) -> Dict[str, Any]:
        """
        Extrait les informations depuis une page historique _Pag1.htm.
        
        Args:
            html_content: Contenu HTML de la page historique
            langue: 'FR' ou 'AR'
            annee: Année du numéro
            numero: Numéro du JO
            
        Returns:
            Dictionnaire avec l'URL de l'index et le nombre de pages
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Détermine la racine historique selon l'année
        if annee <= 1983:
            base_path = "Jo6283"
        else:
            base_path = "Jo8499"
        
        # Construit l'URL de l'index historique
        langue_prefix = "A" if langue == "AR" else "F"
        url_index = f"https://www.joradp.dz/{base_path}/{annee}/{numero}/{langue_prefix}_Pag1.htm"
        
        # Compte les liens vers les pages PDF (AP1.pdf, AP2.pdf, etc.)
        page_links = soup.find_all('a', href=re.compile(rf"{langue_prefix}\d+\.pdf"))
        pages_count = len(page_links)
        
        return {
            "url_index_historique": url_index,
            "pages_attendues": pages_count if pages_count > 0 else None
        }
    
    def discover_annual_index(self, langue: str, annee: int) -> int:
        """
        Découvre tous les numéros pour une année et une langue données.
        
        Args:
            langue: 'FR' ou 'AR'
            annee: Année à découvrir
            
        Returns:
            Nombre de sources découvertes
        """
        # Construit l'URL de l'index annuel
        langue_code = "F" if langue == "FR" else "A"
        index_url = f"https://www.joradp.dz/JRN/Z{langue_code}{annee}.htm"
        
        print(f"Découverte index {langue} {annee}: {index_url}")
        
        # Approche hybride : UTF-16 pour AR 2025-2026 (cas connus), standard pour le reste
        force_encoding = None
        if langue == "AR" and annee >= 2025:
            force_encoding = "utf-16"
        
        response = self.client.get(index_url, force_encoding=force_encoding)
        
        # Si échec avec UTF-16, essaie standard (fallback)
        if not response and force_encoding:
            print(f"  [INFO] Échec UTF-16, tentative encodage standard")
            response = self.client.get(index_url)
        
        if not response:
            print(f"  [FAIL] Impossible de récupérer l'index")
            return 0
        
        # Extrait les numéros depuis l'index
        sources = self.parse_annual_index(response.text, langue, annee)
        print(f"  [OK] {len(sources)} numéros trouvés")
        
        count = 0
        for source in sources:
            # OPTIMISATION : désactive la découverte automatique des pages historiques
            # pour AR 1964-1993 pour accélérer le processus Phase 2
            # Cette découverte peut être faite ultérieurement en Phase 3
            # if langue == "AR" and 1964 <= annee <= 1993:
            #     print(f"    [INFO] Pages historiques désactivées pour accélération")
            
            # Ajoute à la base de données
            source_id = self.db.add_source(
                annee=source["annee"],
                numero=source["numero"],
                langue=source["langue"],
                type_source=source["type"],
                url_complete=source["url_complete"],
                url_index_historique=source.get("url_index_historique"),
                pages_attendues=source.get("pages_attendues")
            )
            count += 1
        
        return count
    
    def discover_range(self, langue: str, annee_debut: int, annee_fin: int) -> Dict[str, int]:
        """
        Découvre une plage d'années pour une langue.
        
        Args:
            langue: 'FR' ou 'AR'
            annee_debut: Année de début
            annee_fin: Année de fin
            
        Returns:
            Statistiques de découverte
        """
        stats = {"total": 0, "success": 0, "failed": 0}
        
        for annee in range(annee_debut, annee_fin + 1):
            count = self.discover_annual_index(langue, annee)
            stats["total"] += 1
            if count > 0:
                stats["success"] += 1
            else:
                stats["failed"] += 1
        
        return stats
    
    def generate_coverage_report(self) -> Dict[str, Any]:
        """Génère le rapport de couverture depuis la base de données."""
        return self.db.get_coverage_report()


def discover_year(db_path: str = "joradp.db", annee: int = 2026, langue: str = "FR"):
    """Découvre une année spécifique pour test."""
    db = JoradpDatabase(db_path)
    with db:
        db.initialize_schema()
    
    with JoradpClient() as client:
        discoverer = JoradpDiscoverer(db, client)
        count = discoverer.discover_annual_index(langue, annee)
        return count
    
    with JoradpClient() as client:
        discoverer = JoradpDiscoverer(db, client)
        count = discoverer.discover_annual_index(langue, annee)
        print(f"\nTotal sources découvertes: {count}")
        
        # Rapport de couverture
        report = discoverer.generate_coverage_report()
        print(f"\nRapport de couverture:")
        print(f"  Total sources: {report['total_sources']}")
        print(f"  Téléchargées: {report['downloaded']}")
        print(f"  Validées: {report['validated']}")
        print(f"  Erreurs: {report['errors']}")


if __name__ == "__main__":
    import sys
    
    # Test sur l'année 2026 français et 2026 arabe (disponible avec formulaire dynamique)
    print("=" * 60)
    print("Test de découverte - Index 2026 Français")
    print("=" * 60)
    count_fr = discover_year(annee=2026, langue="FR")
    print(f"Total découvertes FR 2026: {count_fr}")
    
    print("\n" + "=" * 60)
    print("Test de découverte - Index 2026 Arabe (disponible avec formulaire dynamique)")
    print("=" * 60)
    count_ar = discover_year(annee=2026, langue="AR")
    print(f"Total découvertes AR 2026: {count_ar}")
    
    # Génère le rapport de couverture final
    print("\n" + "=" * 60)
    print("Rapport de couverture final")
    print("=" * 60)
    
    db = JoradpDatabase()
    with db:
        report = db.get_coverage_report()
        print(f"Total sources découvertes: {report['total_sources']}")
        print(f"  Téléchargées: {report['downloaded']}")
        print(f"  Validées: {report['validated']}")
        print(f"  Erreurs: {report['errors']}")
        print(f"\nCouverture par année/langue:")
        for cov in report['coverage_by_year_langue']:
            print(f"  {cov['annee']} {cov['langue']}: {cov['decouvert']} découvert, {cov['telecharge']} téléchargé, {cov['valide']} validé")