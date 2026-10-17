"""Validate a complete F1 data snapshot before enabling writes."""
from .storage import load_records
from .validation import positive_integer, validate_course, validate_student


def load_system(directory):
    """Load five stores; report all errors without rewriting any input file."""
    data, errors = {}, []
    for name in ('classrooms', 'courses', 'students', 'activities', 'enrollments'):
        data[name], problems = load_records(directory / f'{name}.json')
        errors.extend(problems)
    if errors:
        return data, errors
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
    return data, errors
