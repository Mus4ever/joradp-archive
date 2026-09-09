"""Stockage SQLite des ressources et de l'index de la revue.

Tables (base databases/coursupreme_revue.db, séparée de la base décisions) :
  - revue_resources : inventaire + téléchargements (PDF, SHA-256, statuts)
  - revue_index     : entrées du guide de recherche (raw + normalized)

Réutilise le style JORADP (WAL, context manager, statuts, reprise).
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[3]

SCHEMA = """
CREATE TABLE IF NOT EXISTS revue_resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    url TEXT NOT NULL UNIQUE,
    resource_type TEXT DEFAULT 'OTHER',
    issue_number INTEGER,
    issue_year INTEGER,
    language TEXT DEFAULT 'AR',
    pdf_url TEXT,
    local_path TEXT,
    size_bytes INTEGER,
    sha256 TEXT,
    pdf_pages INTEGER,
    downloaded_at TEXT,
    status TEXT DEFAULT 'decouvert',
    error TEXT,
    discovery_methods TEXT,
    discovered_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_rr_status ON revue_resources(status);
CREATE INDEX IF NOT EXISTS idx_rr_year ON revue_resources(issue_year);

CREATE TABLE IF NOT EXISTS revue_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_number TEXT,
    decision_year INTEGER,
    issue_number INTEGER,
    issue_year INTEGER,
    start_page INTEGER,
    chamber TEXT,
    subject TEXT,
    principle TEXT,
    legal_reference TEXT,
    source_pdf TEXT,
    source_page INTEGER,
    raw_text TEXT,
    normalized_text TEXT,
    parser_status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_ri_number ON revue_index(decision_number);
CREATE INDEX IF NOT EXISTS idx_ri_issue ON revue_index(issue_year, issue_number);
CREATE INDEX IF NOT EXISTS idx_ri_status ON revue_index(parser_status);
"""


class RevueStore:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(ROOT / "databases" / "coursupreme_revue.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA synchronous = NORMAL")
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        self.connect()
        self.initialize_schema()
        return self

    def __exit__(self, *a):
        self.close()

    def initialize_schema(self):
        self.connect().executescript(SCHEMA)
        self._conn.commit()

    # --- Ressources -----------------------------------------------------------

    def upsert_resource(self, rec) -> None:
        conn = self.connect()
        conn.execute(
            """INSERT INTO revue_resources
               (title, url, resource_type, issue_number, issue_year, language,
                pdf_url, discovery_methods, status)
               VALUES (?,?,?,?,?,?,?,?, 'decouvert')
               ON CONFLICT(url) DO UPDATE SET
                 title=excluded.title, resource_type=excluded.resource_type,
                 issue_number=excluded.issue_number, issue_year=excluded.issue_year,
                 pdf_url=COALESCE(NULLIF(excluded.pdf_url,''), revue_resources.pdf_url),
                 discovery_methods=excluded.discovery_methods""",
            (rec["title"], rec["url"], rec["resource_type"], rec["issue_number"],
             rec["issue_year"], rec.get("language", "AR"), rec.get("pdf_url") or "",
             json.dumps(rec.get("discovery_methods", []), ensure_ascii=False)),
        )
        conn.commit()

    def mark_downloaded(self, url: str, local_path: str, size: int,
                        sha256: str, pages: Optional[int]) -> None:
        conn = self.connect()
        conn.execute(
            """UPDATE revue_resources
               SET status='telecharge', local_path=?, size_bytes=?, sha256=?,
                   pdf_pages=?, downloaded_at=datetime('now'), error=NULL
               WHERE url=?""",
            (local_path, size, sha256, pages, url),
        )
        conn.commit()

    def mark_error(self, url: str, error: str) -> None:
        conn = self.connect()
        conn.execute("UPDATE revue_resources SET status='erreur', error=? WHERE url=?",
                     (error[:2000], url))
        conn.commit()

    def pending_pdfs(self) -> List[sqlite3.Row]:
        return self.connect().execute(
            "SELECT url, pdf_url, resource_type, issue_year, issue_number, title "
            "FROM revue_resources "
            "WHERE pdf_url IS NOT NULL AND pdf_url != '' "
            "AND status IN ('decouvert','erreur') "
            "ORDER BY resource_type, issue_year, issue_number"
        ).fetchall()

    def counts_by_status(self) -> dict:
        rows = self.connect().execute(
            "SELECT status, COUNT(*) n FROM revue_resources GROUP BY status").fetchall()
        return {r["status"]: r["n"] for r in rows}

    # --- Index du guide ---------------------------------------------------------

    def insert_entries(self, entries) -> int:
        conn = self.connect()
        n = 0
        for e in entries:
            conn.execute(
                """INSERT INTO revue_index
                   (decision_number, decision_year, issue_number, issue_year,
                    start_page, chamber, subject, principle, legal_reference,
                    source_pdf, source_page, raw_text, normalized_text, parser_status)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (e.get("decision_number"), e.get("decision_year"),
                 e.get("issue_number"), e.get("issue_year"), e.get("start_page"),
                 e.get("chamber"), e.get("subject"), e.get("principle"),
                 e.get("legal_reference"), e.get("source_pdf"), e.get("source_page"),
                 e.get("raw_text"), e.get("normalized_text"), e.get("parser_status", "ok")),
            )
            n += 1
        conn.commit()
        return n

    def index_stats(self) -> dict:
        conn = self.connect()
        total = conn.execute("SELECT COUNT(*) n FROM revue_index").fetchone()["n"]
        by_status = {r["status"]: r["n"] for r in conn.execute(
            "SELECT parser_status status, COUNT(*) n FROM revue_index GROUP BY parser_status")}
        years = conn.execute(
            "SELECT MIN(COALESCE(decision_year, issue_year)) a, "
            "MAX(COALESCE(decision_year, issue_year)) b FROM revue_index").fetchone()
        return {"total": total, "par_statut": by_status,
                "annees": (years["a"], years["b"]) if total else None}
