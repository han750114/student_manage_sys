from .validation import validate_course, validate_student

# ==========================================
# 1. 課程管理功能 (Course Management)
# ==========================================

def add_course(courses: list, course_data: dict, valid_classrooms: list) -> dict:
    """功能：新增課程 (包含代號重複與資料合法性檢查)"""
    errors = validate_course(course_data, valid_classrooms)
    if errors:
        return {"ok": False, "data": courses, "errors": errors}
    
    # 檢查課程代號不得重複
    if any(c["course_id"] == course_data["course_id"] for c in courses):
        return {"ok": False, "data": courses, "errors": [f"課程代號 {course_data['course_id']} 已存在"]}
    
    new_course = course_data.copy()
    if "enrolled_students" not in new_course:
        new_course["enrolled_students"] = []

    courses.append(new_course)
    return {"ok": True, "data": courses, "errors": []}


def update_course(courses: list, course_id: str, update_data: dict, valid_classrooms: list) -> dict:
    """功能：修改課程資料"""
    target_course = next((c for c in courses if c["course_id"] == course_id), None)
    if not target_course:
        return {"ok": False, "data": courses, "errors": [f"找不到課程代號 {course_id}"]}

    merged_course = target_course.copy()
    merged_course.update(update_data)
    
    errors = validate_course(merged_course, valid_classrooms)
    if errors:
        return {"ok": False, "data": courses, "errors": errors}

    target_course.update(update_data)
    return {"ok": True, "data": courses, "errors": []}


def remove_course(courses: list, course_id: str) -> dict:
    """功能：刪除課程 (不得刪除已有學生選修的課程)"""
    target_course = next((c for c in courses if c["course_id"] == course_id), None)
    if not target_course:
        return {"ok": False, "data": courses, "errors": [f"找不到課程代號 {course_id}"]}

    # 相依性檢查：已有學生選修時禁止刪除
    if target_course.get("enrolled_students"):
        return {"ok": False, "data": courses, "errors": [f"課程 {course_id} 尚有學生選修，無法直接刪除"]}

    courses.remove(target_course)
    return {"ok": True, "data": courses, "errors": []}


def find_courses(courses: list, course_id: str = None, teacher: str = None, weekday: int = None, course_type: str = None, min_remaining: int = None) -> dict:
    """功能：綜合多條件查詢課程"""
    results = courses.copy()

    if course_id:
        results = [c for c in results if c["course_id"] == course_id]
    if teacher:
        results = [c for c in results if teacher in c.get("teacher", "")]
    if weekday is not None:
        results = [c for c in results if any(slot[0] == weekday for slot in c.get("time_slots", []))]
    if course_type:
        results = [c for c in results if c.get("course_type") == course_type]
    if min_remaining is not None:
        results = [c for c in results if (c.get("capacity", 0) - len(c.get("enrolled_students", []))) >= min_remaining]

    return {"ok": True, "data": results, "errors": []}


# --- 個別單項查詢專用函式 ---

def find_courses_by_id(courses: list, course_id: str) -> dict:
    """功能：依課程代號查詢"""
    return find_courses(courses, course_id=course_id)

def find_courses_by_teacher(courses: list, teacher: str) -> dict:
    """功能：依授課教師查詢"""
    return find_courses(courses, teacher=teacher)

def find_courses_by_weekday(courses: list, weekday: int) -> dict:
    """功能：依上課星期 (1-7) 查詢"""
    return find_courses(courses, weekday=weekday)

def find_courses_by_type(courses: list, course_type: str) -> dict:
    """功能：依必選修類型 (必修/選修) 查詢"""
    return find_courses(courses, course_type=course_type)

def find_courses_by_remaining_capacity(courses: list, min_remaining: int) -> dict:
    """功能：依剩餘名額查詢"""
    return find_courses(courses, min_remaining=min_remaining)


# ==========================================
# 2. 學生管理功能 (Student Management)
# ==========================================

def add_student(students: list, student_data: dict) -> dict:
    """功能：新增學生 (包含學號重複檢查)"""
    errors = validate_student(student_data)
    if errors:
        return {"ok": False, "data": students, "errors": errors}

    # 檢查學號不得重複
    if any(s["student_id"] == student_data["student_id"] for s in students):
        return {"ok": False, "data": students, "errors": [f"學號 {student_data['student_id']} 已存在"]}

    new_student = student_data.copy()
    if "enrolled_courses" not in new_student:
        new_student["enrolled_courses"] = []

    students.append(new_student)
    return {"ok": True, "data": students, "errors": []}


def update_student(students: list, student_id: str, update_data: dict) -> dict:
    """功能：修改學生資料"""
    target_student = next((s for s in students if s["student_id"] == student_id), None)
    if not target_student:
        return {"ok": False, "data": students, "errors": [f"找不到學號 {student_id}"]}

    merged_student = target_student.copy()
    merged_student.update(update_data)

    errors = validate_student(merged_student)
    if errors:
        return {"ok": False, "data": students, "errors": errors}

    target_student.update(update_data)
    return {"ok": True, "data": students, "errors": []}


def remove_student(students: list, student_id: str) -> dict:
    """功能：刪除學生 (尚有選課時禁止刪除)"""
    target_student = next((s for s in students if s["student_id"] == student_id), None)
    if not target_student:
        return {"ok": False, "data": students, "errors": [f"找不到學號 {student_id}"]}

    if target_student.get("enrolled_courses"):
        return {"ok": False, "data": students, "errors": [f"學生 {student_id} 尚有選修課程，請先執行退選程序"]}

    students.remove(target_student)
    return {"ok": True, "data": students, "errors": []}


def find_students(students: list, student_id: str = None, name: str = None, department: str = None) -> dict:
    """功能：綜合多條件查詢學生"""
    results = students.copy()

    if student_id:
        results = [s for s in results if s["student_id"] == student_id]
    if name:
        results = [s for s in results if name in s.get("name", "")]
    if department:
        results = [s for s in results if department in s.get("department", "")]

    return {"ok": True, "data": results, "errors": []}