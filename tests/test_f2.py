"""F2 regression tests using the persisted F1 schema and isolated fixtures."""
from copy import deepcopy
import unittest

from modules.conflicts import F2CourseChecker, add_enrollment, check_enrollment


def make_data():
    """Return two independent rooms/courses and students with no selections."""
    return {
        "students": [dict(student_id=s, name=s, department="CS", max_credits=6)
                     for s in ("S1", "S2")],
        "courses": [dict(course_id=c, name=c, credits=3, course_type="必修",
                         teacher="Teacher", capacity=1, classroom=r,
                         time_slots=[[1, "1"]])
                    for c, r in (("C1", "R1"), ("C2", "R2"))],
        "classrooms": [dict(classroom_id=r, capacity=30) for r in ("R1", "R2")],
        "enrollments": [],
        "activities": [],
    }


def period_times():
    """Explicit synthetic test times; these are not a school timetable."""
    return {p: (f"{8 + i:02d}:00", f"{8 + i:02d}:50")
            for i, p in enumerate("123456789abc")}


def activity(**changes):
    """Return a Monday activity matching period 1 in the test mapping."""
    row = dict(activity_id="A1", name="Study", date="2026-10-26",
               start_time="08:00", end_time="08:50", classroom_id="R2",
               participant_ids=["S1"], status="scheduled")
    row.update(changes)
    return row


class TestF2CourseChecker(unittest.TestCase):
    def setUp(self):
        self.data = make_data()

    def check(self, **kwargs):
        return check_enrollment("S1", "C2", self.data, **kwargs)

    # Normal cases.
    def test_successful_check_does_not_claim_saved_selection(self):
        result = self.check()
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["future_credits"], 3)
        self.assertEqual(self.data["enrollments"], [])

    def test_add_returns_independent_enrollment_list(self):
        result = add_enrollment("S1", "C2", self.data)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"], [{"student_id": "S1", "course_id": "C2"}])
        self.assertEqual(self.data["enrollments"], [])

    def test_checker_wrapper_uses_explicit_enrollments(self):
        checker = F2CourseChecker(self.data["students"], self.data["courses"],
                                  self.data["classrooms"], self.data["enrollments"])
        ok, message = checker.check_course_selection("S1", "C2")
        self.assertTrue(ok)
        self.assertIn("檢查通過", message)

    def test_constructor_and_check_preserve_all_inputs(self):
        before = deepcopy(self.data)
        checker = F2CourseChecker(self.data["students"], self.data["courses"],
                                  self.data["classrooms"], self.data["enrollments"])
        checker.check_course_selection("S1", "C2")
        self.assertEqual(self.data, before)

    # Boundary cases.
    def test_exact_credit_limit_is_allowed(self):
        self.data["enrollments"] = [dict(student_id="S1", course_id="C1")]
        self.data["courses"][1]["time_slots"] = [[1, "2"]]
        self.assertTrue(self.check()["ok"])
        self.assertEqual(self.check()["data"]["future_credits"], 6)

    def test_last_seat_is_allowed(self):
        self.data["courses"][1]["capacity"] = 2
        self.data["enrollments"] = [dict(student_id="S2", course_id="C2")]
        self.assertTrue(self.check()["ok"])

    def test_sunday_last_period(self):
        self.data["courses"][1]["time_slots"] = [[7, "c"]]
        self.assertTrue(self.check()["ok"])

    def test_adjacent_course_periods_do_not_conflict(self):
        self.data["enrollments"] = [dict(student_id="S1", course_id="C1")]
        self.data["courses"][1]["time_slots"] = [[1, "2"]]
        self.assertTrue(self.check()["ok"])

    def test_adjacent_activity_end_does_not_conflict(self):
        self.data["activities"] = [activity(start_time="07:30", end_time="08:00")]
        self.assertTrue(self.check(period_times=period_times())["ok"])

    def test_cancelled_activity_does_not_conflict(self):
        self.data["activities"] = [activity(status="cancelled")]
        self.assertTrue(self.check()["ok"])

    def test_same_period_different_weekday_is_allowed(self):
        self.data["enrollments"] = [dict(student_id="S1", course_id="C1")]
        self.data["courses"][1]["time_slots"] = [[2, "1"]]
        self.assertTrue(self.check()["ok"])

    def test_zero_current_credits(self):
        self.assertEqual(self.check()["data"]["current_credits"], 0)

    def test_multiple_meetings_count_course_credits_once(self):
        self.data["courses"][1]["time_slots"] = [[1, "1"], [3, "a"]]
        self.assertEqual(self.check()["data"]["future_credits"], 3)

    def test_course_with_no_other_students_has_all_seats(self):
        self.assertEqual(self.check()["data"]["remaining_seats"], 1)

    # Error and conflict cases.
    def test_enrollments_drive_all_three_restrictions(self):
        self.data["students"][0]["max_credits"] = 3
        self.data["enrollments"] = [dict(student_id="S1", course_id="C1"),
                                     dict(student_id="S2", course_id="C2")]
        before = deepcopy(self.data)
        result = self.check()
        self.assertFalse(result["ok"])
        self.assertEqual({c["type"] for c in result["data"]["conflicts"]},
                         {"capacity", "credit", "student"})
        self.assertEqual(self.data, before)

    def test_same_slot_reports_every_course(self):
        third = deepcopy(self.data["courses"][0])
        third.update(course_id="C3", name="C3")
        self.data["courses"].append(third)
        self.data["students"][0]["max_credits"] = 9
        self.data["enrollments"] = [dict(student_id="S1", course_id=c) for c in ("C1", "C3")]
        conflicts = self.check()["data"]["conflicts"]
        self.assertEqual({c["id"] for c in conflicts if c["type"] == "student"}, {"C1", "C3"})

    def test_room_conflict_without_student_overlap(self):
        self.data["courses"][1]["classroom"] = "R1"
        result = self.check()
        self.assertFalse(result["ok"])
        self.assertEqual(result["data"]["conflicts"][0]["type"], "room")

    def test_same_room_slot_reports_all_occupying_courses(self):
        third = deepcopy(self.data["courses"][0])
        third.update(course_id="C3", name="C3")
        self.data["courses"].append(third)
        self.data["courses"][1]["classroom"] = "R1"
        conflicts = self.check()["data"]["conflicts"]
        self.assertEqual({c["id"] for c in conflicts if c["type"] == "room"}, {"C1", "C3"})

    def test_course_and_activity_same_slot_are_both_reported(self):
        self.data["enrollments"] = [dict(student_id="S1", course_id="C1")]
        self.data["activities"] = [activity()]
        conflicts = self.check(period_times=period_times())["data"]["conflicts"]
        self.assertEqual({c["type"] for c in conflicts}, {"student", "activity", "room_activity"})

    def test_activity_reports_student_and_room_conflicts(self):
        self.data["activities"] = [activity()]
        result = self.check(period_times=period_times())
        self.assertFalse(result["ok"])
        self.assertEqual({c["type"] for c in result["data"]["conflicts"]},
                         {"activity", "room_activity"})

    def test_duplicate_selection_is_rejected_without_changes(self):
        self.data["enrollments"] = [dict(student_id="S1", course_id="C2")]
        before = deepcopy(self.data)
        self.assertFalse(add_enrollment("S1", "C2", self.data)["ok"])
        self.assertEqual(self.data, before)

    def test_unknown_student_and_course(self):
        for student, course in (("UNKNOWN", "C2"), ("S1", "UNKNOWN")):
            self.assertFalse(check_enrollment(student, course, self.data)["ok"])

    def test_invalid_course_reports_error(self):
        self.data["courses"][1]["time_slots"] = [[1, []]]
        self.assertFalse(self.check()["ok"])

    def test_dangling_enrollment_reports_error(self):
        self.data["enrollments"] = [dict(student_id="S1", course_id="UNKNOWN")]
        self.assertFalse(self.check()["ok"])

    def test_missing_enrollment_store_is_rejected(self):
        del self.data["enrollments"]
        self.assertFalse(self.check()["ok"])

    def test_active_activity_requires_explicit_period_times(self):
        self.data["activities"] = [activity()]
        self.assertFalse(self.check()["ok"])

    def test_invalid_activity_does_not_raise(self):
        self.data["activities"] = [activity(date="invalid")]
        self.assertFalse(self.check(period_times=period_times())["ok"])

    def test_conflicts_sort_by_day_then_custom_period_order(self):
        self.data["courses"][0]["time_slots"] = [[7, "c"], [1, "a"], [1, "9"]]
        self.data["courses"][1]["time_slots"] = [[7, "c"], [1, "a"], [1, "9"]]
        self.data["enrollments"] = [dict(student_id="S1", course_id="C1")]
        conflicts = self.check()["data"]["conflicts"]
        self.assertEqual([(c["day"], c["period"]) for c in conflicts],
                         [(1, "9"), (1, "a"), (7, "c")])


if __name__ == "__main__":
    unittest.main()
