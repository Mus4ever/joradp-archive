"""Modèles de données de la revue de la Cour suprême."""

from dataclasses import dataclass, field, asdict
from typing import Optional, List


@dataclass
class RevueResource:
    """Une ressource découverte (numéro de revue, guide, index...)."""
    id: Optional[int] = None
    title: str = ""
    url: str = ""                      # page source
    resource_type: str = "OTHER"       # REVUE | SPECIAL_ISSUE | GUIDE | INDEX | OTHER
    issue_number: Optional[int] = None
    issue_year: Optional[int] = None
    language: str = "AR"
    pdf_url: str = ""
    # Téléchargement
    local_path: Optional[str] = None
    size_bytes: Optional[int] = None
    sha256: Optional[str] = None
    pdf_pages: Optional[int] = None
    downloaded_at: Optional[str] = None
    status: str = "decouvert"          # decouvert | telecharge | erreur
    error: Optional[str] = None
    discovery_methods: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass
class IndexEntry:
    """Une entrée de l'index du guide (décision publiée dans la revue)."""
    id: Optional[int] = None
    decision_number: Optional[str] = None
    decision_year: Optional[int] = None
    issue_number: Optional[int] = None
    issue_year: Optional[int] = None
    start_page: Optional[int] = None
    chamber: Optional[str] = None
    subject: Optional[str] = None
    principle: Optional[str] = None
    legal_reference: Optional[str] = None
    source_pdf: Optional[str] = None
    source_page: Optional[int] = None   # page du guide où l'entrée apparaît
    raw_text: Optional[str] = None      # texte brut de l'entrée, jamais jeté
    normalized_text: Optional[str] = None
    parser_status: str = "pending"      # pending | ok | partial | error
    created_at: Optional[str] = None

    def to_dict(self):
        return asdict(self)
