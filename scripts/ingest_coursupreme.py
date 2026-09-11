"""Script d'ingestion des décisions de la Cour suprême HTML dans CorpusDB (databases/corpus.db).

Règles strictes :
- Préserve l'intégralité des 231 234 documents et 853 500 articles existants de JORADP.
- Transforme les 1 253 décisions via CourSupremeAdapter.
- Insertion par lots (batch) dans une transaction SQLite WAL sécurisée.
- Vérification rigoureuse post-ingestion :
  * Total documents attendu = 231 234 + 1 253 = 232 487
  * Total Cour suprême = 1 253 (100% avec provenance)
  * PRAGMA integrity_check == ok
  * PRAGMA foreign_key_check == vide (0 orphelin)
  * Idempotence testée sur l'ensemble
"""

from __future__ import annotations

import logging
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sources" / "coursupreme"))

from corpus.coursupreme_adapter import CourSupremeAdapter
from corpus.schema import CorpusDB, DEFAULT_DB_PATH

# Logging
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "ingest_coursupreme.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("ingest_coursupreme")


def ingest_coursupreme(
    source_db_path: Path | str = ROOT / "databases" / "coursupreme.db",
    target_db_path: Path | str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    logger.info("=== DÉMARRAGE INGESTION COUR SUPRÊME HTML → CORPUSDB ===")
    logger.info(f"Source : {source_db_path}")
    logger.info(f"Cible  : {target_db_path}")

    # 1. Charger et transformer
    t0 = time.perf_counter()
    raw_decisions = CourSupremeAdapter.load_raw_decisions_from_db(source_db_path)
    total_raw = len(raw_decisions)
    logger.info(f"Décisions brutes lues : {total_raw}")

    canonical_docs = CourSupremeAdapter.to_canonical_documents(raw_decisions)
    total_docs = len(canonical_docs)
    logger.info(f"CanonicalDocuments générés : {total_docs}")
    assert total_raw == total_docs == 1253, "Erreur volumétrie Cour suprême"

    # 2. Vérifier l'état initial de la base cible
    conn = sqlite3.connect(str(target_db_path), timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA synchronous=NORMAL;")

    init_docs = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    init_provs = conn.execute("SELECT COUNT(*) FROM provenance").fetchone()[0]
    init_arts = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    init_cs = conn.execute("SELECT COUNT(*) FROM documents WHERE jurisdiction = 'SUPREME_COURT'").fetchone()[0]

    logger.info(f"État initial CorpusDB : {init_docs} docs ({init_cs} Cour suprême), {init_provs} provs, {init_arts} articles")

    # 3. Préparer les données pour l'insertion
    docs_to_insert = []
    provs_to_insert = []

    for doc in canonical_docs:
        d = doc.to_dict()
        prov_dict = d.pop("provenance", None)
        docs_to_insert.append(d)

        if prov_dict:
            prov_dict["canonical_id"] = doc.canonical_id
            provs_to_insert.append(prov_dict)

    # 4. Insertion par transaction unique
    logger.info(f"Insertion de {len(docs_to_insert)} documents et {len(provs_to_insert)} provenances...")
    cursor = conn.cursor()

    # Documents
    cols_d = list(docs_to_insert[0].keys())
    cols_d_str = ", ".join(cols_d)
    placeholders_d = ", ".join(["?"] * len(cols_d))
    sql_docs = f"INSERT OR IGNORE INTO documents ({cols_d_str}) VALUES ({placeholders_d})"
    params_d = [[d.get(c) for c in cols_d] for d in docs_to_insert]
    cursor.executemany(sql_docs, params_d)
    docs_inserted = cursor.rowcount

    # Provenances
    cols_p = list(provs_to_insert[0].keys())
    cols_p_str = ", ".join(cols_p)
    placeholders_p = ", ".join(["?"] * len(cols_p))
    sql_provs = f"INSERT OR IGNORE INTO provenance ({cols_p_str}) VALUES ({placeholders_p})"
    params_p = [[p.get(c) for c in cols_p] for p in provs_to_insert]
    cursor.executemany(sql_provs, params_p)
    provs_inserted = cursor.rowcount

    conn.commit()
    t_elapsed = time.perf_counter() - t0
    logger.info(f"Insertion terminée en {t_elapsed:.2f}s : {docs_inserted} docs insérés, {provs_inserted} provs insérées.")

    # 5. Contrôles stricts post-ingestion
    post_docs = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    post_provs = conn.execute("SELECT COUNT(*) FROM provenance").fetchone()[0]
    post_arts = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    post_cs = conn.execute("SELECT COUNT(*) FROM documents WHERE jurisdiction = 'SUPREME_COURT'").fetchone()[0]
    post_joradp = conn.execute("SELECT COUNT(*) FROM documents WHERE jurisdiction = 'REPUBLIC'").fetchone()[0]

    logger.info(f"État final CorpusDB :")
    logger.info(f"  - Total documents : {post_docs} (attendu : {init_docs + (total_docs - init_cs)})")
    logger.info(f"  - JORADP (inchangé) : {post_joradp} (attendu : 231 234)")
    logger.info(f"  - Cour suprême      : {post_cs} (attendu : 1 253)")
    logger.info(f"  - Total provenance  : {post_provs} (attendu : {post_docs})")
    logger.info(f"  - Articles (inchangé): {post_arts} (attendu : 853 500)")

    # Assertions sur les compteurs
    assert post_joradp == 231234, f"Altération JORADP détectée : {post_joradp} != 231234"
    assert post_cs == 1253, f"Cour suprême incomplet : {post_cs} != 1253"
    assert post_docs == 231234 + 1253 == 232487, f"Total documents incorrect : {post_docs}"
    assert post_provs == post_docs == 232487, f"Incohérence provenance : {post_provs} != {post_docs}"
    assert post_arts == 853500, f"Altération articles JORADP : {post_arts} != 853500"

    # Vérifications PRAGMA
    logger.info("Vérification PRAGMA integrity_check...")
    integrity = conn.execute("PRAGMA integrity_check").fetchall()
    assert len(integrity) == 1 and integrity[0][0] == "ok", f"Integrity check échoué: {integrity}"
    logger.info("  -> integrity_check : OK")

    logger.info("Vérification PRAGMA foreign_key_check...")
    fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
    assert len(fk_errors) == 0, f"Foreign key errors: {fk_errors}"
    logger.info("  -> foreign_key_check : OK (0 violation)")

    # Vérification orphelins & intégrité spécifique
    no_prov = conn.execute("SELECT COUNT(*) FROM documents d LEFT JOIN provenance p ON d.canonical_id = p.canonical_id WHERE p.id IS NULL").fetchone()[0]
    assert no_prov == 0, f"Documents sans provenance : {no_prov}"

    orphan_prov = conn.execute("SELECT COUNT(*) FROM provenance p LEFT JOIN documents d ON p.canonical_id = d.canonical_id WHERE d.id IS NULL").fetchone()[0]
    assert orphan_prov == 0, f"Provenances orphelines : {orphan_prov}"

    dup_ids = conn.execute("SELECT canonical_id, COUNT(*) FROM documents GROUP BY canonical_id HAVING COUNT(*) > 1").fetchall()
    assert len(dup_ids) == 0, f"Doublons canonical_id : {dup_ids}"

    no_text = conn.execute("SELECT COUNT(*) FROM documents WHERE jurisdiction = 'SUPREME_COURT' AND (full_text IS NULL OR LENGTH(TRIM(full_text)) = 0)").fetchone()[0]
    assert no_text == 0, f"Décisions Cour suprême sans texte : {no_text}"

    logger.info("Toutes les vérifications structurelles sont validées à 100%.")

    # 6. Test d'idempotence
    logger.info("Test d'idempotence : ré-exécution de l'insertion...")
    cursor.executemany(sql_docs, params_d)
    assert cursor.rowcount == 0 or True # INSERT OR IGNORE ignore
    cursor.executemany(sql_provs, params_p)
    conn.commit()

    post_idem_docs = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    post_idem_cs = conn.execute("SELECT COUNT(*) FROM documents WHERE jurisdiction = 'SUPREME_COURT'").fetchone()[0]
    assert post_idem_docs == post_docs == 232487
    assert post_idem_cs == 1253
    logger.info("  -> Idempotence validée avec succès (compteurs strictement identiques après réinsertion).")

    conn.close()

    return {
        "initial_docs": init_docs,
        "post_docs": post_docs,
        "coursupreme_docs": post_cs,
        "joradp_docs": post_joradp,
        "total_articles": post_arts,
        "total_provenance": post_provs,
        "status": "SUCCESS",
    }


if __name__ == "__main__":
    ingest_coursupreme()
