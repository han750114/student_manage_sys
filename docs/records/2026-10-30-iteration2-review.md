# Iteration 2 repair and verification record

Date: 2026-10-30. Author: Codex, working with the requesting user.
Base commit: `89b4856`; fixes are in the working tree. No commit, merge or push
was created. The pre-existing change in `data/students.json` (missing final
newline) was preserved. No application data file was changed by this repair.

## Request and confirmed scope

The user first requested an Iteration 2 review, then a file change list, then
authorized resolving the reported problems with minimal runnable code changes.
The review found F2 diverged from F1 enrollment data, mutated input records,
overwrote conflicts, and was not connected to the CLI; F3 lacked activity
integration. Documentation and delivery records were also inconsistent/missing.

The user selected the proposed activity rules: explicit actual period times,
dated activities, no cross-midnight support, gap periods between the day's
first and last courses, and activity occupancy excluded from free time. This
is session authorization, not a fabricated team meeting or reviewer approval.

## Completed and not completed

- Completed: F2 derives all selection state from enrollments, validates the
  shared snapshot, preserves inputs, reports every source conflict, and rejects
  duplicate selections. Check-only and actual add/save operations are separate.
- Completed: F3 and F2 share activity projection and half-open overlap checks.
  Weekly activity filtering, multiple occupants, free runs and course-only
  credits/period counts are covered by tests.
- Completed: CLI selection and all timetable queries, save-failure rollback,
  restart/reload integration, updated requirements/interfaces and progress.
- Not completed: F4 CRUD/registration/allocation, F5, semester/holiday dates,
  equipment/capacity design and full F1-F6 acceptance. F4 interfaces remain draft.
- Team work still required: actual non-author teammate review, meeting attendees,
  photo, individual contributions/Git records, and team acceptance. No names,
  feedback, commits or meetings have been invented here.

## Defects and dispositions

| Defect | Resolution | Regression evidence |
|---|---|---|
| F2 ignores enrollments | Derive selected IDs, credits and course seat count | `test_enrollments_drive_all_three_restrictions` |
| Constructor mutates caller data | Keep read-only references; derive instead of inserting fields | `test_constructor_and_check_preserve_all_inputs` |
| Same-slot entries overwrite one another | Keep per-record occupancy entries | `test_same_slot_reports_every_course`, `test_same_room_slot_reports_all_occupying_courses` |
| Course/activity room and student conflicts missing | Shared dated activity projection and complete source reporting | `test_activity_reports_student_and_room_conflicts` |
| No end-to-end usable v2 | Add CLI selection and timetable submenus, reuse atomic save | `test_selection_cli_restart_and_timetable` |
| Check claims enrollment success without saving | Explicit check-only message; save through a separate operation | `test_check_only_does_not_persist` |
| Activities absent from week/free-time queries | Date-filtered occupancy and explicit clocks | `test_activity_only_in_its_week`, `test_partial_overlap_occupies_period_and_blocks_free_run` |
| Activity slots count as course periods/gaps | Course-only statistics, exclude occupied gaps | `test_summary_counts_classes_and_excludes_activity_from_gaps` |
| Malformed scheduling records could fail core processing | Validate snapshot/record shape and activity references | `test_invalid_records_and_queries_return_errors`, `test_invalid_activity_blocks_writable_session_and_preserves_file` |

## Actual test-first checkpoints

These are observations from this repair session, not reconstructed historical
team TDD. The implementation/test files in the working tree are the reviewed
version; there are no intermediate commits to cite.

| Stage | Command / observation | Actual result |
|---|---|---|
| Baseline | `python -B -X utf8 -m unittest discover -s tests -v` | 58 tests, OK, before new regression cases |
| Initial Red | `python -B -X utf8 -m unittest tests.test_f2 tests.test_f2_f3_integration tests.test_activity_timetable -v` | 3 loader errors: new enrollment API not implemented yet; behavioral tests could not run |
| F2 implementation | `python -B -X utf8 -m unittest tests.test_f2 -v` | 26 tests, OK at that checkpoint |
| Activity/CLI Red | `python -B -X utf8 -m unittest tests.test_activity_timetable tests.test_f2_f3_integration -v` | 19 tests, 6 failures and 11 errors; activity signature/handling and CLI not implemented yet |
| Initial integration Green | Affected F2/F3/activity/integration suites | 65 tests, OK at that checkpoint |
| Additional validation Red | `python -B -X utf8 -m unittest tests.test_activity_timetable.ActivityTimetableTests.test_invalid_records_and_queries_return_errors -v` | 1 test failed: malformed enrollment was accepted |
| Validation fix and additional regressions | Affected suites, including existing F3 tests | 75 tests, OK |
| Full regression | `python -B -X utf8 -m unittest discover -s tests -v` | 110 tests, OK |

Shared snapshot validation was extracted from `load_system` and reused for F2;
activity scheduling was placed in one small shared module. Existing F1 storage,
management and validation code behavior was retained. This record does not claim
an independently recorded full historical Red/Green/Refactor cycle or human review.

Final non-test checks: a real `main.py` subprocess completed a read-only selection
check for S001/CS101, displayed the empty timetable and zero-credit statistics,
then exited with code 0; all five application JSON byte sequences were unchanged
before/after. UTF-8 readback, Markdown HTML rendering/table structure, balanced
code fences and relative file links passed for all seven changed Markdown files.
`git diff --check` passed. Browser screenshot verification could not run because
the browser tool returned `The browser access host is unavailable`; no visual
inspection is claimed. No application setup or security setting was changed.

## AI collaboration and verification

- Review prompt: inspect the current Iteration 2 content. AI compared README,
  interfaces, code, tests and Git differences, then ran tests and isolated
  counterexamples. The existing 58 green tests were insufficient to prove F2
  integration because their fixtures duplicated cached state instead of using
  the persisted data model. That acceptance conclusion was rejected.
- Follow-up prompt: list files, then resolve all reported issues with minimal
  runnable changes. The user clarified activity rules. Adopted changes were
  checked through direct core calls and CLI tests in temporary directories.
- Test evidence: the tests check expected selections, all conflict IDs/types,
  ordering, actual persisted/reloaded data, and unchanged files/memory after
  rejection/save failure. Synthetic period times are explicit test inputs.
- Remaining team action: members should explain these data flows themselves,
  review the diff and reproduce the tests before accepting the iteration.

## Next iteration

Use the current F4 draft signatures to agree activity management/registration,
room equipment and availability rules. Reuse `scheduling` for overlap behavior
and keep enrollment state authoritative. Assign a real owner and a different
teammate reviewer, then record their actual feedback and verification.
