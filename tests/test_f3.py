import unittest
from modules.timetable import (
    build_timetable,
    find_free_slots,
    get_cell,
    summarize_timetable,
)


class TestF3Timetable(unittest.TestCase):

    def setUp(self):
        """初始化 F3 測試資料"""
        self.data = {
            "students": [{"student_id": "S001", "name": "張同學"}],
            "courses": [
                {
                    "course_id": "CS101",
                    "name": "微積分",
                    "credits": 3,
                    # 包含同日多門時段與跨日、特殊節次 'a'
                    "time_slots": [[1, "1"], [1, "2"], [3, "a"]],
                },
                {
                    "course_id": "CS102",
                    "name": "程式設計",
                    "credits": 3,
                    # 故意安排在第 6 節，讓星期一第 3, 4, 5 節形成連續 3 節空堂
                    "time_slots": [[1, "6"]],
                },
            ],
            "enrollments": [
                {"student_id": "S001", "course_id": "CS101"},
                {"student_id": "S001", "course_id": "CS102"},
            ],
        }

    def test_build_timetable_grid(self):
        """測試 1: 驗證 12 節次 x 7 天課表二維矩陣建立與特有節次 'a' (第 10 節)"""
        res = build_timetable("S001", self.data)
        self.assertTrue(res["ok"])

        grid = res["data"]
        self.assertEqual(len(grid), 12)  # 12 個節次 (1-9, a, b, c)
        self.assertEqual(len(grid[0]), 7)  # 7 天

        # 檢查特定儲存格內容
        cell_c101 = get_cell(grid, 1, "1")["data"]
        self.assertEqual(cell_c101["id"], "CS101")

        cell_c101_a = get_cell(grid, 3, "a")["data"]
        self.assertEqual(cell_c101_a["id"], "CS101")

    def test_find_consecutive_three_free_slots(self):
        """測試 2: 驗收條件 - 測試連續三節空堂與指定時間區間查詢"""
        res = build_timetable("S001", self.data)
        grid = res["data"]

        # 查詢星期一在第 1~8 節之間，最少連續 3 節的空堂
        query = {
            "days": [1],
            "start_period": "1",
            "end_period": "8",
            "min_length": 3,
        }
        free_res = find_free_slots(grid, query)

        self.assertTrue(free_res["ok"])
        runs = free_res["data"]

        # 預期找到 星期一 第 3 節至第 5 節 (長度 3)
        self.assertEqual(len(runs), 1)
        self.assertEqual(
            runs[0], {"day": 1, "start": "3", "end": "5", "length": 3}
        )

    def test_summarize_timetable(self):
        """測試 3: 驗證每日上課節數、每週總學分與空堂數統計"""
        res = build_timetable("S001", self.data)
        summary = summarize_timetable("S001", self.data, res["data"])

        self.assertTrue(summary["ok"])
        stats = summary["data"]

        self.assertEqual(stats["weekly_credits"], 6)  # CS101(3) + CS102(3)
        self.assertEqual(stats["periods_per_day"][1], 3)  # 星期一共 3 節課
        self.assertEqual(
            stats["gaps_per_day"][1], 3
        )  # 1-2 節與 6 節之間有 3 節空堂

    def test_nonexistent_student(self):
        """測試 4: 錯誤輸入 - 查詢不存在的學生"""
        res = build_timetable("NON_EXIST", self.data)
        self.assertFalse(res["ok"])
        self.assertIn("學生不存在", res["errors"][0])


if __name__ == "__main__":
    unittest.main()