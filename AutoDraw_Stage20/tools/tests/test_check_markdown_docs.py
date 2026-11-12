from __future__ import annotations
import json
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_markdown_docs import (main, check_links, decision_duplicates, github_slug,
                                 heading_anchors, markdown_links, git_blob_sha,
                                 verify_history, check_capability_catalog, find_capabilities,
                                 inspect_capability_consumers)

class MarkdownIntegrityTests(unittest.TestCase):
    def test_slug_and_duplicate_headings(self):
        self.assertEqual(
            github_slug('3. Кандидатный корпус 81 реального изображения (OFFLINE ONLY)'),
            '3-кандидатный-корпус-81-реального-изображения-offline-only')
        self.assertEqual(github_slug('A — B'), 'a--b')
        self.assertIn('старый-якорь', heading_anchors('<a id="старый-якорь"></a>'))
        self.assertEqual(heading_anchors('# Title\n## Раздел\n## Раздел'),
                         {'title', 'раздел', 'раздел-1'})

    def test_markdown_target_and_anchor(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            d = root / 'docs'
            d.mkdir()
            a, b = d / 'README.md', d / 'TASKS.md'
            a.write_text('# Index\n[ok](TASKS.md#раздел)\n[bad](TASKS.md#absent)\n',
                         encoding='utf-8')
            b.write_text('# Title\n## Раздел\n', encoding='utf-8')
            problems, missing = check_links(root, [a, b])
            self.assertEqual(len(problems), 1)
            self.assertEqual(problems[0]['error'], 'missing_fragment')
            self.assertEqual(missing, ['docs/README.md'])

    def test_skip_code_fences(self):
        fence = chr(96) * 3
        content = fence + 'md\n[bad](missing.md)\n' + fence + '\n[good](README.md)'
        self.assertEqual(list(markdown_links(content)), [(4, 'README.md')])

    def test_decision_ids(self):
        self.assertEqual(decision_duplicates(
            '## DEC-016. ROI\n## DEC-016. Knowledge\n## DEC-027. Extra\n'), ['016'])
        self.assertEqual(decision_duplicates(
            '## DEC-016. ROI\n## DEC-027. Knowledge\n'), [])

    def test_snapshot_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            docs = root / 'docs'
            docs.mkdir()
            payload = b'# Historic\n'
            (docs / 'old.md').write_bytes(payload)
            (docs / 'HISTORY_SNAPSHOT_PROVENANCE.json').write_text(
                json.dumps({'snapshots': [
                    {'archive': 'docs/old.md', 'git_blob_sha': git_blob_sha(payload)}
                ]}), encoding='utf-8')
            self.assertEqual(verify_history(root), [])
            (docs / 'old.md').write_bytes(b'Changed!')
            self.assertEqual(verify_history(root)[0]['error'], 'snapshot_changed')


    def test_capability_catalog_ast_contract_and_no_imports(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'docs').mkdir()
            (root / 'source').mkdir()
            (root / 'tests').mkdir()
            (root / 'source' / 'demo.py').write_text(
                'def existing(value, *, safe=True):\n    return value\n',
                encoding='utf-8')
            (root / 'tests' / 'test_demo.py').write_text(
                'def test_smoke():\n    assert True\n', encoding='utf-8')
            row = ('| CAP-001 | найти существующий код | `source/demo.py` | '
                   '`existing` | `value,safe` | shared | только E1 | '
                   '`tests/test_demo.py` |')
            doc = ('<!-- AUTODRAW_CAPABILITIES_START -->\n'
                   + row + '\n<!-- AUTODRAW_CAPABILITIES_END -->\n')
            catalog = root / 'docs' / 'COMPONENT_CATALOG.md'
            catalog.write_text(doc, encoding='utf-8')
            self.assertEqual(check_capability_catalog(root), ([], 1))
            self.assertEqual(find_capabilities(root, 'найти существующий код')[0]['id'], 'CAP-001')
            self.assertEqual(find_capabilities(root, 'слова без совпадений'), [])
            with self.assertRaises(ValueError):
                find_capabilities(root, '')
            catalog.write_text(doc.replace('value,safe', 'value,missing'),
                               encoding='utf-8')
            errors, n = check_capability_catalog(root)
            self.assertEqual(n, 1)
            self.assertIn('missing_contract_arguments', [e['error'] for e in errors])
            catalog.write_text(doc.replace('source/demo.py', '../outside.py'),
                               encoding='utf-8')
            errors, _ = check_capability_catalog(root)
            self.assertIn('invalid_owner', [e['error'] for e in errors])
            catalog.write_text(doc.replace('<!-- AUTODRAW_CAPABILITIES_END -->',
                                           row + '\n<!-- AUTODRAW_CAPABILITIES_END -->'),
                               encoding='utf-8')
            errors, _ = check_capability_catalog(root)
            self.assertIn('invalid_or_duplicate_id', [e['error'] for e in errors])

    def test_catalog_absent_is_not_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            errors, total = check_capability_catalog(Path(temp))
            self.assertEqual(total, 0)
            self.assertEqual(errors[0]['error'], 'missing_catalog')


    def test_actual_catalog_finds_five_reuse_tasks(self):
        root = Path(__file__).resolve().parents[2]
        cases = (
            ('очистить доску', 'CAP-007'),
            ('Selenium Firefox', 'CAP-001'),
            ('точный CHALK', 'CAP-015'),
            ('owner lock', 'CAP-018'),
            ('расход краски', 'CAP-015'),
        )
        for query, expected in cases:
            with self.subTest(query=query):
                found = find_capabilities(root, query)
                self.assertTrue(found)
                self.assertEqual(found[0]['id'], expected)
                self.assertEqual(found[0]['evidence'], 'E1_CANDIDATE_ONLY')



    def test_usage_finds_aliased_and_nested_imports_and_static_cycle(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            prep = root / 'source' / 'preparation'
            tests = prep / 'tests'
            docs = root / 'docs'
            tests.mkdir(parents=True)
            docs.mkdir()
            (prep / 'owner.py').write_text(
                'from consumer import helper\n'
                'def existing(value):\n    return value\n', encoding='utf-8')
            (prep / 'consumer.py').write_text(
                'from owner import existing as renamed\n'
                'def helper():\n    return renamed(1)\n', encoding='utf-8')
            (prep / 'module_user.py').write_text(
                'def use():\n'
                '    import owner as alias\n'
                '    return alias.existing(2)\n', encoding='utf-8')
            (prep / 'unused.py').write_text(
                'from owner import existing\n'
                'def no_call():\n    return 3\n', encoding='utf-8')
            (tests / 'test_owner.py').write_text(
                'def test_thing():\n    pass\n', encoding='utf-8')
            (docs / 'COMPONENT_CATALOG.md').write_text(
                '<!-- AUTODRAW_CAPABILITIES_START -->\n'
                '| CAP-001 | Existing | `source/preparation/owner.py` | '
                '`existing` | `value` | shared | E1 only | '
                '`source/preparation/tests/test_owner.py` |\n'
                '<!-- AUTODRAW_CAPABILITIES_END -->\n', encoding='utf-8')
            result = inspect_capability_consumers(root)
            self.assertEqual(result['catalog_count'], 1)
            self.assertEqual(result['source_files_scanned'], 4)
            self.assertEqual(result['preparation_import_cycles'], [
                ['consumer', 'owner']])
            self.assertEqual(result['preparation_root_import_cycles'], [
                ['consumer', 'owner']])
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['--root', str(root), '--usage']), 1)
            hits = {x['path']: x for x in result['capabilities'][0]['consumers']}
            self.assertEqual(hits['source/preparation/consumer.py']['lines'], [3])
            self.assertEqual(hits['source/preparation/module_user.py']['lines'], [3])
            self.assertEqual(hits['source/preparation/unused.py']['status'],
                             'IMPORTED_ONLY')
            (prep / 'unused.py').write_text('def broken(:\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Cannot complete source AST'):
                inspect_capability_consumers(root)

    def test_cross_domain_bare_imports_only_in_known_entrypoints(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            prep = root / 'source' / 'preparation'
            executor = root / 'source' / 'executor'
            unrelated = root / 'source' / 'other'
            docs = root / 'docs'
            tests = prep / 'tests'
            for folder in (executor, unrelated, docs, tests):
                folder.mkdir(parents=True, exist_ok=True)
            newline = chr(10)
            (prep / 'owner.py').write_text(
                newline.join(('def action(value):', '    return value', '')),
                encoding='utf-8')
            (tests / 'test_owner.py').write_text(
                newline.join(('def test_owner():', '    pass', '')),
                encoding='utf-8')
            (root / 'integrated_app.py').write_text(
                newline.join(('from owner import action as run', 'run(1)', '')),
                encoding='utf-8')
            (executor / 'stage6_execute_plan.py').write_text(
                newline.join(('def execute():', '    import owner as module',
                              '    return module.action(2)', '')),
                encoding='utf-8')
            (unrelated / 'decoy.py').write_text(
                newline.join(('from owner import action', 'action(3)', '')),
                encoding='utf-8')
            (docs / 'COMPONENT_CATALOG.md').write_text(
                newline.join((
                    '<!-- AUTODRAW_CAPABILITIES_START -->',
                    '| CAP-001 | act | `source/preparation/owner.py` | '
                    '`action` | `value` | shared | E1 | '
                    '`source/preparation/tests/test_owner.py` |',
                    '<!-- AUTODRAW_CAPABILITIES_END -->',
                    '',
                )), encoding='utf-8')
            result = inspect_capability_consumers(root)
            self.assertEqual(result['source_files_scanned'], 4)
            matches = {x['path']: x for x in result['capabilities'][0]['consumers']}
            self.assertEqual(matches['integrated_app.py']['lines'], [2])
            self.assertEqual(matches['source/executor/stage6_execute_plan.py']['lines'], [3])
            self.assertNotIn('source/other/decoy.py', matches)
            self.assertEqual(result['preparation_root_import_cycles'], [])

    def test_actual_catalog_usage_is_structural_only(self):
        root = Path(__file__).resolve().parents[2]
        report = inspect_capability_consumers(root)
        self.assertEqual(report['catalog_count'], 20)
        self.assertEqual(report['evidence'], 'E1_STATIC_ONLY')
        self.assertEqual(report['preparation_root_import_cycles'], [])
        self.assertGreaterEqual(report['source_files_scanned'], 130)
        capabilities = {x['id']: x for x in report['capabilities']}
        self.assertTrue(any(
            x['path'] == 'integrated_app.py' and x['lines']
            for x in capabilities['CAP-009']['consumers']))
        for cid in ('CAP-012', 'CAP-013'):
            self.assertTrue(any(
                x['path'] == 'source/executor/stage6_execute_plan.py' and x['lines']
                for x in capabilities[cid]['consumers']))
        self.assertTrue(any(
            x['path'] == 'source/preparation/chalk_fill_ui.py'
            and x['status'] == 'DIRECT_CALL_CANDIDATE'
            for x in capabilities['CAP-007']['consumers']))
        self.assertTrue(any(
            x['path'] == 'source/preparation/fill001_series_stage6_execution.py'
            for x in capabilities['CAP-015']['consumers']))


if __name__ == '__main__':
    unittest.main()
