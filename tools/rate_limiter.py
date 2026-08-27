"""
Rate limiter global pour tous les workers JORADP
Assure un délai minimum entre toutes les requêtes, quel que soit le nombre de workers
"""

import time
import threading
from typing import Optional


class GlobalRateLimiter:
    """
    Rate limiter global avec mutex pour accès thread-safe.
    
    Assure que toutes les requêtes (quel que soit le worker) respectent
    le délai minimum, évitant la multiplication du taux de requêtes.
    """
    
    def __init__(self, min_delay: float = 2.0):
        """
        Initialise le rate limiter global.
        
        Args:
            min_delay: Délai minimum en secondes entre requêtes
        """
        self.min_delay = min_delay
        self._last_request_time = 0.0
        self._lock = threading.Lock()
    
    def wait(self):
        """
        Attend le délai minimum entre requêtes.
        
        Thread-safe : tous les workers partagent le même _last_request_time.
        """
        with self._lock:
            now = time.time()
            elapsed = now - self._last_request_time
            
            if elapsed < self.min_delay:
                sleep_time = self.min_delay - elapsed
                time.sleep(sleep_time)
            
            self._last_request_time = time.time()
    
    def get_wait_time(self) -> float:
        """
        Retourne le temps d'attente restant sans bloquer.
        
        Returns:
            Temps d'attente en secondes (0 si pas d'attente)
        """
        with self._lock:
            now = time.time()
            elapsed = now - self._last_request_time
            
            if elapsed < self.min_delay:
                return self.min_delay - elapsed
            return 0.0


# Instance globale partagée par tous les workers
_global_rate_limiter: Optional[GlobalRateLimiter] = None


def get_global_rate_limiter(min_delay: float = 2.0) -> GlobalRateLimiter:
    """
    Retourne l'instance globale du rate limiter (singleton).
    
    Args:
        min_delay: Délai minimum en secondes (ignoré si déjà initialisé)
    
    Returns:
        Instance globale du rate limiter
    """
    global _global_rate_limiter
    
    if _global_rate_limiter is None:
        _global_rate_limiter = GlobalRateLimiter(min_delay)
    
    return _global_rate_limiter