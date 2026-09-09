"""Normalisation arabe prudente pour les guides de la revue (Phase 3).

Texte extrait du guide = ordre VISUEL (RTL rendu LTR, chiffres à l'endroit).
Transformations, toutes réversibles/reproductibles :
  1. visual_to_logical : inverse chaque ligne en conservant les séquences
     de chiffres/latin à l'endroit (conversion bidi visuel→logique) ;
  2. NFKC : formes de présentation arabe (U+FExx) → formes basiques ;
  3. retrait tatweel (ـ U+0640), zero-width, espaces anormaux.

Aucune transformation ne modifie le contenu juridique (pas de suppression
de diacritiques, pas de réécriture lexicale). raw_text est toujours
conservé à côté de normalized_text.
"""

import re
import unicodedata

# Séquences à ne PAS inverser : chiffres (éventuellement séparés), latin
_LATIN_NUM_RE = re.compile(r"[0-9]+(?:[.,:/-][0-9]+)*|[A-Za-z]+")

_ZERO_WIDTH_RE = re.compile(r"[\u200b-\u200f\u202a-\u202e\ufeff]")
_TATWEEL_RE = re.compile(r"\u0640")
_MULTI_SPACE_RE = re.compile(r"[ \t\u00a0]+")


def visual_to_logical(line: str) -> str:
    """Inverse la ligne (ordre visuel → ordre logique RTL) en préservant
    les chiffres et le latin."""
    if not line:
        return line
    reversed_line = line[::-1]
    # les runs chiffres/latin étaient à l'endroit dans la ligne visuelle ;
    # après inversion globale, ils sont inversés → on les ré-inverse.
    return _LATIN_NUM_RE.sub(lambda m: m.group(0)[::-1], reversed_line)


def normalize_guide_text(text: str) -> str:
    """Chaîne complète de normalisation non destructive."""
    if text is None:
        return None
    out = []
    for line in text.split("\n"):
        line = visual_to_logical(line)
        line = unicodedata.normalize("NFKC", line)
        line = _ZERO_WIDTH_RE.sub("", line)
        line = _TATWEEL_RE.sub("", line)
        line = _MULTI_SPACE_RE.sub(" ", line).strip()
        if line:
            out.append(line)
    return "\n".join(out)


# Colonnes du guide (libellés d'en-tête, ordre visuel gauche→droite après
# extraction) — utilisées par le parser pour assigner les mots aux cellules.
COLUMN_HEADERS = ["رقم القرار", "الصفحة", "السنة", "العدد", "الغرفة",
                  "المرجع القانوني", "المبدأ", "الموضوع"]
