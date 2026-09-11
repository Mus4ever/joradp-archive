"""Script d'ingestion complète du corpus JORADP dans CorpusDB.

Traite les 10 432 fichiers JORADP (FR + AR, 1962–2026),
extrait les actes et articles via JORADPParser,
et insère l'ensemble de façon idempotente et transactionnelle par batch dans databases/corpus.db.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, ".")

from corpus.joradp_parser import JORADPParser, Language
from corpus.models import Article, CanonicalDocument, DocumentProvenance
from corpus.schema import CorpusDB, DEFAULT_DB_PATH

# Configuration du logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "ingest_corpus_db.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("ingest_corpus_db")


def collect_file_tasks() -> List[Tuple[str, str, int, str]]:
    """Inventorie de manière déterministe les 10 432 fichiers markdown.md."""
    extraction_dir = Path("Extraction")
    fr_dir = extraction_dir / "OCR-Fr"
    ar_dir = extraction_dir / "OCR-Ar"
    tasks: List[Tuple[str, str, int, str]] = []

    for lang_str, base_dir in [("FR", fr_dir), ("AR", ar_dir)]:
        if not base_dir.exists():
            continue
        for year_dir in sorted(base_dir.iterdir()):
            if not year_dir.is_dir():
                continue
            try:
                year = int(year_dir.name)
            except ValueError:
                continue
            for pdf_entry in sorted(year_dir.iterdir()):
                if not pdf_entry.is_dir():
                    continue
                md_path = pdf_entry / "markdown.md"
                if not md_path.exists():
                    stem_md = pdf_entry / f"{pdf_entry.stem}.md"
                    if stem_md.exists():
                        md_path = stem_md
                    else:
                        continue
                m_num = pdf_entry.stem[6:9] if len(pdf_entry.stem) >= 9 else pdf_entry.stem
                tasks.append((str(md_path), lang_str, year, m_num))

    return tasks


def parse_worker(task: Tuple[str, str, int, str]) -> Dict[str, Any]:
    """Parse un fichier et renvoie les données sérialisables pour insertion."""
    file_path, lang_str, year, jo_num = task
    lang = Language.FR if lang_str == "FR" else Language.AR

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()

        parsed_items = JORADPParser.parse_text(
            text=text,
            year=year,
            jo_number=jo_num,
            lang=lang,
            raw_path=file_path,
        )

        docs_data = []
        provs_data = []
        arts_data = []

        for doc, articles in parsed_items:
            # Sérialisation Document
            d = doc.to_dict()
            prov_dict = d.pop("provenance", None)
            docs_data.append(d)

            # Sérialisation Provenance
            if doc.provenance:
                p = doc.provenance.to_dict()
                p["canonical_id"] = doc.canonical_id
                provs_data.append(p)
            elif prov_dict:
                prov_dict["canonical_id"] = doc.canonical_id
                provs_data.append(prov_dict)

            # Sérialisation Articles
            for a in articles:
                ad = a.to_dict()
                ad.pop("id", None)
                arts_data.append(ad)

        return {
            "success": True,
            "file": file_path,
            "docs": docs_data,
            "provs": provs_data,
            "arts": arts_data,
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "file": file_path,
            "docs": [],
            "provs": [],
            "arts": [],
            "error": str(e),
        }


def execute_batch_insert(
    conn: sqlite3.Connection,
    batch_docs: List[Dict[str, Any]],
    batch_provs: List[Dict[str, Any]],
    batch_arts: List[Dict[str, Any]],
) -> Tuple[int, int, int]:
    """Insère un lot de documents, provenances et articles au sein d'une transaction unique."""
    if not batch_docs and not batch_provs and not batch_arts:
        return 0, 0, 0

    cursor = conn.cursor()

    # Insertion Documents
    docs_inserted = 0
    if batch_docs:
        cols = list(batch_docs[0].keys())
        cols_str = ", ".join(cols)
        placeholders = ", ".join(["?"] * len(cols))
        sql_docs = f"INSERT OR IGNORE INTO documents ({cols_str}) VALUES ({placeholders})"
        param_list = [[d.get(c) for c in cols] for d in batch_docs]
        cursor.executemany(sql_docs, param_list)
        docs_inserted = cursor.rowcount

    # Insertion Provenance
    provs_inserted = 0
    if batch_provs:
        cols_p = list(batch_provs[0].keys())
        cols_p_str = ", ".join(cols_p)
        placeholders_p = ", ".join(["?"] * len(cols_p))
        sql_provs = f"INSERT OR IGNORE INTO provenance ({cols_p_str}) VALUES ({placeholders_p})"
        param_list_p = [[p.get(c) for c in cols_p] for p in batch_provs]
        cursor.executemany(sql_provs, param_list_p)
        provs_inserted = cursor.rowcount

    # Insertion Articles
    arts_inserted = 0
    if batch_arts:
        cols_a = list(batch_arts[0].keys())
        cols_a_str = ", ".join(cols_a)
        placeholders_a = ", ".join(["?"] * len(cols_a))
        sql_arts = f"INSERT OR IGNORE INTO articles ({cols_a_str}) VALUES ({placeholders_a})"
        param_list_a = [[a.get(c) for c in cols_a] for a in batch_arts]
        cursor.executemany(sql_arts, param_list_a)
        arts_inserted = cursor.rowcount

    conn.commit()
    return docs_inserted, provs_inserted, arts_inserted


def run_ingestion(db_path: Path = DEFAULT_DB_PATH, batch_size_files: int = 250) -> Dict[str, Any]:
    """Orchestre l'ingestion complète."""
    tasks = collect_file_tasks()
    total_files = len(tasks)
    logger.info(f"=== DEMARRAGE INGESTION CORPUSDB : {total_files} FICHIERS ===")
    logger.info(f"Cible SQLite : {db_path.resolve()}")

    # Initialisation de la base
    with CorpusDB(db_path) as db:
        pass  # Garantit la création des tables et index avec WAL et foreign keys

    conn = sqlite3.connect(str(db_path), timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA cache_size=-64000;")  # 64 Mo de cache RAM

    workers = min(16, os.cpu_count() or 4)
    logger.info(f"Workers d'extraction parallèles : {workers}")

    t_start = time.perf_counter()
    processed_files = 0
    failed_files = 0
    errors_log = []

    total_docs_inserted = 0
    total_provs_inserted = 0
    total_arts_inserted = 0

    batch_docs: List[Dict[str, Any]] = []
    batch_provs: List[Dict[str, Any]] = []
    batch_arts: List[Dict[str, Any]] = []

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(parse_worker, task): task for task in tasks}

        for future in as_completed(futures):
            res = future.result()
            processed_files += 1

            if not res["success"]:
                failed_files += 1
                errors_log.append({"file": res["file"], "error": res["error"]})
                logger.error(f"Erreur parsing {res['file']} : {res['error']}")
            else:
                batch_docs.extend(res["docs"])
                batch_provs.extend(res["provs"])
                batch_arts.extend(res["arts"])

            # Ingestion par lot
            if processed_files % batch_size_files == 0 or processed_files == total_files:
                d_ins, p_ins, a_ins = execute_batch_insert(conn, batch_docs, batch_provs, batch_arts)
                total_docs_inserted += d_ins
                total_provs_inserted += p_ins
                total_arts_inserted += a_ins
                batch_docs.clear()
                batch_provs.clear()
                batch_arts.clear()

                elapsed = time.perf_counter() - t_start
                rate = processed_files / elapsed if elapsed > 0 else 0
                logger.info(
                    f"Progression : {processed_files:5d}/{total_files} numéros ({processed_files/total_files*100:5.1f}%) | "
                    f"Vitesse : {rate:5.1f} num/s | "
                    f"Actes insérés : {total_docs_inserted:,} | Articles insérés : {total_arts_inserted:,}"
                )

    conn.close()
    t_total = time.perf_counter() - t_start
    logger.info(f"\nIngestion terminée en {t_total:.2f}s ({processed_files/t_total:.1f} numéros/s)")

    return {
        "total_files": total_files,
        "processed_files": processed_files,
        "failed_files": failed_files,
        "total_docs_inserted": total_docs_inserted,
        "total_provs_inserted": total_provs_inserted,
        "total_arts_inserted": total_arts_inserted,
        "time_seconds": round(t_total, 2),
        "errors": errors_log,
    }


if __name__ == "__main__":
    run_ingestion()
