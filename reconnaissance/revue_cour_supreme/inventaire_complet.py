"""Phase 1 — Inventaire complet et réconciliation des ressources de la revue.

Méthodes comparées :
  A. page officielle de téléchargement (تحميل-مجلة-المحكمة-العليا)
  B. pages officielles voisines (Publications, vente, bibliothèque)
  C. sitemaps WordPress officiels (post/book/decision)
  D. liens internes des pages visitées

Chaque ressource : title, url, resource_type, issue_number, issue_year,
pdf_url, source_page, discovery_methods, status. Aucun PDF téléchargé ici.
Écrit reports/revue_inventory_report.json + .md
"""

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.append(str(ROOT / "tools"))

from bs4 import BeautifulSoup  # noqa: E402
from http_client import JoradpClient, JoradpClientConfig  # noqa: E402

BASE = "https://coursupreme.dz"
OUT = ROOT / "reports"
USER_AGENT = "AlgerianLegalCorpusBot/0.1 (academic legal research; polite crawler)"

DOWNLOAD_PAGE = f"{BASE}/تحميل-مجلة-المحكمة-العليا/"
NB_PAGES = [f"{BASE}/نبذة-تاريخية-2/", f"{BASE}/آخر-مجلة-معروضة-للبيع/"]

KW_MAG = ["مجلة"]          # revue
KW_GUIDE = ["دليل البحث", "دليل قرارات"]  # guides officiels


def find_pdfs(html: str, page_url: str):
    soup = BeautifulSoup(html, "html.parser")
    found = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(page_url, a["href"])
        if ".pdf" in href.lower():
            found.add(href)
    for m in re.finditer(r"[\"'](https?://[^\"']+?\.pdf[^\"']*)[\"']", html):
        found.add(m.group(1))
    return found


def classify(title_dec: str):
    """Type de ressource d'après le titre décodé."""
    if "عدد خاص" in title_dec or "خص" in title_dec:
        return "SPECIAL_ISSUE"
    if re.search(r"عدد[-\s]?\d{2}", title_dec) and "مجلة" in title_dec:
        return "REVUE"
    if "دليل" in title_dec:
        return "GUIDE" if "قرارات" in title_dec or "البحث" in title_dec else "INDEX"
    return "OTHER"


def main():
    config = JoradpClientConfig(user_agent=USER_AGENT)
    inventory = {}   # page_url -> record
    method_hits = {"A_download_page": set(), "B_official_pages": set(),
                   "C_sitemaps": set(), "D_internal_links": set()}

    with JoradpClient(config) as client:
        # --- C. sitemaps : tous les posts, filtre revue/guides ---------------
        posts = []
        for i in (1, 2, 3):
            r = client.get(f"{BASE}/post-sitemap{i}.xml")
            if r:
                posts += re.findall(r"<loc>([^<]+)</loc>", r.text)
        for u in set(posts):
            dec = unquote(u)
            m = re.search(r"عدد[-\s]?(\d{2})[-\s]?(\d{4})", dec)
            if m and "مجلة" in dec:
                method_hits["C_sitemaps"].add(u)
            elif any(k in dec for k in KW_GUIDE):
                method_hits["C_sitemaps"].add(u)

        # --- A. page de téléchargement + D. liens internes --------------------
        r = client.get(DOWNLOAD_PAGE)
        if r is None:
            print("ÉCHEC page de téléchargement")
            return
        soup = BeautifulSoup(r.text, "html.parser")
        art = soup.find("article") or soup
        page_links = set()
        for a in art.find_all("a", href=True):
            href = urljoin(DOWNLOAD_PAGE, a["href"])
            dec = unquote(href)
            if BASE not in href or ".pdf" in href.lower():
                continue
            if "مجلة" in dec or "دليل" in dec:
                page_links.add(href)
        for h in page_links:
            method_hits["A_download_page"].add(h)
            method_hits["D_internal_links"].add(h)

        # --- B. pages officielles voisines ------------------------------------
        for purl in NB_PAGES:
            rp = client.get(purl)
            if rp is None:
                continue
            s2 = BeautifulSoup(rp.text, "html.parser")
            for a in s2.find_all("a", href=True):
                href = urljoin(purl, a["href"])
                dec = unquote(href)
                if BASE in href and ("مجلة" in dec or "دليل البحث" in dec):
                    method_hits["B_official_pages"].add(href)
                    method_hits["D_internal_links"].add(href)

        # --- Union : visiter chaque page-candidat pour extraire le PDF --------
        candidates = set()
        for s in method_hits.values():
            candidates |= s
        candidates |= page_links
        print(f"{len(candidates)} pages-candidates à inventorier")

        for i, url in enumerate(sorted(candidates), 1):
            resp = client.get(url)
            if resp is None:
                status = "PAGE_UNREACHABLE"
                pdfs = []
            else:
                pdfs = sorted(find_pdfs(resp.text, url))
                status = "ACCESSIBLE" if pdfs else "PAGE_OK_NO_PDF"
            dec = unquote(url)
            title = dec.strip("/").split("/")[-1]
            m = re.search(r"عدد[-\s]?(\d{2})[-\s]?(\d{4})", title)
            issue_num, issue_year = (int(m.group(1)), int(m.group(2))) if m else (None, None)
            methods = sorted(k for k, s in method_hits.items() if url in s)
            rec = {
                "title": title[:120],
                "url": url,
                "resource_type": classify(title),
                "issue_number": issue_num,
                "issue_year": issue_year,
                "language": "AR",
                "pdf_urls": pdfs,
                "source_page": url,
                "discovery_methods": methods,
                "status": status,
            }
            inventory[url] = rec
            if i % 10 == 0 or i == len(candidates):
                print(f"  [{i}/{len(candidates)}] {status} {title[:50]}")

    # --- Réconciliation -------------------------------------------------------
    records = list(inventory.values())
    types = Counter(r["resource_type"] for r in records)
    issues = [r for r in records if r["resource_type"] in ("REVUE", "SPECIAL_ISSUE")]
    years = Counter(r["issue_year"] for r in issues if r["issue_year"])
    only_sitemap = [r["url"] for r in records
                    if r["discovery_methods"] == ["C_sitemaps"]]
    only_page = [r["url"] for r in records
                 if r["discovery_methods"] == ["A_download_page", "D_internal_links"]]
    dup_pdf = {}
    for r in records:
        for p in r["pdf_urls"]:
            dup_pdf.setdefault(p, []).append(r["url"])
    dup_pdf = {p: urls for p, urls in dup_pdf.items() if len(urls) > 1}

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": BASE,
        "summary": {
            "ressources_total": len(records),
            "par_type": dict(types),
            "issues_revue": len(issues),
            "annees_couvertes": f"{min(years)}-{max(years)}" if years else None,
            "issues_par_annee": {str(k): v for k, v in sorted(years.items())},
            "pdf_uniques": len({p for r in records for p in r["pdf_urls"]}),
            "pages_sans_pdf": len([r for r in records if r["status"] == "PAGE_OK_NO_PDF"]),
            "doublons_pdf": dup_pdf,
            "uniquement_sitemap": len(only_sitemap),
            "uniquement_page_telechargement": len(only_page),
        },
        "methodes": {k: len(v) for k, v in method_hits.items()},
        "ressources": records,
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "revue_inventory_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown
    lines = [
        "# Inventaire complet et réconciliation — Revue de la Cour suprême",
        f"\nGénéré : {report['generated_at']}\n",
        f"- Ressources totales : {len(records)}",
        f"- Types : {dict(types)}",
        f"- Numéros de revue/spéciaux : {len(issues)} ({min(years)}-{max(years)})",
        f"- PDF uniques référencés : {report['summary']['pdf_uniques']}",
        f"- Pages sans PDF : {report['summary']['pages_sans_pdf']}",
        f"- Trouvées uniquement par sitemap : {len(only_sitemap)}",
        f"- Trouvées uniquement par la page de téléchargement : {len(only_page)}",
        f"- Doublons PDF : {len(dup_pdf)}\n",
        "| Année | Nb numéros |", "|---|---|",
    ]
    for y, n in sorted(years.items()):
        lines.append(f"| {y} | {n} |")
    lines += ["\n## Ressources\n", "| type | année | n° | titre | statut | PDF |", "|---|---|---|---|---|---|"]
    for r in sorted(records, key=lambda r: (r["resource_type"], r["issue_year"] or 0, r["issue_number"] or 0)):
        lines.append(f"| {r['resource_type']} | {r['issue_year'] or '-'} | {r['issue_number'] or '-'} | "
                     f"{r['title'][:60]} | {r['status']} | {len(r['pdf_urls'])} |")
    (OUT / "revue_inventory_report.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"\nRÉSUMÉ : {len(records)} ressources, {len(issues)} numéros ({min(years)}-{max(years)}), "
          f"{report['summary']['pdf_uniques']} PDF uniques")
    print(f"Rapports : revue_inventory_report.json / .md")


if __name__ == "__main__":
    main()
