#!/usr/bin/env python3
"""Read-only AutoDraw Markdown audit. Historical warnings do not erase evidence."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

from capability_catalog import check_capability_catalog, find_capabilities

LINK_RE = re.compile(r'(?<!!)\[[^\]\n]+\]\(([^)\n]+)\)')
HEADING_RE = re.compile(r'^\s{0,3}#{1,6}\s+(.+?)\s*$')
DECISION_RE = re.compile(r'^## DEC-(\d{3})\.\s', re.MULTILINE)
CURRENT_DOCS = {
    'README.md', 'docs/README.md', 'docs/PROJECT_STATUS.md', 'docs/TASKS.md',
    'docs/ROADMAP.md', 'docs/DECISIONS.md', 'docs/TEST_RESULTS.md',
    'docs/WORK_LOG.md', 'docs/CHANGELOG.md', 'docs/AI_WORK_GUIDE.md',
    'docs/KNOWLEDGE_ARCHITECTURE.md'
}
FENCE_RE = re.compile(r'^\s{0,3}(?:' + chr(96) + r'{3,}|~{3,})')
EXPLICIT_ANCHOR_RE = re.compile(r'<a\s+(?:id|name)=[\"\']([^\"\']+)[\"\']', re.IGNORECASE)


def github_slug(title: str) -> str:
    title = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', title)
    title = re.sub(r'<[^>]+>', '', title).replace(chr(96), '')
    title = re.sub(r'[*~]', '', title).strip().strip('#').strip().lower()
    title = ''.join(c for c in title
                    if c in ' -_' or unicodedata.category(c)[0] in ('L', 'N', 'M'))
    return re.sub(r'\s', '-', title)


def heading_anchors(content: str) -> set[str]:
    seen = {}
    result = set()
    fenced = False
    for line in content.splitlines():
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        for anchor in EXPLICIT_ANCHOR_RE.finditer(line):
            result.add(anchor.group(1).lower())
        found = HEADING_RE.match(line)
        if found:
            slug = github_slug(found.group(1))
            index = seen.get(slug, 0)
            seen[slug] = index + 1
            result.add(slug + (f'-{index}' if index else ''))
    return result


def markdown_links(content: str):
    fenced = False
    for n, line in enumerate(content.splitlines(), 1):
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            for m in LINK_RE.finditer(line):
                value = m.group(1).strip()
                if value.startswith('<') and '>' in value:
                    value = value[1:value.find('>')]
                else:
                    value = re.split(r'\s+"[^"]*"\s*$', value, maxsplit=1)[0]
                if value:
                    yield n, value


def local_target(source: Path, destination: str):
    parsed = urlsplit(destination.replace('\\)', ')'))
    if parsed.scheme or parsed.netloc or destination.startswith('//'):
        return None
    path = ((source.parent / unquote(parsed.path)).resolve()
            if parsed.path else source.resolve())
    return path, unquote(parsed.fragment).lower()


def check_links(root: Path, md_paths: list[Path]):
    root = root.resolve()
    index = root / 'docs' / 'README.md'
    indexed = set()
    anchors = {}
    problems = []
    for file in md_paths:
        for line_no, dest in markdown_links(file.read_text(encoding='utf-8')):
            target = local_target(file, dest)
            if target is None:
                continue
            path, fragment = target
            if file == index and path.suffix.lower() == '.md':
                indexed.add(path)
            label = {'file': str(file.relative_to(root)), 'line': line_no,
                     'destination': dest}
            if not path.is_relative_to(root.parent):
                problems.append({**label, 'error': 'outside_repository_root'})
            elif not path.exists():
                problems.append({**label, 'error': 'missing_target'})
            elif fragment and path.is_file() and path.suffix.lower() == '.md':
                if path not in anchors:
                    anchors[path] = heading_anchors(path.read_text(encoding='utf-8'))
                if fragment not in anchors[path]:
                    problems.append({**label, 'error': 'missing_fragment'})
    missing = sorted(str(p.relative_to(root)) for p in md_paths if p not in indexed)
    return problems, missing


def decision_duplicates(content: str):
    counts = Counter(DECISION_RE.findall(content))
    return sorted(x for x, n in counts.items() if n > 1)


def git_blob_sha(data: bytes):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def verify_history(root: Path):
    path = root / 'docs' / 'HISTORY_SNAPSHOT_PROVENANCE.json'
    if not path.is_file():
        return [{'file': str(path), 'error': 'missing_manifest'}]
    data = json.loads(path.read_text(encoding='utf-8'))
    problems = []
    for record in data['snapshots']:
        file = root / record['archive']
        if not file.is_file():
            problems.append({'file': record['archive'], 'error': 'missing_snapshot'})
        elif git_blob_sha(file.read_bytes()) != record['git_blob_sha']:
            problems.append({'file': record['archive'], 'error': 'snapshot_changed'})
    return problems




def audit(root: Path):
    root = root.resolve()
    markdown = sorted(root.rglob('*.md'))
    problems, not_indexed = check_links(root, markdown)
    current = [p for p in problems if p['file'] in CURRENT_DOCS]
    historical = [p for p in problems if p['file'] not in CURRENT_DOCS]
    decisions = root / 'docs' / 'DECISIONS.md'
    duplicates = decision_duplicates(decisions.read_text(encoding='utf-8'))
    snapshots = verify_history(root)
    capability_errors, capability_count = check_capability_catalog(root)
    return {
        'schema_version': 1, 'total_markdown_files': len(markdown),
        'indexed_files': len(markdown) - len(not_indexed),
        'unindexed_files': not_indexed, 'duplicate_decisions': duplicates,
        'current_broken_links': current, 'historical_link_warnings': historical,
        'history_integrity_errors': snapshots,
        'capability_count': capability_count,
        'capability_catalog_errors': capability_errors,
        'external_ci_results_verified': False,
        'status': 'FAIL' if (not_indexed or duplicates or current or snapshots or capability_errors) else 'PASS',
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='AutoDraw_Stage20')
    parser.add_argument('--report')
    parser.add_argument('--find', help='Read-only lookup of existing capability candidates')
    args = parser.parse_args(argv)
    if args.find is not None:
        try:
            candidates = find_capabilities(Path(args.root), args.find)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps({'query': args.find, 'candidates': candidates},
                         ensure_ascii=False, indent=2))
        return 0 if candidates else 2
    result = audit(Path(args.root))
    if args.report:
        dest = Path(args.report)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n',
                        encoding='utf-8')
    summary = {k: len(v) if isinstance(v, list) else v for k, v in result.items()}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    for key in ('unindexed_files', 'duplicate_decisions', 'current_broken_links',
                'historical_link_warnings', 'history_integrity_errors',
                'capability_catalog_errors'):
        if result[key]:
            print(key + ': ' + json.dumps(result[key][:12], ensure_ascii=False))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
