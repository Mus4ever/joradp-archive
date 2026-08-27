"""
Vérifie comment le code actuel génère les URLs
"""

import sys
sys.path.append('tools')

from database import JoradpDatabase

db = JoradpDatabase()
with db:
    conn = db.connect()
    
    # Vérifie FR 1962 (legacy)
    fr_1962 = conn.execute("""
        SELECT url_complete FROM sources 
        WHERE annee = 1962 AND langue = 'FR' AND numero = '001'
    """).fetchone()
    
    if fr_1962:
        print(f"FR 1962-001: {fr_1962[0]}")
    
    # Vérifie AR 1983 (legacy)
    ar_1983 = conn.execute("""
        SELECT url_complete FROM sources 
        WHERE annee = 1983 AND langue = 'AR' AND numero = '001'
    """).fetchone()
    
    if ar_1983:
        print(f"AR 1983-001: {ar_1983[0]}")
    
    # Vérifie FR 2000 (post-1993)
    fr_2000 = conn.execute("""
        SELECT url_complete FROM sources 
        WHERE annee = 2000 AND langue = 'FR' AND numero = '001'
    """).fetchone()
    
    if fr_2000:
        print(f"FR 2000-001: {fr_2000[0]}")
    
    # Vérifie AR 2000 (post-1993)
    ar_2000 = conn.execute("""
        SELECT url_complete FROM sources 
        WHERE annee = 2000 AND langue = 'AR' AND numero = '001'
    """).fetchone()
    
    if ar_2000:
        print(f"AR 2000-001: {ar_2000[0]}")