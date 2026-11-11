
"""F5 多條件課程篩選與可行性檢查模組（尚未實作）。

預計介面：
filter_courses(courses, preferences, enrollments) -> list[dict]
check_course_feasibility(student_id, course_id, data, constraints) -> dict
check_credit_range(selected_courses, min_credits, max_credits) -> list[str]
validate_preferences(preferences) -> list[str]

功能說明：
支援依希望課程、必修清單、學分範圍、不可上課時段及偏好星期篩選課程。
依照學生設定的條件，從課程資料中篩選符合基本要求的候選課程。
檢查課程是否符合最低與最高學分限制。
檢查課程是否安排於學生設定的不可上課時段。
檢查必修課程是否符合選課需求。
共用 conflicts.py 的時間衝突與選課限制檢查機制。
排除已額滿或不符合必要限制的課程。
當篩選條件互相矛盾或無法滿足最低學分時，須回傳明確原因。
區分必要限制與偏好條件，避免將偏好條件視為強制限制。
執行核心處理前須先驗證輸入資料。
操作失敗時不得修改原始資料。
"""
"""F5 多條件課程篩選與可行性檢查模組。"""

from copy import deepcopy
from .conflicts import check_enrollment
from .validation import positive_integer

def validate_preferences(preferences):
    """驗證篩選條件的格式與合理性。"""
    if not isinstance(preferences, dict):
        return ["偏好設定必須為字典。"]
    errors = []
    
    min_c = preferences.get("min_credits")
    max_c = preferences.get("max_credits")
    
    if min_c is not None and not positive_integer(min_c):
        errors.append("最低學分必須為正整數。")
    if max_c is not None and not positive_integer(max_c):
        errors.append("最高學分必須為正整數。")
    if min_c is not None and max_c is not None and min_c > max_c:
        errors.append("最低學分不可大於最高學分。")
        
    unavail = preferences.get("unavailable_slots", [])
    if not isinstance(unavail, list):
        errors.append("不可上課時段必須為清單。")
    else:
        for slot in unavail:
            if not isinstance(slot, (list, tuple)) or len(slot) != 2:
                errors.append(f"無效時段結構：{slot}")
                
    preferred = preferences.get("preferred_days", [])
    if not isinstance(preferred, list):
        errors.append("偏好星期必須為清單。")
    else:
        if any(type(d) is not int or not 1 <= d <= 7 for d in preferred):
            errors.append("偏好星期必須包含 1-7 的整數。")
            
    return errors

def check_credit_range(selected_courses, min_credits, max_credits):
    """檢查選修課程是否落在設定的學分範圍內。"""
    if not isinstance(selected_courses, list):
        return ["已選課程必須為清單。"]
    total = sum(c.get("credits", 0) for c in selected_courses if isinstance(c, dict))
    errors = []
    if min_credits is not None and total < min_credits:
        errors.append(f"總學分 {total} 低於最低限制 {min_credits}。")
    if max_credits is not None and total > max_credits:
        errors.append(f"總學分 {total} 高於最高限制 {max_credits}。")
    return errors

def check_course_feasibility(student_id, course_id, data, constraints):
    """
    綜合檢查單一課程的可行性。
    共用 conflicts.py 檢查衝堂與額滿，並額外檢查學生自訂的不可上課時段。
    """
    result = {"ok": False, "errors": []}
    
    # 1. 驗證自訂條件格式
    val_errors = validate_preferences(constraints)
    if val_errors:
        result["errors"].extend(val_errors)
        return result
        
    # 2. 呼叫 F2 既有的檢查機制 (包含衝堂、額滿、學分上限等)
    enrollment_result = check_enrollment(student_id, course_id, data)
    errors = list(enrollment_result.get("errors", []))
    
    target = next((c for c in data.get("courses", []) if c.get("course_id") == course_id), None)
    if not target:
        errors.append("找不到指定課程。")
        result["errors"] = errors
        return result
        
    # 3. 檢查自訂的「不可上課時段」限制
    unavail = constraints.get("unavailable_slots", [])
    for day, period in target.get("time_slots", []):
        if [day, period] in unavail or (day, period) in unavail:
            errors.append(f"違反不可上課時段限制：星期{day}第{period}節")
            
    result["ok"] = len(errors) == 0
    result["errors"] = errors
    result["data"] = enrollment_result.get("data") 
    return result

def filter_courses(courses, preferences, enrollments):
    """
    依照條件篩選候選課程，排除額滿與違反禁止時段的課程，並標註偏好與必修。
    """
    val_errors = validate_preferences(preferences)
    if val_errors:
        return [{"error": e} for e in val_errors]
        
    candidates = []
    unavail = preferences.get("unavailable_slots", [])
    preferred_days = preferences.get("preferred_days", [])
    desired = preferences.get("desired_courses", [])
    mandatory = preferences.get("mandatory_courses", [])
    
    # 計算各課程目前選課人數，用於過濾額滿課程
    usage = {}
    for e in enrollments:
        cid = e.get("course_id")
        usage[cid] = usage.get(cid, 0) + 1
        
    for course in courses:
        cid = course.get("course_id")
        
        # 若有明確列出必修或希望清單，則僅在此範圍內進行篩選
        if (desired or mandatory) and cid not in desired and cid not in mandatory:
            continue
        
        # 1. 檢查額滿 (必要條件)
        capacity = course.get("capacity", 0)
        enrolled_count = usage.get(cid, 0)
        if enrolled_count >= capacity:
            continue
            
        # 2. 檢查不可上課時段 (必要條件)
        slots = course.get("time_slots", [])
        conflict = False
        for day, period in slots:
            if [day, period] in unavail or (day, period) in unavail:
                conflict = True
                break
        if conflict:
            continue
            
        # 3. 標記偏好條件與屬性 (非強制排除)
        is_preferred = False
        if preferred_days:
            # 只要有一堂課落在偏好的星期即算符合偏好
            is_preferred = any(day in preferred_days for day, period in slots)
            
        course_copy = deepcopy(course)
        course_copy["_is_preferred"] = is_preferred
        course_copy["_is_mandatory"] = (cid in mandatory)
        
        candidates.append(course_copy)
        
    return candidates
