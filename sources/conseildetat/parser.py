"""Parser HTML des décisions du Conseil d'État (conseildetat.dz, Drupal 11).

Sélecteurs établis sur le HTML brut réel (reconnaissance 09/09/2026 — voir
docs/jurisprudence/conseil-etat-reconnaissance.md) :

- <article class="jurisprudence full clearfix">
  → type de noeud via la première classe (jurisprudence, arrets-selectionnes, publications-revue) ;
- div.field--name-field-XXX → extraction de chaque métadonnée Drupal via les
  items de classe 'field--item' ou 'field__item' ;
- Lien PDF : <a href="...pdf"> dans l'article ;
- Dates en arabe (« 20  أفريل  2017 ») → ISO YYYY-MM-DD via mapping des mois.

Aucun sélecteur de position (nth-child), aucune classe générée dynamiquement.
"""

import hashlib
import re
import sys
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup

# Réutilise les fonctions de normalisation de la Cour suprême
import importlib.util
_norm_path = Path(__file__).resolve().parent.parent / "coursupreme" / "normalize.py"
_spec = importlib.util.spec_from_file_location("coursupreme_normalize", _norm_path)
_norm_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_norm_mod)
clean_text = _norm_mod.clean_text
normalize_arabic = _norm_mod.normalize_arabic
normalize_unicode = _norm_mod.normalize_unicode

from models import Decision  # noqa: E402

# Types de nœuds d'intérêt
DECISION_TYPES = {"jurisprudence", "arrets-selectionnes", "publications-revue"}

# Mapping des mois arabes vers numéros (observés dans les champs date du Conseil d'État)
ARABIC_MONTHS = {
    "جانفي": "01", "جانفيي": "01",
    "فيفري": "02", "فبراير": "02",
    "مارس": "03",
    "أفريل": "04", "افريل": "04",
    "ماي": "05", "مايو": "05",
    "جوان": "06", "يونيو": "06",
    "جويلية": "07", "يوليو": "07",
    "أوت": "08", "اوت": "08", "غشت": "08",
    "سبتمبر": "09",
    "أكتوبر": "10", "اكتوبر": "10",
    "نوفمبر": "11",
    "ديسمبر": "12",
}

# Regex pour extraire la date du format « DD  mois_arabe  YYYY »
_DATE_ARABIC_RE = re.compile(
    r"(\d{1,2})\s+("
    + "|".join(re.escape(m) for m in ARABIC_MONTHS)
    + r")\s+(\d{4})"
)

# Regex de repli pour les dates ISO ou numériques déjà formatées
_DATE_NUMERIC_RE = re.compile(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})")
_DATE_DMY_RE = re.compile(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})")

# Regex pour extraire l'année
_YEAR_RE = re.compile(r"\b(19\d\d|20\d\d)\b")


def parse_arabic_date(raw: Optional[str]) -> Optional[str]:
    """Convertit une date arabe « 20  أفريل  2017 » en ISO YYYY-MM-DD.

    Gère également les formats numériques YYYY/MM/DD et DD/MM/YYYY.
    """
    if not raw:
        return None
    raw = clean_text(raw) or ""

    # Format arabe : « DD  mois_arabe  YYYY »
    m = _DATE_ARABIC_RE.search(raw)
    if m:
        day, month_name, year = m.group(1), m.group(2), m.group(3)
        month_num = ARABIC_MONTHS.get(month_name)
        if month_num:
            return f"{int(year):04d}-{month_num}-{int(day):02d}"

    # Format numérique ISO : YYYY/MM/DD ou YYYY-MM-DD
    m = _DATE_NUMERIC_RE.search(raw)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{mo:02d}-{d:02d}"

    # Format numérique DMY : DD/MM/YYYY
    m = _DATE_DMY_RE.search(raw)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{mo:02d}-{d:02d}"

    return None


def extract_year(raw: Optional[str]) -> Optional[str]:
    """Extrait l'année d'une chaîne (date brute ou texte)."""
    if not raw:
        return None
    m = _YEAR_RE.search(str(raw))
    return m.group(1) if m else None


def _get_drupal_field(article, field_name: str) -> Optional[str]:
    """Extrait la valeur d'un champ Drupal depuis l'article HTML.

    Cherche un <div> dont une classe contient 'field--name-<field_name>',
    puis retourne le texte des éléments 'field--item' / 'field__item'.
    """
    el = article.find("div", class_=lambda x: x and f"field--name-{field_name}" in str(x))
    if not el:
        return None

    # Items Drupal 11 : classe 'field--item' ou 'field__item'
    items = el.find_all(class_=lambda x: x and ("field--item" in str(x) or "field__item" in str(x)))
    if items:
        texts = [it.get_text(strip=True) for it in items if it.get_text(strip=True)]
        if len(texts) == 1:
            return texts[0]
        elif len(texts) > 1:
            return " - ".join(texts)

    # Repli : retirer le libellé et retourner le texte brut
    lbl = el.find(class_=lambda x: x and ("field--label" in str(x) or "field__label" in str(x)))
    full_text = el.get_text(strip=True)
    if lbl:
        lbl_txt = lbl.get_text(strip=True)
        return full_text[len(lbl_txt):].strip()
    return full_text.strip() or None


def _extract_pdf_url(article) -> Optional[str]:
    """Extrait l'URL du premier PDF attaché à l'article."""
    for a in article.find_all("a", href=True):
        href = a["href"]
        if ".pdf" in href.lower():
            # Assurer l'URL absolue
            if href.startswith("/"):
                href = f"https://conseildetat.dz{href}"
            return href
    return None


def _detect_node_type(classes: list) -> Optional[str]:
    """Détecte le type de nœud Drupal depuis les classes CSS de l'article."""
    for cls in classes or []:
        if cls in DECISION_TYPES:
            return cls
    return None


def parse_decision(html: bytes, source_url: str, nid: Optional[int] = None) -> Decision:
    """Transforme le HTML brut d'une page /node/NID en objet Decision.

    Lève ValueError si la page n'est pas une page de décision reconnue.
    """
    soup = BeautifulSoup(html, "html.parser")

    article = soup.find("article")
    if not article:
        raise ValueError(f"Pas d'<article> trouvé: {source_url}")

    classes = article.get("class", [])
    node_type = _detect_node_type(classes)
    if not node_type:
        raise ValueError(f"Type de nœud non reconnu ({classes}): {source_url}")

    # Extraction des champs Drupal
    numm = _get_drupal_field(article, "field-numm-arr")
    date_raw = _get_drupal_field(article, "field-date-arr")
    chamber = _get_drupal_field(article, "field-chamber-juris")
    section = _get_drupal_field(article, "field-sect-jurisp")
    keywords = _get_drupal_field(article, "field-keywords-juris")
    classification = _get_drupal_field(article, "field-adapt-juris")
    subject = _get_drupal_field(article, "field-sujet")
    principle = _get_drupal_field(article, "field-princ-arret")
    pdf_url = _extract_pdf_url(article)

    # Normalisation
    date_iso = parse_arabic_date(date_raw)
    year = extract_year(date_raw) or extract_year(date_iso)

    # Texte intégral de l'article
    text = clean_text(article.get_text("\n", strip=True))

    d = Decision(
        nid=nid,
        node_type=node_type,
        decision_number=normalize_arabic(numm),
        date=date_iso,
        date_raw=date_raw,
        year=year,
        chamber=normalize_arabic(chamber),
        section=normalize_arabic(section),
        keywords=normalize_arabic(keywords),
        classification=normalize_arabic(classification),
        subject=normalize_arabic(subject),
        principle=normalize_arabic(principle),
        pdf_url=pdf_url,
        text=text,
        source_url=source_url,
        content_hash=hashlib.sha256(html).hexdigest(),
    )

    return d


def is_decision_page(html: bytes) -> bool:
    """Test rapide : la page contient-elle un article de type décision ?"""
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article")
    if not article:
        return False
    classes = article.get("class", [])
    return _detect_node_type(classes) is not None


def parse_decision_from_file(path: Path, source_url: str = "",
                              nid: Optional[int] = None) -> Decision:
    return parse_decision(path.read_bytes(), source_url=source_url, nid=nid)
