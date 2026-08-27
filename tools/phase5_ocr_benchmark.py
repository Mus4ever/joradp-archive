"""
Banc d'essai OCR Multi-moteurs - Phase 5 (Corrigé A1, A2, A3, A4 & Inversion RTL)
Évalue les moteurs OCR majeurs sur 30 pages de test stratifiées :
1. Tesseract 5.5.0 (CPU Référence officielle avec ara + fra)
2. EasyOCR 1.7.2 (GPU CUDA / Batch avec isolation)
3. PaddleOCR 2.7.3 (PP-OCRv4 Multilingue / cls désactivé + inversion RTL pour AR)
(Surya OCR exclu suite aux tests d'incompatibilité de détection sur scans JORADP)
"""

import sys
import os
import time
import json
import subprocess
import unicodedata
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


# -------------------------------------------------------------
# Normalisation et métriques (Fix A1 & A2)
# -------------------------------------------------------------

ARABIC_ALEF_VARIANTS = re.compile(r'[إأآٱ]')
ARABIC_DIACRITICS    = re.compile(r'[\u064B-\u065F\u0670]')
ARABIC_PUNCT_GLUE    = re.compile(r'([،؛؟!\.,:\(\)«»\-])')


def normalize_for_wer(text: str) -> str:
    """
    Normalisation linguistique stricte pour comparaison OCR :
    - Forme Unicode NFC
    - Unification des variantes d'Alef (إأآٱ -> ا)
    - Suppression des harakat / diacritiques (\u064B-\u065F, \u0670)
    - Séparation des signes de ponctuation collés aux mots
    - Espaces multiples réduits
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = ARABIC_ALEF_VARIANTS.sub('ا', text)
    text = ARABIC_DIACRITICS.sub('', text)
    text = ARABIC_PUNCT_GLUE.sub(r' \1 ', text)
    return re.sub(r'\s+', ' ', text).strip()


def levenshtein(s1: str, s2: str) -> int:
    """Algorithme de Levenshtein itératif robuste et rapide."""
    s1, s2 = s1[:250], s2[:250]
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    m, n = len(s1), len(s2)
    if n == 0:
        return m
    prev = list(range(n + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1] + [0] * n
        for j, c2 in enumerate(s2):
            curr[j + 1] = min(
                prev[j + 1] + 1,      # suppression
                curr[j] + 1,          # insertion
                prev[j] + (c1 != c2)  # substitution
            )
        prev = curr
    return prev[n]


def line_cer(ref_line: str, hyp_line: str) -> float:
    """Calcul CER après normalisation Unicode."""
    r = "".join(normalize_for_wer(ref_line).split())
    h = "".join(normalize_for_wer(hyp_line).split())
    if not r:
        return 0.0 if not h else 1.0
    return min(1.0, levenshtein(r, h) / len(r))


def line_wer(ref_line: str, hyp_line: str) -> float:
    """Calcul WER après normalisation Unicode et séparation ponctuation."""
    r_words = normalize_for_wer(ref_line).split()
    h_words = normalize_for_wer(hyp_line).split()
    if not r_words:
        return 0.0 if not h_words else 1.0
    n, m = len(r_words), len(h_words)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if r_words[i - 1] == h_words[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return min(1.0, dp[n][m] / len(r_words))


def evaluate_ground_truth_matching(gt_lines: List[str], ocr_full_text: str) -> Tuple[float, float]:
    """
    Fix A1 : Alignement par fenêtre glissante sur le flux de mots OCR concaténé.
    Évite de pénaliser les moteurs dont les boîtes de détection découpent une phrase.
    """
    ocr_norm = normalize_for_wer(ocr_full_text)
    ocr_words = ocr_norm.split()
    if not ocr_words:
        return 1.0, 1.0
        
    total_cer = 0.0
    total_wer = 0.0
    M = len(ocr_words)
    
    for ref_line in gt_lines:
        ref_norm = normalize_for_wer(ref_line)
        r_words = ref_norm.split()
        N = len(r_words)
        if N == 0:
            continue
            
        best_wer = 1.0
        best_cer = 1.0
        
        # Fenêtre glissante de tailles N-2 à N+3 autour de la longueur de référence
        min_w = max(1, N - 2)
        max_w = min(M + 1, N + 4)
        
        for w_size in range(min_w, max_w):
            for start in range(0, M - w_size + 1):
                window_words = ocr_words[start:start + w_size]
                hyp_window = " ".join(window_words)
                
                # WER rapide
                dp = [[0] * (w_size + 1) for _ in range(N + 1)]
                for i in range(N + 1): dp[i][0] = i
                for j in range(w_size + 1): dp[0][j] = j
                for i in range(1, N + 1):
                    for j in range(1, w_size + 1):
                        cost = 0 if r_words[i - 1] == window_words[j - 1] else 1
                        dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
                w_val = min(1.0, dp[N][w_size] / N)
                
                if w_val < best_wer:
                    best_wer = w_val
                    best_cer = line_cer(ref_line, hyp_window)
                    if best_wer == 0.0:
                        break
            if best_wer == 0.0:
                break
                
        total_wer += best_wer
        total_cer += best_cer
        
    avg_cer = total_cer / len(gt_lines) if gt_lines else 1.0
    avg_wer = total_wer / len(gt_lines) if gt_lines else 1.0
    return avg_cer, avg_wer


def evaluate_numbers(expected_numbers: List[str], extracted_text: str) -> float:
    """Vérifie l'exactitude d'extraction des chiffres clés et numéros de décret."""
    if not expected_numbers:
        return 1.0
    found = 0
    clean_text = extracted_text.replace(" ", "")
    for num in expected_numbers:
        clean_num = num.replace(" ", "")
        if clean_num in clean_text or num in extracted_text:
            found += 1
    return found / len(expected_numbers)


# -------------------------------------------------------------
# Workers en mode Batch (Fix A3 & A4)
# -------------------------------------------------------------

def run_tesseract_batch(items: List[Dict[str, Any]], langue: str) -> Dict[str, Tuple[str, float]]:
    """Worker batch Tesseract (CPU Référence)."""
    paths_dict = {item["id"]: item["image_path"] for item in items}
    paths_json = json.dumps(paths_dict)
    
    script = f"""
import sys, os, time, json, pytesseract
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')
os.environ['TESSDATA_PREFIX'] = os.path.abspath('tessdata')
pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

lang_code = 'ara' if '{langue}' == 'AR' else 'fra'
config = '--oem 1 --psm 3'

imgs = json.loads({json.dumps(paths_json)})
results = {{}}

for doc_id, img_path in imgs.items():
    img = Image.open(img_path)
    t0 = time.perf_counter()
    txt = pytesseract.image_to_string(img, lang=lang_code, config=config)
    t1 = time.perf_counter()
    results[doc_id] = {{"text": txt, "time": round(t1 - t0, 4)}}

print("---JSON---")
sys.stdout.write(json.dumps(results, ensure_ascii=False))
"""
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    res = subprocess.run([sys.executable, "-c", script], capture_output=True, encoding='utf-8', errors='replace', env=env, timeout=600)
    if "---JSON---" not in res.stdout:
        print(f"[ERREUR Tesseract] {res.stderr[:300]}")
        return {item["id"]: ("", 0.0) for item in items}
    json_str = res.stdout.split("---JSON---")[1].strip()
    data = json.loads(json_str)
    return {k: (v["text"], v["time"]) for k, v in data.items()}


def run_easyocr_batch(items: List[Dict[str, Any]], langue: str) -> Dict[str, Tuple[str, float]]:
    """Worker batch EasyOCR (Fix A4 : CUDA nettoyé, Reader instancié UNE fois, mode batch)."""
    paths_dict = {item["id"]: item["image_path"] for item in items}
    paths_json = json.dumps(paths_dict)
    
    script = f"""
import sys, os, time, json
sys.stdout.reconfigure(encoding='utf-8')

# Fix A4: Nettoyage CUDA_VISIBLE_DEVICES
os.environ.pop('CUDA_VISIBLE_DEVICES', None)
import torch, easyocr

use_gpu = torch.cuda.is_available()
dev_str = f"GPU: {{torch.cuda.get_device_name(0)}}" if use_gpu else "CPU"
print(f"[EasyOCR Device] {{dev_str}}", flush=True)

langs = ['ar', 'en'] if '{langue}' == 'AR' else ['fr', 'en']

# Fix A4: Chargement UNIQUE du modèle
reader = easyocr.Reader(langs, gpu=use_gpu, verbose=False)

imgs = json.loads({json.dumps(paths_json)})
results = {{}}

for doc_id, img_path in imgs.items():
    t0 = time.perf_counter()
    res = reader.readtext(img_path, detail=0)
    t1 = time.perf_counter()
    results[doc_id] = {{"text": "\\n".join(res), "time": round(t1 - t0, 4)}}

print("---JSON---")
sys.stdout.write(json.dumps(results, ensure_ascii=False))
"""
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    res = subprocess.run([sys.executable, "-c", script], capture_output=True, encoding='utf-8', errors='replace', env=env, timeout=600)
    if "---JSON---" not in res.stdout:
        print(f"[ERREUR EasyOCR] {res.stderr[:300]}")
        return {item["id"]: ("", 0.0) for item in items}
    json_str = res.stdout.split("---JSON---")[1].strip()
    data = json.loads(json_str)
    return {k: (v["text"], v["time"]) for k, v in data.items()}


def run_paddle_batch(items: List[Dict[str, Any]], langue: str) -> Dict[str, Tuple[str, float]]:
    """Worker batch PaddleOCR (Fix A3 : use_angle_cls=False + inversion RTL des caractères pour AR)."""
    paths_dict = {item["id"]: item["image_path"] for item in items}
    paths_json = json.dumps(paths_dict)
    
    script = f"""
import sys, os, time, json, re
from paddleocr import PaddleOCR

sys.stdout.reconfigure(encoding='utf-8')

def fix_paddle_arabic_bidi(line: str) -> str:
    if not line: return ""
    tokens = line.split()
    fixed_tokens = []
    for tok in tokens:
        parts = re.split(r'([\d\\u0660-\\u0669]+(?:[\\.\\-/][\\d\\u0660-\\u0669]+)*|[a-zA-Z]+)', tok)
        fixed_parts = []
        for p in parts:
            if not p: continue
            if re.match(r'^[\\d\\u0660-\\u0669]+(?:[\\.\\-/][\\d\\u0660-\\u0669]+)*$', p) or re.match(r'^[a-zA-Z]+$', p):
                fixed_parts.append(p)
            else:
                fixed_parts.append(p[::-1])
        fixed_tokens.append("".join(fixed_parts))
    return " ".join(fixed_tokens[::-1])

if '{langue}' == 'AR':
    ocr = PaddleOCR(use_angle_cls=False, lang='ar', use_gpu=False, show_log=False)
else:
    ocr = PaddleOCR(use_angle_cls=True, lang='french', use_gpu=False, show_log=False)

imgs = json.loads({json.dumps(paths_json)})
results = {{}}

for doc_id, img_path in imgs.items():
    t0 = time.perf_counter()
    cls_flag = False if '{langue}' == 'AR' else True
    res = ocr.ocr(img_path, cls=cls_flag)
    t1 = time.perf_counter()
    lines = []
    if res and res[0]:
        for l in res[0]:
            txt = l[1][0]
            if '{langue}' == 'AR':
                txt = fix_paddle_arabic_bidi(txt)
            lines.append(txt)
    results[doc_id] = {{"text": "\\n".join(lines), "time": round(t1 - t0, 4)}}

print("---JSON---")
sys.stdout.write(json.dumps(results, ensure_ascii=False))
"""
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    res = subprocess.run([sys.executable, "-c", script], capture_output=True, encoding='utf-8', errors='replace', env=env, timeout=600)
    if "---JSON---" not in res.stdout:
        print(f"[ERREUR PaddleOCR] {res.stderr[:300]}")
        return {item["id"]: ("", 0.0) for item in items}
    json_str = res.stdout.split("---JSON---")[1].strip()
    data = json.loads(json_str)
    return {k: (v["text"], v["time"]) for k, v in data.items()}


# -------------------------------------------------------------
# Exécution du Benchmark Complet
# -------------------------------------------------------------

def run_benchmark():
    print("=" * 95)
    print("PHASE 5 — BANC D'ESSAI OCR MULTI-MOTEURS COMPARATIF (VERSION CORRIGÉE)")
    print("=" * 95)
    
    with open("benchmark/ground_truth.json", "r", encoding="utf-8") as f:
        ground_truth = json.load(f)
    with open("benchmark/manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    ar_items = [item for item in manifest if item["langue"] == "AR"]
    fr_items = [item for item in manifest if item["langue"] == "FR"]
    
    print(f"Dataset de référence : {len(manifest)} pages ({len(ar_items)} Arabe + {len(fr_items)} Français)\n")
    
    engines = [
        ("Tesseract 5.5.0", "CPU", run_tesseract_batch),
        ("EasyOCR 1.7.2", "GPU (CUDA)", run_easyocr_batch),
        ("PaddleOCR 2.7.3", "CPU/PP-OCR", run_paddle_batch),
    ]
    
    all_engine_results = []
    
    for engine_name, backend, batch_fn in engines:
        print("-" * 95)
        print(f"ÉVALUATION EN COURS : {engine_name} [{backend}]")
        print("-" * 95)
        
        engine_stats = {
            "engine_name": engine_name,
            "backend": backend,
            "ar_wer_list": [],
            "ar_cer_list": [],
            "ar_num_list": [],
            "ar_time_list": [],
            "fr_wer_list": [],
            "fr_cer_list": [],
            "fr_num_list": [],
            "fr_time_list": [],
            "pages": []
        }
        
        start_engine_total = time.time()
        
        # Traitement par lot : Arabe
        print(f"  > Exécution du lot Arabe ({len(ar_items)} pages)...", flush=True)
        ar_results = batch_fn(ar_items, "AR")
        for item in ar_items:
            doc_id = item["id"]
            era = item["era"]
            gt = ground_truth[doc_id]
            extracted_text, elapsed = ar_results.get(doc_id, ("", 0.0))
            
            cer, wer = evaluate_ground_truth_matching(gt["lines_ground_truth"], extracted_text)
            num_acc = evaluate_numbers(gt.get("key_numbers", []), extracted_text)
            
            engine_stats["ar_wer_list"].append(wer)
            engine_stats["ar_cer_list"].append(cer)
            engine_stats["ar_num_list"].append(num_acc)
            engine_stats["ar_time_list"].append(elapsed)
            
            engine_stats["pages"].append({
                "id": doc_id,
                "langue": "AR",
                "era": era,
                "wer": wer,
                "cer": cer,
                "num_accuracy": num_acc,
                "elapsed": elapsed,
                "sample": extracted_text[:120].replace("\n", " ") if extracted_text else "[VIDE]"
            })
            precision_txt = f"WER: {wer*100:5.1f}% (Précision: {(1-wer)*100:5.1f}%) | CER: {cer*100:5.1f}% | Nombres: {num_acc*100:5.1f}% | {elapsed:4.2f}s"
            print(f"    [{doc_id:<5} AR {era:<10}] {precision_txt}", flush=True)
            
        # Traitement par lot : Français
        print(f"  > Exécution du lot Français ({len(fr_items)} pages)...", flush=True)
        fr_results = batch_fn(fr_items, "FR")
        for item in fr_items:
            doc_id = item["id"]
            era = item["era"]
            gt = ground_truth[doc_id]
            extracted_text, elapsed = fr_results.get(doc_id, ("", 0.0))
            
            cer, wer = evaluate_ground_truth_matching(gt["lines_ground_truth"], extracted_text)
            num_acc = evaluate_numbers(gt.get("key_numbers", []), extracted_text)
            
            engine_stats["fr_wer_list"].append(wer)
            engine_stats["fr_cer_list"].append(cer)
            engine_stats["fr_num_list"].append(num_acc)
            engine_stats["fr_time_list"].append(elapsed)
            
            engine_stats["pages"].append({
                "id": doc_id,
                "langue": "FR",
                "era": era,
                "wer": wer,
                "cer": cer,
                "num_accuracy": num_acc,
                "elapsed": elapsed,
                "sample": extracted_text[:120].replace("\n", " ") if extracted_text else "[VIDE]"
            })
            precision_txt = f"WER: {wer*100:5.1f}% (Précision: {(1-wer)*100:5.1f}%) | CER: {cer*100:5.1f}% | Nombres: {num_acc*100:5.1f}% | {elapsed:4.2f}s"
            print(f"    [{doc_id:<5} FR {era:<10}] {precision_txt}", flush=True)
            
        all_engine_results.append(engine_stats)
        print(f"  Total temps moteur : {time.time() - start_engine_total:.1f}s\n", flush=True)
        
    # Calcul des scores finaux
    summary = []
    for s in all_engine_results:
        ar_wer = sum(s["ar_wer_list"]) / len(s["ar_wer_list"])
        ar_cer = sum(s["ar_cer_list"]) / len(s["ar_cer_list"])
        ar_num = sum(s["ar_num_list"]) / len(s["ar_num_list"])
        ar_time = sum(s["ar_time_list"]) / len(s["ar_time_list"])
        
        fr_wer = sum(s["fr_wer_list"]) / len(s["fr_wer_list"])
        fr_cer = sum(s["fr_cer_list"]) / len(s["fr_cer_list"])
        fr_num = sum(s["fr_num_list"]) / len(s["fr_num_list"])
        fr_time = sum(s["fr_time_list"]) / len(s["fr_time_list"])
        
        speed_ar = max(0.1, min(1.0, 1.0 / (1.0 + ar_time)))
        speed_fr = max(0.1, min(1.0, 1.0 / (1.0 + fr_time)))
        
        score_ar = (0.35 * (1.0 - ar_wer)) + (0.25 * ar_num) + (0.25 * (1.0 - ar_cer)) + (0.15 * speed_ar)
        score_fr = (0.35 * (1.0 - fr_wer)) + (0.25 * fr_num) + (0.25 * (1.0 - fr_cer)) + (0.15 * speed_fr)
        
        summary.append({
            "engine": s["engine_name"],
            "backend": s["backend"],
            "ar_precision_wer": (1.0 - ar_wer),
            "ar_wer": ar_wer,
            "ar_cer": ar_cer,
            "ar_num": ar_num,
            "ar_time": ar_time,
            "ar_score": score_ar,
            "fr_precision_wer": (1.0 - fr_wer),
            "fr_wer": fr_wer,
            "fr_cer": fr_cer,
            "fr_num": fr_num,
            "fr_time": fr_time,
            "fr_score": score_fr
        })
        
    out_json = Path("reports") / "phase5_benchmark_results_final.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "details": all_engine_results}, f, indent=2, ensure_ascii=False)
        
    print("\n" + "=" * 115, flush=True)
    print("BILAN COMPARATIF FINAL DU BANC D'ESSAI OCR MULTI-MOTEURS (PHASE 5 — RECALIBRÉ & VALIDÉ)", flush=True)
    print("=" * 115, flush=True)
    print(f"{'Moteur':<20} | {'Backend':<14} | {'AR Précision':<12} | {'AR Nombres':<10} | {'AR Temps':<8} | {'FR Précision':<12} | {'FR Nombres':<10} | {'FR Temps':<8} | {'Score AR':<8} | {'Score FR':<8}", flush=True)
    print("-" * 140, flush=True)
    for st in summary:
        print(f"{st['engine']:<20} | {st['backend']:<14} | {st['ar_precision_wer']*100:6.1f}%     | {st['ar_num']*100:8.1f}% | {st['ar_time']:6.2f}s | {st['fr_precision_wer']*100:6.1f}%     | {st['fr_num']*100:8.1f}% | {st['fr_time']:6.2f}s | {st['ar_score']*100:6.1f}% | {st['fr_score']*100:6.1f}%", flush=True)

    return summary


if __name__ == "__main__":
    run_benchmark()
