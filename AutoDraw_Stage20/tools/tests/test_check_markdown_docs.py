from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_markdown_docs import (check_links, decision_duplicates, github_slug,
                                 heading_anchors, markdown_links, git_blob_sha,
                                 verify_history)

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

if __name__ == '__main__':
    unittest.main()
