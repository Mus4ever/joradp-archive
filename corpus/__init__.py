"""Corpus canonique unifié — Corpus juridique algérien.

Ce package regroupe le modèle de données canonique et le schéma SQLite
unifié qui servent de socle au pipeline de normalisation, déduplication
et préparation du corpus pour l'entraînement du SLM juridique.

Modules :
    models  — Enums et dataclasses (CanonicalDocument, Article, DocumentProvenance)
    schema  — Gestionnaire SQLite (databases/corpus.db) avec DDL et CRUD
"""

from corpus.models import (
    DocumentType,
    DocumentNature,
    Jurisdiction,
    CourtLevel,
    TextCompleteness,
    ExtractionMethod,
    ExtractionQuality,
    AnonymizationStatus,
    Language,
    CanonicalDocument,
    Article,
    DocumentProvenance,
)
from corpus.schema import CorpusDB
from corpus.joradp_parser import JORADPParser, ParsedAct, ParsedArticle

__all__ = [
    "DocumentType",
    "DocumentNature",
    "Jurisdiction",
    "CourtLevel",
    "TextCompleteness",
    "ExtractionMethod",
    "ExtractionQuality",
    "AnonymizationStatus",
    "Language",
    "CanonicalDocument",
    "Article",
    "DocumentProvenance",
    "CorpusDB",
    "JORADPParser",
    "ParsedAct",
    "ParsedArticle",
]
