"""Reproduce the candidate aggregate used by the rc.2 closeout.

The root is always explicit.  ZIP wrapper paths are removed only when supplied
by the caller; no candidate directory, version or wrapper is guessed.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path,PurePosixPath
from zipfile import ZipFile,BadZipFile

ALGORITHM='sha256-path-sha256-lines-v1'


def sha256_bytes(data):return hashlib.sha256(data).hexdigest()


def aggregate(files):
    """SHA256 of sorted ``relative_posix_path SHA256`` lines, no final newline."""
    return sha256_bytes('\n'.join(f'{p} {files[p]}' for p in sorted(files)).encode('utf8'))


def result(files):
    return dict(algorithm=ALGORITHM,path_format='root-relative POSIX; exact Unicode names',
                encoding='UTF-8',line_separator='LF; no trailing newline',
                excluded_names=['~$*'],file_count=len(files),
                aggregate_sha256=aggregate(files),files=dict(sorted(files.items())))


def directory_fingerprint(root):
    root=Path(root).resolve()
    if not root.is_dir():raise ValueError('CANDIDATE_ROOT_REQUIRED: existing directory expected')
    files={p.relative_to(root).as_posix():sha256_bytes(p.read_bytes())
           for p in root.rglob('*') if p.is_file() and not p.name.startswith('~$')}
    return result(files)


def _archive_path(name):
    if '\\' in name or name.startswith('/'):
        raise ValueError('CANDIDATE_ZIP_PATH_INVALID: '+name)
    parts=PurePosixPath(name).parts
    if not parts or any(part in ('.','..') or ':' in part for part in parts):
        raise ValueError('CANDIDATE_ZIP_PATH_INVALID: '+name)
    # Normalizing a malformed name would change its identity.
    if '/'.join(parts)!=name.rstrip('/'):
        raise ValueError('CANDIDATE_ZIP_PATH_INVALID: '+name)
    return parts


def zip_fingerprint(path,wrapper):
    """Read every member and CRC; bind the explicitly named packaging root."""
    prefix=tuple(_archive_path(wrapper)) if wrapper else ()
    files={};seen=set()
    with ZipFile(path) as archive:
        bad=archive.testzip()
        if bad:raise ValueError('CANDIDATE_ZIP_CRC: '+bad)
        for info in archive.infolist():
            parts=_archive_path(info.filename)
            if parts[:len(prefix)]!=prefix:
                raise ValueError('CANDIDATE_ZIP_WRAPPER_MISMATCH: '+info.filename)
            relative=parts[len(prefix):]
            if not relative:
                if info.is_dir():continue
                raise ValueError('CANDIDATE_ZIP_WRAPPER_FILE: '+info.filename)
            key='/'.join(relative)
            if info.is_dir():continue
            if key in seen:raise ValueError('CANDIDATE_ZIP_DUPLICATE: '+key)
            seen.add(key)
            if relative[-1].startswith('~$'):continue
            files[key]=sha256_bytes(archive.read(info))
    return result(files)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--root',type=Path,help='Exact candidate root; paths below it are hashed')
    g.add_argument('--zip',dest='zip_path',type=Path,help='ZIP to CRC/hash without extracting')
    p.add_argument('--zip-root',help='Exact wrapper in ZIP, e.g. paper-figure-story; use empty string for none')
    a=p.parse_args(argv)
    if a.zip_path is not None and a.zip_root is None:p.error('--zip requires explicit --zip-root')
    if a.root is not None and a.zip_root is not None:p.error('--zip-root applies only to --zip')
    try:
        r=directory_fingerprint(a.root) if a.root is not None else zip_fingerprint(a.zip_path,a.zip_root)
    except (OSError,ValueError,RuntimeError,BadZipFile) as exc:
        print(json.dumps(dict(valid=False,error=str(exc)),ensure_ascii=False));return 2
    # No output manifest is written into the source tree, which would make the
    # tree's own fingerprint circular.
    print(json.dumps(r,ensure_ascii=False,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
