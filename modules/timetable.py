"""F3: weekly timetable (12 periods x 7 days) and free-slot queries.

timetable[period_index][day_index]; empty cell = None.
Functions return {"ok", "data", "errors"} like F1.
"""

PERIODS = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c")
DAYS = 7


def _result(data, errors):
    """Build the team's standard result dict."""
    return {"ok": not errors, "data": data, "errors": errors}


def period_to_index(period):
    """Convert period "1"-"9", "a"-"c" to row index 0-11, or None if invalid."""
    if not isinstance(period, str) or period not in PERIODS:
        return None
    return PERIODS.index(period)


def day_to_index(day):
    """Convert weekday 1-7 to column index 0-6, or None if invalid."""
    if type(day) is not int or not 1 <= day <= 7:
        return None
    return day - 1


def create_empty_timetable():
    """Return a new 12 x 7 grid filled with None."""
    return [[None] * DAYS for _ in range(len(PERIODS))]


def get_student_course_ids(student_id, enrollments):
    """Return course IDs selected by student_id (no duplicates)."""
    course_ids = []
    for record in enrollments:
        if record.get("student_id") != student_id:
            continue
        course_id = record.get("course_id")
        if course_id not in course_ids:
            course_ids.append(course_id)
    return course_ids


def build_timetable(student_id, data, week_start=None):
    """Build one student's weekly timetable.

    Input: student_id; data with "students", "courses", "enrollments";
           week_start reserved for activities (pending team decision).
    Output: 12 x 7 grid, cell = {"kind": "course", "id": ..., "name": ...}.
    Errors: unknown student, missing course, invalid time slot.
    """
    errors = []
    students = data.get("students", [])
    if not any(s.get("student_id") == student_id for s in students):
        return _result(None, ["學生不存在：" + str(student_id)])

    course_ids = get_student_course_ids(student_id, data.get("enrollments", []))
    courses = {c.get("course_id"): c for c in data.get("courses", [])}
    grid = create_empty_timetable()

    for course_id in course_ids:
        course = courses.get(course_id)
        if course is None:
            errors.append(f"課程不存在：{course_id}")
            continue
        for slot in course.get("time_slots", []):
            if not isinstance(slot, (list, tuple)) or len(slot) != 2:
                errors.append(f"{course_id} 時段格式錯誤：{slot}")
                continue
            day, period = slot
            row, col = period_to_index(period), day_to_index(day)
            if row is None or col is None:
                errors.append(f"{course_id} 無效時段：{slot}")
                continue
            if grid[row][col] is not None:
                other = grid[row][col]["id"]
                errors.append(f"時段衝突：星期{day}第{period}節 {other} 與 {course_id}")
                continue
            grid[row][col] = {"kind": "course", "id": course_id, "name": course.get("name")}

    return _result(grid, errors)


def get_cell(timetable, day, period):
    """Return what occupies (day, period); data is None if free."""
    row, col = period_to_index(period), day_to_index(day)
    if row is None or col is None:
        return _result(None, [f"無效時段：星期{day}第{period}節"])
    return _result(timetable[row][col], [])


def get_day(timetable, day):
    """Return [(period, cell), ...] for every occupied period of one day."""
    col = day_to_index(day)
    if col is None:
        return _result(None, [f"無效星期：{day}"])
    used = []
    for row, period in enumerate(PERIODS):
        cell = timetable[row][col]
        if cell is not None:
            used.append((period, cell))
    return _result(used, [])


def find_course_slots(timetable, course_id):
    """Return all (day, period) of course_id, ordered by day then period."""
    slots = []
    for col in range(DAYS):
        for row in range(len(PERIODS)):
            cell = timetable[row][col]
            if cell is not None and cell.get("id") == course_id:
                slots.append((col + 1, PERIODS[row]))
    return _result(slots, [])


def find_free_slots(timetable, query=None):
    """Find runs of consecutive free periods (each day checked separately).

    query (optional keys): "days" (list, default 1-7), "start_period",
    "end_period" (default "1" and "c"), "min_length" (default 1).
    Output: [{"day": 2, "start": "5", "end": "7", "length": 3}, ...]
    """
    query = query or {}
    days = query.get("days", list(range(1, DAYS + 1)))
    start = query.get("start_period", PERIODS[0])
    end = query.get("end_period", PERIODS[-1])
    min_length = query.get("min_length", 1)

    errors = []
    if not isinstance(days, list) or any(day_to_index(d) is None for d in days):
        errors.append(f"無效星期：{days}")
    start_row, end_row = period_to_index(start), period_to_index(end)
    if start_row is None or end_row is None:
        errors.append(f"無效節次：{start}～{end}")
    elif start_row > end_row:
        errors.append(f"開始節次不可晚於結束節次：{start}～{end}")
    if type(min_length) is not int or min_length < 1:
        errors.append(f"最少連續節數須為正整數：{min_length}")
    if errors:
        return _result(None, errors)

    runs = []
    for day in sorted(set(days)):
        col = day_to_index(day)
        run_start = None
        # Go one step past end_row so a run touching the end is still closed.
        for row in range(start_row, end_row + 2):
            free = row <= end_row and timetable[row][col] is None
            if free and run_start is None:
                run_start = row
            elif not free and run_start is not None:
                length = row - run_start
                if length >= min_length:
                    runs.append({"day": day, "start": PERIODS[run_start],
                                 "end": PERIODS[row - 1], "length": length})
                run_start = None
    return _result(runs, [])


def summarize_timetable(student_id, data, timetable):
    """Return periods per day, weekly credits and gap periods per day.

    Gap periods = free periods between the first and last class of a day
    (provisional definition, pending team confirmation).
    """
    periods_per_day = {}
    gaps_per_day = {}
    for col in range(DAYS):
        used_rows = [row for row in range(len(PERIODS)) if timetable[row][col] is not None]
        periods_per_day[col + 1] = len(used_rows)
        if len(used_rows) < 2:
            gaps_per_day[col + 1] = 0
        else:
            span = used_rows[-1] - used_rows[0] + 1
            gaps_per_day[col + 1] = span - len(used_rows)

    courses = {c.get("course_id"): c for c in data.get("courses", [])}
    credits = 0
    for course_id in get_student_course_ids(student_id, data.get("enrollments", [])):
        course = courses.get(course_id)
        if course is not None and type(course.get("credits")) is int:
            credits += course["credits"]

    return _result({
        "periods_per_day": periods_per_day,
        "total_periods": sum(periods_per_day.values()),
        "weekly_credits": credits,
        "gaps_per_day": gaps_per_day,
    }, [])