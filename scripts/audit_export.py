#!/usr/bin/env python3
"""Audit the explicit public file list; optionally create a source-only ZIP."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {'.py', '.js', '.css', '.html', '.svg', '.json', '.webmanifest', '.md', '.txt', '.yml'}
BINARY_FILES = {'examples/cv.demo.pdf', 'docs/demo.png', 'app/public/app-192.png',
                'app/public/app-512.png', 'app/public/app.ico'}
PATTERNS = {
    'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'GitHub credential': re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b'),
    'Telegram credential': re.compile(r'\b\d{7,12}:[A-Za-z0-9_-]{30,}\b'),
    'provider credential': re.compile(r'\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{32,}\b'),
    'personal Windows path': re.compile(r'[A-Za-z]:[\\/]Users[\\/][^\s"<>]+'),
}


def private_path(name):
    parts = PurePosixPath(name).parts
    return (any(p == 'workspace' or p.startswith('workspace-') or p in {'.git', '__pycache__', '.venv'} for p in parts)
            or (PurePosixPath(name).name.startswith('.env') and name != '.env.example')
            or PurePosixPath(name).suffix in {'.sqlite', '.key', '.pem', '.log', '.pyc'})


def audit(root=ROOT):
    names = [line.strip() for line in (root/'public-files.txt').read_text(encoding='utf-8').splitlines()
             if line.strip() and not line.startswith('#')]
    errors = []
    if len(set(names)) != len(names): errors.append('Duplicate entries in public-files.txt')
    for name in names:
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name or private_path(name):
            errors.append('Private or unsafe path in export list: '+name); continue
        file = root/name
        if any(p.is_symlink() for p in [file, *file.parents] if p != root.parent):
            errors.append('Symbolic link in export: '+name); continue
        if not file.is_file():
            errors.append('Missing public file: '+name); continue
        if name in BINARY_FILES: continue
        if path.suffix not in TEXT_SUFFIXES and name not in {'LICENSE', '.gitattributes', '.gitignore', '.env.example', 'public-files.txt'}:
            errors.append('Unreviewed file type: '+name); continue
        try: text = file.read_text(encoding='utf-8-sig')
        except UnicodeDecodeError:
            errors.append('Expected UTF-8 text: '+name); continue
        for label, pattern in PATTERNS.items():
            if pattern.search(text): errors.append(label+' detected in '+name)
        if name.endswith('.md'):
            for link in re.findall(r'\]\(([^)\s]+)\)', text):
                if re.match(r'[a-z]+:|#', link): continue
                target = link.split('#')[0]
                if target and not (file.parent/target).exists():
                    errors.append('Broken documentation link in '+name+': '+target)
    if (root/'.git').exists():
        result = subprocess.run(['git', '-C', str(root), 'ls-files', '-z'], capture_output=True, check=True)
        tracked = result.stdout.decode('utf-8').strip('\x00').split('\x00') if result.stdout else []
        for name in tracked:
            if name not in names: errors.append('Tracked file is not public: '+name)
    return names, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', type=Path, help='Create a new ZIP containing only the audited allowlist')
    options = parser.parse_args()
    names, errors = audit()
    if errors:
        print(json.dumps({'ok':False,'errors':errors},ensure_ascii=False,indent=2)); return 1
    result = {'ok':True,'public_files':len(names),'note':'Review text and images for personal data before publication.'}
    if options.zip:
        destination = options.zip.resolve()
        if destination.exists(): raise SystemExit('Output already exists; choose a new ZIP name.')
        destination.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED) as archive:
            for name in names: archive.write(ROOT/name,'job-search-workspace/'+name)
        result.update(zip=str(destination),sha256=hashlib.sha256(destination.read_bytes()).hexdigest())
    print(json.dumps(result,ensure_ascii=False,indent=2)); return 0


if __name__ == '__main__': sys.exit(main())
