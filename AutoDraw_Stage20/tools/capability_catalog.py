#!/usr/bin/env python3
"""Capability discovery and AST contract validation (read-only, E1 only).

Owns the small Markdown registry parser. No game/GUI imports, no browser
and no execution of indexed Python modules.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path


def check_capability_catalog(root: Path):
    """Static E1 index check; does not import Python or run game/GUI code."""
    root = root.resolve()
    path = root / 'docs' / 'COMPONENT_CATALOG.md'
    if not path.is_file():
        return [{'error': 'missing_catalog'}], 0
    content = path.read_text(encoding='utf-8')
    start = '<!-- AUTODRAW_CAPABILITIES_START -->'
    end = '<!-- AUTODRAW_CAPABILITIES_END -->'
    if content.count(start) != 1 or content.count(end) != 1:
        return [{'error': 'missing_or_duplicate_capability_markers'}], 0
    section = content.split(start, 1)[1].split(end, 1)[0]
    problems, ids, found, cached = [], set(), 0, {}
    for line in section.splitlines():
        if not line.startswith('| CAP-'):
            continue
        cells = [v.strip().strip(chr(96)) for v in line.strip().strip('|').split('|')]
        if len(cells) != 8:
            problems.append({'error': 'wrong_column_count', 'row': line[:100]})
            continue
        cid, _, owner, symbol, arguments, scope, _, test = cells
        found += 1
        if not re.fullmatch(r'CAP-[0-9]{3}', cid) or cid in ids:
            problems.append({'id': cid, 'error': 'invalid_or_duplicate_id'})
        ids.add(cid)
        if scope not in ('shared', 'adapter', 'experimental'):
            problems.append({'id': cid, 'error': 'unknown_scope'})
        for label, relative in (('owner', owner), ('test', test)):
            file = (root / relative).resolve()
            if (not relative or Path(relative).is_absolute()
                    or not file.is_relative_to(root)
                    or file.suffix != '.py' or not file.is_file()):
                problems.append({'id': cid, 'error': 'invalid_' + label,
                                 'path': relative})
        source = (root / owner).resolve()
        if not source.is_relative_to(root) or not source.is_file():
            continue
        if source not in cached:
            try:
                cached[source] = ast.parse(source.read_text(encoding='utf-8'),
                                           filename=str(source))
            except (SyntaxError, UnicodeError) as exc:
                problems.append({'id': cid, 'error': 'invalid_python_ast',
                                 'detail': str(exc)[:120]})
                cached[source] = None
        if cached[source] is None:
            continue
        nodes = [n for n in cached[source].body
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                 and n.name == symbol]
        if len(nodes) != 1:
            problems.append({'id': cid, 'error': 'missing_entrypoint',
                             'symbol': symbol})
            continue
        if arguments == '-':
            continue
        node = nodes[0]
        if isinstance(node, ast.ClassDef):
            problems.append({'id': cid, 'error': 'class_no_direct_signature'})
            continue
        actual = {a.arg for a in
                  node.args.posonlyargs + node.args.args + node.args.kwonlyargs}
        listed = [a.strip() for a in arguments.split(',')]
        if (not all(listed) or len(set(listed)) != len(listed)
                or not set(listed).issubset(actual)):
            problems.append({'id': cid, 'error': 'missing_contract_arguments',
                             'names': sorted(set(listed) - actual)})
    if not found:
        problems.append({'error': 'empty_capability_catalog'})
    return problems, found



def find_capabilities(root: Path, query: str, limit: int = 5):
    """Rank documented candidate entrypoints; NOT a semantic runtime guarantee."""
    errors, _ = check_capability_catalog(root)
    if errors:
        raise ValueError("Capability catalog is structurally invalid: " +
                         str(errors[:3]))
    if not isinstance(query, str) or not query.strip() or not 1 <= limit <= 20:
        raise ValueError("A nonempty query and a bounded result limit are required")
    catalog = (Path(root) / 'docs' / 'COMPONENT_CATALOG.md').read_text(encoding='utf-8')
    section = catalog.split('<!-- AUTODRAW_CAPABILITIES_START -->', 1)[1].split(
        '<!-- AUTODRAW_CAPABILITIES_END -->', 1)[0]
    terms = set(re.findall(r'[^\W_]+', query.casefold()))
    ranked = []
    for row in section.splitlines():
        if not row.startswith('| CAP-'):
            continue
        cells = [c.strip().strip(chr(96)) for c in row.strip().strip('|').split('|')]
        cid, title, owner, entrypoint, _, scope, guard, _ = cells
        title_terms = set(re.findall(r'[^\W_]+', title.casefold()))
        all_terms = set(re.findall(r'[^\W_]+',
                                   (owner + ' ' + entrypoint + ' ' + guard).casefold()))
        score = 3 * len(terms & title_terms) + len(terms & all_terms)
        if score:
            ranked.append((score, {'id': cid, 'title': title,
                                   'owner': owner, 'entrypoint': entrypoint,
                                   'scope': scope, 'evidence': 'E1_CANDIDATE_ONLY'}))
    ranked.sort(key=lambda item: (-item[0], item[1]['id']))
    return [row for _, row in ranked[:limit]]
