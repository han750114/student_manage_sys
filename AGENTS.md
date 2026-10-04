# Project Agent Guidelines

These guidelines apply to this repository and its subdirectories.
Keep development consistent, core functions independently testable, and learning records traceable.
For tools that do not automatically load AGENTS.md, explicitly include this file in the task context.

## Before Making Changes

- Read [README.md](README.md) for assignment requirements, progress, and task scope.
- For data or interface changes, read [requirements](docs/requirements.md) and [data models](docs/data_model.md).
- Inspect current files and Git differences. Preserve teammates' work and avoid unrelated changes.
- Preserve assignment requirements. Draft specifications and examples do not imply team approval or implemented functionality.
- For unresolved rules affecting multiple modules, explain the options and impact and obtain clarification before implementing dependent behavior. Do not label drafts as approved without confirmation.
- Proceed with routine formatting and fixes within the authorized task without repeatedly requesting confirmation.

## Language and Documentation

- Write AGENTS.md, code comments, docstrings, and new technical development documentation in English by default.
- Keep README files and assignment requirements in Traditional Chinese so beginners can follow them.
- Preserve existing Chinese documentation unless its translation is requested; do not translate unrelated files.
- Keep identifiers in English. User-facing CLI language follows the team's requirements rather than the language of the source code.
- Respond in the user's requested language; English development conventions do not require English conversation.
- Save text files as UTF-8.

## Coding Convention v1

1. Use four spaces for indentation.
2. Use snake_case for functions and variables, and PascalCase for classes.
3. Do not use global variables to pass system data between core functions.
4. Validate input data before performing core processing.
5. Represent errors with explicit return results or appropriate exception handling. A single invalid record must not cause the entire system to terminate unexpectedly.
6. Plan normal, boundary, and error cases for every core function.

These six rules are the current team coding convention. The following sections describe how to apply them in this project.

## Structure and Interfaces

- Use syntax compatible with Python 3.10 or later; prefer the standard library.
- Use snake_case for module names as well.
- Keep menus, input(), and presentation in main.py; place core logic in modules/.
- Pass data through parameters and return results. Core functions must not depend on interactive input.
- Document inputs, outputs, and error behavior. Reuse established interfaces and return formats.
- Failed operations must not leave partial updates. Do not conceal failures with overly broad exception handling.
- Share validation and time-conflict functions instead of implementing inconsistent rules in each module.
- Update callers, relevant tests, and design documents when interfaces, fields, or dependencies change.

## Data and Time

- Store application data in data/. The five JSON files use UTF-8 and a top-level list.
- Follow field names and types in docs/data_model.md; do not introduce incompatible formats or rename fields independently.
- Resolve paths relative to the program or project location, not a teammate's absolute filesystem path.
- Use enrollments as the source of truth for course selections. Derive selected courses, total credits, and remaining seats from enrollment records.
- Weekdays are integers 1 through 7. Periods are strings ordered 1 through 9, a, b, c; do not sort them lexicographically.
- Use half-open time intervals [start, end) for overlap checks; check travel time separately.
- Add dated activities only to their applicable timetable week. Actual period times and semester dates still require team confirmation.
- Report malformed JSON and preserve the original file. Never silently replace damaged data with an empty list and overwrite it.
- Use temporary directories or separate fixtures for tests and demonstrations; do not overwrite application data.

Data and time details follow the current design drafts. Handle unresolved details as described under "Before Making Changes."

## Testing and Verification

- Put tests in tests/, use test_*.py filenames and unittest, and call core functions directly.
- Add meaningful normal, boundary, and error tests for functional changes. Documentation-only changes do not require new program tests.
- Run affected tests first; run the full suite for changes affecting multiple modules or interfaces.
- From the repository root, run:

```powershell
python -m unittest discover -s tests -v
```

- F1-F6 require at least 30 automated cases: at least 10 normal, 10 boundary, and 10 error/conflict cases.
- From course week 10 onward, use TDD for new core functionality and preserve actual Red, Green, Refactor, and Regression Test evidence.
- Zero discovered tests, syntax checks, or AI suggestions do not establish functional acceptance.
- After editing Markdown, read it back as UTF-8 and check headings, tables, code fences, and links. Inspect rendered output when rendering tools are available.
- Review Git differences before finishing. Report executed commands, actual results, and anything not verified.

## Progress and Collaboration

- Update README progress based on implemented and verified behavior. Scaffolds, examples, and empty templates do not count as completed features.
- Record specification and interface changes in docs/. Use the [record templates](docs/records/README.md) for actual meetings, reviews, AI collaboration, and TDD evidence.
- Never fabricate test results, team decisions, work dates, reviewer feedback, or TDD history.
- Explain what changed, why, and the main logic clearly enough for teammates to explain the code themselves.
- Arrange review by a teammate other than the original developer, as required by README. AI review does not replace teammate review.
- Do not create commits, push changes, or modify Git configuration unless requested.
