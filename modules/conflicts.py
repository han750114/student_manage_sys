"""F2 enrollment checks over the existing F1 stores; no input/output or mutation."""
from copy import deepcopy

from .scheduling import PERIODS, intervals_overlap, project_activities
from .system_data import validate_system


def check_enrollment(student_id, course_id, data, period_times=None):
    """Return {ok, data, errors} with every enrollment restriction.

    data contains conflicts, current_credits, future_credits, max_credits and
    remaining_seats. Invalid snapshots return data=None. Checks never add a
    selection. Scheduled dated activities require explicit period clock times.
    """
    errors = validate_system(data)
    if errors:
        return {"ok": False, "data": None, "errors": errors}
    students = {s["student_id"]: s for s in data["students"]}
    courses = {c["course_id"]: c for c in data["courses"]}
    if not isinstance(student_id, str) or student_id not in students:
        errors.append("學生不存在。")
    if not isinstance(course_id, str) or course_id not in courses:
        errors.append("課程不存在。")
    if errors:
        return {"ok": False, "data": None, "errors": errors}

    student, target = students[student_id], courses[course_id]
    selected = {e["course_id"] for e in data["enrollments"] if e["student_id"] == student_id}
    current = sum(courses[c]["credits"] for c in selected)
    future = current + (0 if course_id in selected else target["credits"])
    seats = target["capacity"] - sum(e["course_id"] == course_id for e in data["enrollments"])
    conflicts = []
    if course_id in selected:
        conflicts.append({"type": "duplicate", "msg": "已選修此課程，不得重複加選。"})
    if seats <= 0:
        conflicts.append({"type": "capacity", "msg": "課程已額滿。"})
    if future > student["max_credits"]:
        conflicts.append({"type": "credit", "msg": f'學分上限: {student["max_credits"]}，加選後: {future}'})

    # Retain one entry per occupying record instead of overwriting by time slot.
    occupied = []
    for other in data["courses"]:
        if other["course_id"] == course_id:
            continue
        if other["course_id"] in selected:
            occupied.append(("student", other["course_id"], other["name"], other["time_slots"], None))
        if other["classroom"] == target["classroom"]:
            occupied.append(("room", other["course_id"], other["name"], other["time_slots"], None))
    activities, problems = project_activities(data["activities"], period_times)
    errors.extend(problems)
    for activity in activities:
        for kind, applicable in (("activity", student_id in activity["participant_ids"]),
                                 ("room_activity", activity["classroom_id"] == target["classroom"])):
            if applicable:
                occupied.append((kind, activity["activity_id"], activity["name"],
                                 activity["time_slots"], activity["date"]))
    labels = {"student": "與已選課程衝突", "room": "教室課程衝突",
              "activity": "與已參加活動衝突", "room_activity": "教室活動衝突"}
    timed = []
    for day, period in target["time_slots"]:
        for kind, identifier, name, slots, activity_date in occupied:
            if [day, period] in slots or (day, period) in slots:
                message = f"星期{day}第{period}節：{labels[kind]} ({identifier} {name})"
                if activity_date:
                    message += f" 日期 {activity_date}"
                timed.append(dict(type=kind, day=day, period=period, id=identifier,
                                  date=activity_date, msg=message))
    timed.sort(key=lambda c: (c["day"], PERIODS.index(c["period"]), c["id"], c["type"]))
    conflicts.extend(timed)
    errors.extend(c["msg"] for c in conflicts)
    return {"ok": not errors, "data": dict(conflicts=conflicts, current_credits=current,
            future_credits=future, max_credits=student["max_credits"], remaining_seats=seats),
            "errors": errors}


def add_enrollment(student_id, course_id, data, period_times=None):
    """Return a new enrollment list after all checks; caller persists before commit."""
    result = check_enrollment(student_id, course_id, data, period_times)
    if not result["ok"]:
        return {"ok": False, "data": None, "errors": result["errors"]}
    records = deepcopy(data["enrollments"])
    records.append({"student_id": student_id, "course_id": course_id})
    return {"ok": True, "data": records, "errors": []}


class F2CourseChecker:
    """Tuple-returning adapter; explicit enrollments replace legacy embedded fields."""

    def __init__(self, students_data, courses_data, classrooms_data, enrollments_data,
                 activities_data=None, period_times=None):
        self.data = dict(students=students_data, courses=courses_data, classrooms=classrooms_data,
                         enrollments=enrollments_data,
                         activities=activities_data if activities_data is not None else [])
        self.period_times = period_times

    def check_course_selection(self, student_id, target_course_id):
        """Return (allowed, message); successful checks do not enroll or save."""
        result = check_enrollment(student_id, target_course_id, self.data, self.period_times)
        if result["ok"]:
            return True, "檢查通過，尚未加選或存檔。"
        output = [f"學生:{student_id}", f"欲加選:{target_course_id}", "選課結果:失敗"]
        output.extend(f"衝突{i}:{error}" for i, error in enumerate(result["errors"], 1))
        if result["data"] is not None:
            stats = result["data"]
            output.extend([f'目前學分:{stats["current_credits"]}',
                           f'加選後學分:{stats["future_credits"]}',
                           f'學分上限:{stats["max_credits"]}'])
        return False, "\n".join(output)
