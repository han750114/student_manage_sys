import unittest
from modules.conflicts import F2CourseChecker


class TestF2CourseChecker(unittest.TestCase):

    def setUp(self):
        """初始化測試環境與測資"""
        self.students = [
            {
                "student_id": "S001",
                "name": "王小明",
                "department": "資工系",
                "max_credits": 20,
                "current_credits": 18,
                "enrolled_courses": ["CS101"],
                "activities": [{"name": "程式設計讀書會", "time_slots": [[4, "5"]]}],
            }
        ]
        self.courses = [
            {
                "course_id": "CS101",
                "name": "微積分",
                "credits": 3,
                "capacity": 30,
                "classroom": "R101",
                "time_slots": [[2, "3"], [2, "4"]],
                "current_enrollment": 10,
            },
            {
                "course_id": "CS102",
                "name": "Python 程式設計",
                "credits": 3,
                "capacity": 2,
                "classroom": "R101",
                "time_slots": [[2, "3"], [2, "4"], [4, "5"]],
                "current_enrollment": 2,  # 額滿
            },
            {
                "course_id": "CS103",
                "name": "演算法",
                "credits": 2,
                "capacity": 30,
                "classroom": "R102",
                "time_slots": [[5, "1"]],
                "current_enrollment": 5,
            },
        ]
        self.classrooms = [
            {"classroom_id": "R101", "capacity": 50},
            {"classroom_id": "R102", "capacity": 50},
        ]

    def test_successful_course_selection(self):
        """測試 1: 正常成功選課案例"""
        # 調整學生現有學分，使其符合條件
        self.students[0]["current_credits"] = 10
        self.students[0]["enrolled_courses"] = []
        self.students[0]["activities"] = []

        checker = F2CourseChecker(self.students, self.courses, self.classrooms)
        is_success, msg = checker.check_course_selection("S001", "CS103")

        self.assertTrue(is_success)
        self.assertEqual(msg, "選課成功")

    def test_multiple_conflicts_and_sorting(self):
        """測試 2: 驗證「一次列出所有衝突」並確保依照星期與節次（包含 1-9, a, b, c）正確排序"""
        checker = F2CourseChecker(self.students, self.courses, self.classrooms)
        is_success, msg = checker.check_course_selection("S001", "CS102")

        self.assertFalse(is_success)

        # 1. 驗證所有衝突類型皆有被列出（額滿、學分超載、學生衝堂、教室衝堂）
        self.assertIn("課程已額滿", msg)
        self.assertIn("學分上限: 20，加選後: 21", msg)
        self.assertIn("星期2第3節", msg)
        self.assertIn("星期2第4節", msg)
        self.assertIn("星期4第5節", msg)

        # 2. 驗證時間排序（星期2第3節 -> 星期2第4節 -> 星期4第5節）
        idx_t2_p3 = msg.find("星期2第3節")
        idx_t2_p4 = msg.find("星期2第4節")
        idx_t4_p5 = msg.find("星期4第5節")

        self.assertTrue(idx_t2_p3 < idx_t2_p4 < idx_t4_p5)

    def test_nonexistent_student_or_course(self):
        """測試 3: 錯誤輸入 - 不存在的學生或課程 ID"""
        checker = F2CourseChecker(self.students, self.courses, self.classrooms)

        ok1, msg1 = checker.check_course_selection("INVALID_STUDENT", "CS101")
        self.assertFalse(ok1)
        self.assertEqual(msg1, "學生或課程不存在")

        ok2, msg2 = checker.check_course_selection("S001", "INVALID_COURSE")
        self.assertFalse(ok2)
        self.assertEqual(msg2, "學生或課程不存在")


if __name__ == "__main__":
    unittest.main()