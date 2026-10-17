"""Validation for the current F1 JSON schema; return all record errors."""


def positive_integer(value):
    """Exclude bool, which Python otherwise treats as an integer."""
    return type(value) is int and value > 0


def validate_course(course, classrooms=None):
    """Validate a course against room objects or an explicit list of room IDs."""
    if not isinstance(course, dict):
        return ['課程必須為物件。']
    errors = []
    fields = {'course_id', 'name', 'credits', 'course_type', 'teacher', 'capacity',
              'classroom', 'time_slots'}
    unknown = set(course) - fields
    if unknown:
        errors.append(f'不支援的課程欄位：{sorted(unknown)}')
    for key in ('course_id', 'name', 'teacher', 'classroom'):
        if not isinstance(course.get(key), str) or not course[key].strip():
            errors.append(f'{key} 必須為非空字串。')
    for key in ('credits', 'capacity'):
        if not positive_integer(course.get(key)):
            errors.append(f'{key}（學分或人數上限）必須為正整數。')
    if course.get('course_type') not in ('必修', '選修'):
        errors.append('必選修必須為必修或選修。')
    slots = course.get('time_slots')
    if not isinstance(slots, list) or not slots:
        errors.append('至少需要一個上課時段。')
    else:
        seen = []
        for slot in slots:
            if not isinstance(slot, (list, tuple)) or len(slot) != 2:
                errors.append(f'無效時段結構：{slot}')
                continue
            day, period = slot
            if type(day) is not int or not 1 <= day <= 7:
                errors.append(f'無效星期：{day}')
            if not isinstance(period, str) or period not in '123456789abc' or len(period) != 1:
                errors.append(f'無效節次：{period}')
            if slot in seen:
                errors.append(f'重複時段：{slot}')
            seen.append(slot)
    if classrooms is not None:
        ids = [row.get('classroom_id') if isinstance(row, dict) else row for row in classrooms]
        if course.get('classroom') not in ids:
            errors.append('教室不存在。')
    return errors


def validate_student(student):
    """Require student identity, department/year label, and a credit limit."""
    if not isinstance(student, dict):
        return ['學生必須為物件。']
    errors = []
    unknown = set(student) - {'student_id', 'name', 'department', 'max_credits'}
    if unknown:
        errors.append(f'不支援的學生欄位：{sorted(unknown)}')
    for key in ('student_id', 'name', 'department'):
        if not isinstance(student.get(key), str) or not student[key].strip():
            errors.append(f'{key} 必須為非空字串。')
    if not positive_integer(student.get('max_credits')):
        errors.append('學分上限必須為正整數。')
    return errors
