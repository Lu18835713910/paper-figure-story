#!/usr/bin/env python3
"""Install the checked-out PFS skill into one explicit agent skill directory.

Pure stdlib. Installs only Git-tracked regular files from this checkout,
never merges old/new versions, and leaves user files in an external backup.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid

SKILL_NAME = "paper-figure-story"
EXPECTED_VERSION = "1.2.0"


class InstallError(RuntimeError):
    pass


def is_link(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def git_output(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    if result.returncode:
        raise InstallError("Git checkout required: " + result.stderr.decode("utf-8", "replace").strip())
    return result.stdout


def tracked_files(root: Path) -> list[Path]:
    if not (root / ".git").exists():
        raise InstallError("Source must be a Git clone of the repository; do not install from an arbitrary folder.")
    if git_output(root, "status", "--porcelain", "--untracked-files=no").strip():
        raise InstallError("Git checkout contains modified tracked files; use a clean clone")
    raw = git_output(root, "ls-files", "--cached", "-z")
    paths = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        rel = Path(os.fsdecode(item))
        pure = PurePosixPath(item.decode("utf-8", "surrogateescape").replace("\\", "/"))
        if pure.is_absolute() or ".." in pure.parts or ".git" in pure.parts:
            raise InstallError("Unsafe tracked path: " + repr(str(rel)))
        file = root / rel
        if file.is_symlink() or any((root / Path(*rel.parts[:i])).is_symlink() for i in range(1, len(rel.parts))):
            raise InstallError("Tracked symlink rejected: " + str(rel))
        if not file.is_file():
            raise InstallError("Missing/non-regular tracked file: " + str(rel))
        paths.append(rel)
    if not paths:
        raise InstallError("No tracked files in checkout")
    return paths


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_skill(root: Path) -> None:
    version = root / "VERSION"
    skill = root / "SKILL.md"
    runner = root / "scripts" / "run_pfs.py"
    if not all(p.is_file() and not p.is_symlink() for p in (version, skill, runner)):
        raise InstallError("Source lacks VERSION, SKILL.md or scripts/run_pfs.py")
    if version.read_text(encoding="utf-8-sig").strip() != EXPECTED_VERSION:
        raise InstallError("Unsupported VERSION (expected " + EXPECTED_VERSION + ")")
    if "name: paper-figure-story" not in skill.read_text(encoding="utf-8-sig")[:1000]:
        raise InstallError("SKILL.md identity does not match paper-figure-story")


def install(source: Path, target: Path, dry_run: bool = False) -> dict:
    source = source.resolve(strict=True)
    target = target.expanduser().absolute()
    if target.name != SKILL_NAME:
        raise InstallError("Target must end in /paper-figure-story")
    if is_link(target) or is_link(target.parent):
        raise InstallError("Installation target or skill directory is a symlink or reparse point")
    if source == target.parent or source == target:
        raise InstallError("Do not install in-place from an active skill directory; use a separate Git clone")
    validate_skill(source)
    files = tracked_files(source)
    revision = git_output(source, "rev-parse", "HEAD").decode("ascii").strip()
    if target.exists():
        if not target.is_dir() or target.is_symlink():
            raise InstallError("Target is not a normal directory")
        old_skill = target / "SKILL.md"
        if not old_skill.is_file() or "name: paper-figure-story" not in old_skill.read_text(encoding="utf-8-sig")[:1000]:
            raise InstallError("Existing directory is not a recognized PFS skill; refusing to overwrite")
    result = {"status": "DRY_RUN" if dry_run else "INSTALLED", "version": EXPECTED_VERSION,
              "revision": revision, "source": str(source), "target": str(target),
              "tracked_files": len(files), "backup": None}
    if dry_run:
        return result

    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    if is_link(parent):
        raise InstallError("Skill directory is a symlink or reparse point")
    stage = Path(tempfile.mkdtemp(prefix=".pfs-stage-", dir=parent))
    backup = None
    activated = False
    try:
        for rel in files:
            src = source / rel
            dst = stage / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            if file_hash(src) != file_hash(dst):
                raise InstallError("Staging file checksum mismatch: " + str(rel))
        validate_skill(stage)
        if target.exists():
            backup_root = parent.parent / "pfs-skill-backups"  # outside active skills directory
            backup_root.mkdir(parents=True, exist_ok=True)
            if is_link(backup_root):
                raise InstallError("Backup directory is a symlink or reparse point")
            backup = backup_root / (SKILL_NAME + "-" + uuid.uuid4().hex[:12])
            target.rename(backup)
            result["backup"] = str(backup)
        stage.rename(target)
        activated = True
        validate_skill(target)
        for rel in files:
            if file_hash(source / rel) != file_hash(target / rel):
                raise InstallError("Installed file checksum mismatch: " + str(rel))
    except Exception as error:
        if activated and target.exists():
            # Do not delete modified files: quarantine the newly staged install.
            quarantine = parent / (".pfs-failed-" + uuid.uuid4().hex[:12])
            target.rename(quarantine)
            result["quarantine"] = str(quarantine)
        if backup and backup.exists():
            if target.exists():
                raise InstallError("Rollback blocked: original backup preserved at " + str(backup)) from error
            backup.rename(target)
        raise InstallError("Install failed; old installation restored where possible: " + str(error)) from error
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="Separate Git clone to install (defaults to this repository)")
    parser.add_argument("--target", type=Path, default=Path.home() / ".codex" / "skills" / SKILL_NAME,
                        help="Exact skill destination (explicitly change for non-Codex agents)")
    parser.add_argument("--dry-run", action="store_true", help="Validate source and target without writing")
    opts = parser.parse_args(argv)
    try:
        result = install(opts.source, opts.target, opts.dry_run)
    except (OSError, InstallError, UnicodeError, subprocess.SubprocessError) as error:
        print("PFS_INSTALL_BLOCKED: " + str(error), file=sys.stderr)
        return 2
    for key, value in result.items():
        print(f"{key}: {value}")
    if not opts.dry_run:
        print("Restart the agent session; verify the actual loaded SKILL.md path and VERSION.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
