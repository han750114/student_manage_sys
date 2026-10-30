"""Dated activity mapping shared by enrollment checks and weekly timetables."""
from copy import deepcopy
import unittest

from modules.timetable import build_timetable, find_free_slots, summarize_timetable
from tests.test_f2 import activity, make_data, period_times


class ActivityTimetableTests(unittest.TestCase):
    def setUp(self):
        self.data = make_data()
        self.data["activities"] = [activity()]
        self.times = period_times()

    def build(self, week="2026-10-26"):
        return build_timetable("S1", self.data, week, period_times=self.times)

    def test_activity_only_in_its_week(self):
        self.assertEqual(self.build()["data"][0][0]["kind"], "activity")
        self.assertTrue(all(c is None for row in self.build("2026-11-02")["data"] for c in row))

    def test_activity_requires_week_and_explicit_mapping(self):
        self.assertFalse(build_timetable("S1", self.data)["ok"])
        self.assertFalse(build_timetable("S1", self.data, "2026-10-26")["ok"])

    def test_other_students_activity_not_displayed(self):
        self.data["activities"][0]["participant_ids"] = ["S2"]
        self.assertIsNone(self.build()["data"][0][0])

    def test_cancelled_activity_not_displayed(self):
        self.data["activities"][0]["status"] = "cancelled"
        self.assertIsNone(self.build()["data"][0][0])

    def test_partial_overlap_occupies_period_and_blocks_free_run(self):
        self.data["activities"][0].update(start_time="08:30", end_time="09:20")
        grid = self.build()["data"]
        self.assertEqual(grid[0][0]["id"], "A1")
        self.assertEqual(grid[1][0]["id"], "A1")
        free = find_free_slots(grid, {"days": [1], "start_period": "1", "end_period": "3"})
        self.assertEqual(free["data"], [dict(day=1, start="3", end="3", length=1)])

    def test_adjacent_activity_does_not_occupy_previous_period(self):
        self.data["activities"][0].update(start_time="08:50", end_time="09:00")
        self.assertIsNone(self.build()["data"][0][0])
        self.assertIsNone(self.build()["data"][1][0])

    def test_course_activity_collision_reports_error_without_overwriting_course(self):
        self.data["enrollments"] = [dict(student_id="S1", course_id="C1")]
        result = self.build()
        self.assertFalse(result["ok"])
        self.assertEqual(result["data"][0][0]["id"], "C1")

    def test_summary_counts_classes_and_excludes_activity_from_gaps(self):
        self.data["courses"][0]["time_slots"] = [[1, "1"], [1, "4"]]
        self.data["enrollments"] = [dict(student_id="S1", course_id="C1")]
        self.data["activities"][0].update(start_time="09:00", end_time="09:50")
        grid = self.build()["data"]
        summary = summarize_timetable("S1", self.data, grid)["data"]
        self.assertEqual(summary["periods_per_day"][1], 2)
        self.assertEqual(summary["gaps_per_day"][1], 1)
        self.assertEqual(summary["weekly_credits"], 3)

    def test_invalid_date_week_and_cross_midnight_are_errors(self):
        for changes in ({"date": "bad"}, {"start_time": "23:00", "end_time": "01:00"}):
            self.data["activities"] = [activity(**changes)]
            self.assertFalse(self.build()["ok"])
        self.data["activities"] = [activity()]
        self.assertFalse(self.build("bad")["ok"])
        self.assertFalse(self.build("2026-10-27")["ok"])

    def test_mapping_must_cover_all_periods_in_order(self):
        for mapping in ({}, {"1": ("08:00", "09:00")},
                        {**self.times, "2": ("08:30", "09:30")}):
            self.times = mapping
            self.assertFalse(self.build()["ok"])

    def test_build_preserves_inputs_and_mapping(self):
        before = deepcopy((self.data, self.times))
        self.build()
        self.assertEqual((self.data, self.times), before)

    def test_nonoverlapping_activities_in_same_period_are_both_retained(self):
        self.data["activities"] = [activity(start_time="08:00", end_time="08:20"),
                                   activity(activity_id="A2", start_time="08:20", end_time="08:40")]
        result = self.build()
        self.assertTrue(result["ok"])
        self.assertEqual([c["id"] for c in result["data"][0][0]["items"]], ["A1", "A2"])

    def test_overlapping_activities_report_all_pairs(self):
        self.data["activities"] = [activity(activity_id=a) for a in ("A1", "A2", "A3")]
        result = self.build()
        self.assertFalse(result["ok"])
        self.assertEqual(len(result["errors"]), 3)
        self.assertEqual(len(result["data"][0][0]["items"]), 3)

    def test_week_includes_sunday_and_excludes_next_monday(self):
        self.data["activities"] = [activity(date="2026-11-01"),
                                   activity(activity_id="A2", date="2026-11-02")]
        grid = self.build()["data"]
        self.assertEqual(grid[0][6]["id"], "A1")
        self.assertIsNone(grid[0][0])

    def test_activity_id_does_not_match_course_query(self):
        from modules.timetable import find_course_slots
        self.assertEqual(find_course_slots(self.build()["data"], "A1")["data"], [])

    def test_invalid_records_and_queries_return_errors(self):
        for key, value in (("courses", [None]), ("enrollments", [{}]),
                           ("courses", [{"course_id": []}])):
            data = make_data()
            data[key] = value
            self.assertFalse(build_timetable("S1", data)["ok"])
        self.assertFalse(find_free_slots(self.build()["data"], [1])["ok"])


if __name__ == "__main__":
    unittest.main()
