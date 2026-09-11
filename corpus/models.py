"""Modèle de données canonique du corpus juridique algérien.

Définit les enums de typage strict et les dataclasses qui représentent
un document juridique unifié, indépendamment de sa source d'origine
(JORADP, Cour suprême HTML, Revue judiciaire, Conseil d'État).

Principes :
    - Chaque document possède un ``canonical_id`` déterministe et lisible.
    - La provenance complète est conservée (base source, table, PK, URL, hash).
    - Le texte est qualifié par sa complétude, sa méthode d'extraction et sa qualité.
    - Aucune donnée source n'est supprimée : le dédoublonnage passe par des relations.

Convention de nommage du ``canonical_id`` :
    ``{juridiction}_{type}_{numéro}_{date}_{lang}``
    Exemples :
        cs_decision_129299_2017-04-20_ar
        cde_decision_015456_2013-06-18_ar
        joradp_loi_06-01_2006-02-20_fr
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field, asdict
from typing import Optional


# ──────────────────────────────────────────────────────────────────────
# Enums — Typage strict de chaque dimension du document
# ──────────────────────────────────────────────────────────────────────

class DocumentType(enum.Enum):
    """Nature juridique fine du document."""
    LAW = "LAW"                         # Loi / قانون
    DECREE = "DECREE"                   # Décret (législatif, exécutif, présidentiel)
    ORDER = "ORDER"                     # Arrêté / قرار وزاري
    DECISION = "DECISION"               # Décision judiciaire / قرار قضائي
    REVIEW_ARTICLE = "REVIEW_ARTICLE"   # Article de la Revue judiciaire
    INDEX_ENTRY = "INDEX_ENTRY"         # Entrée d'index du Guide de recherche
    CIRCULAR = "CIRCULAR"               # Circulaire / منشور
    NOTICE = "NOTICE"                   # Avis / إعلان
    OPINION = "OPINION"                 # Avis consultatif
    ORDINANCE = "ORDINANCE"             # Ordonnance / أمر
    OTHER = "OTHER"


class DocumentNature(enum.Enum):
    """Catégorie macro — utile pour le SLM (filtrage thématique)."""
    LEGISLATIVE_NORM = "LEGISLATIVE_NORM"       # Texte normatif (JORADP)
    JUDICIAL_DECISION = "JUDICIAL_DECISION"     # Décision de justice
    DOCTRINE_REVIEW = "DOCTRINE_REVIEW"         # Doctrine / Revue
    INDEX_METADATA = "INDEX_METADATA"           # Métadonnées d'index seules


class Jurisdiction(enum.Enum):
    """Source institutionnelle du document."""
    SUPREME_COURT = "SUPREME_COURT"         # المحكمة العليا
    STATE_COUNCIL = "STATE_COUNCIL"         # مجلس الدولة
    REPUBLIC = "REPUBLIC"                   # الجمهورية الجزائرية (JORADP)


class CourtLevel(enum.Enum):
    """Niveau hiérarchique de la juridiction."""
    SUPREME_COURT = "SUPREME_COURT"
    STATE_COUNCIL = "STATE_COUNCIL"
    APPELLATE = "APPELLATE"
    LEGISLATIVE = "LEGISLATIVE"             # Textes normatifs (pas une juridiction)


class TextCompleteness(enum.Enum):
    """Degré de complétude du texte extrait — critique pour la Revue."""
    FULL_TEXT = "FULL_TEXT"                  # Texte intégral vérifié
    PARTIAL_TEXT = "PARTIAL_TEXT"            # Texte incomplet (ex: coupure OCR)
    INDEX_ONLY = "INDEX_ONLY"               # Métadonnées seules, pas de texte


class ExtractionMethod(enum.Enum):
    """Comment le texte a été obtenu à partir de la source brute."""
    NATIVE_HTML = "NATIVE_HTML"             # Scraping HTML structuré (CS, CdE)
    NATIVE_PDF = "NATIVE_PDF"              # PDF avec couche texte native
    OCR_MISTRAL = "OCR_MISTRAL"            # OCR via Mistral (Revue, JORADP)
    INDEX_TABLE = "INDEX_TABLE"            # Parsing d'un tableau d'index
    MARKDOWN_PARSE = "MARKDOWN_PARSE"      # Parsing de Markdown extrait


class ExtractionQuality(enum.Enum):
    """Fiabilité estimée de l'extraction."""
    HIGH = "HIGH"                           # Texte natif, structure claire
    MEDIUM = "MEDIUM"                       # OCR de bonne qualité ou structure partielle
    LOW_CONFIDENCE = "LOW_CONFIDENCE"       # OCR dégradé, mise en page complexe
    CORRUPTED = "CORRUPTED"                 # Texte illisible / irrécupérable


class AnonymizationStatus(enum.Enum):
    """Cycle de protection des données personnelles."""
    NOT_ANONYMIZED = "NOT_ANONYMIZED"       # Données brutes (noms, adresses…)
    ANONYMIZED = "ANONYMIZED"               # Entités masquées / remplacées
    REVIEW_REQUIRED = "REVIEW_REQUIRED"     # Cas ambigus nécessitant vérification humaine


class Language(enum.Enum):
    """Langue du document."""
    AR = "AR"   # Arabe
    FR = "FR"   # Français


# ──────────────────────────────────────────────────────────────────────
# Dataclasses — Structures de données du corpus canonique
# ──────────────────────────────────────────────────────────────────────

@dataclass
class DocumentProvenance:
    """Traçabilité complète de l'origine d'un document.

    Chaque document canonique est relié à sa source par exactement
    une instance de ``DocumentProvenance``, permettant de remonter
    jusqu'au fichier brut (HTML, PDF, Markdown) et à la ligne dans
    la base de données source.
    """
    source_db: str                              # "coursupreme.db" | "conseildetat.db" | …
    source_table: str                           # "decisions" | "revue_decisions" | "sources"
    source_id: int                              # PK dans la table source
    source_url: Optional[str] = None            # URL d'origine (si applicable)
    raw_path: Optional[str] = None              # Chemin vers HTML/PDF/MD brut archivé
    pdf_path: Optional[str] = None              # Chemin vers PDF attaché (CdE, Revue)
    content_hash: Optional[str] = None          # SHA-256 du contenu source brut
    ingested_at: Optional[str] = None           # ISO timestamp d'ingestion dans le corpus

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CanonicalDocument:
    """Document juridique canonique unifié.

    Représente une unité textuelle atomique :
        - Jurisprudence : 1 décision = 1 document
        - JORADP : 1 acte juridique (loi, décret, arrêté…) = 1 document
        - Revue : 1 décision publiée dans un numéro = 1 document
        - Index : 1 entrée d'index du Guide = 1 document
    """
    # ── Identité ──
    canonical_id: str                           # Slug déterministe unique
    document_type: DocumentType
    document_nature: DocumentNature
    jurisdiction: Jurisdiction
    court_level: CourtLevel

    # ── Métadonnées juridiques ──
    chamber: Optional[str] = None               # Chambre ou formation
    section: Optional[str] = None               # Section (CdE uniquement)
    title: Optional[str] = None                 # Titre de l'acte / intitulé
    document_number: Optional[str] = None       # Numéro de décision / loi / décret
    publication_number: Optional[str] = None    # N° du JO ou n° de la livraison de revue
    date: Optional[str] = None                  # ISO YYYY-MM-DD
    year: Optional[int] = None
    language: Language = Language.AR

    # ── Contenu textuel ──
    subject: Optional[str] = None               # Matière / Objet
    keywords: Optional[str] = None              # JSON array sérialisé
    legal_references: Optional[str] = None      # Textes visés / appliqués
    principle: Optional[str] = None             # Principe juridique (المبدأ)
    court_response: Optional[str] = None        # Réponse de la juridiction
    disposition: Optional[str] = None           # Dispositif (منطوق القرار)
    full_text: Optional[str] = None             # Texte complet propre
    text_format: str = "plain_text"             # "markdown" | "plain_text"

    # ── Qualité et extraction ──
    text_completeness: TextCompleteness = TextCompleteness.FULL_TEXT
    extraction_method: ExtractionMethod = ExtractionMethod.NATIVE_HTML
    extraction_quality: ExtractionQuality = ExtractionQuality.HIGH

    # ── Provenance ──
    provenance: Optional[DocumentProvenance] = None

    # ── Relations inter-documents ──
    language_pair_id: Optional[str] = None      # canonical_id du doc miroir FR/AR
    parent_document_id: Optional[str] = None    # Pour articles → loi parente (JORADP)

    # ── Intégrité ──
    canonical_hash: Optional[str] = None        # SHA-256 du full_text normalisé

    # ── Anonymisation ──
    anonymization_status: AnonymizationStatus = AnonymizationStatus.NOT_ANONYMIZED

    # ── Horodatage ──
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Sérialise le document en dict, convertissant les enums en valeurs."""
        d = asdict(self)
        # Convertir les enums en leurs valeurs string
        for key, val in d.items():
            if isinstance(val, enum.Enum):
                d[key] = val.value
        # Convertir les enums imbriqués dans provenance
        if d.get("provenance") and isinstance(d["provenance"], dict):
            for k, v in d["provenance"].items():
                if isinstance(v, enum.Enum):
                    d["provenance"][k] = v.value
        return d


@dataclass
class Article:
    """Article individuel d'un acte JORADP.

    Par exemple, l'Article 1er de la Loi n° 06-01 du 20 février 2006.
    Chaque article est relié à son acte parent via ``parent_document_id``.
    """
    id: Optional[int] = None
    parent_document_id: str = ""                # canonical_id de l'acte parent
    article_number: str = ""                    # "1", "2", "1er", "الأولى"
    title: Optional[str] = None                 # Titre de l'article si existant
    text: str = ""                              # Texte de l'article
    language: Language = Language.FR
    ordinal: int = 0                            # Position séquentielle dans l'acte
    created_at: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        for key, val in d.items():
            if isinstance(val, enum.Enum):
                d[key] = val.value
        return d
