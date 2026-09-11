"""Adaptateur Cour Suprême Revue → CanonicalDocument unifié.

Transforme les 3 274 décisions de la Revue de la Cour suprême (databases/coursupreme_revue.db
et pages OCR dans data/revue/) en objets CanonicalDocument et DocumentProvenance prêts pour CorpusDB.

Fonctionnalités clés :
- Fusionne les décisions modernes (segmentées par text markers) et les décisions legacy (1990-2004).
- Texte intégral : extrait depuis revue_decision_texts pour le legacy et lu depuis les pages OCR
  pour le moderne.
- Définition d'un canonical_id déterministe avec résolution d'ambiguïté par hash et id source :
  cs_revue_{issue_year}_{issue_number}_{decision_number}_ar[_hash_id].
- Aucun champ inventé.
- Traçabilité complète via DocumentProvenance.
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

_INVISIBLE_SPACE_RE = re.compile("[\u00a0\u2000-\u200b\u202f\u205f\u3000\ufeff]")
_MULTI_SPACE_RE = re.compile(r"[ \t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_CLEAN_SLUG_RE = re.compile(r"[^0-9a-zA-Z\-_]")

_DISPOSITION_RE = re.compile(r"(?:لهذه\s*الأسباب|فلهذه\s*الأسباب|قررت\s*المحكمة\s*العليا|تقضي\s*المحكمة\s*العليا)([\s\S]+)$")


def clean_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    text = _INVISIBLE_SPACE_RE.sub(" ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [_MULTI_SPACE_RE.sub(" ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip() or None


class CourSupremeRevueAdapter:
    """Adaptateur pour les décisions de la Revue de la Cour Suprême."""

    @staticmethod
    def clean_id_part(value: Optional[Any]) -> str:
        if not value:
            return ""
        return _CLEAN_SLUG_RE.sub("", str(value)).strip().lower()

    @classmethod
    def build_base_canonical_id(
        cls,
        issue_year: Optional[int | str],
        issue_number: Optional[int | str],
        decision_number: Optional[str],
    ) -> str:
        y_str = cls.clean_id_part(issue_year) or "0000"
        if issue_number is not None and str(issue_number).isdigit():
            n_str = f"{int(issue_number):02d}"
        else:
            n_str = cls.clean_id_part(issue_number) or "00"
        num_str = cls.clean_id_part(decision_number) or "sans_numero"
        return f"cs_revue_{y_str}_{n_str}_{num_str}_ar"

    @classmethod
    def load_raw_decisions_from_db(
        cls, db_path: str | Path = "databases/coursupreme_revue.db"
    ) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = cur.execute(
            """SELECT id, decision_number, date, issue_year, issue_number,
                      chamber, chamber_raw, subject, keywords, legal_references,
                      principle, has_disposition, pdf_start_page, match_verdict,
                      source, created_at
               FROM revue_decisions
               ORDER BY id ASC"""
        ).fetchall()
        decisions = [dict(r) for r in rows]
        conn.close()
        return decisions

    @classmethod
    def load_decision_texts(
        cls, db_path: str | Path = "databases/coursupreme_revue.db"
    ) -> Dict[int, Dict[str, Any]]:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = cur.execute(
            """SELECT id, decision_id, full_text, pdf_start_page, pdf_end_page,
                      page_count, offset_used, offset_confidence, offset_method, char_count
               FROM revue_decision_texts"""
        ).fetchall()
        texts = {r["decision_id"]: dict(r) for r in rows}
        conn.close()
        return texts

    @classmethod
    def read_modern_pages(
        cls,
        revue_data_dir: Path,
        year: int,
        number: int,
        start_page: int,
        next_start_page: Optional[int],
    ) -> Tuple[str, str]:
        pages_dir = revue_data_dir / str(year) / f"issue_{number:02d}" / "pages"
        if not pages_dir.exists():
            return "", ""

        if next_start_page and next_start_page > start_page:
            end_page = next_start_page - 1
        else:
            end_page = start_page + 3

        parts = []
        for pno in range(start_page, end_page + 1):
            pf = pages_dir / f"page-{pno}" / "markdown.md"
            if pf.exists():
                parts.append(pf.read_text(encoding="utf-8"))

        raw_path = str(pages_dir / f"page-{start_page}" / "markdown.md")
        return "\n\n".join(parts), raw_path

    @classmethod
    def to_canonical_documents(
        cls,
        raw_decisions: List[Dict[str, Any]],
        revue_data_dir: str | Path = "data/revue",
        revue_db_path: str | Path = "databases/coursupreme_revue.db",
    ) -> List[CanonicalDocument]:
        data_dir = Path(revue_data_dir)
        stored_texts = cls.load_decision_texts(revue_db_path)

        # 1. Grouper par issue pour calculer les next_start_page pour les décisions modernes
        issue_groups: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
        for d in raw_decisions:
            y, n = d.get("issue_year") or 0, d.get("issue_number") or 0
            issue_groups.setdefault((y, n), []).append(d)

        # 2. Précalculer les base_canonical_id
        base_ids = [
            cls.build_base_canonical_id(d.get("issue_year"), d.get("issue_number"), d.get("decision_number"))
            for d in raw_decisions
        ]
        base_id_counts = Counter(base_ids)

        canonical_docs: List[CanonicalDocument] = []

        for d in raw_decisions:
            dec_id = d["id"]
            y = d.get("issue_year") or 0
            n = d.get("issue_number") or 0
            base_id = cls.build_base_canonical_id(y, n, d.get("decision_number"))

            # Récupération du texte
            raw_text = ""
            raw_path = None
            if dec_id in stored_texts:
                st = stored_texts[dec_id]
                raw_text = st.get("full_text") or ""
                p_start = st.get("pdf_start_page")
                raw_path = f"data/revue/{y}/issue_{n:02d}/pages/page-{p_start}/markdown.md"
            else:
                # Décision moderne
                p_start = d.get("pdf_start_page") or 1
                group = issue_groups.get((y, n), [])
                # Trouver la page suivante
                same_group_pages = sorted(
                    [x.get("pdf_start_page") for x in group if x.get("pdf_start_page") and x.get("pdf_start_page") > p_start]
                )
                next_p = same_group_pages[0] if same_group_pages else None
                raw_text, raw_path = cls.read_modern_pages(data_dir, y, n, p_start, next_p)

            clean_ocr = clean_text(raw_text) or ""
            content_hash = hashlib.sha256(clean_ocr.encode("utf-8")).hexdigest()

            # Règle de résolution des collisions 100% déterministe :
            if base_id_counts[base_id] > 1:
                canonical_id = f"{base_id}_{content_hash[:8]}_id{dec_id}"
            else:
                canonical_id = base_id

            # Année et date
            date_str = d.get("date")
            year_val = None
            if date_str and len(date_str) >= 4 and date_str[:4].isdigit():
                year_val = int(date_str[:4])
            elif y:
                year_val = int(y)

            # Keywords formatés en JSON
            keywords_val = d.get("keywords")
            if keywords_val:
                if not keywords_val.strip().startswith("["):
                    kw_list = [k.strip() for k in re.split(r"[-–—:\n]+", keywords_val) if k.strip()]
                    keywords_json = json.dumps(kw_list, ensure_ascii=False)
                else:
                    keywords_json = keywords_val
            else:
                keywords_json = None

            # Dispositif
            disposition = None
            m_disp = _DISPOSITION_RE.search(clean_ocr)
            if m_disp:
                disposition = clean_text(m_disp.group(0))

            # Titre
            num_display = d.get("decision_number") or f"id-{dec_id}"
            date_display = d.get("date") or f"revue {y}/{n:02d}"
            title = f"قرار المحكمة العليا رقم {num_display} بتاريخ {date_display}"

            # Complétude
            if len(clean_ocr) >= 1000:
                completeness = TextCompleteness.FULL_TEXT
                quality = ExtractionQuality.HIGH
            elif len(clean_ocr) >= 200:
                completeness = TextCompleteness.PARTIAL_TEXT
                quality = ExtractionQuality.MEDIUM
            else:
                completeness = TextCompleteness.INDEX_ONLY
                quality = ExtractionQuality.LOW_CONFIDENCE

            # Provenance
            pdf_rel_path = f"downloads/revue/revue_{y}_{n:02d}.pdf"
            prov = DocumentProvenance(
                source_db="coursupreme_revue.db",
                source_table="revue_decisions",
                source_id=int(dec_id),
                source_url=None,
                raw_path=raw_path,
                pdf_path=pdf_rel_path,
                content_hash=content_hash,
                ingested_at=datetime.utcnow().isoformat(),
            )

            doc = CanonicalDocument(
                canonical_id=canonical_id,
                document_type=DocumentType.DECISION,
                document_nature=DocumentNature.JUDICIAL_DECISION,
                jurisdiction=Jurisdiction.SUPREME_COURT,
                court_level=CourtLevel.SUPREME_COURT,
                chamber=d.get("chamber") or d.get("chamber_raw"),
                section=None,
                title=title,
                document_number=d.get("decision_number"),
                publication_number=f"{y}/{n:02d}",
                date=d.get("date"),
                year=year_val,
                language=Language.AR,
                subject=d.get("subject"),
                keywords=keywords_json,
                legal_references=d.get("legal_references"),
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
                anonymization_status=AnonymizationStatus.NOT_ANONYMIZED,
            )
            canonical_docs.append(doc)

        return canonical_docs
