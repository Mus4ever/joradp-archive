"""Stockage SQLite des décisions de la Cour suprême.

Table unique `decisions` + HTML brut archivé sur disque (RAW jamais détruit).

Réutilise le style du JORADPDatabase ( WAL, context manager, statuts ).
La base vit dans databases/coursupreme.db (ignoré par Git via *.db).
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[2]

SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    court TEXT NOT NULL DEFAULT 'المحكمة العليا',
    chamber TEXT,
    chamber_class TEXT,
    decision_number TEXT,
    date TEXT,
    subject TEXT,
    parties TEXT,
    keywords TEXT,
    legal_references TEXT,
    principle TEXT,
    appeal_ground TEXT,
    court_response TEXT,
    unconstitutionality_grounds TEXT,
    unconstitutionality_response TEXT,
    disposition TEXT,
    president TEXT,
    rapporteur TEXT,
    clerk TEXT,
    extra_sections TEXT,
    extra_metadata TEXT,
    text TEXT,
    language TEXT DEFAULT 'AR',
    source_url TEXT NOT NULL UNIQUE,
    source_type TEXT DEFAULT 'html_page',
    content_hash TEXT,
    raw_path TEXT,
    discovered_at TEXT,
    downloaded_at TEXT,
    category TEXT,
    status TEXT DEFAULT 'decouvert',
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_decisions_status ON decisions(status);
CREATE INDEX IF NOT EXISTS idx_decisions_number ON decisions(decision_number);
CREATE INDEX IF NOT EXISTS idx_decisions_date ON decisions(date);
CREATE INDEX IF NOT EXISTS idx_decisions_chamber ON decisions(chamber);
CREATE INDEX IF NOT EXISTS idx_decisions_hash ON decisions(content_hash);
"""


class DecisionStore:
    """Accès SQLite avec reprise sur interruption (statuts)."""

    def __init__(self, db_path: Optional[str] = None, raw_dir: Optional[Path] = None):
        self.db_path = db_path or str(ROOT / "databases" / "coursupreme.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.raw_dir = Path(raw_dir) if raw_dir else ROOT / "raw" / "coursupreme"
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

    def add_discovered(self, source_url: str, category: Optional[str]) -> bool:
        """Enregistre une URL découverte. True si nouvelle, False si déjà connue."""
        conn = self.connect()
        cur = conn.execute(
            "INSERT OR IGNORE INTO decisions (source_url, category, status, discovered_at) "
            "VALUES (?, ?, 'decouvert', datetime('now'))",
            (source_url, category),
        )
        conn.commit()
        return cur.rowcount > 0

    def add_discovered_batch(self, urls_with_category) -> int:
        """[(url, category), ...] → nombre de nouvelles URLs."""
        new = 0
        for url, cat in urls_with_category:
            if self.add_discovered(url, cat):
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
            INSERT INTO decisions (court, chamber, chamber_class, decision_number, date,
                subject, parties, keywords, legal_references,
                principle, appeal_ground, court_response,
                unconstitutionality_grounds, unconstitutionality_response,
                disposition, president, rapporteur, clerk,
                extra_sections, text, language,
                source_url, source_type, content_hash, raw_path,
                discovered_at, downloaded_at, category, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?,?,'telecharge')
            ON CONFLICT(source_url) DO UPDATE SET
                court=excluded.court, chamber=excluded.chamber,
                chamber_class=excluded.chamber_class,
                decision_number=excluded.decision_number, date=excluded.date,
                subject=excluded.subject, parties=excluded.parties,
                keywords=excluded.keywords,
                legal_references=excluded.legal_references,
                principle=excluded.principle, appeal_ground=excluded.appeal_ground,
                court_response=excluded.court_response,
                unconstitutionality_grounds=excluded.unconstitutionality_grounds,
                unconstitutionality_response=excluded.unconstitutionality_response,
                disposition=excluded.disposition, president=excluded.president,
                rapporteur=excluded.rapporteur, clerk=excluded.clerk,
                extra_sections=excluded.extra_sections, text=excluded.text,
                language=excluded.language, source_type=excluded.source_type,
                content_hash=excluded.content_hash, raw_path=excluded.raw_path,
                downloaded_at=excluded.downloaded_at,
                category=excluded.category, status='telecharge', error=NULL
            """,
            (
                d.court, d.chamber, d.chamber_class, d.decision_number, d.date,
                d.subject, d.parties, d.keywords, d.legal_references,
                d.principle, d.appeal_ground, d.court_response,
                d.unconstitutionality_grounds, d.unconstitutionality_response,
                d.disposition, d.president, d.rapporteur, d.clerk,
                json.dumps(d.extra_sections, ensure_ascii=False),
                d.text, d.language,
                d.source_url, d.source_type, d.content_hash, str(raw_path),
                d.discovered_at or None, d.category,
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

    # --- Requêtes --------------------------------------------------------------

    def pending(self, limit: Optional[int] = None) -> List[sqlite3.Row]:
        """URLs à télécharger : découvertes ou en erreur (reprise)."""
        query = (
            "SELECT id, source_url, category FROM decisions "
            "WHERE status IN ('decouvert', 'erreur') ORDER BY id"
        )
        if limit:
            query += f" LIMIT {int(limit)}"
        return self.connect().execute(query).fetchall()

    def counts_by_status(self) -> dict:
        rows = self.connect().execute(
            "SELECT status, COUNT(*) AS n FROM decisions GROUP BY status"
        ).fetchall()
        return {r["status"]: r["n"] for r in rows}

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
