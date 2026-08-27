"""
Module d'extraction intelligent de texte PDF - Phase 4 (JORADP)
Architecture de classification et de routage page-par-page :
- NATIVE_OK (FR direct, ou AR mono-colonne propre)
- NATIVE_RTL_REORDER (AR multi-colonnes réordonné de droite à gauche)
- CORRUPT_MAPPING (Problème de police/ToUnicode -> NEEDS_REVIEW / OCR)
- SCAN_NO_TEXT (Scan image sans couche texte -> NEEDS_OCR)
"""

import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import pymupdf


class PageClassification:
    NATIVE_OK = "NATIVE_OK"
    NATIVE_RTL_REORDER = "NATIVE_RTL_REORDER"
    CORRUPT_MAPPING = "CORRUPT_MAPPING"
    SCAN_NO_TEXT = "SCAN_NO_TEXT"


class Phase4Extractor:
    """Extracteur intelligent et routeur page par page pour les PDF JORADP."""
    
    def __init__(self, downloads_dir: str = "downloads"):
        self.downloads_dir = Path(downloads_dir)

    def analyze_characters(self, text: str) -> Dict[str, Any]:
        """Analyse la distribution des caractères (arabe, latin, chiffres, suspects)."""
        arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF' or '\u0750' <= c <= '\u077F' or '\uFB50' <= c <= '\uFDFF' or '\uFE70' <= c <= '\uFEFF')
        latin_chars = sum(1 for c in text if 'a' <= c <= 'z' or 'A' <= c <= 'Z')
        digit_chars = sum(1 for c in text if c.isdigit() or '\u0660' <= c <= '\u0669')
        total_printable = sum(1 for c in text if not c.isspace())
        
        # Détection de lettres latines isolées / fragments parasites typiques du bug ToUnicode
        # Ex: "ـﺆﺗﻤﺮH...", "pاﻟﺪول", "Wأﺷﻐﺎل"
        suspect_latin = len(re.findall(r'(?<=[\u0600-\u06FF])[a-zA-Z]|[a-zA-Z](?=[\u0600-\u06FF])|\b[a-zA-Z]\b', text))
        
        # Ratio arabe par rapport au texte alphabétique
        alpha_total = arabic_chars + latin_chars
        arabic_ratio = (arabic_chars / alpha_total) if alpha_total > 0 else 0.0
        
        return {
            "total_chars": len(text),
            "total_printable": total_printable,
            "arabic_chars": arabic_chars,
            "latin_chars": latin_chars,
            "digit_chars": digit_chars,
            "arabic_ratio": arabic_ratio,
            "suspect_latin_count": suspect_latin
        }

    def detect_page_type(self, page: pymupdf.Page, langue: str, raw_text: str, char_stats: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any]]:
        """
        Détermine le type de page et la méthode d'extraction appropriée.
        Retourne (page_type, methode, quality_flags).
        """
        total_printable = char_stats["total_printable"]
        arabic_chars = char_stats["arabic_chars"]
        latin_chars = char_stats["latin_chars"]
        arabic_ratio = char_stats["arabic_ratio"]
        images = page.get_images()
        has_images = len(images) > 0
        
        quality_flags = {
            "has_images": has_images,
            "image_count": len(images),
            "duplicate_lines": False,
            "corrupt_font": False,
            "suspect_latin": char_stats["suspect_latin_count"] > 5
        }
        
        # 1. Cas SCAN : très peu de texte ou aucun texte natif (< 40 caractères utiles)
        if total_printable < 40:
            return PageClassification.SCAN_NO_TEXT, "needs_ocr", quality_flags
        
        # 2. Cas Corrupt Mapping pour PDF Arabe
        if langue == "AR":
            # Si le PDF est censé être en arabe mais a presque 0 arabe et beaucoup de latin (ex: AR2005042)
            if total_printable > 150 and arabic_chars < 50 and latin_chars > 100:
                quality_flags["corrupt_font"] = True
                return PageClassification.CORRUPT_MAPPING, "needs_review", quality_flags
            
            # Si le ratio arabe est anormalement bas (< 40% sur un document plein)
            if total_printable > 300 and arabic_ratio < 0.40:
                quality_flags["corrupt_font"] = True
                return PageClassification.CORRUPT_MAPPING, "needs_review", quality_flags

            # Cas normal Arabe -> Nécessite réordonnancement RTL intelligent
            return PageClassification.NATIVE_RTL_REORDER, "rtl_reorder", quality_flags
        
        else: # Langue FR
            # Vérification simple pour FR
            if total_printable > 150 and latin_chars < 30:
                quality_flags["corrupt_font"] = True
                return PageClassification.CORRUPT_MAPPING, "needs_review", quality_flags
            
            return PageClassification.NATIVE_OK, "native", quality_flags

    def extract_arabic_rtl_reordered(self, page: pymupdf.Page) -> Tuple[str, Dict[str, Any]]:
        """
        Extraction avec réordonnancement RTL intelligent et détection de colonnes.
        Structure typique JORADP:
        - Entête (pleine largeur en haut)
        - Colonne Droite (lue en premier pour l'arabe)
        - Colonne Gauche (lue en second)
        - Éléments pleine largeur intercalés (titres de décrets centrés)
        - Bas de page / numéro de page
        """
        rect = page.rect
        page_width = rect.width
        page_height = rect.height
        mid_x = page_width / 2.0
        
        # Extraction des blocs texte
        raw_blocks = page.get_text("blocks")
        # Garde seulement les blocs texte valides (type 0)
        text_blocks = [b for b in raw_blocks if b[6] == 0 and b[4].strip()]
        
        if not text_blocks:
            return "", {"columns": 0}
        
        # Classification des blocs en :
        # - Header (y1 < 80pt)
        # - Footer (y0 > page_height - 60pt)
        # - Full-width body elements (largeur > 65% de la page)
        # - Right column (centre du bloc à droite de mid_x)
        # - Left column (centre du bloc à gauche de mid_x)
        
        header_blocks = []
        footer_blocks = []
        body_blocks = []
        
        for b in text_blocks:
            x0, y0, x1, y1, text, bno, btype = b
            block_w = x1 - x0
            
            # Header en haut
            if y1 <= 85:
                header_blocks.append(b)
            # Footer en bas
            elif y0 >= page_height - 50:
                footer_blocks.append(b)
            else:
                body_blocks.append(b)
                
        # Trier header de haut en bas
        header_blocks.sort(key=lambda b: (round(b[1] / 10), -b[0]))
        footer_blocks.sort(key=lambda b: (round(b[1] / 10), -b[0]))
        
        # Analyser les blocs du corps pour partitionner en colonnes ou segments verticaux
        # Un bloc qui traverse le centre (x0 < mid_x - 30 and x1 > mid_x + 30) est pleine largeur (ex: titre séparateur)
        segments = []
        current_2col_right = []
        current_2col_left = []
        
        def flush_columns():
            nonlocal current_2col_right, current_2col_left, segments
            if current_2col_right or current_2col_left:
                # Colonne DROITE en premier (RTL), triée verticalement
                current_2col_right.sort(key=lambda b: b[1])
                # Colonne GAUCHE en second, triée verticalement
                current_2col_left.sort(key=lambda b: b[1])
                
                segments.extend(current_2col_right)
                segments.extend(current_2col_left)
                current_2col_right = []
                current_2col_left = []
        
        # Trier d'abord tous les blocs body par Y
        body_blocks.sort(key=lambda b: b[1])
        
        for b in body_blocks:
            x0, y0, x1, y1, text, bno, btype = b
            block_mid = (x0 + x1) / 2.0
            is_full_width = (x1 - x0) > (page_width * 0.65) or (x0 < (mid_x - 40) and x1 > (mid_x + 40))
            
            if is_full_width:
                # Vider les colonnes précédentes
                flush_columns()
                # Insérer l'élément pleine largeur
                segments.append(b)
            else:
                if block_mid >= mid_x:
                    current_2col_right.append(b)
                else:
                    current_2col_left.append(b)
                    
        flush_columns()
        
        # Assembler tout le document dans l'ordre logique
        final_blocks = header_blocks + segments + footer_blocks
        
        # Nettoyage et suppression des doublons consécutifs exacts
        extracted_paragraphs = []
        prev_text = ""
        duplicate_detected = False
        
        for b in final_blocks:
            clean_t = b[4].strip()
            if not clean_t:
                continue
            if clean_t == prev_text:
                duplicate_detected = True
                continue # Évite les doubles couches de texte superposées
            extracted_paragraphs.append(clean_t)
            prev_text = clean_t
            
        final_text = "\n\n".join(extracted_paragraphs)
        
        return final_text, {
            "columns": 2 if (len(body_blocks) > 4) else 1,
            "duplicate_detected": duplicate_detected,
            "block_count": len(final_blocks)
        }

    def extract_french_native(self, page: pymupdf.Page) -> Tuple[str, Dict[str, Any]]:
        """Extraction ordonnée pour le français (colonnes de gauche à droite)."""
        rect = page.rect
        page_width = rect.width
        mid_x = page_width / 2.0
        
        raw_blocks = page.get_text("blocks")
        text_blocks = [b for b in raw_blocks if b[6] == 0 and b[4].strip()]
        
        if not text_blocks:
            return "", {"columns": 0}
            
        header_blocks = []
        footer_blocks = []
        body_left = []
        body_right = []
        full_width_body = []
        
        page_height = rect.height
        
        for b in text_blocks:
            x0, y0, x1, y1, text, bno, btype = b
            block_mid = (x0 + x1) / 2.0
            is_full_width = (x1 - x0) > (page_width * 0.65)
            
            if y1 <= 85:
                header_blocks.append(b)
            elif y0 >= page_height - 50:
                footer_blocks.append(b)
            elif is_full_width:
                full_width_body.append(b)
            elif block_mid < mid_x:
                body_left.append(b)
            else:
                body_right.append(b)
                
        # Tri
        header_blocks.sort(key=lambda b: (round(b[1] / 10), b[0]))
        footer_blocks.sort(key=lambda b: (round(b[1] / 10), b[0]))
        body_left.sort(key=lambda b: b[1])
        body_right.sort(key=lambda b: b[1])
        
        if full_width_body:
            # Si éléments mixtes, tri par Y
            all_body = body_left + body_right + full_width_body
            all_body.sort(key=lambda b: (round(b[1] / 20), b[0]))
            ordered_blocks = header_blocks + all_body + footer_blocks
        else:
            # Ordre standard français 2 colonnes : Gauche puis Droite
            ordered_blocks = header_blocks + body_left + body_right + footer_blocks
            
        paragraphs = [b[4].strip() for b in ordered_blocks if b[4].strip()]
        return "\n\n".join(paragraphs), {"columns": 2 if len(body_right) > 2 else 1}

    def process_page(self, page: pymupdf.Page, langue: str) -> Dict[str, Any]:
        """
        Traite une page unique avec le routeur intelligent.
        Retourne toutes les métriques et le texte extrait.
        """
        raw_default_text = page.get_text()
        char_stats = self.analyze_characters(raw_default_text)
        
        page_type, methode, quality_flags = self.detect_page_type(page, langue, raw_default_text, char_stats)
        
        extracted_text = ""
        layout_info = {}
        
        if page_type == PageClassification.SCAN_NO_TEXT:
            extracted_text = ""
            methode = "needs_ocr"
            quality_score = 0.0
            
        elif page_type == PageClassification.CORRUPT_MAPPING:
            # On conserve le texte brut extrait mais marqué needs_review
            extracted_text = raw_default_text
            methode = "needs_review"
            quality_score = 0.2
            
        elif page_type == PageClassification.NATIVE_RTL_REORDER:
            extracted_text, layout_info = self.extract_arabic_rtl_reordered(page)
            methode = "rtl_reorder"
            quality_score = 0.95 if not quality_flags.get("suspect_latin") else 0.80
            if layout_info.get("duplicate_detected"):
                quality_flags["duplicate_lines"] = True
                
        else: # NATIVE_OK (FR)
            extracted_text, layout_info = self.extract_french_native(page)
            methode = "native_ordered"
            quality_score = 0.98
            
        # Mise à jour des stats finales sur le texte extrait
        final_stats = self.analyze_characters(extracted_text if extracted_text else raw_default_text)
        
        return {
            "page_type": page_type,
            "methode": methode,
            "quality_score": quality_score,
            "quality_flags": quality_flags,
            "extracted_text": extracted_text,
            "total_chars": final_stats["total_chars"],
            "arabic_chars": final_stats["arabic_chars"],
            "latin_chars": final_stats["latin_chars"],
            "digit_chars": final_stats["digit_chars"],
            "arabic_ratio": final_stats["arabic_ratio"],
            "suspect_latin_count": final_stats["suspect_latin_count"],
            "has_images": 1 if quality_flags["has_images"] else 0,
            "layout_info": layout_info
        }

    def extract_pdf_file(self, pdf_path: Path, langue: str) -> Dict[str, Any]:
        """Extrait tout un fichier PDF page par page."""
        if not pdf_path.exists():
            return {"error": f"Fichier non trouvé: {pdf_path}"}
            
        try:
            doc = pymupdf.open(pdf_path)
            total_pages = len(doc)
            pages_results = []
            
            for page_idx in range(total_pages):
                page = doc[page_idx]
                page_res = self.process_page(page, langue)
                page_res["page_num"] = page_idx + 1
                pages_results.append(page_res)
                
            doc.close()
            
            # Synthèse globale du PDF
            types_count = {}
            for p in pages_results:
                ptype = p["page_type"]
                types_count[ptype] = types_count.get(ptype, 0) + 1
                
            # Détermination du statut global du document
            if types_count.get(PageClassification.SCAN_NO_TEXT, 0) == total_pages:
                overall_status = "scan_complet_needs_ocr"
            elif types_count.get(PageClassification.CORRUPT_MAPPING, 0) > 0:
                overall_status = "corrupt_mapping_needs_review"
            elif types_count.get(PageClassification.SCAN_NO_TEXT, 0) > 0:
                overall_status = "mixte_partiel_needs_ocr"
            else:
                overall_status = "extrait_succes"
                
            return {
                "total_pages": total_pages,
                "overall_status": overall_status,
                "types_count": types_count,
                "pages": pages_results,
                "success": True
            }
            
        except Exception as e:
            return {"error": str(e), "success": False}
