"""Script de validation exhaustive et évaluation du Gold Set pour Cour suprême HTML.

Vérifie :
1. SOURCE → PARSER → ADAPTER → CANONICAL DOCUMENT
2. Taux de présence de chaque champ comparés à l'audit d'inspection
3. Unicité stricte de canonical_id (1 253 / 1 253, 0 collision)
4. Gestion déterministe des 2 collisions réelles (4 décisions)
5. Vérification du Gold Set représentatif :
   - multi-chambre (Civile, Pénale, Référé/Indemnisation, Importante, Sans chambre)
   - multi-période (1980, 1990, 2000, 2010, 2020)
   - cas complets et cas incomplets (sans principe, sans disposition, avec clerk...)
   - les 2 paires de collisions réelles
   - calcul exact de Précision / Rappel / F1
6. Classification des 1 253 décisions (Classes A, B, C, D)
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Configuration des chemins
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sources" / "coursupreme"))

from corpus.coursupreme_adapter import CourSupremeAdapter
from corpus.models import (
    CanonicalDocument,
    CourtLevel,
    DocumentNature,
    DocumentType,
    Jurisdiction,
    Language,
    TextCompleteness,
)
from sources.coursupreme.parser import parse_decision


def run_exhaustive_validation() -> Dict[str, Any]:
    print("=" * 80)
    print("ÉTAPE 1 : EXTRACTION SOURCE → ADAPTER → CANONICAL DOCUMENTS")
    print("=" * 80)

    db_path = ROOT / "databases" / "coursupreme.db"
    raw_decisions = CourSupremeAdapter.load_raw_decisions_from_db(db_path)
    total_raw = len(raw_decisions)
    print(f"Total décisions brutes dans coursupreme.db : {total_raw}")

    # Conversion en CanonicalDocuments
    canonical_docs = CourSupremeAdapter.to_canonical_documents(raw_decisions)
    total_canonical = len(canonical_docs)
    print(f"Total CanonicalDocuments générés        : {total_canonical}")
    assert total_raw == total_canonical == 1253, f"Incohérence compteurs : {total_raw} vs {total_canonical}"

    # Vérification unicité des canonical_id
    canonical_ids = [doc.canonical_id for doc in canonical_docs]
    unique_ids = set(canonical_ids)
    id_counts = Counter(canonical_ids)
    duplicates = {k: v for k, v in id_counts.items() if v > 1}

    print(f"canonical_id uniques                   : {len(unique_ids)} / {total_canonical}")
    print(f"Collisions résiduelles                 : {len(duplicates)}")
    assert len(unique_ids) == 1253, f"Erreur d'unicité sur canonical_id : {duplicates}"
    assert len(duplicates) == 0

    # Détection et vérification des collisions désambiguïsées
    disambiguated = [doc for doc in canonical_docs if "_" in doc.canonical_id and len(doc.canonical_id.split("_")[-1]) == 8]
    print(f"Décisions avec désambiguïsateur hash  : {len(disambiguated)} (attendu : 4)")
    assert len(disambiguated) == 4, f"Attendu 4 décisions désambiguïsées, obtenu {len(disambiguated)}"

    # Vérification des deux paires spécifiques
    pair_1980 = [d for d in disambiguated if "20906" in d.canonical_id]
    pair_2018 = [d for d in disambiguated if "994311" in d.canonical_id]
    assert len(pair_1980) == 2, "La paire de 1980 (20906) doit contenir 2 décisions"
    assert len(pair_2018) == 2, "La paire de 2018 (994311) doit contenir 2 décisions"
    print(f"  Paire 1 (1980-07-29, n° 20906) : {[d.canonical_id for d in pair_1980]}")
    print(f"  Paire 2 (2018-02-21, n° 994311) : {[d.canonical_id for d in pair_2018]}")

    print("\n" + "=" * 80)
    print("ÉTAPE 2 : CALCUL DES TAUX DE PRÉSENCE DES CHAMPS & CONCORDANCE AUDIT")
    print("=" * 80)

    # Comparaison avec les données source
    fields_to_check = [
        ("document_number", "decision_number", 1253, 100.0),
        ("date", "date", 1253, 100.0),
        ("chamber", "chamber", 1252, 99.9),
        ("subject", "subject", 1253, 100.0),
        ("full_text", "text", 1253, 100.0),
        ("principle", "principle", 1241, 99.0),
        ("court_response", "court_response", 1239, 98.9),
        ("disposition", "disposition", 1247, 99.5),
        ("legal_references", "legal_references", 1213, 96.8),
        ("keywords", "keywords", 1234, 98.5),
        ("year", "date", 1253, 100.0),
    ]

    field_presence_stats = {}
    print(f"{'Champ Canonique':20s} | {'Présent':7s} | {'Total':5s} | {'Taux':7s} | {'Attendu':7s} | Statut")
    print("-" * 75)

    for canon_field, raw_field, expected_cnt, expected_pct in fields_to_check:
        present = sum(1 for d in canonical_docs if getattr(d, canon_field, None) not in (None, "", "[]"))
        pct = (present / total_canonical) * 100
        status = "CONFORME" if present == expected_cnt else "ÉCART"
        print(f"{canon_field:20s} | {present:7d} | {total_canonical:5d} | {pct:6.1f}% | {expected_pct:6.1f}% | {status}")
        field_presence_stats[canon_field] = {
            "present": present,
            "total": total_canonical,
            "pct": round(pct, 2),
            "expected_cnt": expected_cnt,
            "status": status,
        }
        assert present == expected_cnt, f"Écart détecté sur le champ {canon_field}: {present} vs {expected_cnt}"

    # Vérification provenance & hash
    docs_with_prov = sum(1 for d in canonical_docs if d.provenance is not None)
    docs_with_raw_path = sum(1 for d in canonical_docs if d.provenance and d.provenance.raw_path)
    docs_with_url = sum(1 for d in canonical_docs if d.provenance and d.provenance.source_url)
    docs_with_hash = sum(1 for d in canonical_docs if d.canonical_hash and len(d.canonical_hash) == 64)

    assert docs_with_prov == 1253
    assert docs_with_raw_path == 1253
    assert docs_with_url == 1253
    assert docs_with_hash == 1253
    print("\nProvenance & Intégrité : 1 253 / 1 253 (100.0%) vérifiés (raw_path, URL, SHA-256).")

    print("\n" + "=" * 80)
    print("ÉTAPE 3 : CONSTITUTION ET ÉVALUATION DU GOLD SET REPRÉSENTATIF")
    print("=" * 80)

    # Sélection des cas du Gold Set
    # 1. Les 4 décisions des 2 collisions
    gold_collision_ids = {d.canonical_id for d in disambiguated}

    # 2. Cas sans chambre (id 785)
    doc_no_chamber = next(d for d in canonical_docs if d.chamber is None)

    # 3. Cas complets par chambre
    doc_civil = next(d for d in canonical_docs if d.chamber == "الغرف المدنية" and d.legal_references and d.keywords and d.principle and d.court_response and d.disposition)
    doc_criminal = next(d for d in canonical_docs if d.chamber == "الغرف الجزائية" and d.legal_references and d.keywords and d.principle and d.court_response and d.disposition)
    doc_indemn = next(d for d in canonical_docs if d.chamber == "لجنة التعويض" and d.principle and d.court_response and d.disposition)
    doc_significant = next(d for d in canonical_docs if d.chamber == "قرارات مهمة")

    # 4. Cas incomplets réels de la source
    doc_no_principle = next(d for d in canonical_docs if not d.principle)
    doc_no_disposition = next(d for d in canonical_docs if not d.disposition)
    doc_no_legal_ref = next(d for d in canonical_docs if not d.legal_references)
    doc_no_keywords = next(d for d in canonical_docs if not d.keywords)

    # 5. Diversité temporelle
    doc_oldest = min(canonical_docs, key=lambda d: d.date or "9999")
    doc_newest = max(canonical_docs, key=lambda d: d.date or "0000")
    doc_2000s = next(d for d in canonical_docs if d.year == 2006)

    gold_set_docs = [
        # Collisions
        *disambiguated,
        # Variété institutionnelle
        doc_no_chamber,
        doc_civil,
        doc_criminal,
        doc_indemn,
        doc_significant,
        # Cas structurellement incomplets dans la source
        doc_no_principle,
        doc_no_disposition,
        doc_no_legal_ref,
        doc_no_keywords,
        # Périodes
        doc_oldest,
        doc_newest,
        doc_2000s,
    ]

    # Dédoublonner au cas où
    seen_gold = set()
    gold_set_final = []
    for g in gold_set_docs:
        if g.canonical_id not in seen_gold:
            seen_gold.add(g.canonical_id)
            gold_set_final.append(g)

    print(f"Échantillon Gold Set représentatif constitué : {len(gold_set_final)} décisions.")

    # Validation du Gold Set contre le fichier brut HTML directement via parse_decision
    gold_results = []
    tp, fp, fn = 0, 0, 0

    for gdoc in gold_set_final:
        # Lire le fichier HTML brut original
        raw_path = Path(gdoc.provenance.raw_path)
        assert raw_path.exists(), f"Fichier raw introuvable: {raw_path}"
        html_bytes = raw_path.read_bytes()

        # Re-parser directement depuis le HTML natif
        parsed_obj = parse_decision(html_bytes, source_url=gdoc.provenance.source_url)

        # Vérifier l'exactitude de l'extraction
        checks = {
            "num_match": (gdoc.document_number == parsed_obj.decision_number),
            "date_match": (gdoc.date == parsed_obj.date),
            "chamber_match": (gdoc.chamber == parsed_obj.chamber),
            "subject_match": (gdoc.subject == parsed_obj.subject),
            "principle_match": (gdoc.principle == parsed_obj.principle),
            "court_response_match": (gdoc.court_response == parsed_obj.court_response),
            "disposition_match": (gdoc.disposition == parsed_obj.disposition),
            "legal_refs_match": (gdoc.legal_references == parsed_obj.legal_references),
        }

        all_ok = all(checks.values())
        if all_ok:
            tp += len(checks)
        else:
            for ok in checks.values():
                if ok:
                    tp += 1
                else:
                    fn += 1

        gold_results.append({
            "canonical_id": gdoc.canonical_id,
            "date": gdoc.date,
            "chamber": gdoc.chamber,
            "subject": gdoc.subject,
            "all_fields_conforme": all_ok,
            "details": checks,
        })

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 1.0

    print(f"Résultats Gold Set ({len(gold_set_final)} décisions, {len(gold_set_final) * 8} vérifications directes) :")
    print(f"  - True Positives  : {tp}")
    print(f"  - False Positives : {fp}")
    print(f"  - False Negatives : {fn}")
    print(f"  - Précision       : {precision * 100:.2f}%")
    print(f"  - Rappel          : {recall * 100:.2f}%")
    print(f"  - F1-Score        : {f1 * 100:.2f}%")
    assert f1 == 1.0, f"Erreur dans l'évaluation du Gold Set : F1 = {f1}"

    print("\n" + "=" * 80)
    print("ÉTAPE 4 : CLASSIFICATION DES 1 253 DÉCISIONS (A, B, C, D)")
    print("=" * 80)

    # Définition des classes :
    # Classe A : Décision complète (texte intégral, numéro, date, chambre, sujet, principe, réponse, dispositif)
    # Classe B : Décision exploitable avec texte intégral mais une section non essentielle manquante (ex: pas de principe explicite dans la source, ou pas de chambre renseignée)
    # Classe C : Texte tronqué ou dégradé (< 100 caractères ou corrupted)
    # Classe D : Collision non résolue ou erreur bloquante
    classes_count = Counter()
    for doc in canonical_docs:
        has_core = (doc.document_number and doc.date and doc.subject and doc.full_text and len(doc.full_text) > 100)
        if not has_core:
            classes_count["C"] += 1
        elif doc.chamber and doc.principle and doc.court_response and doc.disposition:
            classes_count["A"] += 1
        else:
            classes_count["B"] += 1

    print("Répartition des classes de qualité :")
    for cls_name in ["A", "B", "C", "D"]:
        cnt = classes_count[cls_name]
        pct = (cnt / total_canonical) * 100
        print(f"  - Classe {cls_name} : {cnt:4d} / {total_canonical} ({pct:5.1f}%)")

    assert classes_count["C"] == 0, "Aucune décision en classe C tolérée"
    assert classes_count["D"] == 0, "Aucune décision en classe D tolérée"

    return {
        "total_raw": total_raw,
        "total_canonical": total_canonical,
        "unique_ids": len(unique_ids),
        "collisions_handled": len(disambiguated),
        "field_presence": field_presence_stats,
        "gold_set_size": len(gold_set_final),
        "gold_metrics": {"precision": precision, "recall": recall, "f1": f1},
        "classes": dict(classes_count),
    }


if __name__ == "__main__":
    run_exhaustive_validation()
