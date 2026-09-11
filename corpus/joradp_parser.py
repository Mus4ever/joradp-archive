"""Parser JORADP — Extraction des Actes Juridiques et Articles (FR / AR).

Transforme les transcriptions Markdown brutes du Journal Officiel
en actes juridiques canoniques (CanonicalDocument) et articles (Article)
prêts pour l'ingestion dans CorpusDB.
"""

from __future__ import annotations

import enum
import hashlib
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Tuple

from corpus.models import (
    AnonymizationStatus,
    Article,
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


# ──────────────────────────────────────────────────────────────────────
# Dictionnaires de mois pour le parsing des dates
# ──────────────────────────────────────────────────────────────────────

# Translation des chiffres arabes orientaux (٠-٩) vers chiffres standards (0-9)
AR_DIGITS_TABLE = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

FR_MONTHS: Dict[str, str] = {
    "janvier": "01", "février": "02", "fevrier": "02", "mars": "03",
    "avril": "04", "mai": "05", "juin": "06", "juillet": "07",
    "août": "08", "aout": "08", "septembre": "09", "octobre": "10",
    "novembre": "11", "décembre": "12", "decembre": "12",
}

AR_MONTHS: Dict[str, str] = {
    "جانفي": "01", "يناير": "01", "كانون الثاني": "01",
    "فيفري": "02", "فبراير": "02", "شباط": "02",
    "مارس": "03", "آذار": "03", "اذار": "03",
    "أفريل": "04", "افريل": "04", "أبريل": "04", "ابريل": "04", "نيسان": "04",
    "ماي": "05", "أيار": "05", "ايار": "05", "مايو": "05",
    "جوان": "06", "حزيران": "06", "يونيو": "06", "يونية": "06",
    "جويلية": "07", "تموز": "07", "يوليو": "07", "يولية": "07",
    "أوت": "08", "اوت": "08", "آب": "08", "اب": "08", "غشت": "08",
    "سبتمبر": "09", "أيلول": "09", "ايلول": "09", "شتنبر": "09",
    "أكتوبر": "10", "اكتوبر": "10", "تشرين الأول": "10", "تشرين الاول": "10",
    "نوفمبر": "11", "تشرين الثاني": "11",
    "ديسمبر": "12", "كانون الأول": "12", "كانون الاول": "12", "دجنبر": "12",
}

AR_MONTHS_PATTERN = "|".join(re.escape(m) for m in AR_MONTHS.keys())


# ──────────────────────────────────────────────────────────────────────
# Dataclasses intermédiaires de parsing
# ──────────────────────────────────────────────────────────────────────

@dataclass
class ParsedArticle:
    """Représentation intermédiaire d'un article extrait."""
    article_number: str
    text: str
    ordinal: int
    title: Optional[str] = None


@dataclass
class ParsedAct:
    """Représentation intermédiaire d'un acte extrait d'un numéro JORADP."""
    raw_title: str
    document_type: DocumentType
    type_slug: str
    document_number: Optional[str]
    normalized_number: Optional[str]
    date_iso: Optional[str]
    year: int
    subject: Optional[str]
    full_text: str
    articles: List[ParsedArticle] = field(default_factory=list)
    start_pos: int = 0
    end_pos: int = 0


# ──────────────────────────────────────────────────────────────────────
# Regex de détection
# ──────────────────────────────────────────────────────────────────────

# En-têtes d'actes en français (tolérant aux majuscules sans accents : DECRET, ARRETE, PRESIDENT...)
RE_ACT_HEADING_FR: Pattern = re.compile(
    r"(?:^|\n)(?:#+\s*|\*\*)?"
    r"((?:Loi(?:\s+organique)?|Ordonnance|D[ée]crets?\s+l[ée]gislatifs?|D[ée]crets?\s+pr[ée]sidentiels?|D[ée]crets?\s+ex[ée]cutifs?|"
    r"D[ée]crets?|Arr[êe]t[ée]s?(?:\s+interminist[ée]riels?|\s+minist[ée]riels?)?|D[ée]cisions?|Circulaires?|"
    r"Accords?(?:\s+du|\s+conclu|\s+entre)?|Statuts?|R[èe]glements?\s+int[ée]rieur|R[èe]glements?|R[ée]solutions?|"
    r"Avis|Proclamations?|Lettre\s+du\s+Pr[ée]sident)\s+(?:n°|du|parti|de\s+l[’\']|de\s+la|de|des|portant|relative|fixant|approuvant|complétant|d'appel|adopt[ée]s?|conclu)[^\n]+)",
    re.IGNORECASE,
)

# En-têtes d'actes en arabe (supporte les intitulés intermédiaires : قانون المالية... رقم, tolérant aux hamzas [أاإآ] et pluriels)
RE_ACT_HEADING_AR: Pattern = re.compile(
    r"(?:^|\n)(?:#+\s*|\*\*)?"
    r"((?:قانون(?:\s+عضوي)?|[أاإآ]مر|مراسيم|مرسومان|مرسوم\s+رئاسي|مرسوم\s+تنفيذي|مرسوم|"
    r"قرارات|قراران|قرار(?:\s+وزاري\s+مشترك|\s+وزاري)?|مقررات|مقرر|مناشير|منشور|[إا]علانات|[إا]علان|بيانات|بيان|رسائل|رسالة|نظام|النظام|لوائح|لائحة)"
    r"(?:\s+[^.\n]{1,50}?)?\s+(?:رقم|مؤرخ|مؤرخة|مؤرخان|في|يتضمن|تتضمن|يتضمنان|يحدد|تحدد|يحددان|يتعلق|تتعلق|يتعلقان|بشأن|المحدد)[^\n]+)",
)

# Préambules légaux FR (pour valider qu'un titre est dans le corps et pas dans le sommaire)
RE_PREAMBLE_FR: Pattern = re.compile(
    r"(?:Le\s+Président\s+de\s+la\s+République|Le\s+Premier\s+ministre|"
    r"Le\s+(?:Président\s+du\s+)?Haut\s+Comité\s+d'Etat|"
    r"L’?\s*Exécutif\s+provisoire|Vu\s+la\s+Constitution|Sur\s+le\s+rapport|Sur\s+proposition|"
    r"Vu\s+l[’\']|Vu\s+le|Vu\s+la|Après\s+avis|Décrète|Ordonne|Arrête|"
    r"Promulgue|La\s+Commission\s+Centrale|Monsieur\s+le\s+Président|"
    r"sont\s+convenus|Adopt[ée]s?\s+par|Le\s+texte\s+intégral|Est\s+publiée|"
    r"OBJET\s*:|A\s+Messieurs|A\s+Mesdames|Délégation\s+aux|Cabinet|"
    r"Par\s+(?:d[ée]crets?|arr[êe]t[ée]s?|d[ée]cisions?))",
    re.IGNORECASE,
)

# Préambules légaux AR (inclut les formules de décrets individuels et tanween)
RE_PREAMBLE_AR: Pattern = re.compile(
    r"(?:إنّ?\s+رئيس\s+الجمهورية|إنّ?\s+الوزير\s+الأول|إنّ?\s+وزير|إنّ?\s+المجلس\s+الدستوري|"
    r"بناء\s*ً?\s*على|وبناء\s*ً?\s*على|بمقتضى|وبمقتضى|يرسم\s+ما\s+يأتي|"
    r"يأمر\s+بما\s+يأتي|يقرر\s+ما\s+يأتي|يصدر\s+القانون|الموضوع\s*:|"
    r"تُنشر\s+اللائحة|ينشر\s+ما\s+يأتي|"
    r"بموجب\s+(?:مرسوم|مراسيم|قرار|قرارات|مقرر)|يصادق\s+على)",
)

# Découpage d'articles FR (inclut 'premier' en lettres et suffixes bis/ter)
RE_ARTICLE_FR: Pattern = re.compile(
    r"(?:^|\n)(?:#+\s*|\*\*)?(?:Article|Art\.)\s*"
    r"((?:[0-9]+(?:er)?|premier)(?:\s*(?:bis|ter|quater|quinquies|sexies|septies|octies|nonies|decies))?)\s*"
    r"[\.:—\-\*]+",
    re.IGNORECASE,
)

# Découpage d'articles AR
RE_ARTICLE_AR: Pattern = re.compile(
    r"(?:^|\n)(?:#+\s*|\*\*)?(?:المادة|مادة)\s*"
    r"([0-9]+|الأولى|الاولى|الثانية|الثالثة|الرابعة|الخامسة|السادسة|"
    r"السابعة|الثامنة|التاسعة|العاشرة|[0-9]+\s*مكرر(?:\s*[0-9]+)?)\s*"
    r"[\.:—\-\*]+",
)

# Détection de ligne de sommaire (se termine par des points ou (p. X) avec numéro de page)
RE_SOMMAIRE_LINE: Pattern = re.compile(
    r"(?:(?:\.\.\.|\.\s*\.\s*\.)\s*\d+|\([Pp]\.?\s*\d+\)\.?|[,.]?\s*[Pp]\.?\s*\d+\.?)\s*$"
)

# Détection de formules finales (signatures) marquant la fin des articles
RE_SIGNATURE_FR: Pattern = re.compile(r"(?:^|\n)Fait\s+à\s+[^\n]+,\s+le\s+[^\n]+", re.IGNORECASE)
RE_SIGNATURE_AR: Pattern = re.compile(r"(?:^|\n)حرر\s+بالجزائر\s+في\s+[^\n]+")


# ──────────────────────────────────────────────────────────────────────
# Classe principale du Parser
# ──────────────────────────────────────────────────────────────────────

class JORADPParser:
    """Parser pour les transcriptions Markdown des Journaux Officiels algériens."""

    @staticmethod
    def detect_language(text: str, default: Language = Language.FR) -> Language:
        """Détecte la langue dominante (FR ou AR) dans un texte."""
        ar_chars = len(re.findall(r"[\u0600-\u06FF]", text[:3000]))
        lat_chars = len(re.findall(r"[a-zA-Z]", text[:3000]))
        if ar_chars > lat_chars:
            return Language.AR
        elif lat_chars > ar_chars:
            return Language.FR
        return default

    @classmethod
    def parse_date(cls, text: str, lang: Language) -> Optional[str]:
        """Extrait et normalise la date grégorienne en ISO YYYY-MM-DD."""
        if lang == Language.FR:
            # Ex: 20 février 2006, 1er juillet 1962, 2 janvier 2023
            match = re.search(
                r"\b([0-9]{1,2})(?:er)?\s+([a-zéèûô]+)\s+([0-9]{4})\b",
                text,
                re.IGNORECASE,
            )
            if match:
                day_str, month_name, year_str = match.groups()
                month_name = month_name.lower().replace("é", "e").replace("è", "e").replace("û", "u")
                month_num = FR_MONTHS.get(month_name)
                if month_num:
                    return f"{year_str}-{month_num}-{int(day_str):02d}"
        else:
            # Ex: 20 فبراير 2006, 2 جانفي سنة 2023, 15 جويلية 1962, ٨ أبريل سنة ١٩٦٥
            clean_text = text.translate(AR_DIGITS_TABLE)
            match = re.search(
                rf"\b([0-9]{{1,2}})\s*({AR_MONTHS_PATTERN})\s*(?:سنة\s+|عام\s+)?([0-9]{{4}})\b",
                clean_text,
            )
            if match:
                day_str, month_name, year_str = match.groups()
                month_num = AR_MONTHS.get(month_name.strip())
                if month_num:
                    return f"{year_str}-{month_num}-{int(day_str):02d}"

        return None

    @classmethod
    def normalize_document_number(cls, num_str: Optional[str], year: int) -> Optional[str]:
        """Normalise le numéro de document sous la forme XX-YY (ex: 23-01).

        Gère l'inversion fréquente en arabe (01-23 -> 23-01 quand l'année est 2023).
        """
        if not num_str:
            return None

        # Nettoyage
        clean = re.sub(r"[^\d\-–/]", "", num_str).replace("–", "-").replace("/", "-")
        parts = clean.split("-")
        if len(parts) == 2:
            p1, p2 = parts[0], parts[1]
            year_suffix = str(year)[-2:]  # ex: "23" pour 2023
            # Si le premier membre est le numéro d'ordre et le second l'année (ex: 01-23 pour 2023)
            if p2 == year_suffix and p1 != year_suffix:
                return f"{year_suffix}-{int(p1):02d}"
            # Si c'est déjà annee-ordre (ex: 23-01)
            elif p1 == year_suffix:
                return f"{year_suffix}-{int(p2):02d}"
            else:
                return f"{p1}-{p2}"
        return clean

    @classmethod
    def detect_document_type(cls, title: str, lang: Language) -> Tuple[DocumentType, str]:
        """Détermine le type juridique et son code slug à partir de l'intitulé."""
        t = title.strip()
        if lang == Language.FR:
            if re.match(r"^Loi\s+organique", t, re.IGNORECASE):
                return DocumentType.LAW, "loi_org"
            elif re.match(r"^Loi\b", t, re.IGNORECASE):
                return DocumentType.LAW, "loi"
            elif re.match(r"^Ordonnance\b", t, re.IGNORECASE):
                return DocumentType.ORDER, "ord"
            elif re.match(r"^D[ée]crets?\s+l[ée]gislatifs?\b", t, re.IGNORECASE):
                return DocumentType.DECREE, "dl"
            elif re.match(r"^D[ée]crets?\s+pr[ée]sidentiels?\b", t, re.IGNORECASE):
                return DocumentType.DECREE, "dp"
            elif re.match(r"^D[ée]crets?\s+ex[ée]cutifs?\b", t, re.IGNORECASE):
                return DocumentType.DECREE, "de"
            elif re.match(r"^D[ée]crets?\b", t, re.IGNORECASE):
                return DocumentType.DECREE, "dec"
            elif re.match(r"^Arr[êe]t[ée]s?\b", t, re.IGNORECASE):
                return DocumentType.ORDER, "arr"
            elif re.match(r"^D[ée]cisions?\b", t, re.IGNORECASE):
                return DocumentType.DECISION, "dcs"
            elif re.match(r"^Circulaires?\b", t, re.IGNORECASE):
                return DocumentType.CIRCULAR, "circ"
            elif re.match(r"^Lettre\b", t, re.IGNORECASE):
                return DocumentType.OTHER, "lettre"
            elif re.match(r"^Accords?\b", t, re.IGNORECASE):
                return DocumentType.OTHER, "accord"
            elif re.match(r"^(?:Statuts?|R[èe]glements?\s+int[ée]rieur|R[èe]glements?)\b", t, re.IGNORECASE):
                return DocumentType.ORDER, "reg"
            elif re.match(r"^R[ée]solutions?\b", t, re.IGNORECASE):
                return DocumentType.ORDER, "res"
            elif re.match(r"^(?:Avis|Proclamations?)\b", t, re.IGNORECASE):
                return DocumentType.NOTICE, "avis"
            return DocumentType.OTHER, "act"
        else:
            if re.match(r"^قانون\s+عضوي", t):
                return DocumentType.LAW, "loi_org"
            elif re.match(r"^قانون\b", t):
                return DocumentType.LAW, "loi"
            elif re.match(r"^[أاإآ]مر\b", t):
                return DocumentType.ORDER, "ord"
            elif re.match(r"^(?:مرسوم|مراسيم|مرسومان)\s+رئاسي(?:ة|ان)?\b", t):
                return DocumentType.DECREE, "dp"
            elif re.match(r"^(?:مرسوم|مراسيم|مرسومان)\s+تنفيذي(?:ة|ان)?\b", t):
                return DocumentType.DECREE, "de"
            elif re.match(r"^(?:مرسوم|مراسيم|مرسومان)\b", t):
                return DocumentType.DECREE, "dec"
            elif re.match(r"^(?:قرار|قرارات|قراران)\b", t):
                return DocumentType.ORDER, "arr"
            elif re.match(r"^(?:مقرر|مقررات)\b", t):
                return DocumentType.DECISION, "dcs"
            elif re.match(r"^(?:منشور|مناشير)\b", t):
                return DocumentType.CIRCULAR, "circ"
            elif re.match(r"^(?:نظام|النظام)\b", t):
                return DocumentType.ORDER, "nizam"
            elif re.match(r"^(?:لائحة|لوائح)\b", t):
                return DocumentType.ORDER, "laiha"
            elif re.match(r"^رسالة\b", t):
                return DocumentType.OTHER, "lettre"
            elif re.match(r"^(?:[إا]علانات?|[إا]علان|بيانات?|بيان)\b", t):
                return DocumentType.NOTICE, "avis"
            return DocumentType.OTHER, "act"

    @classmethod
    def extract_metadata_from_heading(
        cls, heading: str, year: int, lang: Language
    ) -> Dict[str, Optional[str]]:
        """Extrait numéro, date, objet et type depuis une ligne d'en-tête."""
        doc_type, type_slug = cls.detect_document_type(heading, lang)

        # Extraction du numéro
        doc_number: Optional[str] = None
        if lang == Language.FR:
            num_match = re.search(r"\bn°?\s*([0-9]{2,4}[-–/][0-9]{1,4}|[0-9]+)", heading, re.IGNORECASE)
            if num_match:
                doc_number = num_match.group(1)
        else:
            num_match = re.search(r"رقم\s*([0-9]{2,4}[-–/][0-9]{1,4}|[0-9]+)", heading)
            if num_match:
                doc_number = num_match.group(1)

        normalized_number = cls.normalize_document_number(doc_number, year)
        date_iso = cls.parse_date(heading, lang)

        # Extraction de l'objet / sujet
        subject: Optional[str] = None
        if lang == Language.FR:
            subj_match = re.search(r"\b(?:portant|modifiant|relatif\s+à|fixant|déterminant)\s+(.+)$", heading, re.IGNORECASE)
            if subj_match:
                subject = subj_match.group(0).strip().rstrip(".")
        else:
            subj_match = re.search(r"\b(?:يتضمن|تتضمن|يتضمنان|يعدل|تعدل|يعدلان|يحدد|تحدد|يحددان|المتعلق\s+بـ|يتعلق\s+بـ|تتعلق\s+بـ|المحدد)\s+(.+)$", heading)
            if subj_match:
                subject = subj_match.group(0).strip().rstrip(".")

        return {
            "document_type": doc_type,
            "type_slug": type_slug,
            "document_number": doc_number,
            "normalized_number": normalized_number,
            "date_iso": date_iso,
            "subject": subject,
        }

    @classmethod
    def split_articles(cls, act_text: str, lang: Language) -> List[ParsedArticle]:
        """Découpe le corps d'un acte juridique en articles individuels."""
        regex = RE_ARTICLE_FR if lang == Language.FR else RE_ARTICLE_AR
        matches = list(regex.finditer(act_text))
        if not matches:
            return []

        articles: List[ParsedArticle] = []
        for i, m in enumerate(matches):
            art_num = m.group(1).strip()
            if art_num.lower() == "premier":
                art_num = "1er"
            start = m.end()

            # La fin de l'article est le début du prochain article,
            # ou la formule de signature finale, ou la fin de l'acte
            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(act_text)
                # Chercher une formule finale de signature dans le dernier article
                sig_regex = RE_SIGNATURE_FR if lang == Language.FR else RE_SIGNATURE_AR
                sig_match = sig_regex.search(act_text[start:end])
                if sig_match:
                    end = start + sig_match.start()

            art_body = act_text[start:end].strip()
            # Nettoyer les puces ou tirets initiaux éventuels
            art_body = re.sub(r"^[\s—\-\*:]+", "", art_body).strip()

            articles.append(
                ParsedArticle(
                    article_number=art_num,
                    text=art_body,
                    ordinal=i + 1,
                )
            )

        return articles

    @classmethod
    def parse_text(
        cls,
        text: str,
        year: int,
        jo_number: str,
        lang: Optional[Language] = None,
        source_id: int = 0,
        raw_path: Optional[str] = None,
    ) -> List[Tuple[CanonicalDocument, List[Article]]]:
        """Parse l'intégralité d'un numéro JORADP et retourne la liste des actes et articles."""
        if lang is None:
            lang = cls.detect_language(text)

        if lang == Language.AR:
            text = text.translate(AR_DIGITS_TABLE)

        heading_regex = RE_ACT_HEADING_FR if lang == Language.FR else RE_ACT_HEADING_AR
        preamble_regex = RE_PREAMBLE_FR if lang == Language.FR else RE_PREAMBLE_AR

        # Trouver tous les en-têtes d'actes candidats
        candidates = list(heading_regex.finditer(text))

        # Filtrer les candidats qui sont dans le corps (et non dans le sommaire ni dans une rectification)
        valid_acts_markers: List[Tuple[int, str]] = []
        for m in candidates:
            heading = m.group(1).strip().rstrip("*").rstrip(".")
            # Rejeter les lignes typiques de sommaire (... 6, p. 86)
            if RE_SOMMAIRE_LINE.search(heading):
                continue

            # Rejeter les sous-sections de rectificatifs (au lieu de / lire / عوض / يقرأ)
            prefix = text[max(0, m.start() - 60): m.start()].strip().lower()
            if re.search(r"(?:au\s+lieu\s+de|lire|remplacer\s+par|عوض|يقرأ)\s*:?\s*$", prefix):
                continue

            # Vérifier la présence d'un préambule légal ou de formule dans les 1200 caractères qui suivent
            snippet = text[m.end(): m.end() + 1200]
            if preamble_regex.search(snippet):
                valid_acts_markers.append((m.start(), heading))

        # Si aucun acte n'a été validé par préambule, fallback sur tous les non-sommaire et non-rectificatifs
        if not valid_acts_markers and candidates:
            for m in candidates:
                heading = m.group(1).strip().rstrip("*").rstrip(".")
                if RE_SOMMAIRE_LINE.search(heading):
                    continue
                prefix = text[max(0, m.start() - 60): m.start()].strip().lower()
                if re.search(r"(?:au\s+lieu\s+de|lire|remplacer\s+par|عوض|يقرأ)\s*:?\s*$", prefix):
                    continue
                valid_acts_markers.append((m.start(), heading))

        # Première passe : délimiter le texte et éliminer les vrais doublons stricts (titre + hash identiques)
        raw_acts_data = []
        doc_ordinal = 1
        seen_exact_duplicates = set()

        for i, (pos, heading) in enumerate(valid_acts_markers):
            end_pos = valid_acts_markers[i + 1][0] if i + 1 < len(valid_acts_markers) else len(text)
            act_full_text = text[pos:end_pos].strip()
            content_hash = hashlib.sha256(act_full_text.encode("utf-8")).hexdigest()

            # Élimination des doublons stricts (même titre ET même contenu de texte dans le même document)
            exact_dup_key = (heading.strip(), content_hash)
            if exact_dup_key in seen_exact_duplicates:
                continue
            seen_exact_duplicates.add(exact_dup_key)

            meta = cls.extract_metadata_from_heading(heading, year, lang)
            act_date = meta["date_iso"] or cls.parse_date(act_full_text[:500], lang)

            doc_type: DocumentType = meta["document_type"]
            type_slug: str = meta["type_slug"]
            norm_num: Optional[str] = meta["normalized_number"]

            if norm_num:
                num_slug = re.sub(r"[^a-zA-Z0-9\-]", "", norm_num).lower()
            else:
                num_slug = f"ord{doc_ordinal}"

            lang_code = "fr" if lang == Language.FR else "ar"
            base_canonical_id = f"joradp_{year}_{jo_number.zfill(3)}_{type_slug}_{num_slug}_{lang_code}"

            parsed_articles = cls.split_articles(act_full_text, lang)
            raw_acts_data.append({
                "base_canonical_id": base_canonical_id,
                "doc_type": doc_type,
                "heading": heading,
                "norm_num": norm_num,
                "meta_num": meta["document_number"],
                "act_date": act_date,
                "subject": meta["subject"],
                "act_full_text": act_full_text,
                "content_hash": content_hash,
                "parsed_articles": parsed_articles,
            })
            doc_ordinal += 1

        # Compter les occurrences de chaque base_canonical_id pour détecter les collisions d'actes distincts
        base_id_counts = Counter(d["base_canonical_id"] for d in raw_acts_data)

        results: List[Tuple[CanonicalDocument, List[Article]]] = []

        for d in raw_acts_data:
            base_id = d["base_canonical_id"]
            # Si collision entre actes distincts portant le même type et numéro dans le même JO :
            # Désambiguïsateur DÉTERMINISTE et STABLE basé sur les 8 premiers caractères du hash du contenu
            if base_id_counts[base_id] > 1:
                canonical_id = f"{base_id}_{d['content_hash'][:8]}"
            else:
                canonical_id = base_id

            content_hash = d["content_hash"]
            provenance = DocumentProvenance(
                source_db="joradp.db",
                source_table="sources",
                source_id=source_id,
                raw_path=raw_path,
                content_hash=content_hash,
                ingested_at=datetime.utcnow().isoformat(),
            )

            pub_num = f"JO {year}-{jo_number.zfill(3)}"
            doc = CanonicalDocument(
                canonical_id=canonical_id,
                document_type=d["doc_type"],
                document_nature=DocumentNature.LEGISLATIVE_NORM,
                jurisdiction=Jurisdiction.REPUBLIC,
                court_level=CourtLevel.LEGISLATIVE,
                title=d["heading"],
                document_number=d["norm_num"] or d["meta_num"],
                publication_number=pub_num,
                date=d["act_date"],
                year=year,
                language=lang,
                subject=d["subject"],
                full_text=d["act_full_text"],
                text_format="markdown",
                text_completeness=TextCompleteness.FULL_TEXT,
                extraction_method=ExtractionMethod.MARKDOWN_PARSE,
                extraction_quality=ExtractionQuality.HIGH,
                provenance=provenance,
                canonical_hash=content_hash,
                anonymization_status=AnonymizationStatus.NOT_ANONYMIZED,
            )

            articles_list: List[Article] = []
            for pa in d["parsed_articles"]:
                art = Article(
                    parent_document_id=canonical_id,
                    article_number=pa.article_number,
                    title=pa.title,
                    text=pa.text,
                    language=lang,
                    ordinal=pa.ordinal,
                )
                articles_list.append(art)

            results.append((doc, articles_list))

        return results

    @classmethod
    def parse_file(
        cls,
        filepath: str | Path,
        year: Optional[int] = None,
        jo_number: Optional[str] = None,
        lang: Optional[Language] = None,
        source_id: int = 0,
    ) -> List[Tuple[CanonicalDocument, List[Article]]]:
        """Lit et parse un fichier markdown.md de JORADP."""
        path = Path(filepath)
        if not path.is_file():
            raise FileNotFoundError(f"Fichier introuvable : {filepath}")

        # Déduire l'année et le numéro de JO depuis le chemin si non spécifiés
        # Ex: Extraction/OCR-Fr/2023/FR2023001.pdf/markdown.md
        # Ex: Extraction/OCR-Ar/2006/AR2006015.pdf/markdown.md
        if year is None or jo_number is None or lang is None:
            parts = path.parts
            for p in parts:
                if p == "OCR-Fr":
                    lang = lang or Language.FR
                elif p == "OCR-Ar":
                    lang = lang or Language.AR

            # Chercher le nom du dossier parent (ex: FR2023001.pdf)
            parent_name = path.parent.name
            match = re.search(r"([A-Z]{2})([0-9]{4})([0-9]{3})", parent_name)
            if match:
                prefix, y_str, num_str = match.groups()
                year = year or int(y_str)
                jo_number = jo_number or num_str
                if lang is None:
                    lang = Language.FR if prefix == "FR" else Language.AR

        # Valeurs par défaut si non déductibles
        year = year or datetime.now().year
        jo_number = jo_number or "001"
        lang = lang or Language.FR

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        return cls.parse_text(
            text=content,
            year=year,
            jo_number=jo_number,
            lang=lang,
            source_id=source_id,
            raw_path=str(path),
        )

    @classmethod
    def link_bilingual_acts(
        cls,
        fr_items: List[Tuple[CanonicalDocument, List[Article]]],
        ar_items: List[Tuple[CanonicalDocument, List[Article]]],
    ) -> int:
        """Apparie les actes français et arabes d'un même numéro.

        Définit `language_pair_id` sur les deux documents lorsqu'il y a correspondance.
        Retourne le nombre de paires créées.
        """
        linked_count = 0
        # Indexer les actes arabes par (document_type, normalized_document_number)
        ar_index: Dict[Tuple[DocumentType, str], CanonicalDocument] = {}
        for ar_doc, _ in ar_items:
            if ar_doc.document_number:
                key = (ar_doc.document_type, ar_doc.document_number)
                ar_index[key] = ar_doc

        for fr_doc, _ in fr_items:
            if fr_doc.document_number:
                key = (fr_doc.document_type, fr_doc.document_number)
                if key in ar_index:
                    ar_doc = ar_index[key]
                    fr_doc.language_pair_id = ar_doc.canonical_id
                    ar_doc.language_pair_id = fr_doc.canonical_id
                    linked_count += 1

        return linked_count
