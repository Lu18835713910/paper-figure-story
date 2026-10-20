#!/usr/bin/env python3
"""Extract PDF text and a rough figure index once; cache by file SHA256.

This is a navigation aid, not evidence verification. Scientific figures must still
be visually inspected with the original PDF and Methods/legends checked.
"""
import argparse
import hashlib
import json
import pathlib
import re


def sha256_file(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    pa = argparse.ArgumentParser(description=__doc__)
    pa.add_argument('paper', type=pathlib.Path)
    pa.add_argument('--outdir', type=pathlib.Path, required=True)
    pa.add_argument('--force', action='store_true')
    args = pa.parse_args()
    paper = args.paper.resolve()
    if not paper.is_file():
        raise SystemExit('PDF not found: ' + str(paper))
    args.outdir.mkdir(parents=True, exist_ok=True)
    outfile = args.outdir / 'paper_index.json'
    digest = sha256_file(paper)
    if outfile.is_file() and not args.force:
        try:
            cached = json.loads(outfile.read_text(encoding='utf-8'))
            if cached.get('file_sha256') == digest:
                print('CACHE HIT:', outfile)
                print('PAGES:', len(cached.get('pages', [])))
                return
        except (OSError, ValueError):
            pass
    try:
        import fitz
    except ImportError as exc:
        raise SystemExit('PyMuPDF required: python -m pip install pymupdf') from exc
    doc = fitz.open(str(paper))
    pages = []
    full = []
    fig_pat = re.compile(r'(?i)\b(?:fig(?:ure)?)[.\s]*([0-9]+)([a-z]?)\b')
    for i, page in enumerate(doc):
        tx = page.get_text('text', sort=True) or ''
        found = sorted({m.group(1) for m in fig_pat.finditer(tx)}, key=int)
        pages.append({'pdf_page': i+1, 'characters': len(tx), 'figure_mentions': found, 'text': tx})
        full.append(f'\n\n===== PDF PAGE {i+1} =====\n{tx}')
    result = {'source_pdf': str(paper), 'file_sha256': digest,
              'page_count': len(pages), 'pages': pages}
    outfile.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    (args.outdir / 'paper_text.txt').write_text(''.join(full), encoding='utf-8')
    print('INDEX:', outfile)
    print('TEXT:', args.outdir / 'paper_text.txt')
    print('PAGES:', len(pages))
    print('Figure references are candidate navigation hints only; verify against original pages.')


if __name__ == '__main__':
    main()
