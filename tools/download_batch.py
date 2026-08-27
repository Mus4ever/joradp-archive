"""
Téléchargement par lots avec SHA-256 et reprise après interruption
Phase 3 — Lot test initial (50-100 fichiers)
"""

import sys
sys.path.append('tools')

import hashlib
import os
from pathlib import Path
from typing import Optional
from http_client import JoradpClient
from database import JoradpDatabase


class JoradpDownloader:
    """Gestionnaire de téléchargement avec SHA-256 et reprise."""
    
    def __init__(self, db: JoradpDatabase, client: JoradpClient, output_dir: str = "downloads"):
        self.db = db
        self.client = client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def calculate_sha256(self, file_path: Path) -> str:
        """Calcule le SHA-256 d'un fichier."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def download_source(self, source_id: int, url: str, annee: int, numero: str, langue: str) -> bool:
        """
        Télécharge une source et met à jour la base de données.
        
        Returns:
            True si succès, False si échec
        """
        # Chemin local
        local_path = self.output_dir / langue / str(annee) / f"{langue}{annee}{numero}.pdf"
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Si fichier existe déjà, vérifie SHA-256
        if local_path.exists():
            existing_sha256 = self.calculate_sha256(local_path)
            
            # Met à jour la base si déjà téléchargé
            with self.db:
                conn = self.db.connect()
                conn.execute("""
                    UPDATE sources 
                    SET statut = 'telecharge', sha256 = ?, taille_octets = ?, date_telechargement = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (existing_sha256, local_path.stat().st_size, source_id))
                conn.commit()
            
            print(f"  [SKIP] {langue} {annee}-{numero} (déjà téléchargé)")
            return True
        
        # Télécharge le fichier
        response = self.client.get(url)
        
        if not response:
            print(f"  [FAIL] {langue} {annee}-{numero} (HTTP error)")
            
            # Journalise l'erreur
            with self.db:
                conn = self.db.connect()
                conn.execute("""
                    UPDATE sources 
                    SET statut = 'erreur', erreur = 'HTTP error', date_telechargement = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (source_id,))
                conn.commit()
            
            return False
        
        # Sauvegarde le fichier
        with open(local_path, "wb") as f:
            f.write(response.content)
        
        # Calcule SHA-256
        sha256 = self.calculate_sha256(local_path)
        size = local_path.stat().st_size
        
        # Met à jour la base
        with self.db:
            conn = self.db.connect()
            conn.execute("""
                UPDATE sources 
                SET statut = 'telecharge', sha256 = ?, taille_octets = ?, date_telechargement = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (sha256, size, source_id))
            conn.commit()
        
        print(f"  [OK] {langue} {annee}-{numero} ({size} octets, SHA-256: {sha256[:16]}...)")
        return True
    
    def download_batch(self, limit: Optional[int] = None, test_mode: bool = False) -> dict:
        """
        Télécharge un lot de sources.
        
        Args:
            limit: Nombre maximum de sources à télécharger (None = toutes)
            test_mode: Si True, ne télécharge que les sources les plus récentes pour test
            
        Returns:
            Statistiques du lot
        """
        with self.db:
            conn = self.db.connect()
            
            # Sélectionne les sources à télécharger
            if test_mode:
                # Mode test : les 50 sources les plus récentes
                sources = conn.execute("""
                    SELECT id, annee, numero, langue, url_complete 
                    FROM sources 
                    WHERE statut = 'decouvert'
                    ORDER BY annee DESC, numero DESC
                    LIMIT ?
                """, (limit or 50,)).fetchall()
            else:
                # Mode normal : toutes les sources non téléchargées
                query = """
                    SELECT id, annee, numero, langue, url_complete 
                    FROM sources 
                    WHERE statut = 'decouvert'
                    ORDER BY annee, langue, numero
                """
                if limit:
                    query += f" LIMIT {limit}"
                
                sources = conn.execute(query).fetchall()
        
        stats = {
            "total": len(sources),
            "success": 0,
            "failed": 0,
            "skipped": 0
        }
        
        print(f"LOT TÉLÉCHARGEMENT : {len(sources)} sources")
        print("=" * 80)
        
        for source in sources:
            source_id, annee, numero, langue, url = source
            
            success = self.download_source(source_id, url, annee, numero, langue)
            
            if success:
                stats["success"] += 1
            else:
                stats["failed"] += 1
        
        print("=" * 80)
        print(f"STATISTIQUES : {stats['success']} succès, {stats['failed']} échecs, {stats['skipped']} déjà téléchargés")
        
        return stats


def main():
    """Point d'entrée principal."""
    import sys
    
    db = JoradpDatabase()
    
    with db:
        db.initialize_schema()
    
    with JoradpClient() as client:
        downloader = JoradpDownloader(db, client)
        
        # Mode test ou complet selon argument
        test_mode = "--test" in sys.argv
        
        if test_mode:
            # LOT TEST INITIAL (50 fichiers les plus récents)
            print("PHASE 3 — LOT TEST INITIAL")
            print("=" * 80)
            print("Téléchargement des 50 sources les plus récentes pour validation")
            print()
            
            stats = downloader.download_batch(limit=50, test_mode=True)
            
            print("\nLOT TEST TERMINÉ")
            print(f"Succès : {stats['success']}/{stats['total']}")
            print(f"Échecs : {stats['failed']}/{stats['total']}")
            
            if stats['failed'] > 0:
                print("\n[ATTENTION] Des échecs détectés — vérifiez les logs avant téléchargement complet")
        else:
            # TÉLÉCHARGEMENT COMPLET
            print("PHASE 3 — TÉLÉCHARGEMENT COMPLET")
            print("=" * 80)
            print("Téléchargement de toutes les sources découvertes (10 432)")
            print("Temps estimé : ~6 heures (délai 2s entre requêtes)")
            print("Utilise --test pour le mode test")
            print()
            
            stats = downloader.download_batch(test_mode=False)
            
            print("\nTÉLÉCHARGEMENT TERMINÉ")
            print(f"Succès : {stats['success']}/{stats['total']}")
            print(f"Échecs : {stats['failed']}/{stats['total']}")
            print(f"Déjà téléchargés : {stats['skipped']}/{stats['total']}")


if __name__ == "__main__":
    main()