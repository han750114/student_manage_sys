
"""F4 校園活動管理與教室配置模組（尚未實作）。

預計介面：
add_activity(activities, activity, classrooms, courses) -> dict
update_activity(activities, activity_id, updates, classrooms, courses) -> dict
cancel_activity(activities, activity_id) -> dict
find_activities(activities, filters) -> list[dict]
find_available_classrooms(activity, classrooms, courses, activities) -> list[dict]
assign_classroom(activity, classroom_id, classrooms, courses, activities) -> dict

功能說明：
支援校園活動的新增、修改、取消及查詢。
依照教室容量、可用時段及設備需求篩選合適教室。
共用 conflicts.py 的時間衝突檢查機制。
避免課程與活動在相同時段重複使用同一間教室。
活動報名人數不得超過活動或教室容量限制。
若無符合條件的教室，須列出未滿足的配置條件。
執行核心處理前須先驗證輸入資料。
操作失敗時不得修改原始資料。
"""
