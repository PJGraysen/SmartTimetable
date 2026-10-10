# SmartTimetable Pro — Requirements Register

Status legend: **IMPL** = implemented, **PART** = partial, **PLAN** = planned.

## Hard constraints

| ID  | Requirement | Status | Notes |
|-----|-------------|--------|-------|
| H01 | No class collision | IMPL | Solver enforces; ad-hoc check needs block-awareness |
| H02 | No teacher collision | IMPL | Same block-awareness caveat |
| H03 | No room collision | IMPL | Same block-awareness caveat |
| H04 | Required weekly lesson count | IMPL | Verified in v1134/v1135 (0 failures) |
| H05 | Teacher availability | IMPL | Loader scopes to `teacher_availability` |
| H06 | Exactly one free afternoon per teacher | IMPL | 21 teachers assigned; 1 Monday violation to clean |
| H07 | No teaching during free afternoon | IMPL | 0 violations in v1135 |
| H08 | Specialized room requirements | PART | Room model exists; no per-subject requirement enforced in solver yet |
| H09 | Fixed activities | PART | Assembly / prayers configured; contract for Grade 8/9 CAS missing |
| H10 | Monday–Friday only | IMPL | 0 invalid days in v1134/v1135 |
| H11 | Valid periods only | IMPL | Solver model |
| H12 | Room capacity | PLAN | Room.capacity field exists; not enforced |
| H13 | Teacher-subject assignment | IMPL | Loader filters by `teacher_assignments` |

## Soft constraints

| ID  | Requirement | Status | Metric |
|-----|-------------|--------|--------|
| S01 | Subject distribution (≤2 per day) | IMPL | Max observed = 2 |
| S02 | Avoid excessive consecutive | PART | Max 3–4 consecutive; target ≤3 |
| S03 | Reduce teacher gaps | PART | 174–206 gaps across week; high |
| S04 | Balanced teacher workload | IMPL | `BalancedTeacherWorkloadObjective` |
| S05 | Balanced class workload | PART | No explicit objective |
| S06 | Subject spacing | IMPL | Distributed via solver |
| S07 | Preferred teaching periods | PART | `MathsMorningPreferenceObjective` only |
| S08 | Room efficiency | PLAN | — |

## Rotational / pedagogical

| Requirement | Status | Metric |
|-------------|--------|--------|
| ≥70% cell change between versions | IMPL | 87.9% overall, 70.8–95.7% per class |
| Block rotation offset | IMPL | Per-generation offset applied |
| Science-Science adjacency reduced | PART | 4–6 pairs (v1134 6, v1135 4) |
| Science-Maths adjacency reduced | PART | 1–6 pairs |
| Maths in morning preference | IMPL | 100% |

## Business contract compliance

| Class | Weekly periods | Budget | Status |
|-------|---------------|--------|--------|
| Form 4E | 41 | 49 | PASS |
| Form 4W | 41 | 49 | PASS |
| Grade 10E | 48 | 49 | PASS |
| Grade 10W | 48 | 49 | PASS |
| G11E | 48 | 49 | PASS |
| G11W | 48 | 49 | PASS |
| Grade 9E | 34 | 34 | PASS |
