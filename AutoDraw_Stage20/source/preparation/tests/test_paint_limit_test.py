from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from palette_detection import create_palette_document
from palette_profiles import create_palette_profile, validate_palette_profile
from paint_limit_test import (
    PaintLimitTestError,
    STROKE_LENGTH_SCENARIOS,
    analyze_paint_limit_pair,
    analyze_paint_limit_series,
    append_paint_limit_observation,
    build_paint_limit_test_plan,
    make_paint_limit_observation,
)


def make_profile() -> dict:
    document = create_palette_document(
        [{
            "name": "Red",
            "hex": "#FF0000",
            "rgb": [255, 0, 0],
            "screen_x": 110,
            "screen_y": 110,
            "local_x": 10,
            "local_y": 10,
            "source": "manual",
        }],
        screen_size=(1920, 1080),
        region={"x": 100, "y": 100, "width": 40, "height": 40},
    )
    profile = create_palette_profile(document, "Paint limit test", dpi_scale_percent=100)
    profile["colors"][0]["status"] = "confirmed"
    return validate_palette_profile(profile)


class PaintLimitTestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = make_profile()

    def build(self, scenario_id: str, **kwargs):
        return build_paint_limit_test_plan(
            self.profile,
            canvas_width=512,
            canvas_height=288,
            color_hex="#FF0000",
            scenario_id=scenario_id,
            **kwargs,
        )

    def test_scenarios_match_total_length_but_have_different_stroke_counts(self):
        a = self.build("few_long")
        b = self.build("many_short")
        test_a = a["source"]["paint_limit_test"]
        test_b = b["source"]["paint_limit_test"]
        self.assertEqual(test_a["stroke_count"], 10)
        self.assertEqual(test_b["stroke_count"], 80)
        self.assertEqual(test_a["planned_total_drawing_length_px"], 800)
        self.assertEqual(test_b["planned_total_drawing_length_px"], 800)
        self.assertEqual(test_a["stroke_length_px"], 80)
        self.assertEqual(test_b["stroke_length_px"], 10)

    def build_length(self, scenario_id: str, **kwargs):
        total_length = kwargs.pop("target_total_drawing_length_px", 26000)
        return build_paint_limit_test_plan(
            self.profile,
            canvas_width=660,
            canvas_height=340,
            color_hex="#FF0000",
            scenario_id=scenario_id,
            target_total_drawing_length_px=total_length,
            **kwargs,
        )

    def test_fixed_length_scenarios_fit_660x340_and_have_equal_26000px_paths(self):
        expected = {"length_650": (40, 650), "length_200": (130, 200), "length_50": (520, 50), "length_10": (2600, 10)}
        for scenario_id, (count, length) in expected.items():
            with self.subTest(scenario=scenario_id):
                plan = self.build_length(scenario_id)
                test = plan["source"]["paint_limit_test"]
                self.assertEqual(test["stroke_count"], count)
                self.assertEqual(test["stroke_length_px"], length)
                self.assertEqual(test["planned_total_drawing_length_px"], 26000)
                self.assertEqual(plan["canvas"], {"width": 660, "height": 340})
                self.assertLessEqual(max(test["row_y_positions"]), 339)
                all_points = [point for stroke in plan["strokes"] for point in stroke["points"]]
                self.assertGreaterEqual(min(point["x"] for point in all_points), 0)
                self.assertLessEqual(max(point["x"] for point in all_points), 659)
                self.assertGreaterEqual(min(point["y"] for point in all_points), 0)
                self.assertLessEqual(max(point["y"] for point in all_points), 339)
                self.assertEqual(plan["summary"]["drawing_length_px"], 26000)
                self.assertEqual(plan["summary"]["stroke_count"], count)

    def test_all_current_scenarios_fit_at_largest_ui_row_spacing(self):
        for scenario_id in ("length_650", "length_200", "length_50", "length_10"):
            with self.subTest(scenario=scenario_id):
                plan = self.build_length(scenario_id, row_spacing_px=6)
                test = plan["source"]["paint_limit_test"]
                self.assertLessEqual(max(test["row_y_positions"]), 339)
                self.assertEqual(test["planned_total_drawing_length_px"], 26000)

    def test_fixed_length_segments_follow_scanline_order(self):
        plan = self.build_length("length_10")
        locations = [(int(stroke["points"][0]["y"]), int(stroke["points"][0]["x"])) for stroke in plan["strokes"]]
        self.assertEqual(locations, sorted(locations))
        self.assertEqual(len(locations), 2600)
        # Segments on the same row have a transparent gap and stay distinct.
        first_row = [x for y, x in locations if y == locations[0][0]]
        self.assertGreaterEqual(len(first_row), 2)
        self.assertGreater(first_row[1], first_row[0] + 10)

    def test_fixed_length_scenario_requires_exact_divisor(self):
        with self.assertRaisesRegex(PaintLimitTestError, "делиться на неё без остатка"):
            self.build_length("length_650", target_total_drawing_length_px=26010)

    def test_rejects_test_area_above_game_limit(self):
        with self.assertRaisesRegex(PaintLimitTestError, "не может превышать 660 × 340"):
            build_paint_limit_test_plan(
                self.profile, canvas_width=661, canvas_height=340, color_hex="#FF0000",
                scenario_id="length_650", target_total_drawing_length_px=26000,
            )
        with self.assertRaisesRegex(PaintLimitTestError, "не может превышать 660 × 340"):
            build_paint_limit_test_plan(
                self.profile, canvas_width=660, canvas_height=341, color_hex="#FF0000",
                scenario_id="length_650", target_total_drawing_length_px=26000,
            )

    def test_fixed_length_long_stroke_must_fit_canvas_width(self):
        with self.assertRaisesRegex(PaintLimitTestError, "доступно не более"):
            build_paint_limit_test_plan(
                self.profile, canvas_width=512, canvas_height=180, color_hex="#FF0000",
                scenario_id="length_650", target_total_drawing_length_px=26000,
            )

    def test_series_analysis_detects_short_stroke_overhead_signal(self):
        records = [
            {"experiment_id": "S1", "scenario_id": "length_650", "profile_name": "P", "color_hex": "#FF0000",
             "fresh_supply_confirmed": True, "outcome": "all_visible", "last_visible_strokes": 40,
             "stroke_length_px": 650, "planned_strokes": 40, "estimated_visible_path_length_px": 26000,
             "planned_path_length_px": 26000, "target_total_drawing_length_px": 26000},
            {"experiment_id": "S1", "scenario_id": "length_10", "profile_name": "P", "color_hex": "#FF0000",
             "fresh_supply_confirmed": True, "outcome": "partial", "last_visible_strokes": 1800,
             "stroke_length_px": 10, "planned_strokes": 2600, "estimated_visible_path_length_px": 18000,
             "planned_path_length_px": 26000, "target_total_drawing_length_px": 26000},
        ]
        self.assertIn("дополнительный расход", analyze_paint_limit_series(records, "S1"))

    def test_series_analysis_requires_at_least_two_scenarios(self):
        self.assertIn("нужны хотя бы два варианта", analyze_paint_limit_series([], "S2"))

    def test_series_analysis_rejects_different_total_paths(self):
        records = [
            {"experiment_id": "S3", "scenario_id": "length_650", "profile_name": "P", "color_hex": "#FF0000",
             "fresh_supply_confirmed": True, "outcome": "partial", "last_visible_strokes": 20,
             "stroke_length_px": 650, "planned_strokes": 40, "estimated_visible_path_length_px": 13000,
             "planned_path_length_px": 26000, "target_total_drawing_length_px": 26000},
            {"experiment_id": "S3", "scenario_id": "length_10", "profile_name": "P", "color_hex": "#FF0000",
             "fresh_supply_confirmed": True, "outcome": "partial", "last_visible_strokes": 1000,
             "stroke_length_px": 10, "planned_strokes": 2600, "estimated_visible_path_length_px": 10000,
             "planned_path_length_px": 23000, "target_total_drawing_length_px": 23000},
        ]
        self.assertIn("различается суммарная длина", analyze_paint_limit_series(records, "S3"))

    def test_series_analysis_detects_similar_path_thresholds(self):
        records = [
            {"experiment_id": "S4", "scenario_id": "length_650", "profile_name": "P", "color_hex": "#FF0000",
             "fresh_supply_confirmed": True, "outcome": "partial", "last_visible_strokes": 24,
             "stroke_length_px": 650, "planned_strokes": 40, "estimated_visible_path_length_px": 15600,
             "planned_path_length_px": 26000, "target_total_drawing_length_px": 26000},
            {"experiment_id": "S4", "scenario_id": "length_200", "profile_name": "P", "color_hex": "#FF0000",
             "fresh_supply_confirmed": True, "outcome": "partial", "last_visible_strokes": 79,
             "stroke_length_px": 200, "planned_strokes": 130, "estimated_visible_path_length_px": 15800,
             "planned_path_length_px": 26000, "target_total_drawing_length_px": 26000},
        ]
        self.assertIn("вероятно, доминирует расход на длину", analyze_paint_limit_series(records, "S4"))

    def test_plan_uses_single_confirmed_color_and_maintains_top_to_bottom_order(self):
        plan = self.build("many_short")
        self.assertEqual({stroke["color"]["hex"] for stroke in plan["strokes"]}, {"#FF0000"})
        rows = [int(stroke["points"][0]["y"]) for stroke in plan["strokes"]]
        self.assertEqual(rows, sorted(rows))
        self.assertEqual(len(rows), len(set(rows)))
        self.assertEqual(plan["summary"]["stroke_count"], 80)

    def test_plan_records_experiment_metadata(self):
        plan = self.build("few_long", experiment_id="AB12")
        test = plan["source"]["paint_limit_test"]
        self.assertEqual(test["experiment_id"], "AB12")
        self.assertEqual(test["color_hex"], "#FF0000")
        self.assertEqual(test["row_spacing_px"], 3)

    def test_rejects_unconfirmed_color(self):
        self.profile["colors"][0]["status"] = "detected"
        with self.assertRaisesRegex(PaintLimitTestError, "ещё не подтверждён"):
            self.build("few_long")

    def test_rejects_unknown_color(self):
        with self.assertRaisesRegex(PaintLimitTestError, "отсутствует"):
            build_paint_limit_test_plan(
                self.profile, canvas_width=512, canvas_height=288, color_hex="#00FF00", scenario_id="few_long"
            )

    def test_rejects_total_path_shorter_than_800_px(self):
        with self.assertRaisesRegex(PaintLimitTestError, "800"):
            self.build("few_long", target_total_drawing_length_px=720)

    def test_requires_total_path_multiple_of_80_for_exact_ab_comparison(self):
        with self.assertRaisesRegex(PaintLimitTestError, "кратна 80"):
            self.build("many_short", target_total_drawing_length_px=1000)

    def test_rejects_canvas_too_short_for_many_short_strokes(self):
        with self.assertRaisesRegex(PaintLimitTestError, "требует 80 строк"):
            build_paint_limit_test_plan(
                self.profile, canvas_width=100, canvas_height=80, color_hex="#FF0000", scenario_id="many_short"
            )

    def test_rejects_line_that_does_not_fit_width(self):
        with self.assertRaisesRegex(PaintLimitTestError, "доступно не более"):
            build_paint_limit_test_plan(
                self.profile,
                canvas_width=80,
                canvas_height=100,
                color_hex="#FF0000",
                scenario_id="few_long",
                target_total_drawing_length_px=800,
            )

    def test_record_all_visible_requires_comparable_supply_confirmation(self):
        plan = self.build("few_long")
        with self.assertRaisesRegex(PaintLimitTestError, "подтвердите"):
            make_paint_limit_observation(plan, outcome="all_visible", fresh_supply_confirmed=False)
        record = make_paint_limit_observation(plan, outcome="all_visible", fresh_supply_confirmed=True)
        self.assertEqual(record["last_visible_strokes"], 10)
        self.assertEqual(record["estimated_visible_path_length_px"], 800)
        self.assertEqual(record["outcome"], "all_visible")

    def test_record_partial_result_calculates_path_length_and_first_missing_stroke(self):
        plan = self.build("many_short")
        record = make_paint_limit_observation(
            plan, outcome="partial", last_visible_strokes=37, fresh_supply_confirmed=True, notes="visible until row 37"
        )
        self.assertEqual(record["last_visible_strokes"], 37)
        self.assertEqual(record["first_missing_stroke"], 38)
        self.assertEqual(record["estimated_visible_path_length_px"], 370)
        self.assertEqual(record["notes"], "visible until row 37")

    def test_rejects_invalid_partial_count(self):
        plan = self.build("few_long")
        with self.assertRaises(PaintLimitTestError):
            make_paint_limit_observation(plan, outcome="partial", last_visible_strokes=10, fresh_supply_confirmed=True)

    def test_appends_observations_atomically_and_preserves_prior_records(self):
        plan = self.build("few_long", experiment_id="AB12")
        record = make_paint_limit_observation(plan, outcome="all_visible", fresh_supply_confirmed=True)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "observations.json"
            append_paint_limit_observation(path, record)
            append_paint_limit_observation(path, {**record, "scenario_id": "many_short"})
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(payload["records"]), 2)
        self.assertFalse(list(Path(temp).glob("*.tmp")))

    def test_pair_analysis_suspects_stroke_limit_when_short_stroke_run_fails_first(self):
        records = [
            {"experiment_id": "X1", "scenario_id": "few_long", "profile_name": "P", "color_hex": "#FF0000",
             "fresh_supply_confirmed": True, "outcome": "all_visible", "last_visible_strokes": 10,
             "estimated_visible_path_length_px": 800, "planned_path_length_px": 800},
            {"experiment_id": "X1", "scenario_id": "many_short", "profile_name": "P", "color_hex": "#FF0000",
             "fresh_supply_confirmed": True, "outcome": "partial", "last_visible_strokes": 41,
             "estimated_visible_path_length_px": 410, "planned_path_length_px": 800},
        ]
        result = analyze_paint_limit_pair(records, "X1")
        self.assertIn("ограничение числом штрихов", result)

    def test_pair_analysis_suspects_length_limit_when_cutoff_paths_match(self):
        records = [
            {"experiment_id": "X2", "scenario_id": "few_long", "profile_name": "P", "color_hex": "#FF0000",
             "fresh_supply_confirmed": True, "outcome": "partial", "last_visible_strokes": 5,
             "estimated_visible_path_length_px": 400, "planned_path_length_px": 800},
            {"experiment_id": "X2", "scenario_id": "many_short", "profile_name": "P", "color_hex": "#FF0000",
             "fresh_supply_confirmed": True, "outcome": "partial", "last_visible_strokes": 39,
             "estimated_visible_path_length_px": 390, "planned_path_length_px": 800},
        ]
        result = analyze_paint_limit_pair(records, "X2")
        self.assertIn("лимит длины пути", result)

    def test_pair_analysis_does_not_misclassify_no_visible_color_as_a_paint_limit(self):
        records = [
            {"experiment_id": "X3", "scenario_id": "few_long", "profile_name": "P", "color_hex": "#FF0000",
             "fresh_supply_confirmed": True, "outcome": "none_visible", "last_visible_strokes": 0,
             "estimated_visible_path_length_px": 0, "planned_path_length_px": 800,
             "target_total_drawing_length_px": 800, "row_spacing_px": 3},
            {"experiment_id": "X3", "scenario_id": "many_short", "profile_name": "P", "color_hex": "#FF0000",
             "fresh_supply_confirmed": True, "outcome": "all_visible", "last_visible_strokes": 80,
             "estimated_visible_path_length_px": 800, "planned_path_length_px": 800,
             "target_total_drawing_length_px": 800, "row_spacing_px": 3},
        ]
        result = analyze_paint_limit_pair(records, "X3")
        self.assertIn("нельзя уверенно считать лимитом краски", result)

    def test_pair_analysis_requires_both_scenarios(self):
        self.assertIn("нужны оба результата", analyze_paint_limit_pair([], "none").lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
