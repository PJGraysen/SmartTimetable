# SmartTimetable Pro — Project Status

_Last updated: 2026-10-10_

## Where we are

Two timetable generations completed successfully (v1134, v1135). Diversity
target met (87.9% overall cell change). All hard constraints pass once
block-aware collision checks are applied.

## Completed workstreams

### Backend
- Teacher scoping (class/stream/dashboard/Marks Entry)
- Session scoping for all analytics endpoints (teacher sees own, admin sees all)
- Admin school analytics endpoint with class/stream/subject/teacher/term filters
- Auto-audit middleware (writes AuditLog for every successful mutation)
- Error envelope middleware (writes ErrorRecord + JSON response + toast)
- Live activity feed with WebSocket push (Channels + Daphne)
- Teacher management endpoints: create / edit / freeze / retire / reactivate /
  free-afternoon / bulk-assign / delete-guard
- Duty roster: weekly rotation, day/night shifts, day-only preferences,
  auto-rotate preview + apply
- Teacher merge tool: duplicate scan + FK-relink + audit-preserving deactivate
- Analytics performance: grading-band cache, `.values()` in school/teacher
  views, O(N×M) `_by_teacher` rewrite (67s → 4s → 2.7s)
- Cascade signals: TeachingGroup/Subject/Teacher `is_active` propagates to
  InstructionalGroups and LessonRequirements bidirectionally
- Solver loader hardening: excludes school-wide LRs, no-LR teachers,
  deactivated parent chain

### Data
- 20 teachers provisioned with correct LRs matching the business contract
- Grade 11E / 11W seeded with 20 students each (curriculum testing)
- LessonRequirements corrected per business contract:
  - Form 4: 41 periods (32 standalone + 2 blocks × 5/4)
  - Grade 10/11: 48 periods (28 standalone + 4 blocks × 5)
  - Grade 9: 34 periods
- EMCM split into ESS (East) / CORE (West)
- Duplicate LRs (STANDALONE + BLOCK for same subject) removed
- Form 4 forbidden subjects removed (COMP, MUSD, CRA, CSL, ICT, PPI)
- Form 4 practicals (BIOPRAC, CHEMPRAC, PHYPRAC) folded into parent LRs

### Frontend
- Role-based navigation with per-role sidebar items
- Teacher/principal/admin differentiated analytics views
- Class drill-down with radar + subject breakdown + top/focus cards
- Per-student drill-down with chart type switcher (Bar/Line/Pie)
- ConfirmDialog floating modal replacing window.confirm()
- Avatar initials, teacher card grid
- Toast bridge wired to axios interceptor

### Security (partial)
- `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]` (fail-closed default)
- Global `AnonRateThrottle` + `UserRateThrottle`
- `LoginRateThrottle` class created (3/min)
- Prod security block gated on `DEBUG=False` (HSTS, SSL redirect, secure cookies)

## Outstanding items

### Security (in progress)
- Login view throttle wiring (interrupted by an earlier patch conflict)
- LoginAttempt model exists but login_view instrumentation not landed
- Account lockout policy (3 fails → 15 min → email/phone verify) — agreed,
  not implemented
- Device fingerprint capture — agreed, not implemented
- Audit of the 4 remaining `AllowAny` views
- IDOR sweep on object-level fetches

### Solver
- Monday free-afternoon for 1 teacher (contract forbids it) — data cleanup
- `materialize_senior_school_requirements` command fails on missing PPI form

### Analytics
- Software: 4 remaining `[MISSING]` graders in perf test output

## Known false positives
- H01/H02/H03 collision checks in ad-hoc assessment script — block subjects
  legitimately share slots. Must exclude `requirement_type="BLOCK"` before
  counting collisions.
