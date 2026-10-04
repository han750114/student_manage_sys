"""F2 共用衝突檢查模組（尚未實作）。

預計介面：
intervals_overlap(start_a, end_a, start_b, end_b) -> bool
check_enrollment(student_id, course_id, data) -> list[dict]

時間區間採 [開始, 結束)，相鄰區間不視為重疊。
一次收集所有限制問題，依星期與自訂節次順序排列。
"""
