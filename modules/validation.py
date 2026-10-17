# modules/validation.py

def validate_course(course: dict, classrooms: list = None) -> list[str]:
    errors = []
    
    #檢查必要欄位與資料型別
    course_id = course.get("course_id")
    name = course.get("name")
    credits_val = course.get("credits")
    capacity_val = course.get("capacity")
    time_slots = course.get("time_slots", [])
    classroom = course.get("classroom")
    
    if not course_id or not isinstance(course_id, str):
        errors.append("課程代號不得為空或型別錯誤。")
    if not name or not isinstance(name, str):
        errors.append("課程名稱不得為空或型別錯誤。")
        
    # 2. 檢查學分是否為正整數
    if not isinstance(credits_val, int) or isinstance_bool(credits_val) or credits_val <= 0:
        errors.append("學分必須為正整數。")
        
    # 3. 檢查人數上限不得小於 1
    if not isinstance(capacity_val, int) or isinstance_bool(capacity_val) or capacity_val < 1:
        errors.append("課程人數上限不得小於 1。")
        
    # 4. 檢查星期與節次格式 (星期 1-7，節次 1-9, a, b, c)
    valid_periods = set([str(i) for i in range(1, 10)] + ['a', 'b', 'c'])
    if not isinstance(time_slots, list):
        errors.append("上課時段格式錯誤。")
    else:
        for slot in time_slots:
            if not isinstance(slot, (list, tuple)) or len(slot) != 2:
                errors.append(f"不合法的時段結構: {slot}")
                continue
            day, period = slot
            if not isinstance(day, int) or not (1 <= day <= 7):
                errors.append(f"不合法的星期格式: {day} (必須為 1-7)")
            if period not in valid_periods:
                errors.append(f"不合法的節次格式: {period} (支援 1-9, a, b, c)")
                
    # 5. 教室驗證 (若有提供可用教室清單)
    if classrooms is not None and classroom not in classrooms:
        errors.append(f"教室 {classroom} 不存在或未納入配置。")
        
    return errors


def validate_student(student: dict) -> list[str]:
    """
    驗證學生資料是否合法。
    回傳所有驗證問題的字串清單；空清單表示驗證通過。
    """
    errors = []
    
    student_id = student.get("student_id")
    name = student.get("name")
    max_credits = student.get("max_credits", 25)
    
    if not student_id or not isinstance(student_id, str):
        errors.append("學號不得為空或型別錯誤。")
    if not name or not isinstance(name, str):
        errors.append("學生姓名不得為空或型別錯誤。")
    if not isinstance(max_credits, int) or isinstance_bool(max_credits) or max_credits <= 0:
        errors.append("學分上限必須為正整數。")
        
    return errors


def isinstance_bool(val) -> bool:
    #bool 是 int 的子類別，需要排除
    return isinstance(val, bool)