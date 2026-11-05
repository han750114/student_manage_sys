
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

from .scheduling import (intervals_overlap, parse_date, project_activities, time_minutes,
                         validate_activity)
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


def _result(data, errors=()):
    """Build the shared {ok, data, errors} result used across the project."""
    return {"ok": not errors, "data": data, "errors": list(errors)}


def _check_activity(activity, data, period_times):
    """Return every reason activity cannot be saved as it is; [] means valid."""
    errors = validate_activity(activity)
    rooms = {room["classroom_id"]: room for room in data["classrooms"]}
    room = rooms.get(activity.get("classroom_id"))
    if activity.get("classroom_id") and room is None:
        errors.append("教室不存在。")
    student_ids = {s["student_id"] for s in data["students"]}
    participants = activity.get("participant_ids")
    if isinstance(participants, list):
        unknown = [p for p in participants if p not in student_ids]
        if unknown:
            errors.append(f"學生不存在：{', '.join(map(str, unknown))}")
        need = activity.get("capacity")
        if positive_integer(need) and len(participants) > need:
            errors.append(f"報名人數 {len(participants)} 超過活動容量 {need}。")
    if errors:
        return errors
    return check_room(activity, room, data, period_times)


def add_activity(activity, data, period_times):
    """Return a new activity list with activity added, or every reason it cannot be."""
    if not isinstance(activity, dict):
        return _result(None, ["活動必須為物件。"])
    errors = []
    if any(a["activity_id"] == activity.get("activity_id") for a in data["activities"]):
        errors.append("活動代號已存在。")
    errors.extend(_check_activity(activity, data, period_times))
    if errors:
        return _result(None, errors)
    return _result(deepcopy(data["activities"]) + [deepcopy(activity)])


def cancel_activity(activity_id, data):
    """Return a new activity list with the activity marked cancelled (not deleted)."""
    updated = deepcopy(data["activities"])
    target = next((a for a in updated if a["activity_id"] == activity_id), None)
    if target is None:
        return _result(None, ["找不到指定活動。"])
    if target["status"] == "cancelled":
        return _result(None, ["活動已取消。"])
    target["status"] = "cancelled"
    return _result(updated)


def update_activity(activity_id, updates, data, period_times):
    """Return a new activity list with updates applied after re-checking every rule."""
    if not isinstance(updates, dict):
        return _result(None, ["修改內容必須為物件。"])
    index = next((i for i, a in enumerate(data["activities"])
                  if a["activity_id"] == activity_id), None)
    if index is None:
        return _result(None, ["找不到指定活動。"])
    target = data["activities"][index]
    if "activity_id" in updates and updates["activity_id"] != activity_id:
        return _result(None, ["活動代號不可修改。"])
    if target["status"] == "cancelled":
        return _result(None, ["已取消的活動不可修改。"])
    merged = {**target, **updates}
    errors = _check_activity(merged, data, period_times)
    if errors:
        return _result(None, errors)
    updated = deepcopy(data["activities"])
    updated[index] = deepcopy(merged)
    return _result(updated)


def register_participant(activity_id, student_id, data):
    """Return a new activity list with student_id signed up, or every reason it cannot be."""
    updated = deepcopy(data["activities"])
    target = next((a for a in updated if a["activity_id"] == activity_id), None)
    if target is None:
        return _result(None, ["找不到指定活動。"])
    errors = []
    if target["status"] == "cancelled":
        errors.append("活動已取消，無法報名。")
    if student_id not in {s["student_id"] for s in data["students"]}:
        errors.append("學生不存在。")
    if student_id in target["participant_ids"]:
        errors.append("已報名此活動，不得重複報名。")
    need = target.get("capacity")
    if not positive_integer(need):
        errors.append("活動容量必須為正整數。")
    elif len(target["participant_ids"]) >= need:
        errors.append(f"活動已額滿（{need} 人）。")
    if errors:
        return _result(None, errors)
    target["participant_ids"].append(student_id)
    return _result(updated)


def find_activities(activities, date=None, classroom_id=None, status=None, student_id=None):
    """Return matching activities sorted by date and start time; None means no filter."""
    if date is not None:
        try:
            parse_date(date)
        except ValueError:
            return _result([], ["日期須為 YYYY-MM-DD。"])
    if status is not None and status not in ("scheduled", "cancelled"):
        return _result([], ["活動狀態須為 scheduled 或 cancelled。"])
    rows = [a for a in activities
            if (date is None or a["date"] == date)
            and (classroom_id is None or a["classroom_id"] == classroom_id)
            and (status is None or a["status"] == status)
            and (student_id is None or student_id in a["participant_ids"])]
    rows.sort(key=lambda a: (a["date"], a["start_time"]))
    return _result(deepcopy(rows))