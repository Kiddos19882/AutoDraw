"""Negative contracts for ENGINE-001 first-party quota/draw alignment."""
import unittest

from run_fill001_series_egret_replay import align_positive_quota_with_draw


def event(delta, x, t, stroke="stroke-1"):
    return {"strokeId": stroke, "pointDelta": delta, "acceptedPoint": {"x": x, "y": 5}, "t": t}


class QuotaAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.draws = [event(2, 20, 30), event(1, 30, 50)]
        self.quota = [event(1, 10, 10), event(1, 20, 30), event(1, 30, 50)]

    def test_two_accepted_events_recover_prior_point_without_interpolation(self):
        groups = align_positive_quota_with_draw(self.draws, self.quota)
        self.assertIsNotNone(groups)
        self.assertEqual([q["acceptedPoint"] for q in groups[0]],
                         [{"x": 10, "y": 5}, {"x": 20, "y": 5}])

    def test_reject_missing_quota_event(self):
        self.assertIsNone(align_positive_quota_with_draw(self.draws, self.quota[1:]))

    def test_reject_trailing_extra_quota_event(self):
        self.assertIsNone(align_positive_quota_with_draw(
            self.draws, self.quota + [event(1, 40, 60)]))

    def test_reject_last_accepted_point_mismatch(self):
        self.assertIsNone(align_positive_quota_with_draw(
            self.draws, [self.quota[0], event(1, 21, 30), self.quota[2]]))

    def test_reject_quota_event_after_draw_time(self):
        self.assertIsNone(align_positive_quota_with_draw(
            self.draws, [self.quota[0], event(1, 20, 31), self.quota[2]]))

    def test_reject_missing_coordinates(self):
        broken = dict(self.quota[0], acceptedPoint={"x": None, "y": 5})
        self.assertIsNone(align_positive_quota_with_draw(
            self.draws, [broken] + self.quota[1:]))

    def test_reject_nonfinite_draw_time(self):
        self.assertIsNone(align_positive_quota_with_draw(
            [dict(self.draws[0], t=float("nan")), self.draws[1]], self.quota))

    def test_aggregated_quota_not_individually_recoverable(self):
        # Alignment may hold but a delta=2 quota exposes only its final point.
        groups = align_positive_quota_with_draw(
            self.draws, [event(2, 20, 30), event(1, 30, 50)])
        self.assertIsNotNone(groups)
        self.assertEqual(len(groups[0]), 1)
        self.assertEqual(groups[0][0]["pointDelta"], 2)


if __name__ == "__main__":
    unittest.main()
