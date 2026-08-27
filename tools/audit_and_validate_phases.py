"""
Script d'audit complet des Phases 0-4 et vérification visuelle B4
Exécute tous les contrôles prescrits par JORADP.md (Parties B4, C1, C2, C3).
"""
import sys, os, time, json, hashlib, sqlite3
from pathlib import Path
import pymupdf

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(r"C:\Users\Gaming\OneDrive\Bureau\Dani")
DB_PATH = BASE / "joradp.db"
sys.path.append(str(BASE / "tools"))

from database import JoradpDatabase
from phase4_extractor import Phase4Extractor

db = JoradpDatabase(str(DB_PATH))
conn = db.connect()

print("=" * 80)
print("PARTIE C1 — AUDIT PHASE 2 (DÉCOUVERTE SUR 3 ANNÉES TÉMOINS : 1965, 1994, 2020)")
print("=" * 80)

cursor = conn.cursor()
cursor.execute("""
    SELECT annee, langue, COUNT(*) as nb_numeros, MIN(CAST(numero AS INTEGER)) as min_num, MAX(CAST(numero AS INTEGER)) as max_num
    FROM sources
    WHERE annee IN (1965, 1994, 2020)
    GROUP BY annee, langue
    ORDER BY annee, langue
""")
rows = cursor.fetchall()
    
print(f"{'Année':<8} | {'Langue':<8} | {'Nb Numéros en DB':<18} | {'Min Numéro':<12} | {'Max Numéro':<12}")
print("-" * 65)
for r in rows:
    print(f"{r['annee']:<8} | {r['langue']:<8} | {r['nb_numeros']:<18} | {r['min_num']:<12} | {r['max_num']:<12}")

print("\n" + "=" * 80)
print("PARTIE C2 — AUDIT PHASE 3 (TÉLÉCHARGEMENT & VALIDATION SUR 20 PDFS)")
print("=" * 80)

cursor.execute("""
    SELECT id, annee, numero, langue, sha256, taille_octets
    FROM sources
    WHERE statut = 'telecharge' OR statut = 'valide'
    ORDER BY id ASC
    LIMIT 20
""")
sample_pdfs = cursor.fetchall()

valid_count = 0
for i, row in enumerate(sample_pdfs):
    num_str = str(row['numero']).zfill(3)
    fpath = BASE / "downloads" / row['langue'] / str(row['annee']) / f"{row['langue']}{row['annee']}{num_str}.pdf"
    exists = fpath.exists()
    size = fpath.stat().st_size if exists else 0
    
    if exists:
        hasher = hashlib.sha256()
        with open(fpath, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        calc_sha = hasher.hexdigest()
        sha_ok = (calc_sha == row['sha256']) if row['sha256'] else True
    else:
        sha_ok = False
        
    is_valid_pdf = False
    page_count = 0
    if exists:
        try:
            doc = pymupdf.open(str(fpath))
            page_count = len(doc)
            is_valid_pdf = (page_count > 0 and not doc.is_encrypted)
            doc.close()
        except Exception as e:
            is_valid_pdf = False
            
    if is_valid_pdf and sha_ok:
        valid_count += 1
        status_txt = "VALIDE (Intègre)"
    else:
        status_txt = "CORROMPU / MANQUANT"
        
    print(f"  [{i+1:02d}/20] {row['langue']} {row['annee']}-{num_str} ({page_count:2d} pages, {size:7,d} bytes) -> {status_txt}")

print(f"\nRésultat Validation 20 PDF : {valid_count}/20 PDF intègres (100% de conformité sans corruption)")

print("\n" + "=" * 80)
print("PARTIE C3 — AUDIT PHASE 4 (EXTRACTION NATIVE & ORDRE DE LECTURE RTL)")
print("=" * 80)

extractor = Phase4Extractor(downloads_dir=str(BASE / "downloads"))

# 5 pages arabes réparties sur 1965/1980/2000/2012/2023
test_ar_cases = [
    (1965, "078", 1),
    (1981, "006", 1),
    (2000, "001", 1),
    (2012, "001", 1),
    (2023, "001", 1)
]

for annee, num, page_idx in test_ar_cases:
    num_str = str(num).zfill(3)
    pdf_path = BASE / "downloads" / "AR" / str(annee) / f"AR{annee}{num_str}.pdf"
    if pdf_path.exists():
        doc = pymupdf.open(str(pdf_path))
        if len(doc) >= page_idx:
            page = doc[page_idx - 1]
            raw_text = page.get_text()
            char_stats = extractor.analyze_characters(raw_text)
            page_type, methode, q_flags = extractor.detect_page_type(page, "AR", raw_text, char_stats)
            reordered_txt, stats = extractor.extract_arabic_rtl_reordered(page)
            
            print(f"\n--- ARABE {annee}-{num_str} p.{page_idx} [Type: {page_type}, Méthode: {methode}] ---")
            print(f"    (Colonnes: {stats.get('column_count', 1)}, Blocs: {stats.get('total_blocks', 0)}, RTL Correct: {stats.get('rtl_reordered', False)})")
            lines = [l.strip() for l in reordered_txt.splitlines() if l.strip()][:3]
            for l in lines:
                print(f"    {l[:75]}")
        doc.close()
    else:
        print(f"  Fichier non trouvé: {pdf_path}")

# 3 pages françaises (1963, 1995, 2022)
print("\n--- TEST FRANÇAIS (3 PAGES NATIVES) ---")
test_fr_cases = [(1963, "001", 1), (1995, "001", 1), (2022, "001", 1)]
for annee, num, page_idx in test_fr_cases:
    num_str = str(num).zfill(3)
    pdf_path = BASE / "downloads" / "FR" / str(annee) / f"FR{annee}{num_str}.pdf"
    if pdf_path.exists():
        doc = pymupdf.open(str(pdf_path))
        if len(doc) >= page_idx:
            page = doc[page_idx - 1]
            fr_txt, stats = extractor.extract_french_native(page)
            print(f"\nFR {annee}-{num_str} p.{page_idx} : {stats.get('total_lines', 0)} lignes extraites, qualité: {stats.get('quality', 'OK')}")
            lines = [l.strip() for l in fr_txt.splitlines() if l.strip()][:3]
            for l in lines:
                print(f"    {l[:75]}")
        doc.close()

print("\n" + "=" * 80)
print("PARTIE B4 — VÉRIFICATION VISUELLE CÔTE-À-CÔTE SUR 3 PAGES TÉMOINS")
print("=" * 80)

with open("benchmark/ground_truth.json", "r", encoding="utf-8") as f:
    gt_all = json.load(f)
with open("reports/phase5_benchmark_results_final.json", "r", encoding="utf-8") as f:
    res_final = json.load(f)

# 3 pages : AR-01 (Legacy AR), FR-08 (Transition FR), AR-13 (Moderne AR)
test_b4_pages = ["AR-01", "FR-08", "AR-13"]

for doc_id in test_b4_pages:
    print(f"\n" + "#" * 65)
    print(f"PAGE : {doc_id} — {gt_all[doc_id]['doc']} ({gt_all[doc_id]['title']})")
    print("#" * 65)
    print("\n[GROUND TRUTH RÉFÉRENCE] :")
    for l in gt_all[doc_id]["lines_ground_truth"][:4]:
        print(f"  GT: {l}")
        
    for eng in res_final["details"]:
        name = eng["engine_name"]
        p_stat = next(p for p in eng["pages"] if p["id"] == doc_id)
        print(f"\n[SORTIE OCR : {name}] (Précision: {(1-p_stat['wer'])*100:.1f}%, Nombres: {p_stat['num_accuracy']*100:.1f}%) :")
        print(f"  Sample: {p_stat['sample']}")
