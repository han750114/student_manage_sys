
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

from copy import deepcopy

from .scheduling import intervals_overlap, project_activities, time_minutes
from .validation import positive_integer


def check_room(activity, room, data, period_times):
    """Return every unmet condition for placing activity in room; [] means usable.

    Checks capacity, equipment, course clashes and other-activity clashes.
    Inputs are never modified.
    """
    room_id = room["classroom_id"]
    errors = []

    # 1. Capacity
    need = activity.get("capacity")
    if not positive_integer(need):
        errors.append("活動容量必須為正整數。")
    elif room["capacity"] < need:
        errors.append(f"容量不足：教室 {room['capacity']} 人，活動需要 {need} 人")

    # 2. Equipment
    has = room.get("equipment", [])
    for item in activity.get("required_equipment", []):
        if item not in has:
            errors.append(f"缺少設備：{item}")

    # 3. Courses in this room (weekly periods)
    candidate = {**activity, "classroom_id": room_id}
    projected, problems = project_activities([candidate], period_times)
    if problems:
        return errors + problems
    slots = projected[0]["time_slots"] if projected else []
    for course in data["courses"]:
        if course["classroom"] != room_id:
            continue
        for day, period in slots:
            if [day, period] in course["time_slots"]:
                errors.append(f"與課程衝突：星期{day}第{period}節 "
                              f"{course['course_id']} {course['name']}")

    # 4. Other activities in this room (same date, clock times)
    start, end = time_minutes(activity["start_time"]), time_minutes(activity["end_time"])
    for other in data["activities"]:
        if (other["activity_id"] == activity["activity_id"]
                or other["status"] == "cancelled"
                or other["classroom_id"] != room_id
                or other["date"] != activity["date"]):
            continue
        if intervals_overlap(start, end, time_minutes(other["start_time"]),
                             time_minutes(other["end_time"])):
            errors.append(f"與活動衝突：{other['activity_id']} {other['name']} "
                          f"{other['start_time']}-{other['end_time']}")
    return errors


def find_available_classrooms(activity, classrooms, data, period_times):
    """Split rooms into usable ones and unusable ones with their reasons.

    Returns {ok, data, errors}. data = {"available": [rooms, smallest first],
    "unavailable": [{"classroom_id", "reasons"}]}. ok is False when no room fits,
    and errors then lists every room's unmet conditions. Inputs are never modified.
    """
    available, unavailable = [], []
    for room in classrooms:
        reasons = check_room(activity, room, data, period_times)
        if reasons:
            unavailable.append({"classroom_id": room["classroom_id"], "reasons": reasons})
        else:
            available.append(deepcopy(room))
    available.sort(key=lambda room: room["capacity"])
    errors = []
    if not available:
        errors.append("沒有符合條件的教室。")
        for row in unavailable:
            errors.extend(f"{row['classroom_id']}：{reason}" for reason in row["reasons"])
    return {"ok": not errors,
            "data": {"available": available, "unavailable": unavailable},
            "errors": errors}