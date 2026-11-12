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


def inspect_capability_consumers(root: Path):
    """Read-only E1 import/call candidates and flat preparation import cycles.

    Only syntax is inspected. Dynamic imports, monkey-patching, reexports,
    path shadowing and actual runtime behavior are outside this analysis.
    """
    root = Path(root).resolve()
    errors, count = check_capability_catalog(root)
    if errors:
        raise ValueError('Capability catalog is structurally invalid: ' +
                         str(errors[:3]))
    catalog = (root / 'docs' / 'COMPONENT_CATALOG.md').read_text(encoding='utf-8')
    section = catalog.split('<!-- AUTODRAW_CAPABILITIES_START -->', 1)[1].split(
        '<!-- AUTODRAW_CAPABILITIES_END -->', 1)[0]
    entries = {}
    for row in section.splitlines():
        if row.startswith('| CAP-'):
            cells = [c.strip().strip(chr(96)) for c in row.strip().strip('|').split('|')]
            entries[cells[0]] = {'owner': cells[2], 'entrypoint': cells[3]}

    # Source files only. Test imports are not production consumers.
    source_files = sorted(p for base in (root / 'source', root / 'geometry_models',
                                        root / 'shared_image_processing')
                          if base.is_dir()
                          for p in base.rglob('*.py') if 'tests' not in p.parts)
    trees, parse_errors = {}, []
    for path in source_files:
        try:
            trees[path] = ast.parse(path.read_text(encoding='utf-8'),
                                    filename=str(path))
        except (SyntaxError, UnicodeError) as exc:
            parse_errors.append({'path': str(path.relative_to(root)),
                                 'error': str(exc)[:120]})
    if parse_errors:
        # A partial inventory can silently hide actual consumers; fail closed.
        raise ValueError('Cannot complete source AST inventory: ' + str(parse_errors[:3]))

    # Only flat module imports inside source/preparation are unambiguous
    # within this scope. Imports in callbacks count as static candidates.
    prep = root / 'source' / 'preparation'
    prep_modules = {p.stem: p for p in prep.glob('*.py') if p in trees}
    edges = {name: set() for name in prep_modules}
    for name, path in prep_modules.items():
        for node in ast.walk(trees[path]):
            if isinstance(node, ast.Import):
                edges[name].update(alias.name for alias in node.names
                                   if alias.name in prep_modules and alias.name != name)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module in prep_modules and node.module != name:
                    edges[name].add(node.module)
    # Tarjan SCC: list potential cycles only, do not fail CI on legacy debt.
    serial, stack, on_stack, index, low, cycles = 0, [], set(), {}, {}, []
    def visit(v):
        nonlocal serial
        index[v] = serial
        low[v] = serial
        serial += 1
        stack.append(v)
        on_stack.add(v)
        for w in sorted(edges[v]):
            if w not in index:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            component = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                component.append(w)
                if w == v:
                    break
            if len(component) > 1:
                cycles.append(sorted(component))
    for name in sorted(edges):
        if name not in index:
            visit(name)

    capabilities = []
    for cid, record in sorted(entries.items()):
        owner = root / record['owner']
        owner_stem = owner.stem
        symbol = record['entrypoint']
        matches = []
        for source, tree in trees.items():
            if source == owner:
                continue
            # A short module name is only unambiguous in its own directory.
            # Cross-package imports must use an explicit dotted path.
            owner_dot = '.'.join(owner.relative_to(root).with_suffix('').parts)
            functions, modules = set(), set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if ((node.module == owner_stem and source.parent == owner.parent)
                            or node.module == owner_dot):
                        functions.update(alias.asname or alias.name
                                         for alias in node.names if alias.name == symbol)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if ((alias.name == owner_stem and source.parent == owner.parent)
                                or alias.name == owner_dot):
                            modules.add(alias.asname or alias.name.split('.')[0])
            if not functions and not modules:
                continue
            lines = []
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                fn = node.func
                if isinstance(fn, ast.Name) and fn.id in functions:
                    lines.append(node.lineno)
                elif (isinstance(fn, ast.Attribute) and fn.attr == symbol
                      and isinstance(fn.value, ast.Name) and fn.value.id in modules):
                    lines.append(node.lineno)
            matches.append({'path': str(source.relative_to(root)),
                            'status': 'DIRECT_CALL_CANDIDATE' if lines else 'IMPORTED_ONLY',
                            'lines': sorted(set(lines))})
        capabilities.append({'id': cid, **record,
                             'consumers': sorted(matches, key=lambda x: x['path'])})
    return {'schema': 'AUTODRAW_CAPABILITY_STATIC_USAGE_V1',
            'evidence': 'E1_STATIC_ONLY',
            'source_files_scanned': len(trees),
            'catalog_count': count,
            'capabilities': capabilities,
            'preparation_module_count': len(prep_modules),
            'preparation_import_cycles': sorted(cycles),
            'limitations': ['imports in callbacks included',
                            'dynamic and reexported calls not resolved',
                            'name shadowing not resolved',
                            'cycles are static, not runtime execution traces']}
