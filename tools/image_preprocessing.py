"""
Module de Prétraitement d'Image et Segmentation Bicolonne pour Documents JORADP (1962-2026).
Comprend :
1. Deskew (Correction d'inclinaison)
2. Amélioration de Contraste (CLAHE) et Binarisation Adaptative (Sauvola / Otsu Local)
3. Détection de Gouttière et Découpage Bicolonne Ordonné (RTL pour AR / LTR pour FR)
"""

import cv2
import numpy as np
from PIL import Image
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path


def compute_skew_angle(cv_gray: np.ndarray, max_angle: float = 10.0) -> float:
    """
    Calcule l'angle d'inclinaison (skew angle) du texte en degrés via la transformée de Hough
    sur les lignes de texte détectées.
    """
    # Réduction de résolution pour rapidité
    h, w = cv_gray.shape[:2]
    scale = 1000.0 / max(h, w)
    small = cv2.resize(cv_gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    
    # Binarisation et détection de contours horizontaux
    blur = cv2.GaussianBlur(small, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 15)
    
    # Dilatation horizontale pour fusionner les lettres en lignes de texte
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3))
    dilated = cv2.dilate(thresh, kernel, iterations=2)
    
    # Détection des lignes par transformée de Hough probabiliste
    lines = cv2.HoughLinesP(dilated, 1, np.pi / 180, threshold=80, minLineLength=50, maxLineGap=10)
    
    if lines is None or len(lines) == 0:
        return 0.0
        
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx = x2 - x1
        dy = y2 - y1
        if abs(dx) > 1e-4:
            angle = np.arctan2(dy, dx) * 180.0 / np.pi
            # Filtrer les angles plausibles de rotation de scan (-max_angle à +max_angle)
            if -max_angle <= angle <= max_angle:
                angles.append(angle)
                
    if not angles:
        return 0.0
        
    # Médiane pour robustesse aux outliers
    median_angle = float(np.median(angles))
    return median_angle


def deskew_image(cv_img: np.ndarray, angle: Optional[float] = None) -> Tuple[np.ndarray, float]:
    """
    Redresse l'image si un angle d'inclinaison significatif (|angle| >= 0.2°) est détecté.
    """
    if len(cv_img.shape) == 3:
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = cv_img
        
    if angle is None:
        angle = compute_skew_angle(gray)
        
    if abs(angle) < 0.2:
        return cv_img, 0.0
        
    h, w = cv_img.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Remplissage avec fond blanc (255)
    rotated = cv2.warpAffine(
        cv_img, matrix, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255) if len(cv_img.shape) == 3 else 255
    )
    return rotated, angle


def sauvola_threshold(gray: np.ndarray, window_size: int = 35, k: float = 0.2, r: float = 128.0) -> np.ndarray:
    """
    Binarisation adaptative de Sauvola particulièrement efficace pour les scans anciens
    avec fond dégradé, jaunissement et contraste variable.
    """
    # Calcul de la moyenne et écart-type locaux par convolution
    mean = cv2.boxFilter(gray.astype(np.float32), cv2.CV_32F, (window_size, window_size), borderType=cv2.BORDER_REPLICATE)
    sq_mean = cv2.boxFilter((gray.astype(np.float32))**2, cv2.CV_32F, (window_size, window_size), borderType=cv2.BORDER_REPLICATE)
    variance = np.maximum(0, sq_mean - mean**2)
    std = np.sqrt(variance)
    
    # Formule du seuil de Sauvola
    threshold = mean * (1.0 + k * (std / r - 1.0))
    binarized = (gray.astype(np.float32) > threshold).astype(np.uint8) * 255
    return binarized


def preprocess_document_image(
    image_path: str,
    do_deskew: bool = True,
    do_binarize: bool = True,
    binarize_method: str = "sauvola"
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Pipeline complet de prétraitement :
    1. Chargement BGR
    2. Deskew
    3. Amélioration de contraste & Binarisation
    Retourne (img_clean_bgr_or_gray, img_binarized, skew_angle_detected)
    """
    cv_img = cv2.imread(str(image_path))
    if cv_img is None:
        raise FileNotFoundError(f"Impossible de charger l'image : {image_path}")
        
    # 1. Deskew
    angle = 0.0
    if do_deskew:
        cv_img, angle = deskew_image(cv_img)
        
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    
    # 2. Binarisation
    if do_binarize:
        if binarize_method == "sauvola":
            bin_img = sauvola_threshold(gray, window_size=35, k=0.18)
        elif binarize_method == "adaptive":
            bin_img = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)
        else: # Otsu
            _, bin_img = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        bin_img = gray
        
    return cv_img, bin_img, angle


def detect_and_split_columns(
    cv_img: np.ndarray,
    bin_img: np.ndarray,
    langue: str = "AR"
) -> List[Dict[str, Any]]:
    """
    Détecte la gouttière centrale et découpe la page bicolonne en segments logiques :
    - Header (En-tête pleine largeur si présent)
    - Colonne Droite & Colonne Gauche (ordonnées selon RTL si AR, LTR si FR)
    - Footer (Pied de page pleine largeur si présent)
    
    Retourne une liste ordonnée de dictionnaires contenant :
    [{'role': 'header'|'col1'|'col2'|'footer', 'crop_bin': np.ndarray, 'crop_color': np.ndarray, 'bbox': (x,y,w,h)}]
    """
    h, w = bin_img.shape[:2]
    
    # 1. Détection des zones en-tête / pied de page via profil de projection horizontale
    # Inverser pour que le texte soit 1 (noir) et le fond 0 (blanc)
    inv_bin = (bin_img == 0).astype(np.uint8)
    
    # Header threshold (environ les premiers 15% de la page)
    header_h = int(h * 0.12)
    footer_h = int(h * 0.92)
    
    # Body central
    body_inv = inv_bin[header_h:footer_h, :]
    
    # 2. Détection de la gouttière centrale (espace blanc vertical entre colonnes)
    # Projection verticale sur la zone centrale (entre 35% et 65% de la largeur)
    vert_proj = np.sum(body_inv, axis=0) # Densité de texte par colonne X
    
    mid_start = int(w * 0.38)
    mid_end = int(w * 0.62)
    
    central_proj = vert_proj[mid_start:mid_end]
    
    # Trouver le minimum de densité de texte dans la zone centrale (gouttière)
    if len(central_proj) > 0:
        # Lissage pour éviter le bruit
        kernel_size = 15
        smoothed = np.convolve(central_proj, np.ones(kernel_size)/kernel_size, mode='same')
        gutter_local_x = np.argmin(smoothed)
        gutter_x = mid_start + gutter_local_x
        min_density = smoothed[gutter_local_x]
        max_density = np.max(vert_proj)
        is_bicolumn = (min_density < max_density * 0.45)
    else:
        gutter_x = w // 2
        is_bicolumn = True
        
    segments = []
    
    # Header
    header_crop_bin = bin_img[0:header_h, :]
    header_crop_color = cv_img[0:header_h, :]
    if np.sum(inv_bin[0:header_h, :]) > 100: # Si contient du texte
        segments.append({
            "role": "header",
            "crop_bin": header_crop_bin,
            "crop_color": header_crop_color,
            "bbox": (0, 0, w, header_h)
        })
        
    # Colonnes du corps
    if is_bicolumn:
        left_col_bin = bin_img[header_h:footer_h, 0:gutter_x]
        left_col_color = cv_img[header_h:footer_h, 0:gutter_x]
        
        right_col_bin = bin_img[header_h:footer_h, gutter_x:w]
        right_col_color = cv_img[header_h:footer_h, gutter_x:w]
        
        if langue == "AR":
            # RTL : Colonne Droite en PREMIER, puis Colonne Gauche
            segments.append({
                "role": "column_right",
                "crop_bin": right_col_bin,
                "crop_color": right_col_color,
                "bbox": (gutter_x, header_h, w - gutter_x, footer_h - header_h)
            })
            segments.append({
                "role": "column_left",
                "crop_bin": left_col_bin,
                "crop_color": left_col_color,
                "bbox": (0, header_h, gutter_x, footer_h - header_h)
            })
        else:
            # LTR : Colonne Gauche en PREMIER, puis Colonne Droite
            segments.append({
                "role": "column_left",
                "crop_bin": left_col_bin,
                "crop_color": left_col_color,
                "bbox": (0, header_h, gutter_x, footer_h - header_h)
            })
            segments.append({
                "role": "column_right",
                "crop_bin": right_col_bin,
                "crop_color": right_col_color,
                "bbox": (gutter_x, header_h, w - gutter_x, footer_h - header_h)
            })
    else:
        # Page mono-colonne
        body_crop_bin = bin_img[header_h:footer_h, :]
        body_crop_color = cv_img[header_h:footer_h, :]
        segments.append({
            "role": "body_full",
            "crop_bin": body_crop_bin,
            "crop_color": body_crop_color,
            "bbox": (0, header_h, w, footer_h - header_h)
        })
        
    # Footer
    footer_crop_bin = bin_img[footer_h:h, :]
    footer_crop_color = cv_img[footer_h:h, :]
    if np.sum(inv_bin[footer_h:h, :]) > 100:
        segments.append({
            "role": "footer",
            "crop_bin": footer_crop_bin,
            "crop_color": footer_crop_color,
            "bbox": (0, footer_h, w, h - footer_h)
        })
        
    return segments
