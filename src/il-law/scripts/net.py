"""Shared HTTP layer for the il-law scripts.

Every script goes through here so that host allowlisting, throttling,
retry, block-page detection and the citation envelope stay uniform.
"""
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:  # optional: falls back to certifi
    pass

ALLOWED_HOSTS = {
    "knesset.gov.il",
    "fs.knesset.gov.il",
    "he.wikisource.org",
    "api.justice.gov.il",
    "reshumot.justice.gov.il",
    "supremedecisions.court.gov.il",
    "data.gov.il",
    "free-justice.openapi.gov.il",
    "ags.iplan.gov.il",
    "www.sefaria.org",
    "apps.land.gov.il",
    "www.gov.il",
}
S3_HOST_SUFFIX = ".amazonaws.com"  # Reshumot resolver redirects to presigned S3
LEGACY_TLS_HOSTS = {"ags.iplan.gov.il"}
LEGACY_CIPHERS = "DEFAULT:@SECLEVEL=1"

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
TOOL_UA = "il-law-skill/1.0 (personal legal research tool; python-requests)"

DEFAULT_TIMEOUT_S = 40
DEFAULT_INTERVAL_S = 0.4
HOST_INTERVAL_S = {"supremedecisions.court.gov.il": 2.0, "api.justice.gov.il": 1.0}
MAX_ATTEMPTS = 4
BACKOFF_BASE_S = 2.0
RETRY_STATUSES = {429, 500, 502, 503, 504}
INSECURE_ENV = "IL_LAW_INSECURE"
CACHE_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "il-law" / "cache"
BLOCK_MARKERS = ("unauthorized activity", "Just a moment", "Request Rejected")
PDF_MAGIC = b"%PDF"

AUTH_OFFICIAL = "official"
AUTH_COMMUNITY = "community"
AUTH_METADATA = "metadata"

WARNINGS = []
_last_hit = {}
_session = None
_insecure = os.environ.get(INSECURE_ENV) == "1"


class SourceError(Exception):
    """A source answered in a way that must not be treated as data."""

    def __init__(self, kind, message, url=""):
        super().__init__(message)
        self.kind = kind
        self.url = url


def setup_stdout():
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")


def warn(message):
    if message not in WARNINGS:
        WARNINGS.append(message)


class LegacyTlsAdapter(requests.adapters.HTTPAdapter):
    """Some government ArcGIS servers only offer ciphers below OpenSSL's default security level."""

    def init_poolmanager(self, *args, **kwargs):
        import ssl

        context = ssl.create_default_context()
        context.set_ciphers(LEGACY_CIPHERS)
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)


def session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": TOOL_UA, "Accept-Language": "he,en"})
        for host in LEGACY_TLS_HOSTS:
            _session.mount(f"https://{host}", LegacyTlsAdapter())
    return _session


def check_host(url):
    host = urlparse(url).hostname or ""
    if host in ALLOWED_HOSTS or host.endswith(S3_HOST_SUFFIX):
        return host
    raise SourceError("host_not_allowed", f"{host} is not an allowlisted legal source", url)


def _throttle(host):
    interval = HOST_INTERVAL_S.get(host, DEFAULT_INTERVAL_S)
    wait = _last_hit.get(host, 0) + interval - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_hit[host] = time.monotonic()


def _send(method, url, **kwargs):
    global _insecure
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT_S)
    try:
        return session().request(method, url, verify=not _insecure, **kwargs)
    except requests.exceptions.SSLError:
        if _insecure:
            raise
        _insecure = True
        requests.packages.urllib3.disable_warnings()
        warn("tls: unverified (certificate check failed, retried without verification)")
        return session().request(method, url, verify=False, **kwargs)


def _looks_blocked(resp, expect):
    ctype = resp.headers.get("Content-Type", "")
    if expect == "json" and "html" in ctype:
        return True
    if "html" in ctype:
        head = resp.text[:3000]
        return any(marker in head for marker in BLOCK_MARKERS)
    return False


def request(method, url, expect="json", **kwargs):
    """Send with throttle + retry. Raises SourceError instead of returning junk."""
    host = check_host(url)
    last = "no attempt made"
    for attempt in range(MAX_ATTEMPTS):
        _throttle(host)
        try:
            resp = _send(method, url, **kwargs)
        except requests.exceptions.RequestException as exc:
            last = f"connection failed: {type(exc).__name__}"
        else:
            if resp.status_code == 404:
                return resp  # a missing record is an answer, not a transient failure
            if resp.status_code in RETRY_STATUSES:
                last = f"HTTP {resp.status_code}"
            elif _looks_blocked(resp, expect):
                last = "block page returned instead of data"
            else:
                return resp
        time.sleep(BACKOFF_BASE_S * (2**attempt))
    raise SourceError("unreachable", f"{host}: {last} after {MAX_ATTEMPTS} attempts", url)


def _cache_path(url, params):
    key = hashlib.sha256(f"{url}|{json.dumps(params, sort_keys=True)}".encode()).hexdigest()
    return CACHE_DIR / f"{key}.json"


def _cache_read(path, ttl_s):
    if ttl_s and path.exists() and time.time() - path.stat().st_mtime < ttl_s:
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def get_json(url, params=None, headers=None, cache_ttl_s=0):
    path = _cache_path(url, params)
    cached = _cache_read(path, cache_ttl_s)
    if cached is not None:
        return cached
    resp = request("GET", url, params=params, headers=headers)
    data = parse_json(resp, url, ok_statuses=(200,))
    if cache_ttl_s:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def post_json(url, body, headers=None):
    resp = request("POST", url, json=body, headers=headers)
    return parse_json(resp, url, ok_statuses=(200,))


def parse_json(resp, url, ok_statuses):
    if resp.status_code == 404:
        raise SourceError("not_found", "HTTP 404", url)
    if resp.status_code not in ok_statuses:
        raise SourceError("http_error", f"HTTP {resp.status_code}: {resp.text[:200]}", url)
    try:
        return resp.json()
    except ValueError:
        raise SourceError("bad_payload", f"expected JSON, got: {resp.text[:200]}", url)


def get_pdf(url, headers=None):
    """Download a PDF and refuse anything that is not one."""
    resp = request("GET", url, expect="bytes", headers=headers)
    if resp.status_code != 200 or not resp.content.startswith(PDF_MAGIC):
        raise SourceError("not_a_pdf", f"HTTP {resp.status_code}, not a PDF body", url)
    return resp.content


def save_file(content, out_path):
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return {"path": str(path), "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}


def pdf_text(content, max_chars=0):
    import fitz  # PyMuPDF, imported lazily: only PDF commands need it

    with fitz.open(stream=content, filetype="pdf") as doc:
        text = "\n".join(page.get_text() for page in doc)
    return text[:max_chars] if max_chars else text


def require(obj, keys, url):
    for key in keys:
        if key not in obj:
            raise SourceError("schema_drift", f"expected key '{key}' is missing", url)


def envelope(data, source_url, authority, **extra):
    return {
        "status": "ok",
        "source_url": source_url,
        "authority": authority,
        "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "warnings": list(WARNINGS),
        **extra,
        "data": data,
    }


def emit(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def run(main):
    """Entry wrapper: a failed source prints a JSON error and exits non-zero."""
    setup_stdout()
    try:
        emit(main())
    except SourceError as exc:
        emit({"status": exc.kind, "error": str(exc), "source_url": exc.url, "warnings": WARNINGS})
        sys.exit(1)
