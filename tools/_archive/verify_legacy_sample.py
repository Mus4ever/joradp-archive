"""Validate one legacy full PDF against its published page-by-page view.

This is a Phase-0 diagnostic, not the corpus downloader. It intentionally
downloads only the requested issue and enforces the production politeness
constraints so that the result is reproducible without stressing JORADP.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import ssl
import time
from pathlib import Path
from urllib.parse import urljoin

import fitz
import httpx
import truststore


BASE_URL = "https://www.joradp.dz"
USER_AGENT = "JORADPArchivePipeline/0.1 (responsible archival client)"
MIN_INTERVAL_SECONDS = 2.0
MAX_ATTEMPTS = 3
# OpenSSL's SSL_OP_LEGACY_SERVER_CONNECT; Python 3.11 does not export its name.
SSL_OP_LEGACY_SERVER_CONNECT = 0x4


class PoliteClient:
    def __init__(self) -> None:
        context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.options |= SSL_OP_LEGACY_SERVER_CONNECT
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = True
        self.client = httpx.Client(
            verify=context,
            headers={"User-Agent": USER_AGENT},
            timeout=60,
            follow_redirects=True,
        )
        self.next_request_at = 0.0

    def get(self, url: str) -> httpx.Response:
        for attempt in range(MAX_ATTEMPTS):
            delay = self.next_request_at - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            try:
                response = self.client.get(url)
                self.next_request_at = time.monotonic() + MIN_INTERVAL_SECONDS
                response.raise_for_status()
                return response
            except (httpx.HTTPError, OSError):
                if attempt + 1 == MAX_ATTEMPTS:
                    raise
                time.sleep(2**attempt)
        raise AssertionError("unreachable")

    def close(self) -> None:
        self.client.close()


def render_digest(document: fitz.Document, page_index: int) -> tuple[str, int, int]:
    pixmap = document[page_index].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), colorspace=fitz.csGRAY)
    return hashlib.sha256(pixmap.samples).hexdigest(), pixmap.width, pixmap.height


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=1983)
    parser.add_argument("--issue", default="001")
    parser.add_argument("--language", default="A")
    parser.add_argument("--archive-root", default="Jo6283")
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--end-page", type=int)
    parser.add_argument("--out", type=Path, default=Path("reports/legacy_1983_001_validation.json"))
    args = parser.parse_args()

    page_index_url = f"{BASE_URL}/{args.archive_root}/{args.year}/{args.issue}/{args.language}_Pag1.htm"
    full_pdf_url = f"{BASE_URL}/FTP/Jo-Arabe/{args.year}/A{args.year}{args.issue}.pdf"
    client = PoliteClient()
    try:
        page_index = client.get(page_index_url)
        page_links = re.findall(r'HREF="([^\"]+\.pdf)"', page_index.text, flags=re.IGNORECASE)
        page_urls = [urljoin(page_index_url, href) for href in page_links if re.fullmatch(r"AP\d+\.pdf", href, re.I)]
        page_urls.sort(key=lambda url: int(re.search(r"AP(\d+)\.pdf$", url, re.I).group(1)))
        expected_numbers = list(range(1, len(page_urls) + 1))
        found_numbers = [int(re.search(r"AP(\d+)\.pdf$", url, re.I).group(1)) for url in page_urls]
        if found_numbers != expected_numbers:
            raise RuntimeError(f"non-contiguous page links: {found_numbers!r}")

        full_pdf_bytes = client.get(full_pdf_url).content
        full_document = fitz.open(stream=full_pdf_bytes, filetype="pdf")
        comparisons: list[dict[str, object]] = []
        last_page = args.end_page or len(page_urls)
        selected_pages = list(enumerate(page_urls, start=1))[args.start_page - 1 : last_page]
        for page_number, page_url in selected_pages:
            page_document = fitz.open(stream=client.get(page_url).content, filetype="pdf")
            full_digest, full_width, full_height = render_digest(full_document, page_number - 1)
            page_digest, page_width, page_height = render_digest(page_document, 0)
            comparisons.append(
                {
                    "page": page_number,
                    "url": page_url,
                    "same_render": full_digest == page_digest,
                    "full_size": [full_width, full_height],
                    "page_size": [page_width, page_height],
                }
            )
            page_document.close()
            print(f"validated page {page_number}/{len(page_urls)}", flush=True)
        report = {
            "full_pdf_url": full_pdf_url,
            "page_index_url": page_index_url,
            "full_pdf_sha256": hashlib.sha256(full_pdf_bytes).hexdigest(),
            "full_pdf_pages": full_document.page_count,
            "page_view_pages": len(page_urls),
            "validated_range": [args.start_page, last_page],
            "matching_renders": sum(item["same_render"] for item in comparisons),
            "all_renders_match": all(item["same_render"] for item in comparisons),
            "tls": {"verify_mode": "CERT_REQUIRED", "check_hostname": True, "legacy_connect": True},
            "comparisons": comparisons,
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({key: report[key] for key in report if key != "comparisons"}, indent=2))
        full_document.close()
    finally:
        client.close()


if __name__ == "__main__":
    main()
