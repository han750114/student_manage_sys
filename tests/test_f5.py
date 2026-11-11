"""F5 tests for modules/course_filter.py using isolated in-memory fixtures.

No file under data/ is read or written. Test data uses the persisted F1 schema
(time_slots, course_type, classroom, max_credits). Period labels are the
strings 1-9, a, b, c; weekdays are integers 1-7.
"""
from copy import deepcopy
import unittest

from modules.course_filter import (
    check_course_feasibility,
    check_credit_range,
    filter_courses,
    validate_preferences,
)


def make_courses():
    """Return five courses in five different rooms.

    C1 必修 3cr Mon 1-2 (capacity 2)
    C2 選修 3cr Tue 3   (capacity 1, easy to fill)
    C3 選修 2cr Wed c   (capacity 30)
    C4 選修 3cr Mon 2   (overlaps C1 on Mon period 2, different room)
    C5 選修 1cr Sun c   (capacity 30, boundary weekday and period)
    """
    def course(cid, credits, kind, capacity, room, slots):
        return dict(course_id=cid, name=f"課程{cid}", credits=credits,
                    course_type=kind, teacher="老師", capacity=capacity,
                    classroom=room, time_slots=slots)

    return [
        course("C1", 3, "必修", 2, "R1", [[1, "1"], [1, "2"]]),
        course("C2", 3, "選修", 1, "R2", [[2, "3"]]),
        course("C3", 2, "選修", 30, "R3", [[3, "c"]]),
        course("C4", 3, "選修", 30, "R4", [[1, "2"]]),
        course("C5", 1, "選修", 30, "R5", [[7, "c"]]),
    ]


def make_data(enrollments=None):
    """Return a full F1 snapshot accepted by check_enrollment."""
    return {
        "students": [dict(student_id=s, name=s, department="CS", max_credits=6)
                     for s in ("S1", "S2", "S3")],
        "courses": make_courses(),
        "classrooms": [dict(classroom_id=f"R{i}", capacity=60) for i in range(1, 6)],
        "enrollments": list(enrollments or []),
        "activities": [],
    }


def ids(courses):
    """Return the course IDs of a filter result, preserving order."""
    return [c["course_id"] for c in courses]


class TestF5Normal(unittest.TestCase):
    """Normal cases: valid input, expected candidates and feasibility."""

    def setUp(self):
        self.courses = make_courses()

    def test_no_preferences_returns_every_open_course(self):
        result = filter_courses(self.courses, {}, [])
        self.assertEqual(ids(result), ["C1", "C2", "C3", "C4", "C5"])

    def test_desired_courses_limit_candidates(self):
        result = filter_courses(self.courses, {"desired_courses": ["C3", "C5"]}, [])
        self.assertEqual(ids(result), ["C3", "C5"])

    def test_mandatory_courses_are_flagged(self):
        result = filter_courses(self.courses, {"mandatory_courses": ["C1"]}, [])
        flags = {c["course_id"]: c["_is_mandatory"] for c in result}
        self.assertEqual(flags, {"C1": True})

    def test_unavailable_slot_excludes_course(self):
        result = filter_courses(self.courses, {"unavailable_slots": [[2, "3"]]}, [])
        self.assertNotIn("C2", ids(result))
        self.assertIn("C1", ids(result))

    def test_preferred_days_are_marked_not_enforced(self):
        result = filter_courses(self.courses, {"preferred_days": [3]}, [])
        flags = {c["course_id"]: c["_is_preferred"] for c in result}
        self.assertEqual(len(result), 5)
        self.assertTrue(flags["C3"])
        self.assertFalse(flags["C1"])

    def test_valid_preferences_have_no_errors(self):
        prefs = dict(desired_courses=["C1"], mandatory_courses=["C1"],
                     min_credits=3, max_credits=6,
                     unavailable_slots=[[5, "9"]], preferred_days=[1, 2])
        self.assertEqual(validate_preferences(prefs), [])

    def test_credit_range_accepts_total_inside_limits(self):
        selected = [c for c in self.courses if c["course_id"] in ("C1", "C3")]
        self.assertEqual(check_credit_range(selected, 4, 6), [])

    def test_feasibility_passes_for_open_free_course(self):
        result = check_course_feasibility("S1", "C3", make_data(), {})
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["errors"], [])

    def test_feasibility_passes_with_unrelated_unavailable_slot(self):
        result = check_course_feasibility("S1", "C3", make_data(),
                                          {"unavailable_slots": [[5, "1"]]})
        self.assertTrue(result["ok"], result["errors"])

    def test_filter_returns_independent_copies(self):
        result = filter_courses(self.courses, {}, [])
        result[0]["name"] = "changed"
        self.assertEqual(self.courses[0]["name"], "課程C1")

    def test_filter_does_not_modify_inputs(self):
        prefs = dict(desired_courses=["C1", "C3"], preferred_days=[1],
                     unavailable_slots=[[3, "c"]])
        enrollments = [{"student_id": "S1", "course_id": "C1"}]
        before = deepcopy((self.courses, prefs, enrollments))
        filter_courses(self.courses, prefs, enrollments)
        self.assertEqual((self.courses, prefs, enrollments), before)

    def test_tuple_unavailable_slot_is_supported(self):
        result = filter_courses(self.courses, {"unavailable_slots": [(3, "c")]}, [])
        self.assertNotIn("C3", ids(result))

    def test_scenario_valid_plan_meets_credit_range(self):
        """Scenario 1: mandatory + desired electives fit the credit window."""
        prefs = dict(mandatory_courses=["C1"], desired_courses=["C3"],
                     min_credits=5, max_credits=6)
        candidates = filter_courses(self.courses, prefs, [])
        self.assertEqual(ids(candidates), ["C1", "C3"])
        self.assertEqual(check_credit_range(candidates, 5, 6), [])


class TestF5Boundary(unittest.TestCase):
    """Boundary cases: limits, edge weekdays/periods, empty inputs."""

    def setUp(self):
        self.courses = make_courses()

    def test_last_seat_still_available(self):
        enrollments = [{"student_id": "S2", "course_id": "C1"}]  # capacity 2
        result = filter_courses(self.courses, {}, enrollments)
        self.assertIn("C1", ids(result))

    def test_course_full_exactly_at_capacity_is_excluded(self):
        enrollments = [{"student_id": "S2", "course_id": "C2"}]  # capacity 1
        result = filter_courses(self.courses, {}, enrollments)
        self.assertNotIn("C2", ids(result))

    def test_enrollments_for_other_courses_do_not_fill_course(self):
        enrollments = [{"student_id": "S2", "course_id": "C3"}]
        result = filter_courses(self.courses, {}, enrollments)
        self.assertIn("C2", ids(result))

    def test_credit_total_exactly_equals_min(self):
        selected = [c for c in self.courses if c["course_id"] == "C1"]
        self.assertEqual(check_credit_range(selected, 3, 6), [])

    def test_credit_total_exactly_equals_max(self):
        selected = [c for c in self.courses if c["course_id"] in ("C1", "C2")]
        self.assertEqual(check_credit_range(selected, 3, 6), [])

    def test_credit_total_one_below_min(self):
        selected = [c for c in self.courses if c["course_id"] == "C1"]
        self.assertEqual(len(check_credit_range(selected, 4, 6)), 1)

    def test_credit_total_one_above_max(self):
        selected = [c for c in self.courses if c["course_id"] in ("C1", "C2", "C5")]
        self.assertEqual(len(check_credit_range(selected, 1, 6)), 1)

    def test_min_equal_to_max_is_valid(self):
        self.assertEqual(validate_preferences({"min_credits": 3, "max_credits": 3}), [])

    def test_sunday_period_c_unavailable_slot_matches(self):
        result = filter_courses(self.courses, {"unavailable_slots": [[7, "c"]]}, [])
        self.assertNotIn("C5", ids(result))

    def test_adjacent_period_is_not_treated_as_unavailable(self):
        # Mon period 3 is blocked; C1 uses Mon periods 1-2 only.
        result = filter_courses(self.courses, {"unavailable_slots": [[1, "3"]]}, [])
        self.assertIn("C1", ids(result))

    def test_one_blocked_period_excludes_multi_slot_course(self):
        result = filter_courses(self.courses, {"unavailable_slots": [[1, "2"]]}, [])
        self.assertNotIn("C1", ids(result))
        self.assertNotIn("C4", ids(result))

    def test_empty_course_list_returns_empty_result(self):
        self.assertEqual(filter_courses([], {}, []), [])

    def test_empty_credit_selection_with_no_min_has_no_errors(self):
        self.assertEqual(check_credit_range([], None, 6), [])

    def test_empty_credit_selection_below_min_reports_zero_total(self):
        errors = check_credit_range([], 1, None)
        self.assertEqual(len(errors), 1)
        self.assertIn("0", errors[0])

    def test_preferred_days_boundary_values_1_and_7_are_valid(self):
        self.assertEqual(validate_preferences({"preferred_days": [1, 7]}), [])

    def test_mandatory_course_outside_desired_list_is_kept(self):
        prefs = dict(desired_courses=["C3"], mandatory_courses=["C1"])
        self.assertEqual(ids(filter_courses(self.courses, prefs, [])), ["C1", "C3"])

    def test_preferred_day_without_match_does_not_exclude(self):
        result = filter_courses(self.courses, {"preferred_days": [6]}, [])
        self.assertEqual(len(result), 5)
        self.assertFalse(any(c["_is_preferred"] for c in result))


class TestF5ErrorAndConflict(unittest.TestCase):
    """Error and conflict cases, including the five acceptance scenarios."""

    def setUp(self):
        self.courses = make_courses()

    def test_preferences_not_dict_is_rejected(self):
        self.assertTrue(validate_preferences(["C1"]))
        self.assertTrue(validate_preferences(None))

    def test_min_greater_than_max_is_contradictory(self):
        errors = validate_preferences({"min_credits": 10, "max_credits": 4})
        self.assertTrue(any("最低學分不可大於最高學分" in e for e in errors))

    def test_zero_credit_limit_is_rejected(self):
        self.assertTrue(validate_preferences({"min_credits": 0}))

    def test_negative_credit_limit_is_rejected(self):
        self.assertTrue(validate_preferences({"max_credits": -3}))

    def test_bool_and_string_credit_limits_are_rejected(self):
        self.assertTrue(validate_preferences({"min_credits": True}))
        self.assertTrue(validate_preferences({"max_credits": "6"}))

    def test_invalid_preferred_days_are_rejected(self):
        for days in ([0], [8], ["1"], [True], [1.5]):
            with self.subTest(days=days):
                self.assertTrue(validate_preferences({"preferred_days": days}))

    def test_non_list_unavailable_slots_rejected(self):
        self.assertTrue(validate_preferences({"unavailable_slots": "1a"}))

    def test_malformed_unavailable_slot_rejected(self):
        for slot in ([1], [1, "a", "b"], "x", 5):
            with self.subTest(slot=slot):
                self.assertTrue(validate_preferences({"unavailable_slots": [slot]}))

    def test_filter_reports_validation_errors_instead_of_courses(self):
        result = filter_courses(self.courses, {"min_credits": 9, "max_credits": 3}, [])
        self.assertTrue(result)
        self.assertTrue(all("error" in item for item in result))

    def test_invalid_preferences_do_not_modify_inputs(self):
        before = deepcopy(self.courses)
        filter_courses(self.courses, {"preferred_days": [9]}, [])
        self.assertEqual(self.courses, before)

    def test_credit_total_below_min_returns_reason(self):
        """Scenario 2: minimum credits cannot be satisfied."""
        candidates = filter_courses(self.courses, {"desired_courses": ["C5"]}, [])
        errors = check_credit_range(candidates, 6, 12)
        self.assertEqual(len(errors), 1)
        self.assertIn("低於最低限制", errors[0])

    def test_credit_total_above_max_returns_reason(self):
        selected = [c for c in self.courses if c["course_id"] in ("C1", "C2", "C4")]
        errors = check_credit_range(selected, None, 6)
        self.assertEqual(len(errors), 1)
        self.assertIn("高於最高限制", errors[0])

    def test_credit_range_rejects_non_list(self):
        self.assertTrue(check_credit_range("C1", 1, 6))
        self.assertTrue(check_credit_range(None, 1, 6))

    def test_full_course_is_excluded_from_candidates(self):
        """Scenario 3: a desired course is full."""
        enrollments = [{"student_id": "S2", "course_id": "C2"}]
        result = filter_courses(self.courses, {"desired_courses": ["C2"]}, enrollments)
        self.assertEqual(result, [])

    def test_feasibility_rejects_full_course(self):
        data = make_data([{"student_id": "S2", "course_id": "C2"}])
        result = check_course_feasibility("S1", "C2", data, {})
        self.assertFalse(result["ok"])
        self.assertTrue(any("額滿" in e for e in result["errors"]))

    def test_feasibility_rejects_time_conflict_with_selected_course(self):
        data = make_data([{"student_id": "S1", "course_id": "C1"}])
        result = check_course_feasibility("S1", "C4", data, {})
        self.assertFalse(result["ok"])
        self.assertTrue(any("衝突" in e for e in result["errors"]))

    def test_feasibility_rejects_unavailable_slot(self):
        result = check_course_feasibility("S1", "C3", make_data(),
                                          {"unavailable_slots": [[3, "c"]]})
        self.assertFalse(result["ok"])
        self.assertTrue(any("不可上課時段" in e for e in result["errors"]))

    def test_feasibility_reports_all_failures_together(self):
        data = make_data([{"student_id": "S2", "course_id": "C2"}])
        result = check_course_feasibility("S1", "C2", data,
                                          {"unavailable_slots": [[2, "3"]]})
        self.assertFalse(result["ok"])
        self.assertGreaterEqual(len(result["errors"]), 2)

    def test_feasibility_rejects_duplicate_selection(self):
        data = make_data([{"student_id": "S1", "course_id": "C3"}])
        result = check_course_feasibility("S1", "C3", data, {})
        self.assertFalse(result["ok"])

    def test_feasibility_rejects_unknown_student_and_course(self):
        self.assertFalse(check_course_feasibility("NOPE", "C3", make_data(), {})["ok"])
        self.assertFalse(check_course_feasibility("S1", "NOPE", make_data(), {})["ok"])

    def test_feasibility_rejects_invalid_constraints_before_checking(self):
        result = check_course_feasibility("S1", "C3", make_data(),
                                          {"min_credits": 9, "max_credits": 1})
        self.assertFalse(result["ok"])
        self.assertTrue(result["errors"])

    def test_feasibility_exceeding_student_credit_limit(self):
        data = make_data([{"student_id": "S1", "course_id": "C1"},
                          {"student_id": "S1", "course_id": "C2"}])  # 6 of 6 credits
        result = check_course_feasibility("S1", "C3", data, {})
        self.assertFalse(result["ok"])
        self.assertTrue(any("學分上限" in e for e in result["errors"]))

    def test_feasibility_does_not_modify_snapshot(self):
        data = make_data([{"student_id": "S1", "course_id": "C1"}])
        before = deepcopy(data)
        check_course_feasibility("S1", "C3", data, {"unavailable_slots": [[3, "c"]]})
        self.assertEqual(data, before)

    def test_scenario_contradictory_desired_course_in_blocked_slot(self):
        """Scenario 4: the desired/mandatory course sits in a blocked slot."""
        prefs = dict(mandatory_courses=["C1"], unavailable_slots=[[1, "1"]])
        self.assertEqual(filter_courses(self.courses, prefs, []), [])

    def test_scenario_mandatory_courses_conflict_with_each_other(self):
        """Scenario 5: two mandatory courses overlap, so one is infeasible."""
        data = make_data([{"student_id": "S1", "course_id": "C1"}])
        result = check_course_feasibility("S1", "C4", data, {})
        self.assertFalse(result["ok"])
        self.assertTrue(any("星期1第2節" in e for e in result["errors"]))


if __name__ == "__main__":
    unittest.main()