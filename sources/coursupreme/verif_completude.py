"""Vérification indépendante de complétude — coursupreme.dz vs SQLite.

- relance UNIQUEMENT la découverte (listings + pagination, les 6 catégories) ;
- ne télécharge AUCUNE décision ;
- ne modifie RIEN en base (lecture seule sur SQLite) ;
- compare les URLs normalisées exactement comme le scraper ;
- vérifie 10 familles d'anomalies ;
- écrit reports/coursupreme_completeness_report.{json,md} et un verdict PASS/FAIL.

Constat de complétude = par rapport aux listings publics parcourus uniquement ;
ce n'est PAS une preuve d'exhaustivité de la jurisprudence historique.
"""

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.append(str(ROOT / "tools"))
sys.path.insert(0, str(HERE))

from bs4 import BeautifulSoup  # noqa: E402
from http_client import JoradpClient, JoradpClientConfig  # noqa: E402

from discover import (  # noqa: E402
    BASE, CATEGORIES, USER_AGENT,
    extract_decision_urls, last_page_number, normalize_url,
)
from storage import DecisionStore  # noqa: E402

REPORTS = ROOT / "reports"
JSON_OUT = REPORTS / "coursupreme_completeness_report.json"
MD_OUT = REPORTS / "coursupreme_completeness_report.json.md".replace(".json.md", ".md")

# Seuil sous lequel un HTML brut est considéré anormalement petit
# (pages décision réelles observées : ~120 Ko).
RAW_MIN_BYTES = 10_000

KNOWN_CHAMBER_PREFIXES = (
    "civil-chambers", "criminal-chambers", "compensation-committee",
    "significant-decisions", "joint-chambers",
)


# ---------------------------------------------------------------------------
# 1. Découverte indépendante (listings uniquement)
# ---------------------------------------------------------------------------

def crawl_site():
    """Parcourt les 6 catégories et leur pagination complète.

    Retourne {category: {"listing_pages": n, "found": total_liens_bruts,
                         "urls": set}} — aucun téléchargement de décision.
    """
    config = JoradpClientConfig(user_agent=USER_AGENT)
    site = {}
    with JoradpClient(config) as client:
        for name, slug in CATEGORIES.items():
            page1 = f"{BASE}/{slug}/"
            resp = client.get(page1)
            if resp is None:
                site[name] = {"listing_pages": 0, "found": 0, "urls": set(),
                              "error": "page 1 échec"}
                print(f"[{name}] ÉCHEC page 1")
                continue
            n_pages = last_page_number(resp.text)
            urls = extract_decision_urls(resp.text, page1)
            found = len(urls)
            pages_ok = 1
            for p in range(2, n_pages + 1):
                url = f"{page1}page/{p}/"
                r = client.get(url)
                if r is None:
                    print(f"[{name}] page {p}/{n_pages} échec réseau")
                    continue
                f = extract_decision_urls(r.text, url)
                found += len(f)
                urls |= f
                pages_ok += 1
                if p % 10 == 0:
                    print(f"[{name}] page {p}/{n_pages} : {len(urls)} URLs uniques")
            site[name] = {"listing_pages": pages_ok, "found": found,
                          "pages_annoncees": n_pages, "urls": urls}
            print(f"[{name}] terminé : {pages_ok}/{n_pages} pages, {len(urls)} URLs uniques")
    return site


# ---------------------------------------------------------------------------
# 2. Lecture SQLite (lecture seule)
# ---------------------------------------------------------------------------

def read_db(db_path: str):
    store = DecisionStore(db_path=db_path)
    conn = store.connect()
    rows = conn.execute(
        "SELECT source_url, category, chamber, chamber_class, decision_number, "
        "date, content_hash, raw_path, status FROM decisions"
    ).fetchall()
    store.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# 3. Comparaison + anomalies
# ---------------------------------------------------------------------------

def main():
    now = datetime.now(timezone.utc).isoformat()
    print("=== PHASE 1 : parcours des listings (aucune décision téléchargée) ===")
    site = crawl_site()

    print("\n=== PHASE 2 : lecture SQLite (lecture seule) ===")
    db_path = str(ROOT / "databases" / "coursupreme.db")
    db_rows = read_db(db_path)
    db_urls = {normalize_url(r["source_url"]) for r in db_rows}
    db_by_url = {normalize_url(r["source_url"]): r for r in db_rows}

    site_urls = set()
    for info in site.values():
        site_urls |= {normalize_url(u) for u in info["urls"]}

    site_only = sorted(site_urls - db_urls)
    db_only = sorted(db_urls - site_urls)
    common = sorted(site_urls & db_urls)

    site_total = len(site_urls)
    db_total = len(db_urls)

    # --- Contrôle par catégorie --------------------------------------------
    cat_report = []
    for name in CATEGORIES:
        info = site.get(name, {"listing_pages": 0, "found": 0, "urls": set()})
        urls = {normalize_url(u) for u in info["urls"]}
        in_db = sum(1 for u in urls if u in db_by_url)
        missing = sorted(u for u in urls if u not in db_by_url)
        cat_report.append({
            "category": name,
            "listing_pages": info.get("listing_pages", 0),
            "pages_annoncees": info.get("pages_annoncees"),
            "decision_urls_found": info.get("found", 0),
            "unique_decision_urls": len(urls),
            "URLs_already_in_db": in_db,
            "URLs_missing_from_db": len(missing),
            "missing_urls": missing,
        })

    # --- Anomalies ------------------------------------------------------------
    anomalies = {}

    # 1. URL sur le site absente de SQLite (doublon du SITE_ONLY global)
    anomalies["urls_site_absentes_db"] = site_only

    # 2. Décision SQLite absente des listings
    anomalies["urls_db_absentes_site"] = db_only

    # 3. Deux URLs différentes même couple (numéro, date)
    pairs = Counter()
    pair_urls = {}
    for r in db_rows:
        if r["decision_number"] and r["date"]:
            key = (r["decision_number"], r["date"])
            pairs[key] += 1
            pair_urls.setdefault(key, []).append(normalize_url(r["source_url"]))
    dup_pairs = {f"{k[0]}|{k[1]}": v for k, v in pair_urls.items() if pairs[k] > 1}
    anomalies["couples_numero_date_dupliques"] = dup_pairs

    # 4. Catégorie/chambre inconnue
    unknown = [
        {"url": normalize_url(r["source_url"]), "chamber_class": r["chamber_class"]}
        for r in db_rows
        if not r["chamber_class"]
        or not any(r["chamber_class"].startswith(p) for p in KNOWN_CHAMBER_PREFIXES)
    ]
    anomalies["decisions_categorie_inconnue"] = unknown

    # 5/6. Sans numéro / sans date
    anomalies["decisions_sans_numero"] = [
        normalize_url(r["source_url"]) for r in db_rows if not r["decision_number"]
    ]
    anomalies["decisions_sans_date"] = [
        normalize_url(r["source_url"]) for r in db_rows if not r["date"]
    ]

    # 7/8. Numéros dupliqués (le numéro seul, sans la date)
    num_counter = Counter(r["decision_number"] for r in db_rows if r["decision_number"])
    anomalies["numeros_dupliques"] = {
        n: c for n, c in num_counter.items() if c > 1
    }

    # 9. Contenu identique (content_hash dupliqué)
    hash_counter = Counter(r["content_hash"] for r in db_rows if r["content_hash"])
    anomalies["contenus_identiques_hash"] = {
        h: c for h, c in hash_counter.items() if c > 1
    }

    # 10. HTML brut vide ou anormalement petit
    raw_issues = []
    for r in db_rows:
        rp = r["raw_path"]
        if not rp or not Path(rp).exists():
            raw_issues.append({"url": normalize_url(r["source_url"]),
                               "probleme": "fichier brut absent"})
            continue
        size = Path(rp).stat().st_size
        if size == 0:
            raw_issues.append({"url": normalize_url(r["source_url"]),
                               "probleme": "fichier brut vide"})
        elif size < RAW_MIN_BYTES:
            raw_issues.append({"url": normalize_url(r["source_url"]),
                               "probleme": f"fichier brut petit ({size} octets)"})
    anomalies["html_brut_anormal"] = raw_issues

    # --- Verdict ----------------------------------------------------------------
    diff_count = len(site_only) + len(db_only)
    verdict = "PASS" if (site_total == db_total and len(site_only) == 0
                         and len(db_only) == 0) else "FAIL"

    report = {
        "genere_le": now,
        "perimetre": "Complétude par rapport aux listings publics parcourus du "
                     "site officiel uniquement — PAS une preuve d'exhaustivité "
                     "de la jurisprudence historique.",
        "resume": {
            "SITE_TOTAL": site_total,
            "DB_TOTAL": db_total,
            "COMMON": len(common),
            "SITE_ONLY": len(site_only),
            "DB_ONLY": len(db_only),
            "DIFFERENCES": diff_count,
        },
        "categories": cat_report,
        "anomalies": anomalies,
        "verdict": verdict,
        "conclusion": (
            "Les URLs des décisions exposées par les listings parcourus du site "
            "officiel correspondent exactement aux URLs présentes dans notre base "
            "SQLite." if verdict == "PASS" else
            "Écarts détectés entre les listings du site et la base SQLite — "
            "voir site_only/db_only et les URL listées."
        ),
    }

    REPORTS.mkdir(exist_ok=True)
    JSON_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                        encoding="utf-8")

    # --- Markdown -----------------------------------------------------------------
    lines = [
        "# Vérification de complétude — coursupreme.dz vs SQLite",
        f"\nGénéré : {now}\n",
        f"**Verdict : {verdict}**\n",
        f"- SITE_TOTAL : {site_total}",
        f"- DB_TOTAL : {db_total}",
        f"- COMMON : {len(common)}",
        f"- SITE_ONLY : {len(site_only)}",
        f"- DB_ONLY : {len(db_only)}\n",
        "## Par catégorie\n",
        "| catégorie | pages lues | URLs uniques | déjà en base | manquantes en base |",
        "|---|---:|---:|---:|---:|",
    ]
    for c in cat_report:
        lines.append(f"| {c['category']} | {c['listing_pages']} | "
                     f"{c['unique_decision_urls']} | {c['URLs_already_in_db']} | "
                     f"{c['URLs_missing_from_db']} |")
    lines.append("\n## Anomalies\n")
    for k, v in anomalies.items():
        lines.append(f"- **{k}** : {len(v)}")
    lines.append(f"\n> {report['perimetre']}")
    MD_OUT.write_text("\n".join(lines), encoding="utf-8")

    # --- Sortie console -------------------------------------------------------------
    print("\n=== PHASE 3 : anomalies ===")
    for k, v in anomalies.items():
        print(f"  {k}: {len(v)}")
    print("\n" + "=" * 50)
    print(f"SITE_TOTAL: {site_total}")
    print(f"DB_TOTAL:   {db_total}")
    print(f"COMMON:     {len(common)}")
    print(f"SITE_ONLY:  {len(site_only)}")
    print(f"DB_ONLY:    {len(db_only)}")
    for c in cat_report:
        print(f"  {c['category']:14s} pages={c['listing_pages']:2d} "
              f"uniques={c['unique_decision_urls']:5d} "
              f"en_base={c['URLs_already_in_db']:5d} "
              f"manquantes={c['URLs_missing_from_db']}")
    print(f"\nFINAL VERDICT: {verdict}")
    print(f"Rapports : {JSON_OUT.name}, {MD_OUT.name} (dans reports/)")


if __name__ == "__main__":
    main()
