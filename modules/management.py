"""Pure F1 operations. Results contain ok, data, errors; inputs stay unchanged."""
from copy import deepcopy
from .validation import validate_course, validate_student


def result(data, errors=()):
    """Build the common operation result."""
    return {'ok': not errors, 'data': data, 'errors': list(errors)}


def change_record(records, record, key, validate, target_id=None):
    """Validate an addition/update before constructing an independent result."""
    if not isinstance(record, dict):
        return result(records, ['資料必須為物件。'])
    target = None
    if target_id is not None:
        target = next((row for row in records if row[key] == target_id), None)
        if target is None:
            return result(records, ['找不到指定資料。'])
        if key in record and record[key] != target_id:
            return result(records, ['代號不可修改，以免破壞選課關聯。'])
    merged = {**(target or {}), **record}
    errors = validate(merged)
    if target is None and any(row[key] == merged.get(key) for row in records):
        errors.append('代號已存在。')
    if errors:
        return result(records, errors)
    updated = deepcopy(records)
    if target is None:
        updated.append(deepcopy(merged))
    else:
        index = next(i for i, row in enumerate(records) if row[key] == target_id)
        updated[index] = deepcopy(merged)
    return result(updated)


def add_course(courses, course_data, valid_classrooms):
    """Add a validated course with a unique ID."""
    return change_record(courses, course_data, 'course_id',
                         lambda row: validate_course(row, valid_classrooms))


def update_course(courses, course_id, update_data, valid_classrooms):
    """Update course fields; identity is immutable."""
    return change_record(courses, update_data, 'course_id',
                         lambda row: validate_course(row, valid_classrooms), course_id)


def add_student(students, student_data):
    """Add a student with a unique ID."""
    return change_record(students, student_data, 'student_id', validate_student)


def update_student(students, student_id, update_data):
    """Update student fields; identity is immutable."""
    return change_record(students, update_data, 'student_id', validate_student, student_id)


def remove_record(records, identifier, key, enrollments):
    """Reject deletion without authoritative enrollment data or with dependents."""
    if enrollments is None:
        return result(records, ['必須提供選課紀錄才能安全刪除。'])
    if not any(row[key] == identifier for row in records):
        return result(records, ['找不到指定資料。'])
    if any(row.get(key) == identifier for row in enrollments):
        return result(records, ['尚有學生選修或學生尚有選修課程，請先退選。'])
    return result(deepcopy([row for row in records if row[key] != identifier]))


def remove_course(courses, course_id, enrollments=None):
    """Delete only courses without enrollment references."""
    return remove_record(courses, course_id, 'course_id', enrollments)


def remove_student(students, student_id, enrollments=None):
    """Delete only students without enrollment references."""
    return remove_record(students, student_id, 'student_id', enrollments)


def find_courses(courses, course_id=None, teacher=None, weekday=None, course_type=None,
                 min_remaining=None, enrollments=None):
    """Return matching courses; accept legacy filter dictionaries during integration."""
    if isinstance(course_id, dict):
        filters = course_id
        unknown = set(filters) - {'course_id', 'teacher', 'day', 'weekday', 'course_type', 'min_remaining'}
        if unknown:
            return result([], ['不支援的查詢條件。'])
        return find_courses(courses, filters.get('course_id'), filters.get('teacher'),
                            filters.get('weekday', filters.get('day')), filters.get('course_type'),
                            filters.get('min_remaining'), enrollments)
    if weekday is not None and (type(weekday) is not int or not 1 <= weekday <= 7):
        return result([], ['星期必須為 1–7 的整數。'])
    if min_remaining is not None:
        if type(min_remaining) is not int or min_remaining < 0:
            return result([], ['剩餘名額必須為非負整數。'])
        if enrollments is None:
            return result([], ['名額查詢必須提供選課紀錄。'])
    rows = []
    for row in courses:
        if course_id and row['course_id'] != course_id:
            continue
        if teacher and teacher not in row['teacher']:
            continue
        if course_type and row['course_type'] != course_type:
            continue
        if weekday is not None and not any(slot[0] == weekday for slot in row['time_slots']):
            continue
        used = sum(e['course_id'] == row['course_id'] for e in (enrollments or []))
        if min_remaining is None or row['capacity'] - used >= min_remaining:
            rows.append(row)
    return result(deepcopy(rows))


def find_students(students, student_id=None, name=None, department=None):
    """Find students by exact ID and name/department substrings."""
    return result(deepcopy([s for s in students if
        (not student_id or s['student_id'] == student_id) and
        (not name or name in s['name']) and (not department or department in s['department'])]))


def find_courses_by_id(courses, course_id):
    return find_courses(courses, course_id=course_id)


def find_courses_by_teacher(courses, teacher):
    return find_courses(courses, teacher=teacher)


def find_courses_by_weekday(courses, weekday):
    return find_courses(courses, weekday=weekday)


def find_courses_by_type(courses, course_type):
    return find_courses(courses, course_type=course_type)


def find_courses_by_remaining_capacity(courses, min_remaining, enrollments=None):
    return find_courses(courses, min_remaining=min_remaining, enrollments=enrollments)
