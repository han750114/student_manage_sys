
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
