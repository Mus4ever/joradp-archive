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
            # Optimisations SQLite pour vitesse & intégrité
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA synchronous = NORMAL")
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
        """Crée ou met à jour les tables de la base de données."""
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
                extraction_statut TEXT DEFAULT 'non_extrait',
                date_decouverte TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_telechargement TIMESTAMP,
                date_validation TIMESTAMP,
                date_extraction TIMESTAMP,
                erreur TEXT,
                UNIQUE(annee, numero, langue, type)
            )
        """)
        
        # Vérifie si extraction_statut & date_extraction existent déjà dans sources
        cursor.execute("PRAGMA table_info(sources)")
        existing_cols = [row["name"] for row in cursor.fetchall()]
        if "extraction_statut" not in existing_cols:
            cursor.execute("ALTER TABLE sources ADD COLUMN extraction_statut TEXT DEFAULT 'non_extrait'")
        if "date_extraction" not in existing_cols:
            cursor.execute("ALTER TABLE sources ADD COLUMN date_extraction TIMESTAMP")

        # Table granulaire d'extractions page par page (Phase 4)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS page_extractions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                page_numero INTEGER NOT NULL,
                page_type TEXT NOT NULL,
                total_chars INTEGER DEFAULT 0,
                arabic_chars INTEGER DEFAULT 0,
                latin_chars INTEGER DEFAULT 0,
                digit_chars INTEGER DEFAULT 0,
                arabic_ratio REAL DEFAULT 0.0,
                suspect_latin_count INTEGER DEFAULT 0,
                has_images INTEGER DEFAULT 0,
                texte_extrait TEXT,
                methode_extraction TEXT NOT NULL,
                quality_score REAL DEFAULT 1.0,
                quality_flags TEXT,
                date_extraction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES sources(id),
                UNIQUE(source_id, page_numero)
            )
        """)

        # Table historique/legacy d'extractions
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
                needs_ocr BOOLEAN DEFAULT 0,
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
        
        # Index pour optimiser les requêtes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sources_annee ON sources(annee)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sources_langue ON sources(langue)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sources_statut ON sources(statut)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sources_ext_statut ON sources(extraction_statut)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_page_extractions_src ON page_extractions(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_page_extractions_type ON page_extractions(page_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_controles_source ON controles_qualite(source_id)")
        
        conn.commit()
    
    def save_page_extraction(self, source_id: int, page_numero: int, page_type: str,
                             total_chars: int, arabic_chars: int, latin_chars: int,
                             digit_chars: int, arabic_ratio: float, suspect_latin_count: int,
                             has_images: int, texte_extrait: str, methode_extraction: str,
                             quality_score: float = 1.0, quality_flags: Optional[dict] = None) -> int:
        """Enregistre ou met à jour l'extraction d'une page."""
        conn = self.connect()
        cursor = conn.cursor()
        
        flags_json = json.dumps(quality_flags or {}, ensure_ascii=False)
        
        cursor.execute("""
            INSERT INTO page_extractions 
            (source_id, page_numero, page_type, total_chars, arabic_chars, latin_chars,
             digit_chars, arabic_ratio, suspect_latin_count, has_images, texte_extrait,
             methode_extraction, quality_score, quality_flags, date_extraction)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(source_id, page_numero) DO UPDATE SET
                page_type = excluded.page_type,
                total_chars = excluded.total_chars,
                arabic_chars = excluded.arabic_chars,
                latin_chars = excluded.latin_chars,
                digit_chars = excluded.digit_chars,
                arabic_ratio = excluded.arabic_ratio,
                suspect_latin_count = excluded.suspect_latin_count,
                has_images = excluded.has_images,
                texte_extrait = excluded.texte_extrait,
                methode_extraction = excluded.methode_extraction,
                quality_score = excluded.quality_score,
                quality_flags = excluded.quality_flags,
                date_extraction = CURRENT_TIMESTAMP
        """, (source_id, page_numero, page_type, total_chars, arabic_chars, latin_chars,
              digit_chars, arabic_ratio, suspect_latin_count, has_images, texte_extrait,
              methode_extraction, quality_score, flags_json))
        
        conn.commit()
        return cursor.lastrowid
    
    def update_source_extraction_status(self, source_id: int, extraction_statut: str):
        """Met à jour le statut global d'extraction d'un PDF source."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sources 
            SET extraction_statut = ?, date_extraction = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (extraction_statut, source_id))
        conn.commit()

    def get_sources_for_extraction(self, limit: Optional[int] = None, langue: Optional[str] = None,
                                  annee_min: Optional[int] = None, annee_max: Optional[int] = None) -> List[Dict[str, Any]]:
        """Récupère les sources prêtes à extraire."""
        conn = self.connect()
        cursor = conn.cursor()
        
        query = "SELECT * FROM sources WHERE statut = 'telecharge'"
        params = []
        
        if langue:
            query += " AND langue = ?"
            params.append(langue)
        if annee_min is not None:
            query += " AND annee >= ?"
            params.append(annee_min)
        if annee_max is not None:
            query += " AND annee <= ?"
            params.append(annee_max)
            
        query += " ORDER BY annee DESC, numero ASC"
        
        if limit:
            query += f" LIMIT {limit}"
            
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def add_source(self, annee: int, numero: str, langue: str, type_source: str,
                   url_complete: str, url_index_historique: Optional[str] = None,
                   pages_attendues: Optional[int] = None) -> int:
        """Ajoute une source à la base de données."""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO sources 
                (annee, numero, langue, type, url_complete, url_index_historique, pages_attendues)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (annee, numero, langue, type_source, url_complete, url_index_historique, pages_attendues))
            
            conn.commit()
            
            cursor.execute("""
                SELECT id FROM sources 
                WHERE annee = ? AND numero = ? AND langue = ? AND type = ?
            """, (annee, numero, langue, type_source))
            
            return cursor.fetchone()["id"]
            
        except sqlite3.IntegrityError:
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


def init_database(db_path: str = "joradp.db"):
    """Initialise la base de données avec le schéma complet."""
    db = JoradpDatabase(db_path)
    with db:
        db.initialize_schema()
    print(f"Base de données initialisée: {db_path}")
    return db


if __name__ == "__main__":
    db = init_database("joradp.db")
    print("Schema initialized successfully in joradp.db")