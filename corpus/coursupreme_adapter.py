"""Adaptateur Cour Suprême HTML → CanonicalDocument unifié.

Transforme les décisions issues du scraping HTML de la Cour suprême (databases/coursupreme.db
et raw/coursupreme/*.html) en objets CanonicalDocument et DocumentProvenance prêts pour CorpusDB.

Règles de conception :
- Utilise les modèles CanonicalDocument, DocumentProvenance, DocumentType.DECISION, Jurisdiction.SUPREME_COURT.
- Format de base de l'identifiant : cs_decision_{decision_number}_{date}_ar
- Désambiguïsateur déterministe par SHA-256 du texte intégral uniquement en cas de collision.
- Aucun champ inventé : les champs absents restent None.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from corpus.models import (
    AnonymizationStatus,
    CanonicalDocument,
    CourtLevel,
    DocumentNature,
    DocumentProvenance,
    DocumentType,
    ExtractionMethod,
    ExtractionQuality,
    Jurisdiction,
    Language,
    TextCompleteness,
)


class CourSupremeAdapter:
    """Adaptateur de transformation des décisions Cour Suprême HTML en CanonicalDocument."""

    @staticmethod
    def build_base_canonical_id(decision_number: Optional[str], date: Optional[str]) -> str:
        """Génère l'identifiant de base stable : cs_decision_{decision_number}_{date}_ar."""
        num_str = str(decision_number or "sans_numero")
        clean_num = re.sub(r"[^0-9a-zA-Z\-_]", "", num_str).strip().lower() or "sans_numero"
        date_str = str(date or "sans_date")
        clean_date = re.sub(r"[^0-9a-zA-Z\-_]", "", date_str).strip() or "sans_date"
        return f"cs_decision_{clean_num}_{clean_date}_ar"

    @classmethod
    def load_raw_decisions_from_db(
        cls, db_path: str | Path = "databases/coursupreme.db"
    ) -> List[Dict[str, Any]]:
        """Charge l'ensemble des enregistrements de la table decisions de coursupreme.db."""
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = cur.execute(
            """SELECT id, court, chamber, chamber_class, decision_number, date, subject,
                      parties, keywords, legal_references, principle, appeal_ground,
                      court_response, unconstitutionality_grounds, unconstitutionality_response,
                      disposition, president, rapporteur, clerk, extra_sections, extra_metadata,
                      text, language, source_url, source_type, content_hash, raw_path,
                      discovered_at, downloaded_at, category, status, error
               FROM decisions
               ORDER BY id ASC"""
        ).fetchall()
        decisions = [dict(r) for r in rows]
        conn.close()
        return decisions

    @classmethod
    def to_canonical_documents(
        cls, raw_decisions: List[Dict[str, Any]]
    ) -> List[CanonicalDocument]:
        """Convertit la liste des décisions brutes en CanonicalDocuments avec gestion des collisions."""
        # 1. Calculer les base_canonical_id pour recenser les collisions
        base_ids = [
            cls.build_base_canonical_id(d.get("decision_number"), d.get("date"))
            for d in raw_decisions
        ]
        base_id_counts = Counter(base_ids)

        canonical_docs: List[CanonicalDocument] = []

        for d in raw_decisions:
            base_id = cls.build_base_canonical_id(d.get("decision_number"), d.get("date"))
            raw_text = d.get("text") or ""
            content_hash = d.get("content_hash") or hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

            # Règle d'unicité : ajout du hash uniquement pour les collisions réelles
            if base_id_counts[base_id] > 1:
                # Désambiguïsateur déterministe basé sur les 8 premiers caractères du hash
                canonical_id = f"{base_id}_{content_hash[:8]}"
            else:
                canonical_id = base_id

            # Année
            year_val = None
            date_str = d.get("date")
            if date_str and len(date_str) >= 4:
                try:
                    year_val = int(date_str[:4])
                except ValueError:
                    year_val = None

            # Keywords formatés en JSON string si chaîne de mots-clés
            keywords_val = d.get("keywords")
            if keywords_val:
                # Si pas déjà du JSON
                if not keywords_val.strip().startswith("["):
                    # Mots-clés séparés par tirets, virgules ou retours à la ligne
                    kw_list = [k.strip() for k in re.split(r"[-–—,\n]+", keywords_val) if k.strip()]
                    keywords_json = json.dumps(kw_list, ensure_ascii=False)
                else:
                    keywords_json = keywords_val
            else:
                keywords_json = None

            # Métadonnées additionnelles éventuelles dans legal_references / subject
            title = f"قرار المحكمة العليا رقم {d.get('decision_number')} بتاريخ {d.get('date')}"

            # Détermination de la complétude du texte
            if raw_text and len(raw_text.strip()) > 100:
                completeness = TextCompleteness.FULL_TEXT
            else:
                completeness = TextCompleteness.PARTIAL_TEXT

            # Provenance
            prov = DocumentProvenance(
                source_db="coursupreme.db",
                source_table="decisions",
                source_id=int(d["id"]),
                source_url=d.get("source_url"),
                raw_path=d.get("raw_path"),
                content_hash=content_hash,
                ingested_at=datetime.utcnow().isoformat(),
            )

            # Anonymisation : Les décisions sur le site de la Cour suprême sont déjà publiées avec initiales
            anonym_status = (
                AnonymizationStatus.ANONYMIZED
                if d.get("parties")
                else AnonymizationStatus.NOT_ANONYMIZED
            )

            doc = CanonicalDocument(
                canonical_id=canonical_id,
                document_type=DocumentType.DECISION,
                document_nature=DocumentNature.JUDICIAL_DECISION,
                jurisdiction=Jurisdiction.SUPREME_COURT,
                court_level=CourtLevel.SUPREME_COURT,
                chamber=d.get("chamber"),
                section=None,  # La Cour suprême n'a pas de section dans cette source (contrairement au CdE)
                title=title,
                document_number=d.get("decision_number"),
                publication_number=None,
                date=d.get("date"),
                year=year_val,
                language=Language.AR,
                subject=d.get("subject"),
                keywords=keywords_json,
                legal_references=d.get("legal_references"),
                principle=d.get("principle"),
                court_response=d.get("court_response"),
                disposition=d.get("disposition"),
                full_text=raw_text,
                text_format="plain_text",
                text_completeness=completeness,
                extraction_method=ExtractionMethod.NATIVE_HTML,
                extraction_quality=ExtractionQuality.HIGH,
                provenance=prov,
                language_pair_id=None,
                parent_document_id=None,
                canonical_hash=content_hash,
                anonymization_status=anonym_status,
            )
            canonical_docs.append(doc)

        return canonical_docs
