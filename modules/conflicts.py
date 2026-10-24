"""F2 共用衝突檢查模組（尚未實作）。

預計介面：
intervals_overlap(start_a, end_a, start_b, end_b) -> bool
check_enrollment(student_id, course_id, data) -> list[dict]

時間區間採 [開始, 結束)，相鄰區間不視為重疊。
一次收集所有限制問題，依星期與自訂節次順序排列。
"""
import json

class F2CourseChecker:
    def __init__(self, students_data, courses_data, classrooms_data):
        # 將 JSON List 轉為 Dict 以便透過 ID 快速查詢
        self.students = {s["student_id"]: s for s in students_data}
        self.courses = {c["course_id"]: c for c in courses_data}
        self.classrooms = {c["classroom_id"]: c for c in classrooms_data}
        
        # 假設在 F1 系統中，已幫課程物件加上 current_enrollment 屬性
        for c in self.courses.values():
            if "current_enrollment" not in c:
                c["current_enrollment"] = 0 
                
        # 假設在 F1 系統中，已幫學生物件加上 enrolled_courses 與 activities
        for s in self.students.values():
            if "enrolled_courses" not in s:
                s["enrolled_courses"] = []
            if "activities" not in s:
                s["activities"] = []
            if "current_credits" not in s:
                s["current_credits"] = 0

    def check_course_selection(self, student_id, target_course_id):
        """
        F2: 多層次衝堂與選課檢查
        必須檢查所有衝突，發現第一項錯誤後不得立即停止
        """
        conflicts = []
        
        student = self.students.get(student_id)
        target_course = self.courses.get(target_course_id)
        
        if not student or not target_course:
            return False, "學生或課程不存在"

        # 1. 檢查人數限制：若課程已額滿，系統須拒絕加選
        if target_course["current_enrollment"] >= target_course["capacity"]:
            conflicts.append({'type': 'capacity', 'msg': '課程已額滿'})

        # 2. 檢查學分限制：加選後總學分不得超過學生設定的上限
        future_credits = student["current_credits"] + target_course["credits"]
        if future_credits > student["max_credits"]:
            conflicts.append({
                'type': 'credit', 
                'msg': f'學分上限: {student["max_credits"]}，加選後: {future_credits}'
            })

        # 準備學生已佔用的所有時段 (包含已選課程與活動)
        student_occupied_times = {} # {(星期, 節次): "課程/活動名稱"}
        for c_id in student["enrolled_courses"]:
            c_data = self.courses[c_id]
            for day, period in c_data["time_slots"]:
                student_occupied_times[(day, str(period))] = c_data["name"]
                
        # 假設活動也有 time_slots 屬性
        for act in student["activities"]:
            for day, period in act["time_slots"]:
                student_occupied_times[(day, str(period))] = act["name"]

        # 準備目標教室已佔用的時段
        target_room_id = target_course["classroom"]
        room_occupied_times = {} # {(星期, 節次): "課程名稱"}
        # 走訪所有課程，若教室相同，則記錄其時段
        for c_data in self.courses.values():
            if c_data["classroom"] == target_room_id and c_data["course_id"] != target_course_id:
                for day, period in c_data["time_slots"]:
                    room_occupied_times[(day, str(period))] = c_data["name"]

        # 3. 檢查時間衝突
        time_conflicts = []
        for day, period in target_course["time_slots"]:
            day = int(day)
            period = str(period) # 處理 "a", "b", "c" 的情況
            
            # 學生衝堂：同一名學生不得選修上課時段重疊的課程，或檢查活動衝突
            if (day, period) in student_occupied_times:
                conflict_name = student_occupied_times[(day, period)]
                time_conflicts.append((day, period, f"與已選課程/活動衝突 ({conflict_name})"))
                
            # 教室衝堂：同一教室在同一時段不得安排兩門課程或活動
            if (day, period) in room_occupied_times:
                conflict_name = room_occupied_times[(day, period)]
                time_conflicts.append((day, period, f"教室 {target_room_id} 衝突 ({conflict_name})"))

        # 系統必須一次列出所有衝突，依星期及節次排序
        # 針對節次包含 1-9, a, b, c，我們先定義排序權重
        period_order = {str(i): i for i in range(1, 10)}
        period_order.update({'a': 10, 'b': 11, 'c': 12})
        
        time_conflicts.sort(key=lambda x: (x[0], period_order.get(x[1], 99)))
        
        for tc in time_conflicts:
            conflicts.append({'type': 'time', 'day': tc[0], 'period': tc[1], 'msg': tc[2]})

        # 4. 輸出結果
        if not conflicts:
            return True, "選課成功"
        else:
            return False, self.format_output(student, target_course, conflicts)

    def format_output(self, student, course, conflicts):
        """依據作業要求格式化輸出"""
        output = [f"學生:{student['student_id']}", f"欲加選:{course['course_id']} {course['name']}", "選課結果:失敗"]
        
        count = 1
        for c in conflicts:
            if c['type'] == 'time':
                output.append(f"衝突{count}:星期{c['day']}第{c['period']}節 - {c['msg']}")
                count += 1
            else:
                output.append(f"衝突{count}:{c['msg']}")
                count += 1
                
        output.append(f"目前學分:{student['current_credits']}")
        output.append(f"加選後學分:{student['current_credits'] + course['credits']}")
        output.append(f"學分上限:{student['max_credits']}")
        
        return "\n".join(output)

# 測試範例
if __name__ == "__main__":
    with open('students.json', 'r', encoding='utf-8') as f:
        students_data = json.load(f)
    with open('courses.json', 'r', encoding='utf-8') as f:
        courses_data = json.load(f)
    with open('classrooms.json', 'r', encoding='utf-8') as f:
        classrooms_data = json.load(f)

    checker = F2CourseChecker(students_data, courses_data, classrooms_data)
    
    # 模擬 S001 已經選了 CS101 (星期一第3,4節)，且學分已有 24
    checker.students["S001"]["enrolled_courses"] = ["CS101"]
    checker.students["S001"]["current_credits"] = 24
    
    # 嘗試加選 CS103 (星期三第3,4節，3學分) -> 預期觸發學分超載
    is_success, msg = checker.check_course_selection("S001", "CS103")
    print(msg)
