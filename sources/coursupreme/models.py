"""Modèle de données d'une décision de la Cour suprême.

Structure alignée sur le HTML réellement observé (constat du 09/09/2026,
voir docs/coursupreme.md) : bloc de métadonnées <li> + sections <h5>
+ classe de taxonomie sur <article>.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Decision:
    # Identité
    id: Optional[int] = None
    court: str = "المحكمة العليا"  # Cour suprême d'Algérie
    chamber: Optional[str] = None                 # déduite de la classe taxonomy de <article>
    chamber_class: Optional[str] = None           # classe brute ex. "civil-chambers-200"
    decision_number: Optional[str] = None         # رقم القرار
    date: Optional[str] = None                    # تاريخ القرار, ISO YYYY-MM-DD
    subject: Optional[str] = None                 # الموضوع
    parties: Optional[str] = None                 # الأطراف (déjà anonymisées en initiales par la Cour)
    keywords: Optional[str] = None                # الكلمات الأساسية (parfois absent)
    legal_references: Optional[str] = None        # المرجع القانوني (parfois absent)

    # Sections h5 standard (variantes "قرارات مهمة" → champs unconstitutionality_*)
    principle: Optional[str] = None               # المبدأ
    appeal_ground: Optional[str] = None           # وجه الطعن المثار من الطاعن
    court_response: Optional[str] = None          # رد المحكمة العليا عن الوجه
    unconstitutionality_grounds: Optional[str] = None   # أوجه الدفع بعدم الدستورية
    unconstitutionality_response: Optional[str] = None  # رد المحكمة العليا عن أوجه الدفع
    disposition: Optional[str] = None             # منطوق القرار
    president: Optional[str] = None               # الرئيس
    rapporteur: Optional[str] = None              # المستشار المقرر
    clerk: Optional[str] = None                   # أمين الضبط

    # Sections non mappées (robustesse aux évolutions du site)
    extra_sections: dict = field(default_factory=dict)
    extra_metadata: dict = field(default_factory=dict)

    # Texte
    text: Optional[str] = None                    # texte intégral normalisé de entry-content
    language: str = "AR"

    # Provenance (jamais null)
    source_url: str = ""
    source_type: str = "html_page"
    content_hash: Optional[str] = None            # SHA-256 du HTML brut téléchargé
    discovered_at: Optional[str] = None
    downloaded_at: Optional[str] = None
    category: Optional[str] = None                # catégorie de listing d'origine

    # Cycle de vie : decouvert -> telecharge -> parse | erreur
    status: str = "decouvert"
    error: Optional[str] = None

    def to_dict(self):
        return asdict(self)


# Mapping vérifié des classes taxonomy WordPress -> libellés de chambre.
# Complété au fil du constat (classes réellement observées sur <article>).
CHAMBER_CLASSES = {
    "civil-chambers": "الغرف المدنية",
    "criminal-chambers": "الغرف الجزائية",
    "compensation-committee": "لجنة التعويض",
    "significant-decisions": "قرارات مهمة",
    "joint-chambers": "الغرف المجتمعة",
}
