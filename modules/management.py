# modules/management.py
from .validation import validate_course, validate_student

def add_course(courses: list, course: dict, classrooms: list = None) -> dict:
    """
    新增課程。
    操作結果回傳 dict，包含：
      - ok (bool): 是否成功
      - data (list): 成功時為更新後的課程清單
      - errors (list[str]): 失敗時的錯誤訊息清單
    驗證失敗不修改原資料。
    """
    # 1. 檢查代號是否重複
    course_id = course.get("course_id")
    for existing in courses:
        if existing.get("course_id") == course_id:
            return {
                "ok": False,
                "data": courses,
                "errors": [f"錯誤：課程代號 {course_id} 已存在。"]
            }

    # 2. 透過 validation 模組進行格式與資料驗證
    validation_errors = validate_course(course, classrooms)
    if validation_errors:
        return {
            "ok": False,
            "data": courses,
            "errors": validation_errors
        }

    # 3. 驗證通過，建立新清單（確保不直接破壞原資料）
    new_course = dict(course)
    new_course["enrolled_students"] = new_course.get("enrolled_students", [])
    
    updated_courses = list(courses)
    updated_courses.append(new_course)

    return {
        "ok": True,
        "data": updated_courses,
        "errors": []
    }


def find_courses(courses: list, filters: dict, enrollments: list = None) -> list[dict]:
    """
    依條件尋找課程 (find_courses)。
    支援過濾條件如 course_id, teacher, course_type, day 等。
    """
    results = []
    for course in courses:
        match = True
        
        # 依條件過濾
        if "course_id" in filters and filters["course_id"] != course.get("course_id"):
            match = False
        if "teacher" in filters and filters["teacher"] not in course.get("teacher", ""):
            match = False
        if "course_type" in filters and filters["course_type"] != course.get("course_type"):
            match = False
        if "day" in filters:
            time_slots = course.get("time_slots", [])
            if not any(slot[0] == filters["day"] for slot in time_slots):
                match = False
                
        if match:
            results.append(course)
            
    return results


def add_student(students: list, student: dict) -> dict:
    """
    新增學生。
    操作結果回傳 dict，包含 ok、data、errors。
    """
    student_id = student.get("student_id")
    for existing in students:
        if existing.get("student_id") == student_id:
            return {
                "ok": False,
                "data": students,
                "errors": [f"錯誤：學號 {student_id} 已存在。"]
            }

    validation_errors = validate_student(student)
    if validation_errors:
        return {
            "ok": False,
            "data": students,
            "errors": validation_errors
        }

    new_student = dict(student)
    new_student["enrolled_courses"] = new_student.get("enrolled_courses", [])
    
    updated_students = list(students)
    updated_students.append(new_student)

    return {
        "ok": True,
        "data": updated_students,
        "errors": []
    }


def remove_course(courses: list, course_id: str, enrollments: list = None) -> dict:
    """
    刪除課程：若已有學生選修則禁止刪除（相依性檢查）。
    """
    target_course = None
    target_index = -1
    for i, course in enumerate(courses):
        if course.get("course_id") == course_id:
            target_course = course
            target_index = i
            break

    if target_course is None:
        return {
            "ok": False,
            "data": courses,
            "errors": [f"錯誤：找不到課程代號 {course_id}。"]
        }

    # 檢查是否仍有學生選修
    enrolled = target_course.get("enrolled_students", [])
    if len(enrolled) > 0 or (enrollments is not None and any(e.get("course_id") == course_id for e in enrollments)):
        return {
            "ok": False,
            "data": courses,
            "errors": [f"錯誤：課程 {course_id} 尚有學生選修，無法直接刪除。"]
        }

    updated_courses = list(courses)
    updated_courses.pop(target_index)

    return {
        "ok": True,
        "data": updated_courses,
        "errors": []
    }