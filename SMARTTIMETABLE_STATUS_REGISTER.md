# SMARTTIMETABLE PRO
# STATUS REPORT REGISTER
# Senior School Timetable Contract / Solver Validation

Status date: 2026-09-16
Project root: C:\Projects\SmartTimetable

This is the canonical consolidated status register for the SmartTimeTablePro
Senior School timetable implementation and validation work.

It records established historical findings, current evidence, open findings,
implementation state, and remaining validation work.

This document does not itself authorize production-code changes, database
writes, migrations, or solver execution.

---

## 1. RULES OF ENGAGEMENT

1. Whole-file replacements only.
2. Preserve approved architecture, curriculum contract, and feasibility
   objective.
3. No production changes without explicit authorization.
4. Closed defects stay closed unless new evidence reopens them.
5. Work from the actual production loader, solver, persistence path, and
   current data.
6. Every implementation is runnable / live, preferably one-run PowerShell.
7. Diagnostics are read-only unless a change is explicitly authorized.
8. No database writes except where explicitly authorized.
9. No migrations.

---

## 2. TOP-LEVEL STATUS

Production timetable generation is **end-to-end functional, acceptance-
certified, and UI-verified**.

The full pipeline is proven:

    loader -> CP-SAT solve -> FEASIBLE -> objective
           -> physical-cell projection -> persistence
           -> atomic commit -> active version -> API -> UI render

Active term (2026 - Term 1) has a persisted, active, contract-compliant
timetable generated through the UI. The block display renders as composite
per synchronized block on both Grade 10 and Senior School grids.

---

## 3. DEFECT CHAIN — ALL CLOSED

    STT-023     Grade 10 workload / physical-slot distinction
    STT-032     Block-clash representative-member soundness
    STT-032-D   Senior cross-class sync leaked loop variable
    RC#1        Contract period ordinal / raw-number mismatch
    RC#2        Form 4 TECHNICALS_APPLIED / HUMANITIES FRI-9 collision
    RC#3-B2     Synchronized Grade 10 teacher-event collapse
    P1          Persistence rejected teacher-less assignments
    P2          ValueError path left SchedulingRun RUNNING
    P3          Solver member-level vs persisted physical-cell mismatch
    P4-A        Teacher-event ownership duplication in persistence
    PF-1        Block DTO — API presentation contract for blocks
    PF-2        Frontend block rendering
    PF-3        Long-solve browser timeout on /execute/
    PF-4        Default solver time limit insufficient

Each closure carries its own evidence trail:
- pre-fix vs post-fix discrimination for code fixes
- regression tests re-run green at every stage
- production E2E revalidation after persistence-layer changes
- UI verification of final block display rendering

---

## 4. STT-023 — CLOSED

Historical 84/week LessonRequirement workload was conflated with the
current 49 physical teaching-slot contract for Grade 10. Historical
Subject-table count of 52 is unrelated. Current contract: 29 core/
standalone + 20 synchronized block = 49/week.

---

## 5. STT-032 / A / B / C / D — CLOSED

- STT-032: `_add_group_clash_constraints` now aggregates block presence
  via `model.add_max_equality` over all member presences (was: single
  representative). 6/6 tests, pre-fix discrimination confirmed.
- STT-032-D: `_add_senior_school_cross_class_synchronization_constraints`
  resolves per-class contract slots independently and raises
  `ValueError` on asymmetry. 2/2 tests.

---

## 6. RC#1 — CLOSED

`_contract_slot_keys` interpreted contract `period_number` as raw
`PeriodEntity.number`; contract uses teaching-period ordinals (Break /
Lunch excluded). Fixed with ordinal-aware mapping. 3/3 tests.

---

## 7. RC#2 — CLOSED

`FORM4_TECHNICALS_APPLIED_SLOTS` and `FORM4_HUMANITIES_SLOTS` both
contained `('FRI', 9)`. Both blocks are 4-for-4 rigid. Fixed by
replacing TECH entry `('FRI', 9) -> ('THU', 10)`. 4/4 tests.

---

## 8. RC#3 B2 — CLOSED

Grade-10 option blocks are synchronized between 10E and 10W. For each of
10 shared (block, subject) pairs, the same teacher is assigned the same
subject in both streams. Pre-fix: two distinct teacher-occupancy demands.

Fix: `_add_teacher_clash_constraints` accepts `problem` and collapses
synchronized same-teacher cross-stream block pairs to one representative
via `_synchronized_teacher_event_groups`. 6/6 tests.

---

## 9. P1 / P2 / P3 / P4-A — CLOSED

- P1: teacher-less persistence validation — filter None out of the
  teacher existence check. 2/2 tests.
- P2: SchedulingRun lifecycle — ValueError now routes through
  `_mark_failed`. 1/1 test.
- P3: physical-cell projection — `_build_entries` groups by
  (day, period, group) and keeps the deterministic minimum
  `lesson_requirement_id` (R1). 3/3 tests.
- P4-A: teacher-event de-duplication — rows sharing one teacher in a
  cell keep the teacher on the min-group row; siblings are written with
  `teacher_id=None`. 3/3 tests.

---

## 10. PF-1 — API BLOCK DTO — CLOSED

The API exposes a `block` DTO on `TimetableEntryResultSerializer` for
any entry whose subject belongs to a Grade 10 option block or a Senior
School elective block. Otherwise `block` is null.

Shape:

    block = {
      code: "OPTION_2" | "SCIENCE" | ...,
      namespace: "GRADE10" | "SENIOR",
      display: "CHEM / PHY / LIT",
      members: [
        { subject_code: "CHEM", teacher_code: "T005" },
        ...
      ],
      has_any_teacher: true | false
    }

Teacher resolution per member:
    1. TeacherAssignment for this entry's own group + subject
    2. else, TeacherAssignment for the paired stream's group + subject
    3. else, null  (never manufactured)

Implementation: new module
`apps/scheduling/engine/application/block_display.py` with pure
functions `resolve_block_membership` and `build_display`. The
serializer caches per (namespace, block_code, group_code) in
`self.context` to prevent N+1.

Tests: `tests/scheduling/api/test_timetable_block_display.py`, 5 tests:
- block DTO present for Grade 10 entry with teacher codes
- block DTO present for Senior entry, no teacher codes
- block DTO absent for standalone entry
- block DTO stable across 10E/10W for the same block
- no teacher is manufactured where the domain has none

All pass. Regression: 7 suites, 42 tests, all green.

---

## 11. PF-2 — FRONTEND BLOCK RENDER — CLOSED

`frontend/src/services/scheduling.ts`: added types
`TimetableBlockMember`, `TimetableBlockDisplay`, and `block` field on
`TimetableEntryResult`.

`frontend/src/pages/Timetable.tsx`: the cell render IIFE now reads
`entry.block` directly. When present, the cell displays
`block.display` and (if `block.has_any_teacher`) the joined member
teacher codes. Otherwise the cell falls back to `subject_code` /
`teacher_code` for standalone entries.

Verified visually: Grade 10 block cells display `BIO / MUS / FRE`,
`CHEM / PHY / LIT`, `GEO / HIS / CS`, `BUS / AGR` with member teacher
codes below. Senior block cells display `CHEM / BIO / PHY`,
`GEO / HIS`, `CRE / IRE`, `AGR / BUS / CS` with no teacher line.
Standalone subjects unchanged.

---

## 12. PF-3 — LONG-SOLVE BROWSER TIMEOUT — CLOSED

`Scheduling.tsx` previously awaited the `/execute/` HTTP call directly.
Long solves (>4 minutes) exceeded the browser's default request timeout,
so the catch block ran and the frontend never reached the timetable
refresh, leaving the grid on the previous version even though the
backend had completed successfully.

Fix: `generateTimetable()` now fires `/execute/` without blocking, then
polls `getSchedulingRuns()` every 4 s until the run reaches a terminal
status (`COMPLETED` / `FAILED` / `CANCELLED`), then calls
`loadData(true)` which bumps `timetableRefreshKey` and remounts the
Timetable component. Terminal failure still surfaces the backend
diagnostic.

Verified: subsequent UI generation cycles through `v86 -> v87` and the
grid refreshes.

---

## 13. PF-4 — DEFAULT SOLVER TIME LIMIT — CLOSED

`apps/scheduling/engine/application/scheduler.py` default was
`time_limit_seconds: float = 120.0`. The composite objective
(`BalancedTeacherWorkload` + `TeacherConsecutivePeriod`) sometimes
exceeded 120 s before finding a first feasible solution, producing
`UNKNOWN` outcomes.

Changed to `300.0`. All callers inherit via
`SchedulingApplicationService()`'s default constructor. Verified live:
`SchedulingApplicationService().scheduler.solver.time_limit_seconds == 300.0`.

---

## 14. PRODUCTION ACCEPTANCE AUDIT — PASS

Read-only acceptance audit against active versions consistently
reports PASS across all 26 areas:

    A.one_active_version          PASS
    A.run_linked                  PASS
    A.run_status_completed        PASS
    A.solver_feasible_or_optimal  PASS
    A.entries_nonempty            PASS
    A.no_dup_group_slot           PASS
    A.no_dup_room_slot            PASS
    A.no_dup_teacher_slot         PASS
    A.no_reserved_monday_p1       PASS
    C1.one_row_per_cell           PASS
    C2.p4a_teacher_dedup          PASS
    C3.room_dedup                 PASS
    C4.no_reserved_mon_p1         PASS
    C5.lesson_requirement_present PASS
    B.solve_feasible              PASS
    B1.coverage                   PASS
    B1.total_assignment_count     PASS
    B2.group_clash                PASS
    B3.teacher_clash              PASS
    B4.room_clash                 PASS
    B5.reserved_mon_p1            PASS
    B6.single_lesson_per_day      PASS
    B7.block_integrity            PASS
    B8.cross_class_sync           PASS
    D.serializer_render           PASS
    D.fk_resolve_all              PASS

---

## 15. DATABASE CLEANUP — STALE RUNS CANCELLED

15 stale PENDING/RUNNING SchedulingRuns from earlier sessions
(2026-08-21 through 2026-09-07) were marked CANCELLED. Records preserved;
error_message documents the reason and the fact that no version was ever
produced. No deleted rows. No affected timetable versions.

---

## 16. KNOWN DATA STATE — NOT DEFECTS

### 16.1 FRE has no TeacherAssignment in Term 1

The Grade 10 OPTION_1 block member FRE has no TeacherAssignment row for
10E or 10W in Term 1. The block DTO correctly reports
`teacher_code: null` for FRE and `has_any_teacher: true` (because the
other members do have teachers). The UI displays `-` for FRE's teacher.

This is a legitimate curriculum-configuration state — FRE is scheduled
without a teacher, the way the domain permits. The register records this
as intended, not as a defect.

### 16.2 Senior School teacher-less state (unchanged)

3E / 3W / 4E / 4W have no TeacherAssignment rows in Term 1. Their block
DTOs report `has_any_teacher: false` and the UI renders them with no
teacher line. Sanctioned by the existing data/model/test contract.

---

## 17. ARCHITECTURAL LIMITS — RECORDED, NOT DEFECTS

### 17.1 TimetableEntry.lesson_requirement is singular

For a multi-member synchronized block cell, only one representative
member (R1: minimum `lesson_requirement_id`) is persisted. Other members
are scheduled in the solver and share the same physical cell but are not
individually represented in `TimetableEntry`. The block DTO in the API
exposes the full block membership on every entry of that block, so the
UI has complete information; the persistence layer retains its
one-row-per-physical-cell model.

Full block-member **row-level** persistence remains a possible future
enhancement, requiring a schema change and its own authorization.

### 17.2 Teacher identity may be null in persisted rows

Under P4-A, when a physical teacher event is shared across two groups,
only one persisted row carries the teacher. The DTO's per-member teacher
resolution corrects for this at the API layer. Consumers that read
`TimetableEntry.teacher_id` directly must treat null as "see the sibling
row of the same physical cell."

---

## 18. CHANGE CONTROL STATE

Source-code changes applied this session:

    apps/scheduling/engine/solver/model.py
      STT-032      _add_group_clash_constraints (add_max_equality)
      STT-032-D    _add_senior_school_cross_class_synchronization_constraints
      RC#1         _contract_slot_keys (ordinal mapping)
      RC#3-B2      _add_teacher_clash_constraints (+ problem; subsumption)
      RC#3-B2      build() call site (problem= added)

    apps/scheduling/engine/application/grade10_parallel_blocks.py
      RC#2         FORM4_TECHNICALS_APPLIED_SLOTS  FRI-9 -> THU-10

    apps/scheduling/engine/application/timetable_persistence.py
      P1           _validate_assignments (None filter)
      P3 R1        _build_entries (physical-cell projection)
      P4-A         _build_entries (teacher-event de-dup)

    apps/scheduling/engine/application/scheduling_application.py
      P2           execute() ValueError -> _mark_failed

    apps/scheduling/engine/application/scheduler.py
      PF-4         create_default_scheduler time_limit 120.0 -> 300.0

    apps/scheduling/engine/application/block_display.py   (NEW)
      PF-1         pure block DTO builder

    apps/scheduling/api/serializers.py
      PF-1         TimetableEntryResultSerializer + block field

    frontend/src/services/scheduling.ts
      PF-2         block DTO types added

    frontend/src/pages/Timetable.tsx
      PF-2         block-aware cell render

    frontend/src/Scheduling.tsx
      PF-3         poll-based execute + refresh

Tests added this session:

    tests/scheduling/engine/solver/test_group_clash_constraints.py
    tests/scheduling/engine/solver/test_stt032d_cross_class_sync.py
    tests/scheduling/engine/solver/test_contract_slot_keys_ordinal.py
    tests/scheduling/engine/solver/test_rc2_tech_thu_slot.py
    tests/scheduling/engine/solver/test_rc3_sync_teacher_event.py
    tests/scheduling/engine/application/test_timetable_persistence.py  (P1, P3, P4-A)
    tests/scheduling/engine/application/test_scheduling_application.py  (P2)
    tests/scheduling/api/test_timetable_block_display.py                (PF-1)

Database writes:

    Authorized persistence runs producing timetable versions.
    Authorized cleanup marking 15 stale PENDING/RUNNING runs CANCELLED.
    No schema writes. No migrations. No curriculum or TeacherAssignment
    changes.

---

## 19. REGISTER CONTROL

Last updated: 2026-09-16

Register location: C:\Projects\SmartTimetable\SMARTTIMETABLE_STATUS_REGISTER.md

No status is promoted from pending/user-asserted to verified without
corresponding source evidence.

---
