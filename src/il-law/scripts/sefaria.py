"""Sefaria - Jewish legal texts (Mishpat Ivri). Not binding Israeli law; cite as context only.

  sefaria.py text --ref "Shulchan Arukh, Choshen Mishpat 231.1"
  sefaria.py search --text "דינא דמלכותא" [--limit 10]
"""
import argparse
import os
import re
import sys
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import net

BASE = "https://www.sefaria.org/api/"
SITE = "https://www.sefaria.org/"
DEFAULT_LIMIT = 10
TAG_RE = re.compile(r"<[^>]+>")
NOT_BINDING = "Jewish law source (Sefaria) - context only, not binding Israeli law"


def strip_tags(value):
    if isinstance(value, list):
        return [strip_tags(v) for v in value]
    return TAG_RE.sub("", value or "")


def cmd_text(args):
    url = BASE + "texts/" + quote(args.ref)
    data = net.get_json(url, params={"context": "0", "commentary": "0"})
    net.require(data, ["ref", "he"], url)
    net.warn(NOT_BINDING)
    payload = {"ref": data["ref"], "he_ref": data.get("heRef"), "hebrew": strip_tags(data["he"]),
               "english": strip_tags(data.get("text")), "page_url": SITE + quote(data["ref"].replace(" ", "_"))}
    return net.envelope(payload, url, net.AUTH_COMMUNITY)


def cmd_search(args):
    url = BASE + "search-wrapper"
    body = {"query": args.text, "type": "text", "size": args.limit, "field": "naive_lemmatizer"}
    data = net.post_json(url, body)
    hits = data.get("hits", {}).get("hits", [])
    net.warn(NOT_BINDING)
    rows = [{"ref": h["_id"].split(" (")[0], "snippet": strip_tags(" ".join(h.get("highlight", {}).get("naive_lemmatizer", [])))}
            for h in hits]
    return net.envelope(rows, url, net.AUTH_COMMUNITY, total=data.get("hits", {}).get("total"), shown=len(rows))


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    text = sub.add_parser("text")
    text.add_argument("--ref", required=True)
    text.set_defaults(func=cmd_text)
    search = sub.add_parser("search")
    search.add_argument("--text", required=True)
    search.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    search.set_defaults(func=cmd_search)
    return parser


def main():
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    net.run(main)
