"""Validate a complete F1 data snapshot before enabling writes."""
from .storage import load_records
from .validation import positive_integer, validate_course, validate_student
from .scheduling import validate_activity


def load_system(directory):
    """Load five stores; report all errors without rewriting any input file."""
    data, errors = {}, []
    for name in ('classrooms', 'courses', 'students', 'activities', 'enrollments'):
        data[name], problems = load_records(directory / f'{name}.json')
        errors.extend(problems)
    if errors:
        return data, errors
    return data, validate_system(data)


def validate_system(data):
    """Validate an in-memory five-store snapshot; return errors without mutation."""
    names = ('classrooms', 'courses', 'students', 'activities', 'enrollments')
    if not isinstance(data, dict):
        return ['系統資料須為字典。']
    errors = []
    for name in names:
        rows = data.get(name)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            errors.append(f'{name} 必須為物件清單。')
    if errors:
        return errors
    for name, key in [('classrooms', 'classroom_id'), ('courses', 'course_id'),
                      ('students', 'student_id')]:
        identifiers = []
        for index, row in enumerate(data[name], 1):
            identifier = row.get(key)
            if not isinstance(identifier, str) or not identifier.strip() or identifier in identifiers:
                errors.append(f'{name} 第 {index} 筆：無效或重複的代號。')
            identifiers.append(identifier)
            if name == 'courses':
                problems = validate_course(row, data['classrooms'])
            elif name == 'students':
                problems = validate_student(row)
            else:
                problems = [] if positive_integer(row.get('capacity')) else ['教室容量必須為正整數。']
            errors.extend(f'{name} 第 {index} 筆：{problem}' for problem in problems)
    student_ids = [row.get('student_id') for row in data['students']]
    course_ids = [row.get('course_id') for row in data['courses']]
    seen = []
    for index, row in enumerate(data['enrollments'], 1):
        pair = (row.get('student_id'), row.get('course_id'))
        if (set(row) != {'student_id', 'course_id'} or
                not all(isinstance(value, str) for value in pair) or
                pair[0] not in student_ids or pair[1] not in course_ids or pair in seen):
            errors.append(f'enrollments 第 {index} 筆：無效或重複的選課關係。')
        seen.append(pair)
    activity_ids = []
    room_ids = [row.get('classroom_id') for row in data['classrooms']]
    for index, row in enumerate(data['activities'], 1):
        problems = validate_activity(row)
        identifier = row.get('activity_id')
        if identifier in activity_ids:
            problems.append('活動代號不得重複。')
        activity_ids.append(identifier)
        if row.get('classroom_id') not in room_ids:
            problems.append('活動教室不存在。')
        participants = row.get('participant_ids')
        if isinstance(participants, list) and any(p not in student_ids for p in participants):
            problems.append('活動參加者不存在。')
        errors.extend(f'activities 第 {index} 筆：{problem}' for problem in problems)
    return errors
