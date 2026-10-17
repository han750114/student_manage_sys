# F1 implementation and interfaces

Updated 2026-10-17 after the user requested fixes and CLI integration. These are
implementation choices, not a claim of a team meeting or teammate approval.

## Current JSON format

- courses: course_id, name, credits, course_type, teacher, capacity, classroom,
  time_slots. IDs/names/teacher/classroom are nonempty strings. credits and
  capacity are positive integers excluding bool. course_type is 必修 or 選修.
  time_slots is a nonempty list of [day, period] pairs. Day is integer 1–7;
  period is a single string from 1–9, a, b, c. Duplicate slots are rejected.
  classroom references a classroom_id; the current F1 format uses one classroom
  per course. Per-slot room allocation remains future integration work.
- students: student_id, name, department (department/year label), max_credits.
  Strings must be nonempty; max_credits is a positive integer excluding bool.
- classrooms: classroom_id and positive integer capacity are required.
  Existing sample rooms have no building/equipment metadata; none is invented.
- enrollments: student_id and course_id only, both existing IDs; pairs are unique.
- activities: loaded as a JSON list of objects but not edited or semantically
  validated by the F1 CLI. Activity scheduling remains unimplemented.

The samples retained 20 courses, 15 students and 5 rooms. Empty
enrolled_students/enrolled_courses fields were removed after checking that all
were empty. Enrollments are authoritative for selections, credits and seats.
Old nonempty embedded arrays must be reconciled explicitly before import;
validators reject them instead of silently discarding relations.

## Core functions

All management functions return {ok: bool, data: list, errors: list[str]}.
Successful mutations return independent deep copies. Failed operations preserve
inputs. Records supplied directly to management must follow the validated schema;
load_system validates persisted data before the CLI can mutate it.

- add_course(courses, course_data, valid_classrooms)
- update_course(courses, course_id, update_data, valid_classrooms)
- remove_course(courses, course_id, enrollments=None)
- find_courses(courses, course_id=None, teacher=None, weekday=None,
  course_type=None, min_remaining=None, enrollments=None)
- add_student(students, student_data)
- update_student(students, student_id, update_data)
- remove_student(students, student_id, enrollments=None)
- find_students(students, student_id=None, name=None, department=None)

Identifiers are immutable in updates, preventing duplicate IDs and dangling
references. Deletion requires enrollment data and rejects referenced records.
Seat filtering also requires enrollment data. Single-condition query wrappers
remain available; find_courses_by_remaining_capacity accepts enrollments.
find_courses also accepts an old filter dictionary as its second argument,
with day translated to weekday; it now returns a result dictionary consistently.
Callers must use result['data'], not treat the result itself as a course list.

validate_course accepts room objects or a list of room ID strings. Actual room
capacity versus course capacity is not enforced here; the draft leaves that
joint rule unresolved. No F2 enrollment/time-conflict behavior is claimed.

## Persistence and CLI

load_records(path) returns (records, errors). Missing, corrupt, non-list and
non-object records are explicit errors. load_system(directory) validates IDs,
F1 records and enrollment references; errors block the whole writable session
and preserve original files. No partial valid subset is saved over bad data.

save_records(path, records) returns None or raises OSError/ValueError. It writes
a temporary file beside the destination, flushes it, and atomically replaces
one store. main.py updates memory only after successful persistence. Each CRUD
operation touches one store; no multi-file transaction is claimed.

main(data_dir=None) resolves data relative to the program by default. The optional
directory supports isolated tests. Menus offer course/student CRUD. Empty query
fields mean unrestricted; empty update fields retain existing values. IDs cannot
be edited. Deletion requires y. EOF/Ctrl+C exit; successful actions are already
saved. Output displays actual field names and derived values for inspection.

Full F1-F6 acceptance, the required normal/boundary/error distribution, F2-F5
integration, and review by a teammate remain separate requirements.
