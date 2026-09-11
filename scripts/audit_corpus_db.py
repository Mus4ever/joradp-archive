"""Script d'audit exhaustif et rigoureux de databases/corpus.db après ingestion.

Vérifie l'intégralité des 15 points exigés par le protocole de validation.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
from corpus.schema import DEFAULT_DB_PATH
from scripts.ingest_corpus_db import run_ingestion


def audit_corpus_db():
    db_path = DEFAULT_DB_PATH
    print(f"=== AUDIT COMPLET DE CORPUSDB : {db_path} ===\n")
    assert db_path.exists(), f"La base {db_path} n'existe pas !"

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON;")

    audit = {}

    # 1. Compteurs exacts
    n_docs = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    n_provs = conn.execute("SELECT COUNT(*) FROM provenance").fetchone()[0]
    n_arts = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    n_rels = conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0]

    print(f"TABLES PRINCIPALES :")
    print(f"  documents  : {n_docs:,} actes")
    print(f"  provenance : {n_provs:,} fiches de traçabilité")
    print(f"  articles   : {n_arts:,} articles juridiques")
    print(f"  relations  : {n_rels:,} relations\n")

    audit["counts"] = {
        "documents": n_docs,
        "provenance": n_provs,
        "articles": n_arts,
        "relations": n_rels,
    }

    # 2. Intégrité SQLite
    print("CONTROLES D'INTEGRITE :")
    integrity_check = conn.execute("PRAGMA integrity_check").fetchall()
    is_integrity_ok = len(integrity_check) == 1 and integrity_check[0][0] == "ok"
    print(f"  1. PRAGMA integrity_check : {'OK' if is_integrity_ok else integrity_check}")
    audit["integrity_ok"] = is_integrity_ok

    fk_check = conn.execute("PRAGMA foreign_key_check").fetchall()
    is_fk_ok = len(fk_check) == 0
    print(f"  2. PRAGMA foreign_key_check : {'OK (0 violation)' if is_fk_ok else fk_check}")
    audit["foreign_keys_ok"] = is_fk_ok

    # 3. Canonical IDs uniques et non nuls
    null_ids = conn.execute("SELECT COUNT(*) FROM documents WHERE canonical_id IS NULL OR canonical_id = ''").fetchone()[0]
    distinct_ids = conn.execute("SELECT COUNT(DISTINCT canonical_id) FROM documents").fetchone()[0]
    ids_unique = (null_ids == 0) and (distinct_ids == n_docs)
    print(f"  3. Canonical IDs uniques   : {'OK (100% uniques)' if ids_unique else f'ERR (distinct={distinct_ids}, total={n_docs})'}")
    audit["canonical_ids_unique"] = ids_unique

    # 4. Orphelins provenance / document
    prov_without_doc = conn.execute("""
        SELECT COUNT(*) FROM provenance p
        LEFT JOIN documents d ON p.canonical_id = d.canonical_id
        WHERE d.canonical_id IS NULL
    """).fetchone()[0]
    doc_without_prov = conn.execute("""
        SELECT COUNT(*) FROM documents d
        LEFT JOIN provenance p ON d.canonical_id = p.canonical_id
        WHERE p.canonical_id IS NULL
    """).fetchone()[0]
    print(f"  4. Documents sans provenance : {doc_without_prov}")
    print(f"  5. Provenance sans document  : {prov_without_doc}")
    audit["docs_without_prov"] = doc_without_prov
    audit["prov_without_doc"] = prov_without_doc

    # 5. Orphelins articles / document
    art_without_doc = conn.execute("""
        SELECT COUNT(*) FROM articles a
        LEFT JOIN documents d ON a.parent_document_id = d.canonical_id
        WHERE d.canonical_id IS NULL
    """).fetchone()[0]
    print(f"  6. Articles sans document parent : {art_without_doc}")
    audit["articles_without_doc"] = art_without_doc

    # 6. Doublons d'articles (parent_document_id, ordinal)
    art_dups = conn.execute("""
        SELECT COUNT(*) FROM (
            SELECT parent_document_id, ordinal, COUNT(*) as cnt
            FROM articles
            GROUP BY parent_document_id, ordinal
            HAVING cnt > 1
        )
    """).fetchone()[0]
    print(f"  7. Doublons articles (parent, ordinal) : {art_dups}")
    audit["articles_duplicates"] = art_dups

    # 7. Répartition linguistique FR / AR
    print("\nREPARTITIONS JURIDIQUES ET METADONNEES :")
    lang_dist = dict(conn.execute("SELECT language, COUNT(*) FROM documents GROUP BY language").fetchall())
    print(f"  Langues (documents) : {lang_dist}")
    art_lang_dist = dict(conn.execute("SELECT language, COUNT(*) FROM articles GROUP BY language").fetchall())
    print(f"  Langues (articles)  : {art_lang_dist}")
    audit["language_distribution"] = lang_dist

    # 8. Répartition par type de document
    type_dist = dict(conn.execute("SELECT document_type, COUNT(*) FROM documents GROUP BY document_type ORDER BY COUNT(*) DESC").fetchall())
    print(f"  Types d'actes : {type_dist}")
    audit["type_distribution"] = type_dist

    # 9. Couverture temporelle par décennie
    years = conn.execute("SELECT MIN(year), MAX(year), COUNT(DISTINCT year) FROM documents").fetchone()
    print(f"  Années couvertes : {years[0]} -> {years[1]} ({years[2]} années distinctes)")
    audit["year_min"] = years[0]
    audit["year_max"] = years[1]
    audit["years_count"] = years[2]

    # 10. FTS5
    fts_tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND sql LIKE '%fts5%'").fetchall()]
    print(f"  Tables FTS5 présentes : {fts_tables if fts_tables else 'Aucune (FTS5 non activé dans le schéma standard)'}")
    audit["fts5_tables"] = fts_tables

    # 11. Taille du fichier de base de données
    conn.close()
    db_size_bytes = db_path.stat().st_size
    db_size_mb = db_size_bytes / (1024 * 1024)
    print(f"\nTAILLE DU FICHIER CORPUS.DB : {db_size_mb:.2f} Mo ({db_size_bytes:,} octets)")
    audit["db_size_mb"] = round(db_size_mb, 2)
    audit["db_size_bytes"] = db_size_bytes

    # 12. Test d'idempotence : ré-exécution partielle / vérification que les compteurs ne bougent pas
    print("\nTEST D'IDEMPOTENCE (Relance sur 500 fichiers témoins)...")
    t0_idem = time.perf_counter()
    from scripts.ingest_corpus_db import collect_file_tasks, parse_worker, execute_batch_insert
    test_tasks = collect_file_tasks()[:500]
    conn_idem = sqlite3.connect(str(db_path))
    conn_idem.execute("PRAGMA foreign_keys=ON;")
    
    b_docs, b_provs, b_arts = [], [], []
    for t in test_tasks:
        res = parse_worker(t)
        if res["success"]:
            b_docs.extend(res["docs"])
            b_provs.extend(res["provs"])
            b_arts.extend(res["arts"])
    
    # Exécution de l'insert sur des données déjà existantes
    d_ins, p_ins, a_ins = execute_batch_insert(conn_idem, b_docs, b_provs, b_arts)
    conn_idem.close()

    conn_final = sqlite3.connect(str(db_path))
    n_docs_after = conn_final.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    n_arts_after = conn_final.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    conn_final.close()

    is_idempotent = (n_docs_after == n_docs) and (n_arts_after == n_arts)
    print(f"  Actes insérés lors du re-run    : {d_ins} (attendu: 0)")
    print(f"  Articles insérés lors du re-run : {a_ins} (attendu: 0)")
    print(f"  Compteurs après ré-ingestion   : docs={n_docs_after:,} (delta={n_docs_after - n_docs}), arts={n_arts_after:,} (delta={n_arts_after - n_arts})")
    print(f"  IDEMPOTENCE : {'PARFAITE (OUI)' if is_idempotent else 'NON'}")
    audit["idempotency_ok"] = is_idempotent

    # Écriture du rapport JSON d'audit
    out_json = Path("reports/corpus_db_post_ingestion_audit.json")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=2)
    print(f"\nRapport d'audit sauvegardé dans : {out_json}")

    return audit


if __name__ == "__main__":
    audit_corpus_db()
