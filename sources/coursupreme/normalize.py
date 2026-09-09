"""Normalisation du texte des décisions (arabe et français).

Fonctions de base testées hors ligne (tests/test_coursupreme_normalize.py) :
- espaces multiples, insécables, zero-width
- dates vers ISO
- numéros de décision
- nettoyage HTML résiduel
"""

import re
import unicodedata
from typing import Optional


# --- Espaces et caractères invisibles -------------------------------------

# Espaces Unicode à ramener à l'espace simple (inclut insécable U+00A0,
# étroite insécable U+202F, zero-width space U+200B, BOM U+FEFF, etc.)
_INVISIBLE_SPACE_RE = re.compile(
    "[\u00a0\u2000-\u200b\u202f\u205f\u3000\ufeff]"
)
_MULTI_SPACE_RE = re.compile(r"[ \t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")


def clean_text(text: Optional[str]) -> Optional[str]:
    """Nettoie espaces et caractères invisibles, préserve les retours à la ligne."""
    if text is None:
        return None
    text = _INVISIBLE_SPACE_RE.sub(" ", text)
    # sépare les <br> transformés en \n par le parser avant ce nettoyage
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [_MULTI_SPACE_RE.sub(" ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip() or None


# --- Dates -----------------------------------------------------------------

# Formats réellement observés dans les métadonnées <li> :
#   "2016/01/13", "2019-10-09" (champ date déjà ISO), et dans les slugs
#   "13-01-2016" (JJ-MM-AAAA) et "07-17-2019" (MM-JJ-AAAA, variantes US).
_DATE_PATTERNS = [
    (re.compile(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})"), "ymd"),
    (re.compile(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})"), "dmy_or_mdy"),
]


def normalize_date(raw: Optional[str], day_first: bool = True) -> Optional[str]:
    """Convertit une date vers ISO YYYY-MM-DD. Retourne None si non parsable.

    day_first : pour les dates ambiguës JJ/MM vs MM/JJ. Les métadonnées du
    site sont AAAA/MM/JJ ; les slugs mélangent les deux ordres, d'où le
    paramètre explicite plutôt qu'une supposition.
    """
    if not raw:
        return None
    raw = clean_text(raw) or ""
    for pattern, order in _DATE_PATTERNS:
        m = pattern.search(raw)
        if not m:
            continue
        if order == "ymd":
            y, mo, d = m.group(1), m.group(2), m.group(3)
        else:
            a, b, y = m.group(1), m.group(2), m.group(3)
            if day_first:
                d, mo = a, b
            else:
                mo, d = a, b
        try:
            if 1 <= int(mo) <= 12 and 1 <= int(d) <= 31:
                return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
        except ValueError:
            continue
    return None


# --- Numéros de décision ----------------------------------------------------

_NUM_RE = re.compile(r"\d+")


def normalize_decision_number(raw: Optional[str]) -> Optional[str]:
    """Extrait le numéro de décision du libellé "رقم القرار:  7799" ou "01".

    Conserve la valeur telle qu'affichée (str) : les numéros de dossier
    (ex. 1040786) et les numéros de décision (ex. 01) ne sont pas comparables.
    """
    if not raw:
        return None
    raw = clean_text(raw) or ""
    m = _NUM_RE.search(raw)
    return m.group(0) if m else None


# --- Texte arabe ------------------------------------------------------------

# Diacritiques arabes (harakat) : préservés par défaut — le texte juridique
# peut en dépender subtilement ; on fournit l'outil mais on ne l'applique pas
# automatiquement.
ARABIC_DIACRITICS = re.compile(r"[\u064b-\u065f\u0670]")

# Ligatures et formes de présentation à normaliser vers la forme basique
ARABIC_PRESENTATION = {
    "\ufef5": "لا", "\ufef6": "لا", "\ufef7": "لأ", "\ufef8": "لأ",
    "\ufef9": "لإ", "\ufefa": "لإ", "\ufefb": "لا", "\ufefc": "لا",
}


def normalize_arabic(text: Optional[str], strip_diacritics: bool = False) -> Optional[str]:
    """Normalisation douce du texte arabe (pas de destruction d'information
    par défaut : les diacritiques ne sont retirés que sur demande explicite)."""
    if text is None:
        return None
    for src, dst in ARABIC_PRESENTATION.items():
        text = text.replace(src, dst)
    if strip_diacritics:
        text = ARABIC_DIACRITICS.sub("", text)
    return clean_text(text)


def normalize_unicode(text: Optional[str]) -> Optional[str]:
    """NFC (composition) : formes canoniques cohérentes pour le stockage."""
    if text is None:
        return None
    return unicodedata.normalize("NFC", text)
