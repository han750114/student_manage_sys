"""F2 共用衝突檢查模組（尚未實作）。

預計介面：
intervals_overlap(start_a, end_a, start_b, end_b) -> bool
check_enrollment(student_id, course_id, data) -> list[dict]

時間區間採 [開始, 結束)，相鄰區間不視為重疊。
一次收集所有限制問題，依星期與自訂節次順序排列。
"""
def check_course_selection(student_id, target_course_id, db):
    """
    F2: 多層次衝堂與選課檢查模組
    """
    conflicts = []
    
    # 取得基礎資料 (需替換為你們 F1 實作的資料讀取方式)
    student = db.get_student(student_id)
    target_course = db.get_course(target_course_id)
    
    # 1. 檢查人數限制
    if target_course.current_enrollment >= target_course.max_capacity:
        # 人數限制通常不具備星期節次，可依團隊討論決定如何顯示
        conflicts.append({'type': 'capacity', 'msg': '課程已額滿'})

    # 2. 檢查學分限制
    future_credits = student.current_credits + target_course.credits
    if future_credits > student.max_credits:
        conflicts.append({'type': 'credit', 'msg': f'學分上限: {student.max_credits}，加選後: {future_credits}'})

    # 3. 時間衝突檢查 (設計可重複使用的函式)
    # 假設時間格式為 tuple: (星期, 節次)，例如 (2, '3') 代表星期二第3節
    time_conflicts = []
    
    for time_slot in target_course.time_slots:
        day, period = time_slot
        
        # 3a. 學生衝堂 & 活動衝突
        if has_time_conflict(student.schedule, day, period):
            time_conflicts.append((day, period, '學生課程或活動衝堂'))
            
        # 3b. 教室衝堂 (需檢查該課程預定教室的時段)
        target_room = target_course.classroom
        if target_room and has_time_conflict(db.get_classroom_schedule(target_room), day, period):
            time_conflicts.append((day, period, '教室衝堂'))

    # 將時間衝突依星期及節次排序 (驗收條件)
    # 節次可能包含 'a', 'b', 'c'，團隊需在 F1/F2 討論好排序權重
    time_conflicts.sort(key=lambda x: (x[0], str(x[1])))
    
    for tc in time_conflicts:
        conflicts.append({'type': 'time', 'day': tc[0], 'period': tc[1], 'msg': tc[2]})

    # 4. 輸出結果判定
    if not conflicts:
        return True, "選課成功"
    else:
        return False, format_conflicts_output(student_id, target_course, conflicts)

def has_time_conflict(schedule, day, period):
    """可重複使用的時間衝突判斷函式"""
    # 根據你們的資料結構實作，例如檢查二維陣列或 dict
    pass

def format_conflicts_output(student_id, course, conflicts):
    """依照規格書的輸出結果範例格式化字串"""
    # 實作將 conflicts 轉換為規格書要求的文字格式
    pass
