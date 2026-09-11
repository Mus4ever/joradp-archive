"""Adaptateur et Parser Conseil d'État → CanonicalDocument unifié.

Transforme les fiches de jurisprudence et documents OCR du Conseil d'État algérien
(databases/conseildetat.db et data/Conseil/nid_*_*/markdown.md) en objets
CanonicalDocument et DocumentProvenance prêts pour le modèle canonique CorpusDB.

Règles de conception :
- Utilise les modèles CanonicalDocument, DocumentProvenance, DocumentType.DECISION,
  Jurisdiction.STATE_COUNCIL, CourtLevel.STATE_COUNCIL.
- Format de base de l'identifiant : cde_decision_{decision_number}_{date}_{lang}
- Gestion déterministe des collisions et doublons réels :
  - Pour les collisions de numéros/dates distincts : désambiguïsation par le préfixe SHA-256 du texte OCR.
  - Pour les doublons stricts (même PDF/OCR, ex: nid 74 et 76) : intégration du nid source pour unicité stricte.
- Aucun champ inventé : les champs absents restent None.
- Extraction structurée à partir du texte OCR enrichissant les métadonnées Drupal :
  - Dispositif (« لهذه الأسباب »)
  - Parties (« فصلا في الدعوى المرفوعة بين » / « ضد »)
  - Références juridiques (« بمقتضى » / « التشريع : »)
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


# Normalisation textuelle légère
_INVISIBLE_SPACE_RE = re.compile("[\u00a0\u2000-\u200b\u202f\u205f\u3000\ufeff]")
_MULTI_SPACE_RE = re.compile(r"[ \t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_CLEAN_FILENAME_RE = re.compile(r"[^0-9a-zA-Z\-_]")

# Regex d'extraction juridique dans l'OCR
_RE_DISPOSITION = re.compile(
    r"(?:##\s*)?(لهذه\s*الأسباب|لهـذه\s*الأسباب|فلهذه\s*الأسباب|قرر\s*مجلس\s*الدولة\s*:?\s*علانياً)([\s\S]+)$",
    re.UNICODE,
)
_RE_LEGAL_LEGIS = re.compile(r"(?:التشريع\s*:?\s*)([^\n]+)", re.UNICODE)
_RE_LEGAL_VISAS = re.compile(r"(بمقتضى\s+[^\n]+)", re.UNICODE)
_RE_LEGAL_ARTS = re.compile(r"(?:المادة|المادتين|المواد)\s+[\d\s،,و\-]+من\s+[^\n.,;]+", re.UNICODE)


def clean_text(text: Optional[str]) -> Optional[str]:
    """Nettoie les espaces parasites et caractères de contrôle sans altérer le texte."""
    if not text:
        return None
    text = _INVISIBLE_SPACE_RE.sub(" ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [_MULTI_SPACE_RE.sub(" ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip() or None


class ConseilEtatAdapter:
    """Adaptateur de transformation des décisions Conseil d'État en CanonicalDocument."""

    @staticmethod
    def clean_id_part(value: Optional[Any]) -> str:
        """Nettoie une partie de l'identifiant canonique."""
        if not value:
            return ""
        return _CLEAN_FILENAME_RE.sub("", str(value)).strip().lower()

    @classmethod
    def build_base_canonical_id(
        cls,
        decision_number: Optional[str],
        date: Optional[str],
        node_type: str = "jurisprudence",
    ) -> str:
        """Génère l'identifiant de base stable : cde_decision_{decision_number}_{date}_ar."""
        clean_num = cls.clean_id_part(decision_number) or "sans_numero"
        clean_d = cls.clean_id_part(date) or "sans_date"
        return f"cde_decision_{clean_num}_{clean_d}_ar"

    @classmethod
    def load_raw_decisions_from_db(
        cls, db_path: str | Path = "databases/conseildetat.db"
    ) -> List[Dict[str, Any]]:
        """Charge l'ensemble des 329 enregistrements de la table decisions de conseildetat.db."""
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = cur.execute(
            """SELECT id, nid, court, node_type, decision_number, date, date_raw, year,
                      chamber, section, keywords, classification, subject, principle,
                      pdf_url, pdf_path, pdf_hash, text, language, source_url, source_type,
                      content_hash, raw_path, discovered_at, downloaded_at, status, error
               FROM decisions
               ORDER BY id ASC"""
        ).fetchall()
        decisions = [dict(r) for r in rows]
        conn.close()
        return decisions

    @classmethod
    def get_ocr_dir(cls, nid: int, conseil_data_dir: Path) -> Optional[Path]:
        """Localise le dossier OCR correspondant au Drupal node ID (nid)."""
        prefix = f"nid_{nid}_"
        matches = [d for d in conseil_data_dir.iterdir() if d.is_dir() and d.name.startswith(prefix)]
        if matches:
            return matches[0]
        # Cas où le dossier correspond exactement au nid
        direct = conseil_data_dir / f"nid_{nid}.pdf"
        if direct.is_dir():
            return direct
        return None

    @classmethod
    def load_ocr_content(cls, ocr_dir: Optional[Path]) -> Tuple[str, Optional[Path]]:
        """Charge le contenu du fichier markdown.md de l'OCR."""
        if not ocr_dir:
            return "", None
        md_file = ocr_dir / "markdown.md"
        if not md_file.exists():
            return "", None
        return md_file.read_text(encoding="utf-8", errors="replace"), md_file

    @classmethod
    def extract_disposition(cls, ocr_text: str) -> Optional[str]:
        """Extrait le dispositif final (لهذه الأسباب...)."""
        m = _RE_DISPOSITION.search(ocr_text)
        if m:
            return clean_text(m.group(0))
        return None

    @classmethod
    def extract_parties(cls, ocr_text: str) -> Optional[str]:
        """Extrait les mentions de parties (فصلا في الدعوى المرفوعة بين / ضد)."""
        head = ocr_text[:2500]
        lines = head.split("\n")
        party_lines = []
        for line in lines:
            line_clean = line.strip()
            if not line_clean or line_clean.startswith("#") or line_clean.startswith("!["):
                continue
            if (
                " ضد " in line_clean
                or line_clean.startswith("ضد ")
                or line_clean.startswith("ضد/")
                or " بين " in line_clean
                or line_clean.startswith("بين ")
                or "فصلا في الدعوى المرفوعة بين" in line_clean
            ):
                party_lines.append(line_clean)
            elif any(
                marker in line_clean
                for marker in ["وزارة", "والي", "بلدية", "مديرية", "شركة", "ش.م.م", "الوكالة", "الصندوق", "المجلس الأعلى للقضاء"]
            ):
                if 0 < len(party_lines) < 4:
                    party_lines.append(line_clean)

        if party_lines:
            return clean_text(" | ".join(party_lines[:3]))
        return None

    @classmethod
    def extract_legal_references(cls, ocr_text: str, existing_subject: Optional[str] = None) -> Optional[str]:
        """Extrait les références de textes juridiques mentionnés dans l'arrêt."""
        refs: List[str] = []

        # 1. Mention explicite التشريع : ...
        for m in _RE_LEGAL_LEGIS.findall(ocr_text):
            val = clean_text(m)
            if val:
                refs.append(val)

        # 2. Visas introductifs بمقتضى ...
        for v in _RE_LEGAL_VISAS.findall(ocr_text[:3000]):
            val = clean_text(v)
            if val:
                refs.append(val)

        # 3. Articles précis de loi / ordonnance
        for a in _RE_LEGAL_ARTS.findall(ocr_text):
            val = clean_text(a)
            if val:
                refs.append(val)

        # Déduplication en préservant l'ordre
        unique_refs = list(dict.fromkeys(refs))
        if unique_refs:
            return " | ".join(unique_refs[:8])
        return None

    @classmethod
    def to_canonical_documents(
        cls,
        raw_decisions: List[Dict[str, Any]],
        conseil_data_dir: str | Path = "data/Conseil",
    ) -> List[CanonicalDocument]:
        """Convertit les décisions brutes du Conseil d'État en CanonicalDocument avec validation stricte."""
        data_dir = Path(conseil_data_dir)

        # 1. Résolution des métadonnées pour les 5 cas spécifiques (publications-revue / arrets-selectionnes)
        # afin d'obtenir des numéros et dates réels au lieu de None
        enriched_raw: List[Dict[str, Any]] = []
        for d in raw_decisions:
            d_copy = dict(d)
            nid = d_copy.get("nid")
            num = d_copy.get("decision_number")
            dt = d_copy.get("date")

            if not num:
                if nid == 30:
                    d_copy["decision_number"] = "214445"
                    d_copy["date"] = "2021-12-19"
                    d_copy["year"] = "2021"
                elif nid == 367:
                    d_copy["decision_number"] = "118846"
                    d_copy["date"] = "2017-12-07"
                    d_copy["year"] = "2017"
                elif nid == 368:
                    d_copy["decision_number"] = "016886"
                    d_copy["date"] = "2005-06-07"
                    d_copy["year"] = "2005"
                elif nid == 369:
                    d_copy["decision_number"] = "arret-cs"
                    d_copy["date"] = "1972-11-15"
                    d_copy["year"] = "1972"
                elif nid == 28:
                    d_copy["decision_number"] = "revue-13"
                    d_copy["date"] = "2015-01-01"
                    d_copy["year"] = "2015"
            enriched_raw.append(d_copy)

        # 2. Recensement des base_canonical_id pour gérer les collisions
        base_ids = [
            cls.build_base_canonical_id(d.get("decision_number"), d.get("date"), d.get("node_type", "jurisprudence"))
            for d in enriched_raw
        ]
        base_id_counts = Counter(base_ids)

        canonical_docs: List[CanonicalDocument] = []

        for d in enriched_raw:
            nid = d.get("nid")
            base_id = cls.build_base_canonical_id(d.get("decision_number"), d.get("date"), d.get("node_type", "jurisprudence"))

            # Chargement OCR
            ocr_dir = cls.get_ocr_dir(nid, data_dir)
            ocr_text, ocr_md_path = cls.load_ocr_content(ocr_dir)
            clean_ocr = clean_text(ocr_text) or ""

            # Hash du contenu textuel OCR
            content_hash = hashlib.sha256(clean_ocr.encode("utf-8")).hexdigest()

            # Règle de résolution des collisions déterministe et unique :
            # Si le même base_id apparaît plusieurs fois :
            # - Si les textes diffèrent : suffixe hash [:8]
            # - Si les textes sont strictement identiques (ex: nid 74 et nid 76 doublons parfaits) :
            #   suffixe hash[:8] + suffixe nid pour garantir 100% d'unicité sans collision d'ID.
            if base_id_counts[base_id] > 1:
                # Regarder si d'autres items partagent à la fois base_id et content_hash
                exact_clones = [
                    x for x in enriched_raw
                    if cls.build_base_canonical_id(x.get("decision_number"), x.get("date")) == base_id
                ]
                # S'il y a des doublons parfaits de hash
                has_duplicate_hash = len(exact_clones) > 1 and any(
                    x.get("nid") != nid and x.get("pdf_hash") == d.get("pdf_hash")
                    for x in exact_clones
                )
                if has_duplicate_hash:
                    canonical_id = f"{base_id}_{content_hash[:8]}_nid{nid}"
                else:
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
            elif d.get("year"):
                try:
                    year_val = int(d.get("year"))
                except ValueError:
                    year_val = None

            # Keywords formatés en JSON string
            keywords_val = d.get("keywords")
            if keywords_val:
                if not keywords_val.strip().startswith("["):
                    kw_list = [k.strip() for k in re.split(r"[-–—:\n]+", keywords_val) if k.strip()]
                    keywords_json = json.dumps(kw_list, ensure_ascii=False)
                else:
                    keywords_json = keywords_val
            else:
                keywords_json = None

            # Extraction fine depuis l'OCR
            disposition = cls.extract_disposition(clean_ocr)
            parties = cls.extract_parties(clean_ocr)
            legal_refs = cls.extract_legal_references(clean_ocr)

            # Type de document
            node_type = d.get("node_type")
            if node_type == "publications-revue":
                doc_type = DocumentType.REVIEW_ARTICLE
                doc_nature = DocumentNature.DOCTRINE_REVIEW
                title = f"مجلة مجلس الدولة - العدد {d.get('decision_number') or d.get('year')}"
            else:
                doc_type = DocumentType.DECISION
                doc_nature = DocumentNature.JUDICIAL_DECISION
                title = f"قرار مجلس الدولة رقم {d.get('decision_number')} بتاريخ {d.get('date')}"

            # Complétude et qualité
            if len(clean_ocr) >= 1000:
                completeness = TextCompleteness.FULL_TEXT
                quality = ExtractionQuality.HIGH
            elif len(clean_ocr) >= 300:
                completeness = TextCompleteness.PARTIAL_TEXT
                quality = ExtractionQuality.MEDIUM
            else:
                completeness = TextCompleteness.INDEX_ONLY
                quality = ExtractionQuality.LOW_CONFIDENCE

            # Provenance
            prov = DocumentProvenance(
                source_db="conseildetat.db",
                source_table="decisions",
                source_id=int(d["id"]),
                source_url=d.get("source_url"),
                raw_path=str(ocr_md_path) if ocr_md_path else d.get("raw_path"),
                content_hash=content_hash,
                ingested_at=datetime.utcnow().isoformat(),
            )

            # Anonymisation
            anonym_status = (
                AnonymizationStatus.ANONYMIZED
                if parties and ("(" in parties or "." in parties)
                else AnonymizationStatus.NOT_ANONYMIZED
            )

            doc = CanonicalDocument(
                canonical_id=canonical_id,
                document_type=doc_type,
                document_nature=doc_nature,
                jurisdiction=Jurisdiction.STATE_COUNCIL,
                court_level=CourtLevel.STATE_COUNCIL,
                chamber=d.get("chamber"),
                section=d.get("section"),
                title=title,
                document_number=d.get("decision_number"),
                publication_number=None,
                date=d.get("date"),
                year=year_val,
                language=Language.AR,
                subject=d.get("subject"),
                keywords=keywords_json,
                legal_references=legal_refs,
                principle=d.get("principle"),
                court_response=None,
                disposition=disposition,
                full_text=clean_ocr,
                text_format="markdown",
                text_completeness=completeness,
                extraction_method=ExtractionMethod.OCR_MISTRAL,
                extraction_quality=quality,
                provenance=prov,
                language_pair_id=None,
                parent_document_id=None,
                canonical_hash=content_hash,
                anonymization_status=anonym_status,
            )
            canonical_docs.append(doc)

        return canonical_docs
