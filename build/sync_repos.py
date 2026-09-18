"""Pull every hiyabh repo tagged with the `claude-skill` topic into catalog.json.

Existing entries keep their hand-edited fields (icon, title, tagline, category,
badge); only the URL is refreshed. New repos get a default card that can be
polished by editing catalog.json. Runs daily from .github/workflows/sync.yml.

Usage:  python build/sync_repos.py        (GITHUB_TOKEN optional, raises rate limit)
"""
import json
import os
import sys
import urllib.request

from common import CATALOG, OWNER, REPO, dump_json, load_json

TOPIC = "claude-skill"
API = f"https://api.github.com/search/repositories?q=user:{OWNER}+topic:{TOPIC}&per_page=100"
DEFAULT_ICON = "🧩"
DEFAULT_CATEGORY = "other"
TIMEOUT_S = 30


def fetch_repos():
    req = urllib.request.Request(API, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return json.load(resp)["items"]


def page_url(repo):
    return repo.get("homepage") or f"https://{OWNER}.github.io/{repo['name']}/"


def new_entry(repo):
    return {
        "repo": repo["name"],
        "icon": DEFAULT_ICON,
        "title": repo["name"],
        "tagline": repo.get("description") or "",
        "category": DEFAULT_CATEGORY,
        "url": page_url(repo),
    }


def merge(catalog, repos):
    by_repo = {e["repo"]: e for e in catalog["external"]}
    added = []
    for repo in repos:
        if repo["name"] == REPO or repo.get("private"):
            continue
        if repo["name"] in by_repo:
            by_repo[repo["name"]]["url"] = by_repo[repo["name"]].get("url") or page_url(repo)
        else:
            entry = new_entry(repo)
            catalog["external"].append(entry)
            added.append(entry["repo"])
    return added


def main():
    try:
        repos = fetch_repos()
    except OSError as err:
        print(f"GitHub API unreachable ({err}); catalog left unchanged.")
        return 0
    catalog = load_json(CATALOG)
    added = merge(catalog, repos)
    if added:
        dump_json(CATALOG, catalog)
    print(f"{len(repos)} tagged repos; added: {', '.join(added) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
