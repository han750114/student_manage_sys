# tests/__init__.py
import unittest
import sys
import os
# 將專案根目錄加入系統路徑，確保可以順利找到 modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.management import add_course, find_courses, add_student, remove_course

class TestF1Management(unittest.TestCase):
    
    def setUp(self):
        """初始化測試資料"""
        self.courses = []
        self.students = []
        self.classrooms = ["C101", "C102", "C103"]

    def test_add_course_normal(self):
        """【正常案例】成功新增一門課程"""
        course_data = {
            "course_id": "CS101",
            "name": "Python程式設計",
            "credits": 3,
            "course_type": "必修",
            "teacher": "張老師",
            "capacity": 50,
            "classroom": "C101",
            "time_slots": [[1, "3"], [1, "4"]]
        }
        result = add_course(self.courses, course_data, self.classrooms)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["errors"], [])

    def test_add_course_duplicate_id(self):
        """【錯誤案例】課程代號重複，應拒絕新增"""
        course_data = {
            "course_id": "CS101",
            "name": "Python程式設計",
            "credits": 3,
            "course_type": "必修",
            "teacher": "張老師",
            "capacity": 50,
            "classroom": "C101",
            "time_slots": [[1, "3"]]
        }
        res1 = add_course(self.courses, course_data, self.classrooms)
        self.assertTrue(res1["ok"])
        self.courses = res1["data"]
        
        res2 = add_course(self.courses, course_data, self.classrooms)
        self.assertFalse(res2["ok"])
        self.assertIn("已存在", res2["errors"][0])

    def test_add_course_invalid_credits(self):
        """【邊界/錯誤案例】學分必須為正整數（如 0 應被拒絕）"""
        course_data = {
            "course_id": "CS102",
            "name": "資料結構",
            "credits": 0,
            "course_type": "必修",
            "teacher": "李老師",
            "capacity": 40,
            "classroom": "C102",
            "time_slots": [[2, "1"]]
        }
        result = add_course(self.courses, course_data, self.classrooms)
        self.assertFalse(result["ok"])
        self.assertTrue(any("學分" in err for err in result["errors"]))

    def test_remove_course_with_enrollment(self):
        """【錯誤/相依性案例】課程尚有學生選修時，禁止刪除"""
        course_data = {
            "course_id": "CS103",
            "name": "演算法",
            "credits": 3,
            "course_type": "選修",
            "teacher": "王老師",
            "capacity": 30,
            "classroom": "C103",
            "time_slots": [[3, "2"]],
            "enrolled_students": ["S001"]
        }
        res_add = add_course(self.courses, course_data, self.classrooms)
        self.courses = res_add["data"]
        
        res_remove = remove_course(self.courses, "CS103")
        self.assertFalse(res_remove["ok"])
        self.assertIn("尚有學生選修", res_remove["errors"][0])

if __name__ == "__main__":
    unittest.main()