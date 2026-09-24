# SmartTimetable Pro - Progress Status

**Updated:** 2026-09-05 21:50 +03:00  
**Scope:** Grade 10 solver, API, and timetable UI integration

## Overall Position

The core Grade 10 implementation is substantially advanced and the current
backend/frontend changes are validated. A fresh timetable has **not** yet been
persisted because the live Term 1 input is genuinely infeasible with the
currently configured rooms and teacher assignments.

| Workstream | Status | Current position |
| --- | --- | --- |
| Day/period domain types | Complete | Fixed the `str`/`.value` crash. |
| Grade 10 block configuration | Complete | One canonical configuration defines the four elective blocks. |
| Within-class elective synchronization | Complete | Each block's subjects share the same day/period within 10E or 10W. |
| Cross-class elective synchronization | Pending | 10E and 10W are not yet constrained to use the same block slots. |
| Solver performance | Complete | Removed room permutation symmetry; live infeasibility now returns in about 10 seconds instead of timing out after 120+ seconds. |
| API teacher data | Complete | Nullable teacher fields now serialize safely. |
| Timetable cell rendering | Complete for actual cell data | The UI renders full actual subject/teacher codes for complete elective cells. |
| Metadata-driven frontend | Pending | The UI still hard-codes the class list, period grid, breaks, and block metadata. |
| Live timetable generation | Blocked by data | Four active rooms and current Grade 10 staffing do not form a feasible solution. |

## Completed Work

### 1. Fixed the scheduler crash

The failed run `840a5f31-22fb-4a4f-91a1-92720b69fe7c` initially reported:

```text
'str' object has no attribute 'value'
```

Root cause: `DjangoSchedulingLoader` converted day values to the domain
`DayOfWeek` enum, but left `Period.part_of_day` as a Django string. The
infeasibility diagnostic and validation paths correctly expected a domain
`PartOfDay` enum.

Completed changes:

- `backend/apps/scheduling/engine/infrastructure/django_loader.py` now
  normalizes `part_of_day` through `_coerce_part_of_day()`.
- Regression coverage verifies that loaded periods contain
  `PartOfDay.MORNING`, not only a string-equivalent value.
- The real Term 1 diagnostic path now completes rather than crashing.

The Unicode checkmark error from `test_gen.py` was a separate Windows
CP1252-console output issue. It masked the scheduler result but did not cause
the scheduler failure.

### 2. Restored one authoritative Grade 10 elective-block configuration

`backend/apps/scheduling/engine/application/grade10_parallel_blocks.py` is
now the single Grade 10 source of truth and defines:

| Block | Subjects | Shared slots per week |
| --- | --- | ---: |
| OPTION_1 | BIO / MUS / FRE | 5 |
| OPTION_2 | CHEM / PHY / LIT | 5 |
| OPTION_3 | GEO / HIS / CS | 5 |
| OPTION_4 | BUS / AGR | 5 |

This restores the missing
`GRADE10_PARALLEL_SUBJECT_TO_BLOCK` mapping that had previously caused
generation to fail.

The solver now consumes this configuration rather than maintaining empty,
duplicated local block constants. The Grade 10 academic-contract audit passes
against the current database representation.

### 3. Corrected physical lesson-capacity accounting

The active Grade 10 data contains 20 subject requirements per class:

- 84 independently persisted subject entries per class.
- 49 physical timetable cells per class after the four elective blocks are
  coalesced into shared slots.

The solver preserves 50 physical weekday slots, including Monday P1, then
reserves Monday P1 for Assembly. This leaves exactly 49 schedulable teaching
slots per class.

The infeasibility diagnostics now:

- Count an elective block once per shared cell rather than once per subject.
- Exclude Monday P1 from group, teacher, and room capacity calculations.
- Avoid incorrectly treating a teacherless placement as a hard infeasibility,
  because the domain model intentionally supports a null teacher.

### 4. Reduced solver search complexity while preserving room safety

The original model created a separate Boolean variable for every
lesson/teacher/slot/room combination. With four interchangeable rooms, this
created substantial room-permutation symmetry and caused long searches.

The revised solver:

- Creates variables for lesson/teacher/slot combinations only.
- Applies unavailable-room rules while building valid slot capacity.
- Enforces the number of simultaneously selected lessons in a slot to be no
  greater than the number of eligible rooms.
- Deterministically assigns a distinct eligible room to every selected lesson
  after CP-SAT solves.

This preserves room availability and no-room-clash behavior while reducing the
live Term 1 model from roughly 10,400 CP-SAT variables to:

```text
Assignment variables: 1,960
Total CP-SAT variables: 4,312
Constraints: 7,216
```

The production dimension audit now reports:

```text
ELIGIBLE TIMETABLE SLOTS: 49
EXPECTED VARIABLES: 1960
ACTUAL VARIABLES:   1960
MISMATCHED REQS:    0
RESULT: PASS
```

### 5. Improved the timetable API and UI

Backend API:

- `TimetableEntryResultSerializer` now safely returns `null` for a missing
  teacher or room display name instead of serializing Python implementation
  text.
- The API continues to provide each entry's actual `subject_code`,
  `teacher_code`, `employee_code`, room, group, day, and period.

Frontend:

- `frontend/src/pages/Timetable.tsx` now uses the authoritative block members
  `GEO/HIS/CS` and `BUS/AGR`.
- It renders full teacher codes such as `T019`; it no longer shortens them to
  numbers.
- A Grade 10 elective cell is displayed as a block only when the API actually
  supplies every expected subject in that exact class/day/period cell.
- Teacher codes are taken from those actual same-cell entries. The UI no
  longer fills a missing cell from another day, class, or global subject
  fallback.
- Incomplete historical cells remain visible as their actual individual
  entries instead of being presented as a fabricated complete block.

## Current Live Data Findings

No production database records were changed during this work.

The current Term 1 input has:

| Finding | Current state | Impact |
| --- | --- | --- |
| Active rooms | 4 | Insufficient in combination with current Grade 10 staffing. |
| FRE teacher assignment | Missing for 10E and 10W | The system can schedule teacherless FRE entries, but the UI correctly has no teacher code to display. |
| GST teacher assignment | Missing for 10E and 10W | The system can schedule teacherless GST entries, but the UI correctly has no teacher code to display. |
| T019 Grade 10 load | 34 subject entries across 10E and 10W | BUS, CS, ICT, and MUS assignments constrain the available room/teacher combinations. |
| Live solver result | `INFEASIBLE` in 9.89 seconds | No new timetable version was created. |

Read-only in-memory feasibility checks established that either of the following
restores a feasible solution:

1. Add one additional generic active room, for a total of five rooms.
2. Reassign either BUS, CS, or MUS for both Grade 10 groups away from T019 to
   a qualified active teacher.

With an in-memory fifth room, the solver found a feasible solution with all
168 subject entries and valid rooms assigned. No such room was created in the
database.

The current database has active but currently unassigned teachers:
`T002`, `T003`, `T008`, `T012`, `T013`, `T017`, and `T020`. Subject competence
and actual availability must be confirmed before assigning any of them.

## Integration Work Still Required

### Required before accepting a new Grade 10 timetable

1. Add the explicit cross-class hard constraint requested for Grade 10:
   matching elective blocks in 10E and 10W must use the same day/period slot.
   The current solver synchronizes subjects within each class's block, but not
   the matching block across the two classes.
2. Resolve the live resource/staffing infeasibility:
   activate an approved fifth room, or redistribute one of T019's BUS, CS, or
   MUS assignments to a qualified teacher.
3. Assign qualified active teachers to FRE and GST for both 10E and 10W if
   every displayed lesson must show a teacher code.
4. Run a new scheduling run and persist a new timetable version. Historical
   versions and failed runs must remain untouched.
5. Run the Grade 10 runtime audit against the new persisted version. Acceptance
   requires the exact shared slot sets for every elective block and all
   teacher/group/room rules to pass.

### Required for full backend/frontend authority alignment

The current UI uses the backend entries correctly, but it still contains
hard-coded presentation metadata:

- `DAYS`, `CLASSES`, `COLUMNS`, break placement, and Grade 10 block metadata
  are declared in `frontend/src/pages/Timetable.tsx`.
- The backend already exposes a `slots` payload, but the frontend does not yet
  build its timetable grid from it.
- The slot payload currently includes 50 physical slots, including Monday P1.
  The API should explicitly identify reserved/non-teaching slots so the
  frontend can render Assembly without counting it as teaching.

The next integration step should expose and consume authoritative timetable
metadata for active groups, periods, breaks/activities, reserved slots, and
Grade 10 block definitions. The frontend should then derive its grid and
labels solely from that API data.

## Validation Completed

| Validation | Result |
| --- | --- |
| Grade 10 database academic-contract audit | Pass |
| Production generation dimension audit | Pass |
| Affected backend test suite | 133 passed |
| Frontend production build | Pass |
| Frontend lint | Completed with pre-existing warnings; no errors |
| Real Term 1 solver diagnostic path | Completes without the previous `.value` crash |

## Repository State

- The implementation is currently uncommitted.
- The working tree contains the backend, frontend, tests, and this progress
  report described above.
- `django_loader.py`, `solver/model.py`, and `solver.py` already had local
  edits when this work began; the current changes build on that local work.
- Do not reset or discard the working tree before reviewing and committing the
  completed changes.

## Acceptance Gate

The Grade 10 timetable is accepted only after a newly generated, persisted
version demonstrates all of the following:

- 49 schedulable teaching cells per Grade 10 class.
- Monday P1 remains Assembly and is not a lesson.
- Each four elective blocks' members share exactly five slots within each
  class.
- Matching elective blocks for 10E and 10W share the same slots once the
  cross-class rule is implemented.
- Every displayed elective subject uses an actual API entry and shows its
  actual teacher code.
- No teacher, instructional-group, room, availability, or free-afternoon
  violations occur.

## v9 / Variable-Candidate Root Trace Status

### TimetableSlot architecture confirmed

The production `TimetableSlot` entity represents a physical timetable
coordinate rather than a group-owned slot.

Its production structure is:

`day + period_id + period_number + part_of_day`

The production slot builder creates the complete active teaching-period
universe for each weekday.

The resulting production timetable contains:

- 5 weekdays
- 10 teaching periods per weekday
- 50 physical timetable slots

`TimetableSlot` does **not** carry `instructional_group_id`.

This is intentional and must not be changed merely to attach group identity.

### Correct scheduling architecture

The root trace for group-aware scheduling is:

`LessonRequirement`
→ `instructional_group_id`
→ scheduling variable / candidate
→ `TimetableSlot`

The physical slot is therefore reusable by different instructional groups.
Group ownership is established by the scheduling variable/candidate layer,
not by modifying the physical slot entity.

### Grade 10 production demand

The production `SchedulingProblem` contains:

- `10E` = 84 periods/week
- `10W` = 84 periods/week

Therefore both Grade 10 streams retain the established curriculum
requirement contract of 84 periods/week each.

### Capacity-diagnosis correction

The previous diagnostic calculated:

`84 demand - 0 group-owned slots`

That equation is invalid for the production architecture.

The 50 physical timetable slots are not a single pool representing the
capacity of one instructional group.

Each instructional group can potentially occupy the same physical
day/period coordinates, subject to:

- teacher constraints
- room constraints
- curriculum requirements
- group conflict constraints
- institutional reservations
- other scheduling constraints

Therefore the previous `-84` slack result does **not** demonstrate zero
Grade 10 production capacity.

It was a diagnostic artifact caused by treating a physical
`TimetableSlot` as though it were group-owned.

### Current root-cause investigation target

The next diagnostic must inspect the actual production variable-generation
and candidate-generation path.

The investigation must establish:

1. Grade 10 lesson requirements enter variable generation with the correct
   `instructional_group_id`.
2. Every generated candidate retains that group identity.
3. Each candidate references the correct physical `TimetableSlot`.
4. Group conflicts are enforced at the variable / constraint layer.
5. Teacher constraints are applied without losing group identity.
6. Room constraints are applied without losing group identity.

A production defect should only be declared if the actual production
variable/candidate chain loses, substitutes, or corrupts
`instructional_group_id`.

### v9 execution-path correction

The first v9 diagnostic execution was launched from:

`C:\Projects\SmartTimetable\backend`

while the diagnostic assumed the current working directory was the project
root.

This caused:

`ModuleNotFoundError: No module named 'config'`

The failure occurred before the production loader was reached.

This is therefore classified as a diagnostic execution-path/import-root
problem, not as evidence of a Django production configuration defect.

The corrected diagnostic must explicitly resolve:

`C:\Projects\SmartTimetable`

as the project root and ensure the appropriate backend/project paths are
available for Django imports.

### Governance / safety status

This investigation remains read-only.

- No solver invoked.
- No database writes performed.
- No production source files modified.
- No GitHub repository accessed.
- No curriculum requirements altered.
- Grade 10 curriculum contract preserved.
- Form 3 curriculum contract preserved.
- Form 4 curriculum contract preserved.
- `TimetableSlot` architecture preserved.
- The invalid zero-group-slot capacity interpretation has been retired.
- Investigation remains focused on the production variable/candidate chain.

### Next diagnostic

The next production trace must follow actual generated scheduling
variables/candidates rather than attempting to infer group ownership from
`TimetableSlot`.

Relevant local production/test trace points include:

- `trace_actual_variable_generation.py`
- `trace_actual_variable_generation_v2.py`
- `trace_opt1_variable_generation.py`
- `trace_opt1_variables.py`
- `verify_senior_school_group_mapping.py`
- scheduling engine infrastructure tests
- solver variable/constraint tests

The next result must distinguish clearly between:

`physical slot identity`

and

`instructional group identity`

before any production code change is considered.
