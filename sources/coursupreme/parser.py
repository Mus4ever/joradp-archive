"""Parser HTML des décisions de la Cour suprême.

Sélecteurs établis sur le HTML brut réel (9 fixtures, 09/09/2026 — voir
docs/coursupreme.md) :

- <article class="decision type-decision status-publish <taxonomy>-N">
  → chambre via la classe taxonomy (stable, préfixe connu) ;
- div.entry-content > wpb-content-wrapper > ul > li  → bloc métadonnées
  "label: valeur" (رقم القرار، تاريخ القرار، الموضوع، الأطراف،
  الكلمات الأساسية، المرجع القانوني) ;
- sections : li > h5 (label) + li > p (contenu) ; certaines sections
  existent vides (h5 sans p — ex. وجه الطعن) : c'est un fait du site,
  pas une erreur de parsing.

Aucun sélecteur de position (nth-child), aucune classe générée dynamiquement.
"""

import hashlib
import re
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup

from models import Decision, CHAMBER_CLASSES
from normalize import (
    clean_text,
    normalize_arabic,
    normalize_date,
    normalize_decision_number,
    normalize_unicode,
)

# Libellés exacts observés dans les <li> de métadonnées (préfixes).
_META_LABELS = {
    "رقم القرار": "decision_number",
    "تاريخ القرار": "date",
    "الموضوع": "subject",
    "الأطراف": "parties",
    "الكلمات الأساسية": "keywords",
    "المرجع القانوني": "legal_references",
}

# Libellés exacts observés dans les <h5> de sections (préfixes, deux points
# et espaces finaux absorbés par la comparaison startswith).
_SECTION_LABELS = {
    "المبدأ": "principle",
    "وجه الطعن المثار من الطاعن المرتبط بالمبدأ": "appeal_ground",
    "رد المحكمة العليا عن الوجه المرتبط بالمبدأ": "court_response",
    "أوجه الدفع بعدم الدستورية": "unconstitutionality_grounds",
    "رد المحكمة العليا عن أوجه الدفع بعدم الدستورية": "unconstitutionality_response",
    "منطوق القرار": "disposition",
    "الرئيس": "president",
    "المستشار المقرر": "rapporteur",
    "أمين الضبط": "clerk",
}

# Chambres : classes taxonomy WordPress réellement observées sur <article>.
_TAXONOMY_RE = re.compile(
    r"^(civil-chambers|criminal-chambers|compensation-committee|"
    r"significant-decisions|joint-chambers)(-\d+)?$"
)

_DECISION_URL_RE = re.compile(r"/decision/[^/]+/?$")

_KNOWN_SECTION_FIELDS = set(_SECTION_LABELS.values())


def _strip_label(text: str) -> str:
    """Retire le préfixe "label:" d'une valeur de métadonnée."""
    return re.sub(r"^([^:]+):\s*", "", text, count=1)


def _taxonomy_class(article_classes) -> Optional[str]:
    for cls in article_classes or []:
        if _TAXONOMY_RE.match(cls):
            return cls
    return None


def chamber_from_class(cls: Optional[str]) -> Optional[str]:
    if not cls:
        return None
    for prefix, label in CHAMBER_CLASSES.items():
        if cls.startswith(prefix):
            return label
    return None


def parse_decision(html: bytes, source_url: str, category: Optional[str] = None) -> Decision:
    """Transforme le HTML brut d'une page /decision/ en objet Decision.

    Ne lève pas d'exception sur les champs manquants : les champs restent
    None et le contrôle qualité les comptera. Lève ValueError uniquement
    si la page n'est pas une page de décision (pas d'<article class=...>).
    """
    soup = BeautifulSoup(html, "html.parser")

    article = soup.find("article", id=True) or soup.find("article")
    classes = article.get("class") if article else None
    if not classes or "decision" not in (classes or []):
        raise ValueError(f"Pas une page de décision: {source_url}")

    taxonomy = _taxonomy_class(classes)

    content = article.find("div", class_="entry-content")
    if content is None:
        raise ValueError(f"entry-content introuvable: {source_url}")

    d = Decision(
        chamber=chamber_from_class(taxonomy),
        chamber_class=taxonomy,
        source_url=source_url,
        content_hash=hashlib.sha256(html).hexdigest(),
        category=category,
    )

    # --- Métadonnées : premiers <li> "label: valeur" -----------------------
    for li in content.find_all("li"):
        text = clean_text(li.get_text(" ", strip=True))
        if not text or ":" not in text:
            continue
        label = text.split(":", 1)[0].strip()
        value = clean_text(_strip_label(text))
        if label.startswith("رقم القرار"):
            d.decision_number = normalize_decision_number(value)
        elif label.startswith("تاريخ القرار"):
            d.date = normalize_date(value, day_first=True) or value
        elif label.startswith("الموضوع"):
            d.subject = normalize_arabic(value)
        elif label.startswith("الأطراف"):
            d.parties = normalize_arabic(value)
        elif label.startswith("الكلمات الأساسية"):
            d.keywords = normalize_arabic(value)
        elif label.startswith("المرجع القانوني"):
            d.legal_references = normalize_arabic(value)
        # les <li> de section (h5) n'ont pas de ":" au niveau texte → ignorés ici

    # --- Sections : li > h5 (label) + contenu -------------------------------
    # Contenu d'une section, par ordre de fiabilité :
    #   1. les <p> du <li> qui porte le h5 (cas standard) ;
    #   2. en repli, les <p> situés entre ce h5 et le h5 suivant dans l'ordre
    #      du document (cas constaté : variantes "قرارات مهمة" où le li du
    #      "رد المحكمة" est vide et le texte vit dans un <p> orphelin).
    h5s = content.find_all("h5")
    for idx, h5 in enumerate(h5s):
        label = clean_text(h5.get_text(" ", strip=True)) or ""
        label_clean = label.rstrip(":").strip()
        next_h5 = h5s[idx + 1] if idx + 1 < len(h5s) else None

        paragraphs = []
        li = h5.parent
        if li is not None and li.name == "li":
            paragraphs = li.find_all("p")

        if not paragraphs and next_h5 is not None:
            for el in h5.next_elements:
                if el is next_h5:
                    break
                if getattr(el, "name", None) is None:
                    continue  # chaînes de texte
                if content not in el.parents:
                    break  # sorti du conteneur de contenu
                if el.name == "p":
                    paragraphs.append(el)

        value = clean_text(
            normalize_arabic("\n".join(p.get_text("\n", strip=True) for p in paragraphs))
        )
        matched = None
        for known, field_name in _SECTION_LABELS.items():
            if label_clean.startswith(known):
                matched = field_name
                break
        if matched:
            setattr(d, matched, value)  # None si section réellement vide
        else:
            d.extra_sections[label_clean or "sans_titre"] = value

    # --- Texte intégral de entry-content ------------------------------------
    d.text = clean_text(content.get_text("\n", strip=True))

    return d


def is_decision_url(url: str) -> bool:
    return bool(_DECISION_URL_RE.search(url))


def parse_decision_from_file(path: Path, source_url: str = "", category: Optional[str] = None) -> Decision:
    return parse_decision(path.read_bytes(), source_url=source_url, category=category)
