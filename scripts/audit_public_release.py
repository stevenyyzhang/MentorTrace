"""Audit publishable files and frozen English corpora without printing data."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_DIRS = {'runs', 'workspaces', 'data', 'private', 'local-releases', '.release-work', 'tmp', 'output', '.venv', 'venv', '__pycache__', '.git'}
FORBIDDEN_CORPUS_KEYS = {'original_comments', 'marked_text', 'local_context', 'version_evidence', 'transitions', 'source_pdf', 'source_pdf_relative', 'source_file', 'source_documents', 'source_pages', 'selected_paragraph', 'short_quote', 'annotation_author_raw', 'student_family'}
TEXT_EXTENSIONS = {'.py', '.md', '.json', '.yaml', '.yml', '.css', '.txt', '.toml', '.html'}
PATTERNS = {
    'absolute_windows_path': re.compile(r'\b[A-Za-z]:[\\/]'),
    'absolute_home_path': re.compile(r'/(?:Users|home|mnt|workspace)/[^\s"\']+'),
    'email_address': re.compile(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b'),
    'credential': re.compile(r'\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,})\b'),
}

def files(root=ROOT):
    result = []
    for path in root.rglob('*'):
        if path.is_file() and not any(part in PRIVATE_DIRS for part in path.relative_to(root).parts):
            result.append(path)
    return sorted(result)

def audit(root=ROOT, deny_terms=()):
    root = Path(root).resolve()
    findings = []
    inventory = []
    corpus_files = 0
    for path in files(root):
        rel = path.relative_to(root).as_posix()
        if path.suffix.lower() in {'.pdf', '.doc', '.docx', '.tex', '.zip', '.7z', '.png', '.jpg', '.jpeg'}:
            if rel != 'examples/report_bilingual.pdf':
                findings.append({'file': rel, 'rule': 'source_or_unapproved_binary'})
        elif path.suffix not in TEXT_EXTENSIONS and path.name not in {'VERSION', '.gitignore', '.gitattributes', 'LICENSE'}:
            findings.append({'file': rel, 'rule': 'unrecognized_distribution_file'})
        if path.suffix in TEXT_EXTENSIONS or path.name in {'VERSION', '.gitignore', '.gitattributes', 'LICENSE'}:
            text = path.read_text(encoding='utf-8-sig')
            for name, pattern in PATTERNS.items():
                if pattern.search(text):
                    findings.append({'file': rel, 'rule': name})
            for term in deny_terms:
                if term and re.search(r'(?<![A-Za-z])' + re.escape(term) + r'(?![A-Za-z])', text, re.I):
                    findings.append({'file': rel, 'rule': 'private_identity_denylist'})
                    break
            if rel.startswith('corpus/') and path.suffix == '.json':
                corpus_files += 1
                if re.search(r'[\u3400-\u9fff]', text):
                    findings.append({'file': rel, 'rule': 'non_english_corpus'})
                value = json.loads(text)
                def inspect(node):
                    if isinstance(node, dict):
                        for key, child in node.items():
                            if not key.isascii():
                                findings.append({'file': rel, 'rule': 'non_ascii_key'})
                            if key in FORBIDDEN_CORPUS_KEYS:
                                findings.append({'file': rel, 'rule': 'private_or_source_excerpt_field', 'field': key})
                            inspect(child)
                    elif isinstance(node, list):
                        for child in node:
                            inspect(child)
                inspect(value)
        inventory.append({'path': rel, 'bytes': path.stat().st_size,
                          'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    for folder in ['corpus/advisor-concerns-v1', 'corpus/published-cases-v1']:
        package = root / folder
        if not (package / 'FREEZE.json').exists():
            findings.append({'file': folder, 'rule': 'missing_frozen_corpus'})
            continue
        freeze = json.loads((package / 'FREEZE.json').read_text(encoding='utf-8'))
        expected = freeze['files']
        actual = {path.relative_to(package).as_posix() for path in package.rglob('*') if path.is_file() and path.name != 'FREEZE.json'}
        if set(expected) != actual:
            findings.append({'file': folder, 'rule': 'freeze_inventory_mismatch'})
        for rel, digest in expected.items():
            target = (package / rel).resolve()
            if not target.is_relative_to(package.resolve()) or not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                findings.append({'file': folder, 'rule': 'freeze_hash_mismatch'})
    return {'version': (root/'VERSION').read_text(encoding='utf-8').strip() if (root/'VERSION').is_file() else 'not_declared', 'status': 'pass' if not findings else 'fail',
            'scanned_files': len(inventory), 'corpus_json_files': corpus_files,
            'findings': findings, 'inventory': inventory,
            'limits': 'Automated rules complement semantic abstraction review; they do not certify legal rights or diagnostic equivalence.'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--private-denylist', type=Path, help='Local JSON array; never distribute its contents')
    args = parser.parse_args()
    terms = json.loads(args.private_denylist.read_text(encoding='utf-8')) if args.private_denylist else []
    result = audit(deny_terms=terms)
    # Do not hash this audit into itself.
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({k:v for k,v in result.items() if k != 'inventory'}, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'inventory'}, indent=2))
    raise SystemExit(0 if result['status'] == 'pass' else 1)
