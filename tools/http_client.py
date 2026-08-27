"""
Client HTTP JORADP avec support TLS legacy et politesse serveur.

Solution TLS : truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT) + SSL_OP_LEGACY_SERVER_CONNECT
maintient CERT_REQUIRED et check_hostname=True pour la sécurité.
"""

import ssl
import time
import httpx
import truststore
from typing import Optional
from dataclasses import dataclass


@dataclass
class JoradpClientConfig:
    """Configuration du client JORADP."""
    base_url: str = "https://www.joradp.dz"
    min_delay: float = 2.0  # Secondes minimum entre requêtes
    max_retries: int = 3
    timeout: int = 30
    user_agent: str = "JORADPArchivePipeline/0.1 (responsible archival client)"


class JoradpClient:
    """Client HTTP avec support TLS legacy et politesse serveur."""
    
    def __init__(self, config: Optional[JoradpClientConfig] = None):
        self.config = config or JoradpClientConfig()
        self._last_request_time = 0.0
        self._context = self._create_ssl_context()
        self._client: Optional[httpx.Client] = None
        
    def _create_ssl_context(self) -> ssl.SSLContext:
        """
        Crée un contexte SSL compatible avec le serveur JORADP.
        
        Utilise truststore pour le magasin de certificats Windows et active
        SSL_OP_LEGACY_SERVER_CONNECT (0x4) pour la renégociation legacy
        tout en maintenant CERT_REQUIRED et check_hostname=True.
        """
        context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        # SSL_OP_LEGACY_SERVER_CONNECT = 0x4
        context.options |= 0x4
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = True
        return context
    
    def _wait_for_rate_limit(self):
        """Attend le délai minimum entre requêtes."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.config.min_delay:
            sleep_time = self.config.min_delay - elapsed
            time.sleep(sleep_time)
        self._last_request_time = time.time()
    
    def _get_client(self) -> httpx.Client:
        """Crée ou retourne le client httpx."""
        if self._client is None:
            self._client = httpx.Client(
                verify=self._context,
                timeout=self.config.timeout,
                headers={"User-Agent": self.config.user_agent}
            )
        return self._client
    
    def get(self, url: str, retries: int = 0, force_encoding: Optional[str] = None) -> Optional[httpx.Response]:
        """
        Effectue une requête GET avec retry et politesse.
        
        Args:
            url: URL cible
            retries: Nombre de tentatives déjà effectuées (appel récursif)
            force_encoding: Force un encodage spécifique (ex: 'utf-16' pour AR 2026)
            
        Returns:
            Response httpx ou None si échec après max_retries
        """
        self._wait_for_rate_limit()
        client = self._get_client()
        
        try:
            response = client.get(url)
            response.raise_for_status()
            
            # Force l'encodage si demandé (utile pour UTF-16)
            if force_encoding:
                response.encoding = force_encoding
            
            return response
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 503, 504) and retries < self.config.max_retries:
                # Backoff exponentiel : 2^retries secondes
                backoff = min(2 ** retries, 60)  # Max 60 secondes
                time.sleep(backoff)
                return self.get(url, retries + 1, force_encoding)
            return None
            
        except (httpx.RequestError, httpx.TimeoutException) as e:
            if retries < self.config.max_retries:
                backoff = min(2 ** retries, 60)
                time.sleep(backoff)
                return self.get(url, retries + 1, force_encoding)
            return None
    
    def close(self):
        """Ferme le client HTTP."""
        if self._client:
            self._client.close()
            self._client = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def test_client():
    """Test le client sur plusieurs URLs du site."""
    test_urls = [
        "https://www.joradp.dz/JRN/ZF2026.htm",  # Index français 2026
        "https://www.joradp.dz/JRN/ZA2026.htm",  # Index arabe 2026
        "https://www.joradp.dz/FTP/Jo-Arabe/1983/A1983001.pdf",  # PDF legacy
    ]
    
    with JoradpClient() as client:
        for url in test_urls:
            print(f"Test: {url}")
            response = client.get(url)
            if response:
                print(f"  [OK] HTTP {response.status_code}")
                print(f"  [OK] Content-Type: {response.headers.get('content-type', 'N/A')}")
                print(f"  [OK] Size: {len(response.content)} octets")
            else:
                print(f"  [FAIL] Echec")
            print()


if __name__ == "__main__":
    test_client()