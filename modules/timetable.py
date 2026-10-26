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
    # TODO 1: unknown student -> return _result(None, ["學生不存在：" + student_id])
    # TODO 2: course IDs from get_student_course_ids()
    # TODO 3: dict course_id -> course
    # TODO 4: grid = create_empty_timetable()
    # TODO 5: fill grid[row][col] for each [day, period]; what if already occupied?
    pass


def get_cell(timetable, day, period):
    """Return what occupies (day, period); None if free."""
    # TODO
    pass


def find_course_slots(timetable, course_id):
    """Return all (day, period) of course_id, ordered by day then period."""
    # TODO: loop days outside, periods inside.
    pass


def find_free_slots(timetable, query):
    """Find runs of consecutive free periods.

    query (optional keys): "days", "start_period", "end_period", "min_length".
    Output: [{"day": 2, "start": "5", "end": "7", "length": 3}, ...]
    """
    # TODO: validate query; count consecutive None per day.
    # Trap: a run that reaches end_period must still be recorded.
    pass


def summarize_timetable(student_id, data, timetable):
    """Return periods per day and weekly credits (free periods: pending)."""
    # TODO: credits count once per course, not once per slot.
    pass