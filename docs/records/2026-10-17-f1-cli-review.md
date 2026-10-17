# F1 review fixes and CLI integration

- Date: 2026-10-17. Starting commit: c373415.
- Request: fix the reported F1 review findings and connect main.py.
- Original issues: mutable inputs, editable duplicate IDs, duplicated enrollment
  sources, classroom object mismatch, invalid slot exceptions, stale interfaces,
  and undiscovered tests.
- Adopted choices: immutable identifiers; independent mutation results;
  authoritative enrollments; existing F1 field names retained; explicit failure
  results; whole-session write blocking on invalid persisted data.
- Empty legacy enrollment arrays were checked and removed. Other sample values
  are preserved; the detailed interface changes are in ../f1_interfaces.md.
- Red: before implementation, `python -m unittest discover -s tests -v` ran
  15 new tests and reported 8 failures and 5 errors. Invalid-slot subtests also
  exposed a TypeError. The course identity test initially passed because the
  old classroom mismatch rejected its input; the same test later exercised
  identity rejection with valid room objects.
- Green: after core fixes, the same command passed all 15 tests.
- Refactor: removed an unused CLI integer-input helper after consolidating
  field conversion in read_fields. Shared mutation/deletion helpers keep
  course and student result behavior consistent.
- Regression: `python -m unittest discover -s tests -v` passed 35 tests after
  the refactor. Existing four tests were relocated from __init__.py to
  test_management.py; the enrollment test now supplies actual enrollment records.
- Integration tests use temporary directories, not application data. They cover
  course/student CRUD and restart, persistence failures, deletion confirmation,
  corrupted files, invalid references, Unicode, EOF and Ctrl+C.
- Additional checks: actual load_system returned no errors; counts were 20
  courses, 15 students, 5 rooms and zero activities/enrollments. git diff --check
  passed with only line-ending conversion notices from Git.
- Not verified: full F1-F6 acceptance and its required test-category distribution,
  activity semantics, F2 conflict rules, or teammate review. No meeting, teammate
  approval, commit or push is claimed. Personal reflections remain for members.
