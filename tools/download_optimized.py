"""
Téléchargement par lots avec reprise et validation légère des PDF.
Phase 3
"""

import sys
sys.path.append('tools')

import hashlib
import time
import signal
import threading
import os
from pathlib import Path
from typing import Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from http_client import JoradpClient
from database import JoradpDatabase
from rate_limiter import get_global_rate_limiter


@dataclass
class DownloadResult:
    """Résultat d'un téléchargement individuel."""
    source_id: int
    annee: int
    numero: str
    langue: str
    url: str
    http_status: Optional[int]
    file_size: Optional[int]
    download_duration: float
    retries: int
    validation_result: str
    final_status: str
    error: Optional[str]


class OptimizedDownloader:
    """
    Downloader avec workers, validation et reprise.
    
    Caractéristiques:
    - Max 3 workers (hard limit)
    - Rate limiter global partagé
    - .part file pour écriture atomique
    - Validation PDF légère (en-tête et taille)
    - Streaming download
    - Graceful Ctrl+C
    """
    
    def __init__(self, db: JoradpDatabase, client: JoradpClient, output_dir: str = "downloads", max_workers: int = 1):
        """
        Initialise le downloader optimisé.
        
        Args:
            db: Base de données SQLite
            client: Client HTTP JORADP
            output_dir: Répertoire de sortie
            max_workers: Nombre de workers (1-3 uniquement)
        """
        if max_workers < 1 or max_workers > 3:
            raise ValueError("max_workers doit être entre 1 et 3")
        
        self.db = db
        self.client = client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.max_workers = max_workers
        self.rate_limiter = get_global_rate_limiter()
        self._shutdown_flag = threading.Event()
        
        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Gestionnaire de signal pour arrêt gracieux."""
        print("\n[INFO] Arrêt gracieux demandé...")
        self._shutdown_flag.set()
    
    def calculate_sha256(self, file_path: Path) -> str:
        """Calcule le SHA-256 d'un fichier."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def validate_pdf(self, file_path: Path) -> tuple[bool, str]:
        """
        Valide un PDF téléchargé.
        
        Returns:
            (is_valid, error_message)
        """
        # Validation A: Magic header
        try:
            with open(file_path, "rb") as f:
                header = f.read(4)
                if header != b"%PDF":
                    return False, "Invalid magic header (not %PDF)"
        except Exception as e:
            return False, f"Cannot read file: {e}"
        
        # Validation B: File size
        file_size = file_path.stat().st_size
        if file_size == 0:
            return False, "Zero file size"
        if file_size < 100:  # PDF minimal size
            return False, f"File too small: {file_size} bytes"
        
        return True, "PDF header and size valid"
    
    def download_source(self, source_id: int, url: str, annee: int, numero: str, langue: str) -> DownloadResult:
        """
        Télécharge une source avec validation complète.
        
        Returns:
            DownloadResult avec tous les détails
        """
        start_time = time.time()
        retries = 0
        error = None
        
        # Chemin local
        local_path = self.output_dir / langue / str(annee) / f"{langue}{annee}{numero}.pdf"
        part_path = local_path.with_suffix(".pdf.part")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Nettoie .part file existant
        if part_path.exists():
            part_path.unlink()
        
        # Si fichier existe déjà, vérifie SHA-256
        if local_path.exists():
            sha256 = self.calculate_sha256(local_path)
            size = local_path.stat().st_size
            
            # Validation rapide
            is_valid, validation_msg = self.validate_pdf(local_path)
            
            if is_valid:
                # Met à jour la base
                with self.db:
                    conn = self.db.connect()
                    conn.execute("""
                        UPDATE sources 
                        SET statut = 'telecharge', sha256 = ?, taille_octets = ?, date_telechargement = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (sha256, size, source_id))
                    conn.commit()
                
                return DownloadResult(
                    source_id=source_id,
                    annee=annee,
                    numero=numero,
                    langue=langue,
                    url=url,
                    http_status=None,
                    file_size=size,
                    download_duration=0.0,
                    retries=0,
                    validation_result=validation_msg,
                    final_status="skipped",
                    error=None
                )
            else:
                # Fichier corrompu, supprime et retélécharge
                local_path.unlink()
        
        # Téléchargement avec retry
        for attempt in range(self.client.config.max_retries + 1):
            if self._shutdown_flag.is_set():
                return DownloadResult(
                    source_id=source_id,
                    annee=annee,
                    numero=numero,
                    langue=langue,
                    url=url,
                    http_status=None,
                    file_size=None,
                    download_duration=time.time() - start_time,
                    retries=attempt,
                    validation_result="aborted",
                    final_status="aborted",
                    error="Shutdown requested"
                )
            
            # Rate limiter global
            self.rate_limiter.wait()
            
            try:
                response = self.client.get(url, retries=attempt)
                
                if not response:
                    retries = attempt
                    error = f"HTTP error (attempt {attempt + 1})"
                    time.sleep(min(2 ** attempt, 60))  # Backoff
                    continue
                
                # Streaming download vers .part file
                with open(part_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        if self._shutdown_flag.is_set():
                            part_path.unlink()
                            return DownloadResult(
                                source_id=source_id,
                                annee=annee,
                                numero=numero,
                                langue=langue,
                                url=url,
                                http_status=response.status_code,
                                file_size=None,
                                download_duration=time.time() - start_time,
                                retries=attempt,
                                validation_result="aborted",
                                final_status="aborted",
                                error="Shutdown requested"
                            )
                        f.write(chunk)
                
                # Validation
                is_valid, validation_msg = self.validate_pdf(part_path)
                
                if not is_valid:
                    part_path.unlink()
                    retries = attempt
                    error = f"Validation failed: {validation_msg}"
                    time.sleep(min(2 ** attempt, 60))
                    continue
                
                # Renommage atomique .part -> .pdf (os.replace écrase sur Windows/Unix)
                os.replace(part_path, local_path)
                
                # SHA-256
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
                
                return DownloadResult(
                    source_id=source_id,
                    annee=annee,
                    numero=numero,
                    langue=langue,
                    url=url,
                    http_status=response.status_code,
                    file_size=size,
                    download_duration=time.time() - start_time,
                    retries=attempt,
                    validation_result=validation_msg,
                    final_status="success",
                    error=None
                )
                
            except Exception as e:
                retries = attempt
                error = str(e)
                time.sleep(min(2 ** attempt, 60))
        
        # Échec après tous les retries
        # Journalise l'erreur
        with self.db:
            conn = self.db.connect()
            conn.execute("""
                UPDATE sources 
                SET statut = 'erreur', erreur = ?, date_telechargement = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (error, source_id))
            conn.commit()
        
        return DownloadResult(
            source_id=source_id,
            annee=annee,
            numero=numero,
            langue=langue,
            url=url,
            http_status=None,
            file_size=None,
            download_duration=time.time() - start_time,
            retries=retries,
            validation_result="failed",
            final_status="error",
            error=error
        )
    
    def download_batch(self, limit: Optional[int] = None) -> List[DownloadResult]:
        """
        Télécharge un lot de sources avec workers.
        
        Args:
            limit: Nombre maximum de sources
            
        Returns:
            Liste des DownloadResult
        """
        with self.db:
            conn = self.db.connect()
            
            # Sélectionne les sources
            query = """
                SELECT id, annee, numero, langue, url_complete
                FROM sources
                WHERE statut = 'decouvert'
                ORDER BY annee, langue, numero
            """
            if limit:
                query += f" LIMIT {limit}"
            sources = conn.execute(query).fetchall()
        
        print(f"LOT TÉLÉCHARGEMENT : {len(sources)} sources")
        print(f"Workers : {self.max_workers}")
        print(f"Rate limiter : {self.rate_limiter.min_delay}s minimum entre requêtes")
        print("=" * 80)
        
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Soumet les tâches
            future_to_source = {}
            for source in sources:
                source_id, annee, numero, langue, url = source
                
                if self._shutdown_flag.is_set():
                    break
                
                future = executor.submit(
                    self.download_source,
                    source_id, url, annee, numero, langue
                )
                future_to_source[future] = source
            
            # Collecte les résultats
            for future in as_completed(future_to_source):
                if self._shutdown_flag.is_set():
                    # Annule les futures en attente
                    for f in future_to_source:
                        f.cancel()
                    break
                
                result = future.result()
                results.append(result)
                
                status_symbol = "[OK]" if result.final_status == "success" else "[SKIP]" if result.final_status == "skipped" else "[FAIL]"
                print(f"{status_symbol} {result.langue} {result.annee}-{result.numero} : {result.final_status}")
        
        print("=" * 80)
        
        return results


def main():
    """Point d'entrée principal."""
    import sys
    
    # Parse arguments
    workers = 1
    limit = None
    
    for arg in sys.argv[1:]:
        if arg.startswith("--workers="):
            workers = int(arg.split("=")[1])
        elif arg.startswith("--limit="):
            limit = int(arg.split("=", 1)[1])
    
    db = JoradpDatabase()
    
    with db:
        db.initialize_schema()
    
    with JoradpClient() as client:
        downloader = OptimizedDownloader(db, client, max_workers=workers)
        
        print("PHASE 3 — TÉLÉCHARGEMENT")
        print("=" * 80)
        print(f"Workers: {workers}")
        print()
        results = downloader.download_batch(limit=limit)
        successful = len([r for r in results if r.final_status == "success"])
        failed = len([r for r in results if r.final_status == "error"])
        print(f"\nTÉLÉCHARGEMENT TERMINÉ: {successful}/{len(results)} succès, {failed} échecs")


if __name__ == "__main__":
    main()
