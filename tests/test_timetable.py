"""Tests for F3 timetable module (modules/timetable.py)."""
import copy
import unittest

from modules.timetable import (
    DAYS, PERIODS, build_timetable, create_empty_timetable, day_to_index,
    find_course_slots, find_free_slots, get_cell, get_day,
    get_student_course_ids, period_to_index, summarize_timetable,
)


def make_data():
    """S001: CS101 (Mon 3,4), CS102 (Mon 5,6), CS111 (Mon a, Wed a). S002: none."""
    return {
        "students": [{"student_id": "S001"}, {"student_id": "S002"}],
        "courses": [
            {"course_id": "CS101", "name": "Python", "credits": 3,
             "time_slots": [[1, "3"], [1, "4"]]},
            {"course_id": "CS102", "name": "DS", "credits": 2,
             "time_slots": [[1, "5"], [1, "6"]]},
            {"course_id": "CS111", "name": "AI", "credits": 3,
             "time_slots": [[1, "a"], [3, "a"]]},
        ],
        "enrollments": [
            {"student_id": "S001", "course_id": "CS101"},
            {"student_id": "S001", "course_id": "CS102"},
            {"student_id": "S001", "course_id": "CS111"},
        ],
    }


def runs(result):
    """Turn find_free_slots output into short tuples for comparison."""
    return [(r["day"], r["start"], r["end"], r["length"]) for r in result["data"]]


class TestTimetable(unittest.TestCase):

    def setUp(self):
        self.data = make_data()
        self.grid = build_timetable("S001", self.data)["data"]

    # ---------- normal cases ----------

    def test_empty_grid_is_12_by_7_and_rows_independent(self):
        """【正常案例】課表矩陣為 12 節次 x 7 天，且各列互不影響"""
        grid = create_empty_timetable()
        self.assertEqual(len(grid), len(PERIODS))
        self.assertTrue(all(len(row) == DAYS for row in grid))
        grid[0][0] = "X"
        self.assertEqual(sum(row.count("X") for row in grid), 1)

    def test_multiple_courses_same_day(self):
        """【正常案例】同一天多門課程"""
        periods = [p for p, _ in get_day(self.grid, 1)["data"]]
        self.assertEqual(periods, ["3", "4", "5", "6", "a"])

    def test_course_meeting_several_times(self):
        """【正常案例】同一課程每週多次上課，所有時段皆顯示"""
        result = find_course_slots(self.grid, "CS111")
        self.assertEqual(result["data"], [(1, "a"), (3, "a")])

    def test_get_cell_returns_course(self):
        """【正常案例】依星期與節次查詢"""
        self.assertEqual(get_cell(self.grid, 1, "3")["data"]["id"], "CS101")
        self.assertIsNone(get_cell(self.grid, 2, "3")["data"])

    def test_three_consecutive_free_periods(self):
        """【正常案例】查詢連續三節空堂"""
        result = find_free_slots(self.grid, {"days": [1], "min_length": 3})
        self.assertEqual(runs(result), [(1, "7", "9", 3)])

    def test_cross_day_query(self):
        """【正常案例】跨日查詢（星期一與星期三）"""
        result = find_free_slots(self.grid, {"days": [1, 3],
                                             "start_period": "8", "end_period": "c"})
        self.assertEqual(runs(result), [(1, "8", "9", 2), (1, "b", "c", 2),
                                        (3, "8", "9", 2), (3, "b", "c", 2)])

    def test_summary(self):
        """【正常案例】每日節數、每週學分、空堂數"""
        s = summarize_timetable("S001", self.data, self.grid)["data"]
        self.assertEqual(s["periods_per_day"][1], 5)
        self.assertEqual(s["periods_per_day"][3], 1)
        self.assertEqual(s["weekly_credits"], 8)
        self.assertEqual(s["gaps_per_day"][1], 3)

    # ---------- boundary cases ----------

    def test_index_boundaries(self):
        """【邊界案例】節次 1/c、星期 1/7 為合法邊界；超出範圍回傳 None"""
        self.assertEqual(period_to_index("1"), 0)
        self.assertEqual(period_to_index("c"), 11)
        self.assertEqual(day_to_index(1), 0)
        self.assertEqual(day_to_index(7), 6)
        for bad in ("d", "0", 3, None):
            self.assertIsNone(period_to_index(bad))
        for bad in (0, 8, "1", True):
            self.assertIsNone(day_to_index(bad))

    def test_free_run_reaching_last_period(self):
        """【邊界案例】空堂延伸到最後一節 c 仍須列出"""
        grid = build_timetable("S002", self.data)["data"]
        result = find_free_slots(grid, {"days": [7], "start_period": "a",
                                        "end_period": "c", "min_length": 3})
        self.assertEqual(runs(result), [(7, "a", "c", 3)])

    def test_student_without_enrollments(self):
        """【邊界案例】學生沒有選課：課表全空、學分為 0"""
        result = build_timetable("S002", self.data)
        self.assertTrue(result["ok"])
        self.assertTrue(all(cell is None for row in result["data"] for cell in row))
        s = summarize_timetable("S002", self.data, result["data"])["data"]
        self.assertEqual(s["weekly_credits"], 0)

    def test_duplicate_enrollment_counted_once(self):
        """【邊界案例】重複選課紀錄只計算一次學分"""
        self.data["enrollments"].append({"student_id": "S001", "course_id": "CS101"})
        self.assertEqual(get_student_course_ids("S001", self.data["enrollments"]),
                         ["CS101", "CS102", "CS111"])
        s = summarize_timetable("S001", self.data, self.grid)["data"]
        self.assertEqual(s["weekly_credits"], 8)

    # ---------- error cases ----------

    def test_unknown_student(self):
        """【錯誤案例】學號不存在"""
        result = build_timetable("S999", self.data)
        self.assertFalse(result["ok"])
        self.assertIsNone(result["data"])
        self.assertIn("學生不存在", result["errors"][0])

    def test_missing_course_and_conflict_reported(self):
        """【錯誤/衝突案例】課程不存在與時段衝突皆列出，且不覆蓋原課程"""
        self.data["courses"].append({"course_id": "CS999", "name": "Clash",
                                     "credits": 3, "time_slots": [[1, "3"]]})
        self.data["enrollments"].append({"student_id": "S001", "course_id": "CS999"})
        self.data["enrollments"].append({"student_id": "S001", "course_id": "XX000"})
        result = build_timetable("S001", self.data)
        self.assertFalse(result["ok"])
        self.assertEqual(len(result["errors"]), 2)
        self.assertEqual(get_cell(result["data"], 1, "3")["data"]["id"], "CS101")

    def test_invalid_free_slot_queries(self):
        """【錯誤案例】無效查詢條件"""
        bad_queries = [
            {"start_period": "c", "end_period": "1"},
            {"min_length": 0},
            {"days": [8]},
            {"start_period": "z"},
        ]
        for query in bad_queries:
            result = find_free_slots(self.grid, query)
            self.assertFalse(result["ok"], query)
            self.assertIsNone(result["data"])

    def test_get_cell_invalid(self):
        """【錯誤案例】查詢不存在的星期或節次"""
        self.assertFalse(get_cell(self.grid, 8, "3")["ok"])
        self.assertFalse(get_cell(self.grid, 1, "z")["ok"])

    def test_build_does_not_mutate_input(self):
        """【錯誤預防案例】產生課表不得修改傳入資料"""
        before = copy.deepcopy(self.data)
        build_timetable("S001", self.data)
        self.assertEqual(self.data, before)


if __name__ == "__main__":
    unittest.main()