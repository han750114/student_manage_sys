# F4/F5 CLI integration

## Scope

The CLI exposes the existing F4 and F5 core functions using the same five stores
as F1-F3. This integration does not establish full Iteration 3 acceptance or
teammate review. No new school clock times, semester dates, equipment inventory,
or classroom availability rules are assumed.

## F4 menu and persistence

Main menu option `5` provides:

| Submenu | Operation | Persistence |
|---|---|---|
| 1 | `add_activity` | Save the returned activity list |
| 2 | `update_activity` | Save the returned activity list |
| 3 | `cancel_activity`, with confirmation | Save the returned activity list |
| 4 | `find_activities`, filtered by date, room, status and participant | Read only |
| 5 | `find_available_classrooms` for a proposed activity | Read only |
| 6 | `register_participant` | Save the returned activity list |

The activity form collects `activity_id`, `name`, `date`, `start_time`,
`end_time`, `capacity`, `classroom_id` and `required_equipment`. New activities
start with `participant_ids=[]` and `status="scheduled"`. Registration is a
separate operation. Existing additional activity metadata is preserved by updates.
The room-search form omits `classroom_id`, since the core checks each room.

Blank update fields retain their values. An equipment value of `-` clears the
equipment list. All twelve actual period intervals are requested for additions,
updates and room searches, including the first activity in an empty store.
`read_period_times(data, required=False)` retains existing F2/F3 behavior;
`required=True` also supports a proposed activity. Clocks are runtime values only.

Mutation results use the existing `save_result` path: atomically replace
`activities.json`, then update session data. Save failures preserve the original
file and in-memory state. Cancelled activities remain in the store.

## F5 menu and interface extension

Main menu option `6` provides three independent read-only operations:

1. Candidate filtering by desired/mandatory course IDs, forbidden slots and
   preferred weekdays. Preferred weekdays are annotations rather than exclusions.
   The CLI reports mandatory IDs absent from the resulting candidates.
2. Individual course feasibility for a student, including forbidden slots and the
   existing F2 enrollment restrictions. Success does not enroll the student.
3. Credit-range checking for an explicitly entered course list. Unknown and
   duplicate IDs are rejected. Blank credit bounds mean no bound; supplied bounds
   follow the existing positive-integer validation.

Candidate lists are alternatives, not complete schedules. Credit-range checks do
not check conflicts among the listed courses. Enrollment remains main menu `3`.

The core interface adds one backward-compatible optional argument:

```python
check_course_feasibility(student_id, course_id, data, constraints, period_times=None)
```

`period_times` is forwarded unchanged to `check_enrollment`; the CLI requests it
when scheduled activities exist. Existing four-argument calls remain valid when
there are no scheduled activities. The existing core result format is retained.

## Known limitations and pending work

- F4 registration and activity changes do not yet validate participants' course
  or other-activity conflicts. Classroom conflicts are checked separately.
- Deleting a student still does not protect activity participant references;
  this can prevent a subsequent startup. The relationship policy remains pending.
- Existing F4/F5 core input-validation defects from the review remain, including
  malformed equipment/participants and some invalid preference types. The new CLI
  collects typed values for its forms; direct core callers still need the fixes.
- F5's core individual check still does not enforce a custom `max_credits` in
  `constraints`. The CLI offers credit bounds through its separate credit-list
  operation; individual feasibility uses the student's stored credit ceiling.
- F5 still lacks a consolidated plan-level explanation of every unmet condition.
- Real classroom equipment data and availability semantics remain incomplete.
- `tests/storage_test.py` is still excluded by default unittest discovery.

## Verification

All CLI tests use temporary stores and synthetic clocks. Production data is not
written. `tests/test_f4_f5_cli.py` adds 24 tests covering activity creation,
registration, updates, cancellation, restart/timetable visibility, room conflicts,
equipment filtering, invalid input, full capacity, failed saves, F5 checks,
read-only behavior and optional-clock compatibility.

Executed on 2026-11-13:

| Command | Actual result |
|---|---|
| `python -B -X utf8 -m unittest tests.test_f4_f5_cli tests.test_f4 tests.test_f5 -v` | 124 passed |
| `python -B -X utf8 -m unittest discover -s tests -v` | 235 passed |
| `python -B -X utf8 -m unittest discover -s tests -p '*test*.py' -q` | 285 passed, including the 50 storage tests |

These results verify the tested paths, not full acceptance or resolution of the
known limitations. No TDD history or human review is claimed.
