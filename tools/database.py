"""
Base de données SQLite pour le pipeline JORADP.

Schéma complet pour suivre la découverte, téléchargement, extraction et contrôle qualité.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


class JoradpDatabase:
    """Gestionnaire de base de données SQLite pour JORADP."""
    
    def __init__(self, db_path: str = "joradp.db"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        
    def connect(self):
        """Établit la connexion à la base de données."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row  # Accès par nom de colonne
        return self._conn
    
    def close(self):
        """Ferme la connexion à la base de données."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def initialize_schema(self):
        """Crée les tables de la base de données si elles n'existent pas."""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Table de découverte des sources
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                annee INTEGER NOT NULL,
                numero TEXT NOT NULL,
                langue TEXT NOT NULL,
                type TEXT NOT NULL,
                url_complete TEXT NOT NULL,
                url_index_historique TEXT,
                pages_attendues INTEGER,
                statut TEXT DEFAULT 'decouvert',
                sha256 TEXT,
                taille_octets INTEGER,
                date_decouverte TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_telechargement TIMESTAMP,
                date_validation TIMESTAMP,
                erreur TEXT,
                UNIQUE(annee, numero, langue, type)
            )
        """)
        
        # Table de métadonnées d'extraction
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extractions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                page_numero INTEGER,
                texte_natif TEXT,
                texte_ocr TEXT,
                methode_extraction TEXT,
                moteur_ocr TEXT,
                confidence_ocr REAL,
                date_extraction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES sources(id)
            )
        """)
        
        # Table de contrôle qualité
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS controles_qualite (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                type_controle TEXT NOT NULL,
                resultat TEXT NOT NULL,
                details TEXT,
                date_controle TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES sources(id)
            )
        """)
        
        # Index pour optimiser les requêtes courantes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sources_annee ON sources(annee)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sources_langue ON sources(langue)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sources_statut ON sources(statut)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_extractions_source ON extractions(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_controles_source ON controles_qualite(source_id)")
        
        conn.commit()
    
    def add_source(self, annee: int, numero: str, langue: str, type_source: str,
                   url_complete: str, url_index_historique: Optional[str] = None,
                   pages_attendues: Optional[int] = None) -> int:
        """
        Ajoute une source à la base de données.
        
        Returns:
            ID de la source créée ou existante
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO sources 
                (annee, numero, langue, type, url_complete, url_index_historique, pages_attendues)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (annee, numero, langue, type_source, url_complete, url_index_historique, pages_attendues))
            
            conn.commit()
            
            # Retourne l'ID (existant ou nouveau)
            cursor.execute("""
                SELECT id FROM sources 
                WHERE annee = ? AND numero = ? AND langue = ? AND type = ?
            """, (annee, numero, langue, type_source))
            
            return cursor.fetchone()["id"]
            
        except sqlite3.IntegrityError:
            # En cas de conflit, récupère l'ID existant
            cursor.execute("""
                SELECT id FROM sources 
                WHERE annee = ? AND numero = ? AND langue = ? AND type = ?
            """, (annee, numero, langue, type_source))
            return cursor.fetchone()["id"]
    
    def update_source_status(self, source_id: int, statut: str, 
                            sha256: Optional[str] = None, 
                            taille_octets: Optional[int] = None,
                            erreur: Optional[str] = None):
        """Met à jour le statut d'une source."""
        conn = self.connect()
        cursor = conn.cursor()
        
        updates = ["statut = ?"]
        params = [statut]
        
        if sha256 is not None:
            updates.append("sha256 = ?")
            params.append(sha256)
            
        if taille_octets is not None:
            updates.append("taille_octets = ?")
            params.append(taille_octets)
            
        if erreur is not None:
            updates.append("erreur = ?")
            params.append(erreur)
        
        # Met à jour les timestamps appropriés
        if statut == "telecharge":
            updates.append("date_telechargement = CURRENT_TIMESTAMP")
        elif statut == "valide":
            updates.append("date_validation = CURRENT_TIMESTAMP")
        
        params.append(source_id)
        
        cursor.execute(f"""
            UPDATE sources 
            SET {', '.join(updates)}
            WHERE id = ?
        """, params)
        
        conn.commit()
    
    def get_sources_by_year(self, annee: int, langue: Optional[str] = None) -> List[Dict[str, Any]]:
        """Récupère toutes les sources pour une année donnée."""
        conn = self.connect()
        cursor = conn.cursor()
        
        if langue:
            cursor.execute("""
                SELECT * FROM sources 
                WHERE annee = ? AND langue = ?
                ORDER BY numero
            """, (annee, langue))
        else:
            cursor.execute("""
                SELECT * FROM sources 
                WHERE annee = ?
                ORDER BY langue, numero
            """, (annee,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_coverage_report(self) -> Dict[str, Any]:
        """Génère un rapport de couverture par année et langue."""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Couverture par année et langue
        cursor.execute("""
            SELECT annee, langue, statut, COUNT(*) as count
            FROM sources
            GROUP BY annee, langue, statut
            ORDER BY annee, langue, statut
        """)
        
        coverage = {}
        for row in cursor.fetchall():
            annee = row["annee"]
            langue = row["langue"]
            statut = row["statut"]
            count = row["count"]
            
            key = f"{annee}_{langue}"
            if key not in coverage:
                coverage[key] = {"annee": annee, "langue": langue, "decouvert": 0, "telecharge": 0, "valide": 0, "erreur": 0}
            
            coverage[key][statut] = count
        
        # Statistiques globales
        cursor.execute("SELECT COUNT(*) as total FROM sources")
        total = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COUNT(*) as downloaded FROM sources WHERE statut = 'telecharge'")
        downloaded = cursor.fetchone()["downloaded"]
        
        cursor.execute("SELECT COUNT(*) as validated FROM sources WHERE statut = 'valide'")
        validated = cursor.fetchone()["validated"]
        
        cursor.execute("SELECT COUNT(*) as errors FROM sources WHERE statut = 'erreur'")
        errors = cursor.fetchone()["errors"]
        
        return {
            "total_sources": total,
            "downloaded": downloaded,
            "validated": validated,
            "errors": errors,
            "coverage_by_year_langue": list(coverage.values())
        }
    
    def get_pending_downloads(self) -> List[Dict[str, Any]]:
        """Récupère les sources en attente de téléchargement."""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM sources 
            WHERE statut = 'decouvert'
            ORDER BY annee, langue, numero
        """)
        
        return [dict(row) for row in cursor.fetchall()]


def init_database(db_path: str = "joradp.db"):
    """Initialise la base de données avec le schéma complet."""
    db = JoradpDatabase(db_path)
    with db:
        db.initialize_schema()
    print(f"Base de données initialisée: {db_path}")
    return db


if __name__ == "__main__":
    # Test d'initialisation
    db = init_database("test_joradp.db")
    
    # Test d'ajout de source
    source_id = db.add_source(
        annee=2026,
        numero="001",
        langue="FR",
        type_source="pdf_complet",
        url_complete="https://www.joradp.dz/FTP/Jo-Francais/2026/F2026001.pdf"
    )
    print(f"Source ajoutée avec ID: {source_id}")
    
    # Test de rapport de couverture
    report = db.get_coverage_report()
    print("Rapport de couverture:", json.dumps(report, indent=2, default=str))
    
    # Nettoyage du test
    db.close()
    import os
    os.remove("test_joradp.db")
    print("Base de test supprimée")