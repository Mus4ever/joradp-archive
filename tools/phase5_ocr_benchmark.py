"""
Banc d'essai OCR Multi-moteurs - Phase 5 (Isolation des processus & Mesure scientifique)
Évalue les moteurs OCR majeurs sur 30 pages de test stratifiées :
1. EasyOCR 1.7.2 (GPU CUDA - GTX 1660 Super)
2. PaddleOCR 2.7.3 (PP-OCRv4 Multilingue)
3. Tesseract 5.5.0 (CPU Référence officielle avec ara + fra)
4. Surya OCR (GPU CUDA)
"""

import sys
import os
import time
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Tuple

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


def levenshtein(s1: str, s2: str) -> int:
    """Algorithme de Levenshtein iteratif (pas recursif) pour eviter stack overflow."""
    # Limite les chaines trop longues pour la vitesse (max 200 chars chacune)
    s1, s2 = s1[:200], s2[:200]
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    m, n = len(s1), len(s2)
    if n == 0:
        return m
    # Utilise un seul tableau 1D pour la performance memoire
    prev = list(range(n + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1] + [0] * n
        for j, c2 in enumerate(s2):
            curr[j + 1] = min(
                prev[j + 1] + 1,   # suppression
                curr[j] + 1,       # insertion
                prev[j] + (c1 != c2)  # substitution
            )
        prev = curr
    return prev[n]


def line_cer(ref_line: str, hyp_line: str) -> float:
    r = "".join(ref_line.split())
    h = "".join(hyp_line.split())
    if not r:
        return 0.0 if not h else 1.0
    return min(1.0, levenshtein(r, h) / len(r))


def line_wer(ref_line: str, hyp_line: str) -> float:
    r_words = ref_line.split()
    h_words = hyp_line.split()
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
    ocr_lines = [l.strip() for l in ocr_full_text.splitlines() if l.strip()]
    if not ocr_lines:
        return 1.0, 1.0
        
    total_cer = 0.0
    total_wer = 0.0
    
    for ref_line in gt_lines:
        best_cer = 1.0
        best_wer = 1.0
        for hyp_line in ocr_lines:
            cer = line_cer(ref_line, hyp_line)
            if cer < best_cer:
                best_cer = cer
                best_wer = line_wer(ref_line, hyp_line)
        total_cer += best_cer
        total_wer += best_wer
        
    avg_cer = total_cer / len(gt_lines) if gt_lines else 1.0
    avg_wer = total_wer / len(gt_lines) if gt_lines else 1.0
    return avg_cer, avg_wer


def evaluate_numbers(expected_numbers: List[str], extracted_text: str) -> float:
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
# Workers isolés par sous-processus
# -------------------------------------------------------------

def run_tesseract_worker(image_path: str, langue: str) -> Tuple[str, float]:
    script = f"""
import sys, os, time, pytesseract
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')
os.environ['TESSDATA_PREFIX'] = os.path.abspath('tessdata')
pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

img = Image.open(r'{image_path}')
lang_code = 'ara' if '{langue}' == 'AR' else 'fra'
config = '--oem 1 --psm 3'

t0 = time.perf_counter()
txt = pytesseract.image_to_string(img, lang=lang_code, config=config)
t1 = time.perf_counter()

print(f"TIME:{{t1-t0:.4f}}")
print("---OUTPUT---")
sys.stdout.write(txt)
"""
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    res = subprocess.run([sys.executable, "-c", script], capture_output=True, encoding='utf-8', errors='replace', env=env, timeout=120)
    if res.returncode != 0 or not res.stdout:
        return "", 0.0
    parts = res.stdout.split("---OUTPUT---")
    try:
        time_str = parts[0].split("TIME:")[-1].strip().split("\n")[0]
        elapsed = float(time_str)
        text = parts[1] if len(parts) > 1 else ""
        return text, elapsed
    except Exception:
        return "", 0.0


def run_easyocr_worker(image_path: str, langue: str) -> Tuple[str, float]:
    script = f"""
import sys, os, time, easyocr, torch

sys.stdout.reconfigure(encoding='utf-8')
use_gpu = torch.cuda.is_available()
langs = ['ar', 'en'] if '{langue}' == 'AR' else ['fr', 'en']

reader = easyocr.Reader(langs, gpu=use_gpu, verbose=False)

t0 = time.perf_counter()
res = reader.readtext(r'{image_path}', detail=0)
t1 = time.perf_counter()

print(f"TIME:{{t1-t0:.4f}}")
print("---OUTPUT---")
sys.stdout.write("\\n".join(res))
"""
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    res = subprocess.run([sys.executable, "-c", script], capture_output=True, encoding='utf-8', errors='replace', env=env, timeout=120)
    if res.returncode != 0 or not res.stdout:
        return "", 0.0
    parts = res.stdout.split("---OUTPUT---")
    try:
        time_str = parts[0].split("TIME:")[-1].strip().split("\n")[0]
        elapsed = float(time_str)
        text = parts[1] if len(parts) > 1 else ""
        return text, elapsed
    except Exception:
        return "", 0.0


def run_paddle_worker(image_path: str, langue: str) -> Tuple[str, float]:
    script = f"""
import sys, os, time
from paddleocr import PaddleOCR

sys.stdout.reconfigure(encoding='utf-8')
lang_code = 'ar' if '{langue}' == 'AR' else 'french'
ocr = PaddleOCR(use_angle_cls=True, lang=lang_code, use_gpu=False, show_log=False)

t0 = time.perf_counter()
res = ocr.ocr(r'{image_path}', cls=True)
t1 = time.perf_counter()

lines = []
if res and res[0]:
    for l in res[0]:
        lines.append(l[1][0])

print(f"TIME:{{t1-t0:.4f}}")
print("---OUTPUT---")
sys.stdout.write("\\n".join(lines))
"""
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    res = subprocess.run([sys.executable, "-c", script], capture_output=True, encoding='utf-8', errors='replace', env=env, timeout=120)
    if res.returncode != 0 or not res.stdout:
        return "", 0.0
    parts = res.stdout.split("---OUTPUT---")
    try:
        time_str = parts[0].split("TIME:")[-1].strip().split("\n")[0]
        elapsed = float(time_str)
        text = parts[1] if len(parts) > 1 else ""
        return text, elapsed
    except Exception:
        return "", 0.0


def run_surya_worker(image_path: str, langue: str) -> Tuple[str, float]:
    script = f"""
import sys, os, time, warnings
warnings.filterwarnings('ignore')
from PIL import Image
from surya.ocr import run_ocr
from surya.model.detection.model import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor

sys.stdout.reconfigure(encoding='utf-8')
det_p, det_m = load_det_processor(), load_det_model()
rec_p, rec_m = load_rec_processor(), load_rec_model()

img = Image.open(r'{image_path}').convert('RGB')
langs = ['ar'] if '{langue}' == 'AR' else ['fr']

t0 = time.perf_counter()
preds = run_ocr([img], [langs], det_m, det_p, rec_m, rec_p)
t1 = time.perf_counter()

lines = []
if preds and preds[0].text_lines:
    for l in preds[0].text_lines:
        lines.append(l.text)

print(f"TIME:{{t1-t0:.4f}}")
print("---OUTPUT---")
sys.stdout.write("\\n".join(lines))
"""
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    try:
        res = subprocess.run([sys.executable, "-c", script], capture_output=True, encoding='utf-8', errors='replace', env=env, timeout=180)
    except subprocess.TimeoutExpired:
        return "", 0.0
    if res.returncode != 0 or not res.stdout or "---OUTPUT---" not in res.stdout:
        return "", 0.0
    parts = res.stdout.split("---OUTPUT---")
    try:
        time_str = parts[0].split("TIME:")[-1].strip().split("\n")[0]
        elapsed = float(time_str)
        text = parts[1] if len(parts) > 1 else ""
        return text, elapsed
    except Exception:
        return "", 0.0


def run_benchmark():
    print("=" * 95)
    print("PHASE 5 — BANC D'ESSAI OCR MULTI-MOTEURS COMPARATIF (GPU & CPU)")
    print("=" * 95)
    
    with open("benchmark/ground_truth.json", "r", encoding="utf-8") as f:
        ground_truth = json.load(f)
    with open("benchmark/manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    print(f"Dataset de référence : {len(manifest)} pages (15 Arabe + 15 Français)\n")
    
    engines = [
        ("Tesseract 5.5.0", "CPU", run_tesseract_worker),
        ("EasyOCR 1.7.2", "GPU (CUDA)", run_easyocr_worker),
        ("PaddleOCR 2.7.3", "CPU/PP-OCR", run_paddle_worker),
        ("Surya OCR 0.8.3", "GPU (CUDA fp16)", run_surya_worker),
    ]
    
    all_engine_results = []
    
    for engine_name, backend, worker_fn in engines:
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
        
        for item in manifest:
            doc_id = item["id"]
            langue = item["langue"]
            img_path = item["image_path"]
            era = item["era"]
            desc = item["desc"]
            gt = ground_truth[doc_id]
            
            try:
                extracted_text, elapsed = worker_fn(img_path, langue)
            except Exception:
                extracted_text, elapsed = "", 0.0
            
            cer, wer = evaluate_ground_truth_matching(gt["lines_ground_truth"], extracted_text)
            num_acc = evaluate_numbers(gt.get("key_numbers", []), extracted_text)
            
            if langue == "AR":
                engine_stats["ar_wer_list"].append(wer)
                engine_stats["ar_cer_list"].append(cer)
                engine_stats["ar_num_list"].append(num_acc)
                engine_stats["ar_time_list"].append(elapsed)
            else:
                engine_stats["fr_wer_list"].append(wer)
                engine_stats["fr_cer_list"].append(cer)
                engine_stats["fr_num_list"].append(num_acc)
                engine_stats["fr_time_list"].append(elapsed)
                
            engine_stats["pages"].append({
                "id": doc_id,
                "langue": langue,
                "era": era,
                "wer": wer,
                "cer": cer,
                "num_accuracy": num_acc,
                "elapsed": elapsed,
                "sample": extracted_text[:120].replace("\n", " ") if extracted_text else "[VIDE]"
            })
            
            precision_txt = f"WER: {wer*100:5.1f}% (Précision: {(1-wer)*100:5.1f}%) | CER: {cer*100:5.1f}% | Nombres: {num_acc*100:5.1f}% | {elapsed:4.2f}s"
            print(f"  [{doc_id:<5} {langue} {era:<10}] {precision_txt}", flush=True)
            
        all_engine_results.append(engine_stats)
        print(f"Total temps moteur : {time.time() - start_engine_total:.1f}s\n", flush=True)
        
    # Calcul des scores
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
        
    out_json = Path("reports") / "phase5_benchmark_results.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "details": all_engine_results}, f, indent=2, ensure_ascii=False)
        
    print("\n" + "=" * 115, flush=True)
    print("BILAN COMPARATIF FINAL DU BANC D'ESSAI OCR MULTI-MOTEURS (PHASE 5)", flush=True)
    print("=" * 115, flush=True)
    print(f"{'Moteur':<20} | {'Backend':<14} | {'AR Précision':<12} | {'AR Nombres':<10} | {'AR Temps':<8} | {'FR Précision':<12} | {'FR Nombres':<10} | {'FR Temps':<8} | {'Score AR':<8} | {'Score FR':<8}", flush=True)
    print("-" * 140, flush=True)
    for st in summary:
        print(f"{st['engine']:<20} | {st['backend']:<14} | {st['ar_precision_wer']*100:6.1f}%     | {st['ar_num']*100:8.1f}% | {st['ar_time']:6.2f}s | {st['fr_precision_wer']*100:6.1f}%     | {st['fr_num']*100:8.1f}% | {st['fr_time']:6.2f}s | {st['ar_score']*100:6.1f}% | {st['fr_score']*100:6.1f}%", flush=True)

    return summary

if __name__ == "__main__":
    run_benchmark()
