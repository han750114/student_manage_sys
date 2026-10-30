# F2/F3 integration and operation

Updated 2026-10-30. This describes the working tree implementation, not a
teammate approval or full F1-F6 acceptance. F1 record formats remain as documented
in [f1_interfaces.md](f1_interfaces.md).

## Data flow and persistence

`load_system` reads and validates the existing five stores. `enrollments` is the
only selection source. F2 derives student selections, credits and occupied seats
from those records. It never inserts cached fields into students or courses.

`check_enrollment` is read-only. `add_enrollment` returns an independent new
enrollment list after a successful check. The CLI uses the existing `save_result`:
save one JSON file atomically first, then replace the in-memory list. Validation
or save failures preserve the files and the in-memory selections. A subsequent
F3 query uses that same selection list, including after restarting the program.

## Interfaces

All result functions below return `{"ok": bool, "data": ..., "errors": list[str]}`.
Core functions do not prompt, print or write files.

| Function | Input | Output / error behavior |
|---|---|---|
| `system_data.validate_system(data)` | Five-store dictionary | Error strings; no I/O or mutation. Shared with `load_system`. |
| `conflicts.check_enrollment(student_id, course_id, data, period_times=None)` | Existing F1 records and optional explicit clock mapping | `data` contains `conflicts`, `current_credits`, `future_credits`, `max_credits`, `remaining_seats`. Invalid records/IDs return `data=None`; all decidable restrictions are collected after validation. |
| `conflicts.add_enrollment(student_id, course_id, data, period_times=None)` | Same input | A new enrollment list, or `data=None` and errors. Caller saves before committing. |
| `timetable.build_timetable(student_id, data, week_start=None, period_times=None)` | Student, shared records, optional Monday date and mapping | 12 rows by 7 columns; errors include unknown student, missing course, malformed slot, bad activity configuration and overlapping occupants. |
| `timetable.get_day(grid, day)` | Built grid, weekday 1-7 | Occupied `(period, cell)` pairs. |
| `timetable.get_cell(grid, day, period)` | Built grid and a valid slot | Cell or `None` for free time. |
| `timetable.find_course_slots(grid, course_id)` | Built grid and course ID | Course slots sorted by day, then period; activity IDs do not match courses. |
| `timetable.find_free_slots(grid, query=None)` | Built grid; optional days, start/end period, min_length | Maximal consecutive unoccupied runs, checked separately for each requested day. |
| `timetable.summarize_timetable(student_id, data, grid)` | Matching student/data and successfully built grid | Course periods per day, weekly course credits and free gap periods per day. |

`F2CourseChecker(students, courses, classrooms, enrollments, activities=None,
period_times=None)` remains a tuple-returning adapter. Its fourth argument is
now required so missing enrollment data cannot silently mean no selections.
`check_course_selection` returns `(allowed, message)`. A successful message says
the check passed and nothing was enrolled or saved. The old embedded selection,
credit and enrollment-count fields are unsupported; all callers/tests were
updated to the existing persisted format. The broken root-file demonstration
was removed; use `python main.py` from the project root.

Every conflict retains its source ID. Timed entries contain `type`, `day`,
`period`, `id`, `date` (null for recurring courses), and `msg`. Timed conflicts
sort by weekday and `1..9,a,b,c`, with deterministic ID/type ties. Duplicate
selection, capacity and credit errors precede timed entries. No same-slot
record is overwritten while collecting F2 conflicts.

## Activity scheduling rules

The user explicitly confirmed these integration rules in this session:

- Use actual dates/start/end times from activities and explicit caller-supplied
  period times. No school clock times are assumed.
- Cross-midnight activities are rejected for this iteration.
- Gap statistics count unoccupied periods between the first and last course
  of each day. Activities occupy time but add no course credits or course periods.

The supported scheduling subset is `activity_id`, `name`, `date`, `start_time`,
`end_time`, `classroom_id`, `participant_ids`, and `status`. IDs/names/room IDs
are nonempty strings, dates are `YYYY-MM-DD`, times are `HH:MM`, participants
are unique existing student IDs, and rooms must exist. Activity IDs are unique.
Scheduled activities use `scheduled`; `cancelled` activities occupy no time.
Additional draft F4 fields are retained but do not imply capacity/equipment
allocation or registration has been implemented.

`period_times` maps every string in `1..9,a,b,c` to `[start_time, end_time]`
(tuples are also accepted). Intervals must be increasing and non-overlapping
within one day; gaps are allowed. It is an execution parameter, not a sixth
store. The CLI asks for all twelve intervals when scheduled activities exist.
Input is local to the operation and must be provided again on the next entry.

Both F2 and F3 use `scheduling.project_activities` and `intervals_overlap`.
Intervals are half-open `[start, end)`: a touching end is not an overlap, and
any partial overlap occupies that period. F2 checks all supplied scheduled
activity dates against recurring weekly courses; semester/holiday filtering
is not invented while those dates remain undecided. Supply the applicable
activity dataset. F3 requires a Monday query date when scheduled activities
exist and includes only dates in that seven-day window and the student's
participations. Cancelled activities are ignored. An activity entirely outside
the configured period intervals occupies no matrix cell; the original record
is preserved.

Cells are `None` or dictionaries with `kind` (`course`/`activity`), `id`, `name`.
Activity cells also carry date/start/end times. Multiple activities within one
period are retained in `items`; real interval overlaps are reported as errors,
while touching or disjoint activities in that same period are retained without
a false conflict. The CLI prints all items. Course/activity collisions preserve
the course as the primary cell, retain additional items, and return errors.
Callers must check `ok` before using a partial grid for queries/statistics.

## CLI

Run `python main.py` from the repository root:

1. Existing course/student management remains at options 1 and 2.
2. Option 3 opens selection checks. Sub-option 1 checks only; sub-option 2
   checks and saves the new selection. Enter an existing student/course ID.
3. Option 4 asks for a student and optional query-week Monday. When scheduled
   activities exist, enter the date and explicit period times (`HH:MM-HH:MM`).
4. The timetable submenu offers the full grid, weekday query, cell query,
   course query, consecutive free runs, and statistics.
5. Use 0 to return/exit. Invalid numeric/query input reports an error without
   terminating the session. EOF/Ctrl+C uses the existing orderly exit handling.

## Verification and remaining work

Tests use in-memory fixtures or temporary directories; application JSON is not
rewritten. See [tests/README.md](../tests/README.md) for the command and category
mapping, and the [session record](records/2026-10-30-iteration2-review.md) for
actual repair/test checkpoints.

F4 CRUD, room allocation, activity signup and its capacity/equipment checks,
F5, semester/holiday rules and F7-F11 remain outside this integration. Existing
F4 interface declarations in `modules/activities.py` are still a draft, not an
implemented module. A teammate review, meeting/photo records and personal work
records must be supplied by the actual team; AI records do not replace them.
