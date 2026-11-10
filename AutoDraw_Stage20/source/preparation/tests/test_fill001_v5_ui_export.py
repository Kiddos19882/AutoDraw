"""Frozen V5 export remains non-executable and never overwrites earlier evidence."""
from __future__ import annotations

import json
from types import SimpleNamespace

from chalk_fill_ui import Fill001Tab


class Variable:
    def __init__(self, value=""):
        self.value = value
    def get(self):
        return self.value
    def set(self, value):
        self.value = value


def make_tab(tmp_path, candidate):
    tab = Fill001Tab.__new__(Fill001Tab)
    tab.output_dir = tmp_path
    tab.v5_candidate_var = Variable(candidate)
    tab.status_var = Variable()
    return tab


def test_v5_ui_export_pinned_two_brush_widths_and_no_automatic_run(tmp_path):
    tab = make_tab(tmp_path, "K_trim_0_y189_w3")
    tab.export_v5_source_plan()
    path = tmp_path / "v5_source_plans" / "K_trim_0_y189_w3.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    assert [int(x["metadata"]["brush_value"]) for x in document["strokes"]] == [10] * 28 + [3]
    assert document["generation"]["automatic_execution_allowed"] is False
    assert "сохранён" in tab.status_var.get()
    original = path.read_bytes()
    tab.export_v5_source_plan()
    assert path.read_bytes() == original
    assert "BLOCKED" in tab.status_var.get()


def test_v5_ui_rejects_unknown_candidate_without_creating_files(tmp_path):
    tab = make_tab(tmp_path, "K_trim_2_y190_w2")
    tab.export_v5_source_plan()
    assert "BLOCKED" in tab.status_var.get()
    assert not (tmp_path / "v5_source_plans").exists()
