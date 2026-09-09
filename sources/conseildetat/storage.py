"""Stockage SQLite des décisions du Conseil d'État.

Table unique `decisions` + HTML brut archivé sur disque (RAW jamais détruit).

Réutilise le style du DecisionStore de la Cour suprême (WAL, context manager, statuts).
La base vit dans databases/conseildetat.db (ignoré par Git via *.db).
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[2]

SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nid INTEGER,
    court TEXT NOT NULL DEFAULT 'مجلس الدولة',
    node_type TEXT DEFAULT 'jurisprudence',
    decision_number TEXT,
    date TEXT,
    date_raw TEXT,
    year TEXT,
    chamber TEXT,
    section TEXT,
    keywords TEXT,
    classification TEXT,
    subject TEXT,
    principle TEXT,
    pdf_url TEXT,
    pdf_path TEXT,
    pdf_hash TEXT,
    text TEXT,
    language TEXT DEFAULT 'AR',
    source_url TEXT NOT NULL UNIQUE,
    source_type TEXT DEFAULT 'html_page',
    content_hash TEXT,
    raw_path TEXT,
    discovered_at TEXT,
    downloaded_at TEXT,
    status TEXT DEFAULT 'decouvert',
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_ce_status ON decisions(status);
CREATE INDEX IF NOT EXISTS idx_ce_number ON decisions(decision_number);
CREATE INDEX IF NOT EXISTS idx_ce_date ON decisions(date);
CREATE INDEX IF NOT EXISTS idx_ce_chamber ON decisions(chamber);
CREATE INDEX IF NOT EXISTS idx_ce_hash ON decisions(content_hash);
CREATE INDEX IF NOT EXISTS idx_ce_nid ON decisions(nid);
CREATE INDEX IF NOT EXISTS idx_ce_node_type ON decisions(node_type);
"""


class DecisionStore:
    """Accès SQLite avec reprise sur interruption (statuts)."""

    def __init__(self, db_path: Optional[str] = None, raw_dir: Optional[Path] = None):
        self.db_path = db_path or str(ROOT / "databases" / "conseildetat.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.raw_dir = Path(raw_dir) if raw_dir else ROOT / "raw" / "conseildetat"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
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

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def initialize_schema(self):
        self.connect().executescript(SCHEMA)
        self._conn.commit()

    # --- Découverte ----------------------------------------------------------

    def add_discovered(self, source_url: str, nid: Optional[int] = None,
                       node_type: str = "jurisprudence") -> bool:
        """Enregistre une URL découverte. True si nouvelle, False si déjà connue."""
        conn = self.connect()
        cur = conn.execute(
            "INSERT OR IGNORE INTO decisions (source_url, nid, node_type, status, discovered_at) "
            "VALUES (?, ?, ?, 'decouvert', datetime('now'))",
            (source_url, nid, node_type),
        )
        conn.commit()
        return cur.rowcount > 0

    def add_discovered_batch(self, entries) -> int:
        """[(url, nid, node_type), ...] → nombre de nouvelles URLs."""
        new = 0
        for url, nid, node_type in entries:
            if self.add_discovered(url, nid, node_type):
                new += 1
        return new

    # --- Téléchargement / parsing ---------------------------------------------

    def save_decision(self, decision, raw_html: bytes) -> None:
        """Persiste la décision parsée + le HTML brut sur disque (RAW conservé)."""
        conn = self.connect()
        raw_path = self._raw_path_for(decision.source_url)
        raw_path.write_bytes(raw_html)
        d = decision
        conn.execute(
            """
            INSERT INTO decisions (nid, court, node_type, decision_number, date,
                date_raw, year, chamber, section, keywords, classification,
                subject, principle, pdf_url, text, language,
                source_url, source_type, content_hash, raw_path,
                discovered_at, downloaded_at, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),'telecharge')
            ON CONFLICT(source_url) DO UPDATE SET
                nid=excluded.nid, court=excluded.court,
                node_type=excluded.node_type,
                decision_number=excluded.decision_number, date=excluded.date,
                date_raw=excluded.date_raw, year=excluded.year,
                chamber=excluded.chamber, section=excluded.section,
                keywords=excluded.keywords,
                classification=excluded.classification,
                subject=excluded.subject,
                principle=excluded.principle, pdf_url=excluded.pdf_url,
                text=excluded.text, language=excluded.language,
                source_type=excluded.source_type,
                content_hash=excluded.content_hash, raw_path=excluded.raw_path,
                downloaded_at=datetime('now'),
                status='telecharge', error=NULL
            """,
            (
                d.nid, d.court, d.node_type, d.decision_number, d.date,
                d.date_raw, d.year, d.chamber, d.section, d.keywords,
                d.classification, d.subject, d.principle, d.pdf_url,
                d.text, d.language,
                d.source_url, d.source_type, d.content_hash, str(raw_path),
                d.discovered_at or None,
            ),
        )
        conn.commit()

    def mark_error(self, source_url: str, error: str) -> None:
        conn = self.connect()
        conn.execute(
            "UPDATE decisions SET status='erreur', error=? WHERE source_url=?",
            (error[:2000], source_url),
        )
        conn.commit()

    def save_pdf_info(self, source_url: str, pdf_path: str, pdf_hash: str) -> None:
        """Enregistre le chemin et hash du PDF téléchargé."""
        conn = self.connect()
        conn.execute(
            "UPDATE decisions SET pdf_path=?, pdf_hash=? WHERE source_url=?",
            (pdf_path, pdf_hash, source_url),
        )
        conn.commit()

    # --- Requêtes --------------------------------------------------------------

    def pending(self, limit: Optional[int] = None) -> List[sqlite3.Row]:
        """URLs à télécharger : découvertes ou en erreur (reprise)."""
        query = (
            "SELECT id, source_url, nid, node_type FROM decisions "
            "WHERE status IN ('decouvert', 'erreur') ORDER BY nid"
        )
        if limit:
            query += f" LIMIT {int(limit)}"
        return self.connect().execute(query).fetchall()

    def decisions_with_pdf(self, downloaded_only: bool = False) -> List[sqlite3.Row]:
        """Décisions ayant un pdf_url renseigné."""
        query = "SELECT id, source_url, nid, pdf_url, pdf_path, pdf_hash FROM decisions WHERE pdf_url IS NOT NULL"
        if downloaded_only:
            query += " AND pdf_path IS NOT NULL"
        else:
            query += " AND (pdf_path IS NULL OR pdf_path = '')"
        query += " ORDER BY nid"
        return self.connect().execute(query).fetchall()

    def counts_by_status(self) -> dict:
        rows = self.connect().execute(
            "SELECT status, COUNT(*) AS n FROM decisions GROUP BY status"
        ).fetchall()
        return {r["status"]: r["n"] for r in rows}

    def counts_by_type(self) -> dict:
        rows = self.connect().execute(
            "SELECT node_type, COUNT(*) AS n FROM decisions GROUP BY node_type"
        ).fetchall()
        return {r["node_type"]: r["n"] for r in rows}

    def duplicate_hashes(self) -> List[dict]:
        """Décisions partageant le même content_hash (contenu identique)."""
        rows = self.connect().execute(
            "SELECT content_hash, COUNT(*) AS n, GROUP_CONCAT(source_url) AS urls "
            "FROM decisions WHERE content_hash IS NOT NULL "
            "GROUP BY content_hash HAVING n > 1"
        ).fetchall()
        return [dict(r) for r in rows]

    def _raw_path_for(self, source_url: str) -> Path:
        import hashlib
        h = hashlib.sha256(source_url.encode()).hexdigest()[:16]
        return self.raw_dir / f"{h}.html"
