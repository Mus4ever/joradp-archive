"""Modèle de données d'une décision du Conseil d'État algérien.

Structure alignée sur le HTML Drupal 11 réellement observé sur conseildetat.dz
(constat du 09/09/2026, voir docs/jurisprudence/conseil-etat-reconnaissance.md) :

  <article class="jurisprudence full clearfix">
    ├── field--name-field-numm-arr       (Numéro de décision)
    ├── field--name-field-date-arr       (Date de décision)
    ├── field--name-field-chamber-juris  (Chambre)
    ├── field--name-field-sect-jurisp    (Section)
    ├── field--name-field-keywords-juris (Mots-clés)
    ├── field--name-field-adapt-juris    (Classification / Tkayyuf)
    ├── field--name-field-sujet          (Objet / Sujet)
    ├── field--name-field-princ-arret    (Principe juridique / Mabda)
    └── field--name-field-details-arret  (Fichier PDF complet attaché)
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List


@dataclass
class Decision:
    # Identité
    id: Optional[int] = None
    nid: Optional[int] = None                       # Drupal node ID
    court: str = "مجلس الدولة"                      # Conseil d'État d'Algérie
    node_type: str = "jurisprudence"                 # jurisprudence | arrets-selectionnes | publications-revue
    decision_number: Optional[str] = None            # رقم القرار (field-numm-arr)
    date: Optional[str] = None                       # تاريخ القرار, ISO YYYY-MM-DD
    date_raw: Optional[str] = None                   # Date brute (ex: « 20  أفريل  2017 »)
    year: Optional[str] = None                       # Année extraite

    # Métadonnées structurées Drupal
    chamber: Optional[str] = None                    # الغرفة (field-chamber-juris)
    section: Optional[str] = None                    # القسم (field-sect-jurisp) — 57% renseigné
    keywords: Optional[str] = None                   # الكلمات المفتاحية (field-keywords-juris)
    classification: Optional[str] = None             # التكييف (field-adapt-juris)
    subject: Optional[str] = None                    # الموضوع (field-sujet)

    # Principe juridique (Mabda) — 100% renseigné, texte clair
    principle: Optional[str] = None                  # المبدأ (field-princ-arret)

    # PDF attaché
    pdf_url: Optional[str] = None                    # URL du PDF de l'arrêt intégral
    pdf_path: Optional[str] = None                   # Chemin local du PDF téléchargé
    pdf_hash: Optional[str] = None                   # SHA-256 du PDF téléchargé

    # Texte intégral de la fiche HTML
    text: Optional[str] = None                       # Texte normalisé de l'article complet
    language: str = "AR"

    # Provenance
    source_url: str = ""
    source_type: str = "html_page"
    content_hash: Optional[str] = None               # SHA-256 du HTML brut
    discovered_at: Optional[str] = None
    downloaded_at: Optional[str] = None

    # Cycle de vie : decouvert -> telecharge | erreur
    status: str = "decouvert"
    error: Optional[str] = None

    def to_dict(self):
        return asdict(self)
