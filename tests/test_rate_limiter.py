"""
Tests pour le rate limiter global
"""

import sys
sys.path.append('tools')

import time
import threading
from rate_limiter import GlobalRateLimiter, get_global_rate_limiter


def test_basic_rate_limiting():
    """Test basique du rate limiter."""
    print("TEST: Basic rate limiting")
    
    limiter = GlobalRateLimiter(min_delay=1.0)
    
    start = time.time()
    limiter.wait()
    limiter.wait()
    limiter.wait()
    elapsed = time.time() - start
    
    # 3 requêtes avec 1s min delay = ~2s minimum
    assert elapsed >= 2.0, f"Expected >= 2.0s, got {elapsed:.2f}s"
    assert elapsed < 2.5, f"Expected < 2.5s, got {elapsed:.2f}s"
    
    print(f"  [OK] 3 requests in {elapsed:.2f}s (expected ~2s)")


def test_thread_safety():
    """Test la sécurité thread-safe du rate limiter."""
    print("TEST: Thread safety")
    
    limiter = GlobalRateLimiter(min_delay=0.5)
    results = []
    
    def worker(worker_id):
        for i in range(3):
            limiter.wait()
            results.append((worker_id, time.time()))
    
    threads = []
    for i in range(3):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # Vérifie que les requêtes sont espacées
    assert len(results) == 9, f"Expected 9 results, got {len(results)}"
    
    # Chaque requête doit être au moins 0.5s après la précédente
    for i in range(1, len(results)):
        prev_time = results[i-1][1]
        curr_time = results[i][1]
        assert curr_time - prev_time >= 0.45, f"Requests too close: {curr_time - prev_time:.2f}s"
    
    print(f"  [OK] 9 requests from 3 workers properly rate-limited")


def test_global_singleton():
    """Test que le singleton global fonctionne."""
    print("TEST: Global singleton")
    
    limiter1 = get_global_rate_limiter(min_delay=1.0)
    limiter2 = get_global_rate_limiter(min_delay=2.0)
    
    # Deuxième appel doit retourner la même instance
    assert limiter1 is limiter2, "Singleton should return same instance"
    assert limiter1.min_delay == 1.0, "First delay should be preserved"
    
    print(f"  [OK] Singleton pattern works correctly")


def test_get_wait_time():
    """Test la méthode get_wait_time."""
    print("TEST: get_wait_time method")
    
    limiter = GlobalRateLimiter(min_delay=1.0)
    
    # Premier appel doit retourner 0
    wait_time = limiter.get_wait_time()
    assert wait_time == 0.0, f"Expected 0.0, got {wait_time}"
    
    # Après un wait, doit être proche de min_delay (car _last_request_time vient d'être mis à jour)
    limiter.wait()
    wait_time = limiter.get_wait_time()
    assert wait_time > 0.9, f"Expected > 0.9s after wait, got {wait_time}"
    assert wait_time <= 1.0, f"Expected <= 1.0s after wait, got {wait_time}"
    
    # Attendre le délai complet
    time.sleep(1.1)
    wait_time = limiter.get_wait_time()
    assert wait_time == 0.0, f"Expected 0.0 after delay, got {wait_time}"
    
    print(f"  [OK] get_wait_time works correctly")


if __name__ == "__main__":
    print("RATE LIMITER TESTS")
    print("=" * 80)
    
    test_basic_rate_limiting()
    test_thread_safety()
    test_global_singleton()
    test_get_wait_time()
    
    print("=" * 80)
    print("ALL TESTS PASSED")