"""Hebrew Wikisource "ספר החוקים הפתוח": consolidated statute text.

Community-maintained and NOT official. Always report the revision date and
confirm validity / latest amendment with knesset.py (or cite.py law).

  wikisrc.py find --name "התכנון והבניה"
  wikisrc.py get --title "חוק המקרקעין"                 (header + table of sections)
  wikisrc.py get --title "חוק המקרקעין" --section 59ב,62
  wikisrc.py grep --title "חוק המקרקעין" --text "רכוש משותף"
  wikisrc.py get --title "חוק המקרקעין" --out law.txt   (full text to a file)
"""
import argparse
import os
import re
import sys
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import net

API = "https://he.wikisource.org/w/api.php"
PAGE_URL = "https://he.wikisource.org/wiki/"
PERMALINK = "https://he.wikisource.org/w/index.php?oldid={revid}"
SEARCH_LIMIT = 10
GREP_LIMIT = 15
UNOFFICIAL = "unofficial community text (Wikisource) - verify validity and latest amendment against the Knesset register"

SECTION_RE = re.compile(r"\{\{ח:סעיף\|([^|}]*)\|?([^|}]*)[^}]*\}\}")
KNESSET_ID_RE = re.compile(r"\{\{ח:מאגר\|(\d+)\}\}")
INNER_TEMPLATE_RE = re.compile(r"\{\{ח:[^|{}]+\|([^{}]*)\}\}")
BARE_TEMPLATE_RE = re.compile(r"\{\{ח:[^|{}]+\}\}")
MAX_UNWRAP_PASSES = 6


def api(params):
    return net.get_json(API, params={"format": "json", "formatversion": "2", **params})


def load_page(title):
    params = {"action": "query", "titles": title, "prop": "revisions", "redirects": "1",
              "rvprop": "content|timestamp|ids", "rvslots": "main"}
    page = api(params)["query"]["pages"][0]
    if page.get("missing"):
        raise net.SourceError("not_found", f"no Wikisource page titled '{title}' - use: find --name", API)
    rev = page["revisions"][0]
    return page["title"], rev, rev["slots"]["main"]["content"]


def unwrap(text):
    """Reduce {{ח:...}} templates to their visible text (last argument)."""
    for _ in range(MAX_UNWRAP_PASSES):
        text, count = INNER_TEMPLATE_RE.subn(lambda m: m.group(1).split("|")[-1], text)
        if not count:
            break
    return BARE_TEMPLATE_RE.sub("", text).strip()


def split_sections(wikitext):
    marks = list(SECTION_RE.finditer(wikitext))
    sections = []
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(wikitext)
        body = unwrap(wikitext[mark.end():end])
        sections.append({"number": mark.group(1).strip(), "title": mark.group(2).strip(), "text": body})
    return sections


def page_meta(title, rev, wikitext):
    match = KNESSET_ID_RE.search(wikitext)
    return {
        "title": title,
        "page_url": PAGE_URL + quote(title.replace(" ", "_")),
        "revision_timestamp": rev["timestamp"],
        "knesset_law_id": int(match.group(1)) if match else None,
        "chars": len(wikitext),
    }


def result(title, rev, wikitext, payload):
    net.warn(UNOFFICIAL)
    data = {**page_meta(title, rev, wikitext), **payload}
    return net.envelope(data, PERMALINK.format(revid=rev["revid"]), net.AUTH_COMMUNITY)


def cmd_find(args):
    params = {"action": "query", "list": "search", "srsearch": f"intitle:{args.name}",
              "srlimit": str(SEARCH_LIMIT), "srprop": "size|timestamp"}
    hits = api(params)["query"]["search"]
    rows = [{"title": h["title"], "size": h["size"], "last_edit": h["timestamp"]} for h in hits]
    return net.envelope(rows, API, net.AUTH_COMMUNITY)


def cmd_get(args):
    title, rev, wikitext = load_page(args.title)
    sections = split_sections(wikitext)
    if args.out:
        body = "\n\n".join(f"{s['number']}. {s['title']}\n{s['text']}" for s in sections)
        return result(title, rev, wikitext, {"saved": net.save_file(body.encode("utf-8"), args.out)})
    if args.section:
        wanted = {n.strip() for n in args.section.split(",")}
        found = [s for s in sections if s["number"] in wanted]
        missing = sorted(wanted - {s["number"] for s in found})
        return result(title, rev, wikitext, {"sections": found, "sections_not_found": missing})
    toc = [f"{s['number']} - {s['title']}" for s in sections]
    return result(title, rev, wikitext, {"section_count": len(toc), "toc": toc})


def cmd_grep(args):
    title, rev, wikitext = load_page(args.title)
    hits = [s for s in split_sections(wikitext) if args.text in s["text"] or args.text in s["title"]]
    if len(hits) > GREP_LIMIT:
        net.warn(f"{len(hits)} sections match - showing the first {GREP_LIMIT}")
    return result(title, rev, wikitext, {"match_count": len(hits), "sections": hits[:GREP_LIMIT]})


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    find = sub.add_parser("find")
    find.add_argument("--name", required=True)
    find.set_defaults(func=cmd_find)
    get = sub.add_parser("get")
    get.add_argument("--title", required=True)
    get.add_argument("--section", help="comma-separated section numbers, e.g. 59ב,62")
    get.add_argument("--out", help="write the full cleaned text to this file")
    get.set_defaults(func=cmd_get)
    grep = sub.add_parser("grep")
    grep.add_argument("--title", required=True)
    grep.add_argument("--text", required=True)
    grep.set_defaults(func=cmd_grep)
    return parser


def main():
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    net.run(main)
