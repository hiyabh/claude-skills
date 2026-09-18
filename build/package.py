"""Pack src/<name>/ into dl/<name>.tar.gz (layout: skills/<name>/...).

Archives are deterministic (fixed mtime/owner, sorted entries, gzip mtime 0)
so rebuilding unchanged sources produces byte-identical files and no git churn.
"""
import gzip
import io
import tarfile

from common import DL_DIR, SRC_DIR

EXCLUDE_NAMES = {"__pycache__", ".DS_Store", "page.json", "Thumbs.db"}
EXCLUDE_SUFFIXES = (".pyc", ".pyo")
FIXED_MTIME = 1_700_000_000


def _included(path):
    if any(part in EXCLUDE_NAMES for part in path.parts):
        return False
    return not path.name.endswith(EXCLUDE_SUFFIXES)


def _tarinfo(arcname, path):
    info = tarfile.TarInfo(arcname)
    info.mtime = FIXED_MTIME
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    if path.is_dir():
        info.type, info.mode = tarfile.DIRTYPE, 0o755
    else:
        info.size = path.stat().st_size
        info.mode = 0o755 if path.suffix in (".sh", ".py") else 0o644
    return info


def pack(skill_dir):
    name = skill_dir.name
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
        entries = [skill_dir] + sorted(p for p in skill_dir.rglob("*") if _included(p))
        for path in entries:
            arcname = f"skills/{name}/{path.relative_to(skill_dir).as_posix()}".rstrip("/.")
            info = _tarinfo(arcname, path)
            if path.is_dir():
                tar.addfile(info)
            else:
                with path.open("rb") as fh:
                    tar.addfile(info, fh)
    DL_DIR.mkdir(exist_ok=True)
    target = DL_DIR / f"{name}.tar.gz"
    with target.open("wb") as out, gzip.GzipFile(fileobj=out, mode="wb", mtime=0) as gz:
        gz.write(raw.getvalue())
    return target


def pack_all():
    return [pack(d) for d in sorted(SRC_DIR.iterdir()) if (d / "SKILL.md").is_file()]
