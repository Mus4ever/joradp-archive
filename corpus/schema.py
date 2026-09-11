"""Schéma SQLite canonique unifié — databases/corpus.db

Gère la base de données du corpus juridique canonique avec 4 tables :
    - ``documents``   : 1 ligne par document juridique unifié
    - ``provenance``  : 1 ligne par document, traçabilité vers la source
    - ``articles``    : Articles individuels des actes JORADP
    - ``relations``   : Liens inter-documents (doublons, bilinguisme, citations)

Principes :
    - Mode WAL pour la concurrence lecture/écriture.
    - Clés étrangères activées (``PRAGMA foreign_keys = ON``).
    - INSERT OR IGNORE sur ``canonical_id`` pour l'idempotence.
    - Aucune suppression automatique — le dédoublonnage passe par ``relations``.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

from corpus.models import (
    CanonicalDocument,
    Article,
    DocumentProvenance,
)

# ──────────────────────────────────────────────────────────────────────
# Chemins
# ──────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "databases" / "corpus.db"


# ──────────────────────────────────────────────────────────────────────
# DDL — Définition des tables et index
# ──────────────────────────────────────────────────────────────────────

SCHEMA_DOCUMENTS = """
CREATE TABLE IF NOT EXISTS documents (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_id          TEXT NOT NULL UNIQUE,

    -- Classification juridique
    document_type         TEXT NOT NULL,
    document_nature       TEXT NOT NULL,
    jurisdiction          TEXT NOT NULL,
    court_level           TEXT NOT NULL,

    -- Métadonnées juridiques
    chamber               TEXT,
    section               TEXT,
    title                 TEXT,
    document_number       TEXT,
    publication_number    TEXT,
    date                  TEXT,
    year                  INTEGER,
    language              TEXT NOT NULL,

    -- Contenu textuel
    subject               TEXT,
    keywords              TEXT,
    legal_references      TEXT,
    principle             TEXT,
    court_response        TEXT,
    disposition           TEXT,
    full_text             TEXT,
    text_format           TEXT DEFAULT 'plain_text',

    -- Qualité et extraction
    text_completeness     TEXT NOT NULL,
    extraction_method     TEXT NOT NULL,
    extraction_quality    TEXT NOT NULL,

    -- Relations inter-documents
    language_pair_id      TEXT,
    parent_document_id    TEXT,

    -- Intégrité
    canonical_hash        TEXT,

    -- Anonymisation
    anonymization_status  TEXT DEFAULT 'NOT_ANONYMIZED',

    -- Horodatage
    created_at            TEXT DEFAULT (datetime('now')),
    updated_at            TEXT DEFAULT (datetime('now'))
);
"""

SCHEMA_PROVENANCE = """
CREATE TABLE IF NOT EXISTS provenance (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_id    TEXT NOT NULL UNIQUE,
    source_db       TEXT NOT NULL,
    source_table    TEXT NOT NULL,
    source_id       INTEGER NOT NULL,
    source_url      TEXT,
    raw_path        TEXT,
    pdf_path        TEXT,
    content_hash    TEXT,
    ingested_at     TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (canonical_id) REFERENCES documents(canonical_id)
);
"""

SCHEMA_ARTICLES = """
CREATE TABLE IF NOT EXISTS articles (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_document_id    TEXT NOT NULL,
    article_number        TEXT NOT NULL,
    title                 TEXT,
    text                  TEXT NOT NULL,
    language              TEXT NOT NULL,
    ordinal               INTEGER NOT NULL,
    created_at            TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (parent_document_id) REFERENCES documents(canonical_id)
);
"""

SCHEMA_RELATIONS = """
CREATE TABLE IF NOT EXISTS relations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id       TEXT NOT NULL,
    target_id       TEXT NOT NULL,
    relation_type   TEXT NOT NULL,
    confidence      REAL,
    metadata        TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(source_id, target_id, relation_type),
    FOREIGN KEY (source_id) REFERENCES documents(canonical_id),
    FOREIGN KEY (target_id) REFERENCES documents(canonical_id)
);
"""

INDEXES = [
    # documents
    "CREATE INDEX IF NOT EXISTS idx_doc_type ON documents(document_type);",
    "CREATE INDEX IF NOT EXISTS idx_doc_nature ON documents(document_nature);",
    "CREATE INDEX IF NOT EXISTS idx_doc_jurisdiction ON documents(jurisdiction);",
    "CREATE INDEX IF NOT EXISTS idx_doc_year ON documents(year);",
    "CREATE INDEX IF NOT EXISTS idx_doc_language ON documents(language);",
    "CREATE INDEX IF NOT EXISTS idx_doc_completeness ON documents(text_completeness);",
    "CREATE INDEX IF NOT EXISTS idx_doc_hash ON documents(canonical_hash);",
    "CREATE INDEX IF NOT EXISTS idx_doc_parent ON documents(parent_document_id);",
    "CREATE INDEX IF NOT EXISTS idx_doc_search ON documents(jurisdiction, document_number, date, chamber);",
    # provenance
    "CREATE INDEX IF NOT EXISTS idx_prov_source ON provenance(source_db, source_table, source_id);",
    # articles
    "CREATE INDEX IF NOT EXISTS idx_art_parent ON articles(parent_document_id);",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_art_parent_ordinal ON articles(parent_document_id, ordinal);",
    # relations
    "CREATE INDEX IF NOT EXISTS idx_rel_source ON relations(source_id);",
    "CREATE INDEX IF NOT EXISTS idx_rel_target ON relations(target_id);",
    "CREATE INDEX IF NOT EXISTS idx_rel_type ON relations(relation_type);",
]


# ──────────────────────────────────────────────────────────────────────
# Classe CorpusDB — Gestionnaire de la base canonique
# ──────────────────────────────────────────────────────────────────────

class CorpusDB:
    """Gestionnaire SQLite du corpus canonique unifié.

    Usage :
        >>> with CorpusDB() as db:
        ...     db.insert_document(doc)
        ...     db.insert_provenance(doc.canonical_id, prov)

    La base est créée automatiquement à la première ouverture.
    Le mode WAL et les foreign keys sont activés par défaut.
    """

    def __init__(self, db_path: Optional[str | Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.conn: Optional[sqlite3.Connection] = None

    # ── Context Manager ──────────────────────────────────────────────

    def __enter__(self) -> "CorpusDB":
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def open(self) -> None:
        """Ouvre la connexion et initialise le schéma si nécessaire."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA foreign_keys=ON;")
        self._init_schema()

    def close(self) -> None:
        """Ferme la connexion proprement."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def _init_schema(self) -> None:
        """Crée les tables et index si inexistants."""
        assert self.conn is not None
        self.conn.executescript(SCHEMA_DOCUMENTS)
        self.conn.executescript(SCHEMA_PROVENANCE)
        self.conn.executescript(SCHEMA_ARTICLES)
        self.conn.executescript(SCHEMA_RELATIONS)
        for idx_sql in INDEXES:
            self.conn.execute(idx_sql)
        self.conn.commit()

    # ── Insertion ─────────────────────────────────────────────────────

    def insert_document(self, doc: CanonicalDocument) -> bool:
        """Insère un document canonique. Retourne True si inséré, False si doublon.

        Utilise INSERT OR IGNORE pour l'idempotence sur ``canonical_id``.
        """
        assert self.conn is not None
        d = doc.to_dict()
        # Extraire la provenance (gérée séparément)
        d.pop("provenance", None)

        cols = ", ".join(d.keys())
        placeholders = ", ".join(["?"] * len(d))
        sql = f"INSERT OR IGNORE INTO documents ({cols}) VALUES ({placeholders})"

        cursor = self.conn.execute(sql, list(d.values()))
        self.conn.commit()
        return cursor.rowcount > 0

    def insert_provenance(self, canonical_id: str, prov: DocumentProvenance) -> bool:
        """Insère la provenance d'un document. Retourne True si inséré."""
        assert self.conn is not None
        d = prov.to_dict()
        d["canonical_id"] = canonical_id

        cols = ", ".join(d.keys())
        placeholders = ", ".join(["?"] * len(d))
        sql = f"INSERT OR IGNORE INTO provenance ({cols}) VALUES ({placeholders})"

        cursor = self.conn.execute(sql, list(d.values()))
        self.conn.commit()
        return cursor.rowcount > 0

    def insert_article(self, article: Article) -> bool:
        """Insère un article JORADP. Retourne True si inséré."""
        assert self.conn is not None
        d = article.to_dict()
        d.pop("id", None)  # Auto-increment

        cols = ", ".join(d.keys())
        placeholders = ", ".join(["?"] * len(d))
        sql = f"INSERT INTO articles ({cols}) VALUES ({placeholders})"

        cursor = self.conn.execute(sql, list(d.values()))
        self.conn.commit()
        return cursor.rowcount > 0

    def insert_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        confidence: Optional[float] = None,
        metadata: Optional[str] = None,
    ) -> bool:
        """Insère une relation entre deux documents. Retourne True si inséré."""
        assert self.conn is not None
        sql = """INSERT OR IGNORE INTO relations
                 (source_id, target_id, relation_type, confidence, metadata)
                 VALUES (?, ?, ?, ?, ?)"""
        cursor = self.conn.execute(
            sql, (source_id, target_id, relation_type, confidence, metadata)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    # ── Lecture ────────────────────────────────────────────────────────

    def get_document(self, canonical_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un document avec sa provenance jointe."""
        assert self.conn is not None
        row = self.conn.execute(
            """SELECT d.*, p.source_db, p.source_table, p.source_id,
                      p.source_url, p.raw_path, p.pdf_path,
                      p.content_hash, p.ingested_at
               FROM documents d
               LEFT JOIN provenance p ON d.canonical_id = p.canonical_id
               WHERE d.canonical_id = ?""",
            (canonical_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_articles(self, parent_document_id: str) -> List[Dict[str, Any]]:
        """Récupère tous les articles d'un acte JORADP, triés par ordinal."""
        assert self.conn is not None
        rows = self.conn.execute(
            "SELECT * FROM articles WHERE parent_document_id = ? ORDER BY ordinal",
            (parent_document_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_relations(self, canonical_id: str) -> List[Dict[str, Any]]:
        """Récupère toutes les relations d'un document (comme source ou cible)."""
        assert self.conn is not None
        rows = self.conn.execute(
            """SELECT * FROM relations
               WHERE source_id = ? OR target_id = ?
               ORDER BY relation_type""",
            (canonical_id, canonical_id),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Statistiques ──────────────────────────────────────────────────

    def count_documents(self) -> int:
        """Nombre total de documents dans le corpus."""
        assert self.conn is not None
        return self.conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    def count_by(self, field: str) -> Dict[str, int]:
        """Distribution des valeurs d'un champ donné.

        Args:
            field: Nom de la colonne dans ``documents`` (ex: 'jurisdiction',
                   'document_type', 'language', 'text_completeness').

        Returns:
            Dict { valeur: count }
        """
        assert self.conn is not None
        # Protection contre l'injection SQL : le champ doit être un identifiant valide
        if not field.isidentifier():
            raise ValueError(f"Nom de champ invalide : {field!r}")
        rows = self.conn.execute(
            f"SELECT {field}, COUNT(*) FROM documents GROUP BY {field} ORDER BY COUNT(*) DESC"
        ).fetchall()
        return {row[0]: row[1] for row in rows}

    def find_duplicates_by_hash(self) -> List[Dict[str, Any]]:
        """Trouve les groupes de documents partageant le même canonical_hash.

        Retourne uniquement les groupes avec 2+ documents (doublons potentiels).
        """
        assert self.conn is not None
        rows = self.conn.execute(
            """SELECT canonical_hash, GROUP_CONCAT(canonical_id) as ids, COUNT(*) as cnt
               FROM documents
               WHERE canonical_hash IS NOT NULL
               GROUP BY canonical_hash
               HAVING cnt > 1
               ORDER BY cnt DESC"""
        ).fetchall()
        return [dict(r) for r in rows]

    def table_counts(self) -> Dict[str, int]:
        """Nombre de lignes par table — utile pour les rapports."""
        assert self.conn is not None
        result = {}
        for table in ("documents", "provenance", "articles", "relations"):
            result[table] = self.conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
        return result
