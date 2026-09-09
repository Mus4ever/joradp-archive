"""Rapport qualité du corpus Conseil d'État — Phase audit et conformité.

Produit reports/conseildetat_quality_report.json :
- statistiques globales de découverte, scraping HTML et téléchargement PDF ;
- répartition par type de document (jurisprudence, arrêts sélectionnés, revue) ;
- complétude des champs (taux de remplissage) ;
- distributions temporelles, de chambres et présence des pièces jointes PDF ;
- métriques de longueur de texte et détection de doublons.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from storage import DecisionStore  # noqa: E402

OUT = ROOT / "reports" / "conseildetat_quality_report.json"

FIELDS = [
    "decision_number", "date", "date_raw", "chamber", "section",
    "keywords", "classification", "subject", "principle", "pdf_url",
    "pdf_path", "text"
]


def build_report(db_path: str) -> dict:
    store = DecisionStore(db_path=db_path)
    conn = store.connect()

    counts = store.counts_by_status()
    total = sum(counts.values())
    downloaded = counts.get("telecharge", 0)
    errors = counts.get("erreur", 0)
    attempted = downloaded + errors

    # Statistiques types
    type_counts = store.counts_by_type()

    report = {
        "genere_le": datetime.now(timezone.utc).isoformat(),
        "juridiction": "Conseil d'État (مجلس الدولة)",
        "source": "https://conseildetat.dz",
        "resume": {
            "decouvertes": total,
            "telechargees_html": downloaded,
            "echecs_html": errors,
            "restantes": counts.get("decouvert", 0),
            "taux_reussite_html": round(downloaded / attempted * 100, 1) if attempted else None,
            "repartition_types": type_counts,
        },
    }

    # --- Qualité des décisions téléchargées --------------------------------
    rows = conn.execute(
        "SELECT * FROM decisions WHERE status='telecharge'"
    ).fetchall()

    manquants = {f: 0 for f in FIELDS}
    longueurs = []
    annees = {}
    chambres = {}
    sections = {}
    pdfs_attaches = 0
    pdfs_telecharges = 0
    invalides = 0

    for r in rows:
        d = dict(r)
        if not d.get("text") or len(d["text"]) < 50:
            invalides += 1
        for f in FIELDS:
            if not d.get(f):
                manquants[f] += 1
        if d.get("text"):
            longueurs.append(len(d["text"]))
        if d.get("year"):
            an = str(d["year"])
            annees[an] = annees.get(an, 0) + 1
        elif d.get("date"):
            an = d["date"][:4]
            annees[an] = annees.get(an, 0) + 1

        ch = d.get("chamber") or "non_renseignee"
        chambres[ch] = chambres.get(ch, 0) + 1

        sec = d.get("section") or "non_renseignee"
        sections[sec] = sections.get(sec, 0) + 1

        if d.get("pdf_url"):
            pdfs_attaches += 1
        if d.get("pdf_path"):
            pdfs_telecharges += 1

    n = len(rows) or 1
    report["qualite"] = {
        "total_analysees": len(rows),
        "pages_invalides_texte_court": invalides,
        "champs_manquants": {
            f: {"n": v, "taux_pct": round(v / n * 100, 1)}
            for f, v in manquants.items()
        },
        "longueur_texte": {
            "moyenne": int(sum(longueurs) / n) if longueurs else 0,
            "min": min(longueurs) if longueurs else 0,
            "max": max(longueurs) if longueurs else 0,
        },
        "doublons_contenu": len(store.duplicate_hashes()),
        "distribution_chambres": dict(sorted(chambres.items(), key=lambda kv: -kv[1])),
        "distribution_sections": dict(sorted(sections.items(), key=lambda kv: -kv[1])),
        "distribution_annees": dict(sorted(annees.items())),
        "pieces_jointes_pdf": {
            "avec_lien_pdf": pdfs_attaches,
            "pdf_telecharges_localement": pdfs_telecharges,
            "taux_recouvrement_pdf": round(pdfs_telecharges / (pdfs_attaches or 1) * 100, 1),
        },
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

    ap = argparse.ArgumentParser(description="Rapport qualité Conseil d'État")
    ap.add_argument("--db", default=str(ROOT / "databases" / "conseildetat.db"))
    args = ap.parse_args()

    report = build_report(args.db)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    r = report["resume"]
    q = report["qualite"]
    print(f"Découvertes: {r['decouvertes']} | HTML téléchargés: {r['telechargees_html']} | "
          f"Échecs: {r['echecs_html']} | Taux: {r['taux_reussite_html']}%")
    print(f"PDFs détectés: {q['pieces_jointes_pdf']['avec_lien_pdf']} | "
          f"PDFs téléchargés: {q['pieces_jointes_pdf']['pdf_telecharges_localement']}")
    print(f"Texte moyen: {q['longueur_texte']['moyenne']}c | Invalides: {q['pages_invalides_texte_court']} | "
          f"Doublons: {q['doublons_contenu']}")
    top_manques = sorted(q["champs_manquants"].items(),
                         key=lambda kv: -kv[1]["n"])[:4]
    print("Champs les plus manquants:", [(f, m["n"]) for f, m in top_manques])
    print(f"Rapport écrit dans : {OUT}")


if __name__ == "__main__":
    main()
