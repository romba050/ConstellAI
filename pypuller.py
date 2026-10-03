#!/usr/bin/env python3
"""
collect_sources.py

Copies source files from the current folder into a single export folder,
preserving relative paths, and writes a manifest for review/sharing.

Default:
- Collects .py files only
- Skips common junk/large folders (venv, node_modules, __pycache__, .git, etc.)
- Copies (not moves)
- Preserves timestamps

Extra (NEW):
- Also copies any .bat files that live next to this script into the export folder root
  (enabled by default via --include-bat-here).

Usage (run inside project root):
  python collect_sources.py

Optional:
  python collect_sources.py --ext .py .js .ts .tsx .css .html
  python collect_sources.py --out __EXPORT_SOURCES__
  python collect_sources.py --include-hidden
  python collect_sources.py --follow-symlinks
  python collect_sources.py --max-mb 2
  python collect_sources.py --dry-run
  python collect_sources.py --no-include-bat-here
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2
from typing import Iterable, List, Optional, Set


DEFAULT_SKIP_DIRS = {
    ".git", ".hg", ".svn",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".idea", ".vscode",
    "venv", ".venv", "env", ".env",
    "node_modules",
    "dist", "build", ".next", ".nuxt", "out",
    ".tox",
    "site-packages",
    ".ipynb_checkpoints",
}

DEFAULT_SKIP_FILES_GLOBS = {
    "*.pyc", "*.pyo", "*.pyd",
    "*.so", "*.dll", "*.dylib",
    "*.exe", "*.bin",
    "*.zip", "*.tar", "*.gz", "*.7z", "*.rar",
    "*.png", "*.jpg", "*.jpeg", "*.webp", "*.gif",
    "*.mp4", "*.mov", "*.avi", "*.mkv",
    "*.pdf",
    "*.db", "*.sqlite", "*.sqlite3",
    "*.log",
}

EXPORT_DIR_DEFAULT = "__EXPORT_SOURCES__"


@dataclass
class ManifestEntry:
    rel_path: str
    bytes: int
    sha256: str
    copied_to: str


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def matches_any_glob(name: str, globs: Set[str]) -> bool:
    return any(fnmatch.fnmatch(name, g) for g in globs)


def should_skip_dir(dir_name: str, skip_dirs: Set[str], include_hidden: bool) -> bool:
    if dir_name in skip_dirs:
        return True
    if not include_hidden and dir_name.startswith("."):
        return True
    return False


def should_skip_file(file_name: str, skip_files_globs: Set[str], include_hidden: bool) -> bool:
    if matches_any_glob(file_name, skip_files_globs):
        return True
    if not include_hidden and file_name.startswith("."):
        return True
    return False


def normalize_exts(exts: List[str]) -> Set[str]:
    norm = set()
    for e in exts:
        e = e.strip()
        if not e:
            continue
        if not e.startswith("."):
            e = "." + e
        norm.add(e.lower())
    return norm


def iter_source_files(
    root: Path,
    exts: Set[str],
    out_dir: Path,
    skip_dirs: Set[str],
    skip_files_globs: Set[str],
    include_hidden: bool,
    follow_symlinks: bool,
) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
        dpath = Path(dirpath)

        # prevent descending into export folder itself
        if out_dir in dpath.parents or dpath == out_dir:
            dirnames[:] = []
            continue

        # filter directories in-place (controls os.walk recursion)
        dirnames[:] = [
            d for d in dirnames
            if not should_skip_dir(d, skip_dirs, include_hidden)
        ]

        for fn in filenames:
            if should_skip_file(fn, skip_files_globs, include_hidden):
                continue
            p = dpath / fn
            if p.suffix.lower() in exts:
                yield p


def copy_bat_files_next_to_script(
    *,
    script_dir: Path,
    root: Path,
    out_dir: Path,
    dry_run: bool,
    max_bytes: int,
) -> List[ManifestEntry]:
    entries: List[ManifestEntry] = []

    # If script_dir is not under root, do nothing (keeps behavior safe).
    try:
        script_dir.relative_to(root)
    except ValueError:
        return entries

    bat_files = sorted(script_dir.glob("*.bat"))
    for src in bat_files:
        try:
            size = src.stat().st_size
        except OSError:
            continue

        if size > max_bytes:
            continue

        # Copy into export root (flattened), keeping filename only.
        dst = out_dir / src.name

        if dry_run:
            print(f"[DRY] {src.relative_to(root)} -> {dst.relative_to(root)}")
            sha = "DRY_RUN"
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            copy2(src, dst)
            sha = sha256_file(dst)

        entries.append(ManifestEntry(
            rel_path=str(src.relative_to(root)).replace("\\", "/"),
            bytes=size,
            sha256=sha,
            copied_to=str(dst.relative_to(root)).replace("\\", "/"),
        ))

    return entries


def main() -> int:
    ap = argparse.ArgumentParser(description="Collect source files into one export folder with manifest.")
    ap.add_argument("--out", default=EXPORT_DIR_DEFAULT, help="Output folder name (created inside root).")
    ap.add_argument("--ext", nargs="+", default=[".py"], help="Extensions to include, e.g. .py .js .ts .tsx .css .html")
    ap.add_argument("--include-hidden", action="store_true", help="Include hidden files/dirs starting with '.'")
    ap.add_argument("--follow-symlinks", action="store_true", help="Follow symlinks during traversal.")
    ap.add_argument("--max-mb", type=float, default=5.0, help="Skip files larger than this size (MB).")
    ap.add_argument("--dry-run", action="store_true", help="Print actions without copying.")

    # NEW: copy .bat next to the script into export root
    ap.add_argument(
        "--include-bat-here",
        dest="include_bat_here",
        action="store_true",
        default=True,
        help="Copy any .bat files located next to this script into the export folder root (default: on).",
    )
    ap.add_argument(
        "--no-include-bat-here",
        dest="include_bat_here",
        action="store_false",
        help="Disable copying .bat files located next to this script.",
    )

    args = ap.parse_args()

    root = Path.cwd().resolve()
    out_dir = (root / args.out).resolve()
    exts = normalize_exts(args.ext)

    skip_dirs = set(DEFAULT_SKIP_DIRS)
    skip_files_globs = set(DEFAULT_SKIP_FILES_GLOBS)

    max_bytes = int(args.max_mb * 1024 * 1024)

    entries: List[ManifestEntry] = []
    planned = list(iter_source_files(
        root=root,
        exts=exts,
        out_dir=out_dir,
        skip_dirs=skip_dirs,
        skip_files_globs=skip_files_globs,
        include_hidden=args.include_hidden,
        follow_symlinks=args.follow_symlinks,
    ))

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    for src in planned:
        try:
            size = src.stat().st_size
        except OSError:
            continue

        if size > max_bytes:
            continue

        rel = src.relative_to(root)
        dst = out_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)

        if args.dry_run:
            print(f"[DRY] {rel} -> {dst.relative_to(root)}")
            sha = "DRY_RUN"
        else:
            copy2(src, dst)
            sha = sha256_file(dst)

        entries.append(ManifestEntry(
            rel_path=str(rel).replace("\\", "/"),
            bytes=size,
            sha256=sha,
            copied_to=str(dst.relative_to(root)).replace("\\", "/"),
        ))

    # NEW: copy .bat files from the script folder into export root
    if args.include_bat_here:
        script_dir = Path(__file__).resolve().parent
        bat_entries = copy_bat_files_next_to_script(
            script_dir=script_dir,
            root=root,
            out_dir=out_dir,
            dry_run=args.dry_run,
            max_bytes=max_bytes,
        )
        entries.extend(bat_entries)

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "export_dir": str(out_dir),
        "included_exts": sorted(list(exts)),
        "skipped_dirs": sorted(list(skip_dirs)),
        "skipped_file_globs": sorted(list(skip_files_globs)),
        "max_mb": args.max_mb,
        "file_count": len(entries),
        "files": [asdict(e) for e in entries],
    }

    if args.dry_run:
        print(f"\n[DRY] WOULD WRITE MANIFEST.json WITH {len(entries)} FILES")
        return 0

    manifest_path = out_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"OK: COPIED {len(entries)} FILES INTO: {out_dir}")
    print(f"OK: WROTE MANIFEST: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())