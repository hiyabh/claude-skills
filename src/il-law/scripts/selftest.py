"""Live self-test of every il-law source. Asserts content, not just HTTP 200.

  selftest.py                 run all probes, print a pass/fail table, exit 1 on any failure
  selftest.py --only supreme,knesset
  selftest.py --break knesset  (sanity check: force one probe to fail loudly)
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import datagov
import iplan
import knesset
import net
import reshumot
import sefaria
import supreme
import wikisrc

LAND_LAW_ID = 2000416
LAND_LAW_WORD = "מקרקעין"
LAND_LAW_TITLE = "חוק המקרקעין"
SUPREME_PHRASE = "דייר סרבן"
SUPREME_FROM = "2020-01-01"
GAZETTE_ID = "/officialGazette/statuteBook/3579"
SEFARIA_REF = "Shulchan Arukh, Choshen Mishpat 231.1"
IPLAN_CITY = "ירושלים"
MIN_PDF_BYTES = 10_000
BROKEN_URL = "https://knesset.gov.il/OdataV4/DoesNotExist/"


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def probe_knesset():
    law = net.get_json(f"{knesset.BASE}KNS_IsraelLaw({LAND_LAW_ID})")
    expect(LAND_LAW_WORD in law.get("Name", ""), "law 2000416 is not חוק המקרקעין")
    expect(law.get("LawValidityDesc"), "validity field empty")
    total, rows = knesset.law_amendments(LAND_LAW_ID, 1)
    expect(total > 30 and rows and rows[0].get("documents"), "amendment chain missing documents")
    return f"{law['Name']} | {law['LawValidityDesc']} | {total} bindings"


def probe_wikisource():
    title, rev, wikitext = wikisrc.load_page(LAND_LAW_TITLE)
    meta = wikisrc.page_meta(title, rev, wikitext)
    expect(meta["knesset_law_id"] == LAND_LAW_ID, "page lacks the {{ח:מאגר}} link to the Knesset id")
    sections = wikisrc.split_sections(wikitext)
    expect(len(sections) > 100, f"only {len(sections)} sections parsed")
    return f"{len(sections)} sections | revision {meta['revision_timestamp'][:10]}"


def probe_reshumot():
    data = net.get_json(reshumot.BASE + "/official-gazette", params={"ID": GAZETTE_ID}, headers=reshumot.HEADERS)
    expect(data.get("portfolios"), "gazette issue lookup returned nothing")
    path = reshumot.slim_portfolio(data["portfolios"][0])["pdf_path"]
    signed = reshumot.resolve_pdf(path)
    expect(signed.startswith("https://"), "resolver did not return a signed URL")
    pdf = net.get_pdf(signed)
    expect(len(pdf) > MIN_PDF_BYTES, "gazette PDF too small")
    return f"issue {GAZETTE_ID} | PDF {len(pdf)} bytes"


def probe_supreme():
    body = supreme.search_body(SUPREME_PHRASE, SUPREME_FROM, time.strftime("%Y-%m-%d"))
    result = supreme.run_search(body, "all", 1)
    expect(result["total_matches"] > 0 and result["data"], "no rulings for a phrase known to exist")
    row = result["data"][0]
    pdf = net.get_pdf(row["pdf_url"], headers=supreme.HEADERS)
    expect(len(pdf) > MIN_PDF_BYTES, "ruling PDF too small")
    return f"{result['total_matches']} matches | first {row['case']} | PDF {len(pdf)} bytes"


def probe_datagov():
    rows, total, _ = datagov.datastore(datagov.RESOURCES["samay"], limit=1)
    expect(total > 20_000 and rows, f"samay dataset shrank to {total} rows")
    link = rows[0].get("link", "")
    expect(link.startswith(datagov.PDF_HOST), "samay row has no free-justice PDF link")
    pdf = net.get_pdf(link)
    return f"{total} appraiser decisions | PDF {len(pdf)} bytes"


def probe_iplan():
    rows = iplan.query(f"plan_county_name = '{IPLAN_CITY}'", 1)
    expect(rows and rows[0].get("pl_number"), "no plans returned for Jerusalem")
    return f"plan {rows[0]['pl_number']} | updated {rows[0]['last_update']}"


def probe_sefaria():
    data = net.get_json(sefaria.BASE + "texts/" + SEFARIA_REF.replace(" ", "%20").replace(",", "%2C"))
    expect(data.get("he"), "Hebrew text empty")
    return f"{data['ref']}"


PROBES = {
    "knesset": probe_knesset, "wikisource": probe_wikisource, "reshumot": probe_reshumot,
    "supreme": probe_supreme, "datagov": probe_datagov, "iplan": probe_iplan, "sefaria": probe_sefaria,
}


def run_probe(name):
    net.WARNINGS.clear()
    started = time.monotonic()
    try:
        detail = PROBES[name]()
        status = "PASS"
    except (AssertionError, net.SourceError, KeyError, ValueError) as exc:
        detail, status = f"{type(exc).__name__}: {exc}", "FAIL"
    return {"source": name, "status": status, "seconds": round(time.monotonic() - started, 1),
            "detail": detail, "warnings": list(net.WARNINGS)}


def print_table(results):
    width = max(len(r["source"]) for r in results)
    for r in results:
        print(f"{r['status']:4} {r['source']:<{width}} {r['seconds']:>5}s  {r['detail']}")
        for warning in r["warnings"]:
            print(f"     {'':<{width}}         ! {warning}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", help="comma-separated probe names")
    parser.add_argument("--break", dest="break_probe", choices=list(PROBES), help="force a probe to fail")
    args = parser.parse_args()
    if args.break_probe == "knesset":
        knesset.BASE = BROKEN_URL
    names = args.only.split(",") if args.only else list(PROBES)
    results = [run_probe(name) for name in names]
    print_table(results)
    failed = [r["source"] for r in results if r["status"] != "PASS"]
    print(f"\n{len(results) - len(failed)}/{len(results)} sources OK" + (f" - FAILED: {', '.join(failed)}" if failed else ""))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    net.setup_stdout()
    main()
