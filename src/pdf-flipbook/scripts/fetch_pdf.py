"""Try to extract the original source PDF URL from a flipbook viewer page.

Works for heyzine and many flipbook hosts that embed the original PDF on a CDN.
Prints the discovered PDF URL to stdout (or downloads it with --download OUT).

Usage:
  python fetch_pdf.py "https://heyzine.com/flip-book/XXXX.html"
  python fetch_pdf.py "<url>" --download "out.pdf"
"""
import argparse
import re
import sys
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
PDF_RE = re.compile(r'https?://[^"\'\s\\]+\.pdf', re.IGNORECASE)


def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="ignore")


def find_pdf(url: str) -> str | None:
    html = fetch_html(url)
    matches = PDF_RE.findall(html)
    if not matches:
        # try unescaped \/ JSON style
        html2 = html.replace("\\/", "/")
        matches = PDF_RE.findall(html2)
    if not matches:
        return None
    # prefer CDN/uploaded originals
    for m in matches:
        if "uploaded" in m or "cdn" in m:
            return m
    return matches[0]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--download", default=None)
    args = ap.parse_args()

    pdf_url = find_pdf(args.url)
    if not pdf_url:
        sys.exit("No PDF found on that page. Download it manually or use browser tools.")
    print(pdf_url)

    if args.download:
        req = urllib.request.Request(pdf_url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as r, open(args.download, "wb") as f:
            f.write(r.read())
        print(f"Downloaded -> {args.download}")


if __name__ == "__main__":
    main()
