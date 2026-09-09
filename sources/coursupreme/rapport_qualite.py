"""Rapport qualité du corpus Cour suprême — Phase 10.

Produit reports/coursupreme_quality_report.json :
découvertes/téléchargements/échecs, doublons, champs manquants,
longueurs, distributions par chambre/année/langue.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from storage import DecisionStore  # noqa: E402

OUT = ROOT / "reports" / "coursupreme_quality_report.json"

FIELDS = [
    "decision_number", "date", "subject", "parties", "keywords",
    "legal_references", "principle", "court_response", "disposition",
    "president", "rapporteur",
]


def build_report(db_path: str) -> dict:
    store = DecisionStore(db_path=db_path)
    conn = store.connect()

    counts = store.counts_by_status()
    total = sum(counts.values())
    downloaded = counts.get("telecharge", 0)
    errors = counts.get("erreur", 0)
    attempted = downloaded + errors

    report = {
        "genere_le": datetime.now(timezone.utc).isoformat(),
        "resume": {
            "decouvertes": total,
            "telechargees": downloaded,
            "echecs": errors,
            "restantes": counts.get("decouvert", 0),
            "taux_reussite": round(downloaded / attempted * 100, 1) if attempted else None,
        },
    }

    # --- Qualité des décisions téléchargées --------------------------------
    rows = conn.execute(
        "SELECT * FROM decisions WHERE status='telecharge'"
    ).fetchall()

    manquants = {f: 0 for f in FIELDS}
    longueurs, annees, chambres = [], {}, {}
    invalides = 0

    for r in rows:
        d = dict(r)
        if not d.get("text") or len(d["text"]) < 200:
            invalides += 1
        for f in FIELDS:
            if not d.get(f):
                manquants[f] += 1
        if d.get("text"):
            longueurs.append(len(d["text"]))
        if d.get("date"):
            an = d["date"][:4]
            annees[an] = annees.get(an, 0) + 1
        ch = d.get("chamber") or "inconnue"
        chambres[ch] = chambres.get(ch, 0) + 1

    n = len(rows) or 1
    report["qualite"] = {
        "analysees": len(rows),
        "pages_invalides_texte_court_ou_vide": invalides,
        "champs_manquants": {f: {"n": v, "taux_pct": round(v / n * 100, 1)}
                              for f, v in manquants.items()},
        "longueur_texte": {
            "moyenne": int(sum(longueurs) / n) if longueurs else 0,
            "min": min(longueurs) if longueurs else 0,
            "max": max(longueurs) if longueurs else 0,
        },
        "doublons_contenu": len(store.duplicate_hashes()),
        "distribution_chambres": dict(sorted(chambres.items(), key=lambda kv: -kv[1])),
        "distribution_annees": dict(sorted(annees.items())),
        "langues": {"AR": len(rows)},
    }

    # --- Échantillon d'erreurs ------------------------------------------------
    err_rows = conn.execute(
        "SELECT source_url, error FROM decisions WHERE status='erreur' LIMIT 20"
    ).fetchall()
    report["erreurs_echantillon"] = [dict(e) for e in err_rows]

    return report


def main():
    import argparse

    ap = argparse.ArgumentParser(description="Rapport qualité coursupreme")
    ap.add_argument("--db", default=str(ROOT / "databases" / "coursupreme.db"))
    args = ap.parse_args()

    report = build_report(args.db)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    r = report["resume"]
    q = report["qualite"]
    print(f"Découvertes: {r['decouvertes']} | téléchargées: {r['telechargees']} | "
          f"échecs: {r['echecs']} | taux: {r['taux_reussite']}%")
    print(f"Analyisées: {q['analysees']} | invalides: {q['pages_invalides_texte_court_ou_vide']} | "
          f"doublons: {q['doublons_contenu']}")
    print(f"Texte moyen: {q['longueur_texte']['moyenne']}c | "
          f"chambres: {list(q['distribution_chambres'].items())[:4]}")
    top_manques = sorted(q["champs_manquants"].items(),
                         key=lambda kv: -kv[1]["n"])[:3]
    print("Champs les plus manquants:",
          [(f, m["n"]) for f, m in top_manques])
    print(f"Rapport: {OUT}")


if __name__ == "__main__":
    main()
