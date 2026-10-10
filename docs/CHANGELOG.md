# SmartTimetable Pro — Changelog

## 2026-10-10

### Solver / data integrity
- Fixed: solver now excludes school-wide LRs (no IG) and no-LR teachers
  from the problem set
- Fixed: loader requires full parent chain `is_active=True` (subject,
  IG, TG)
- Added: cascade signals — `TeachingGroup.is_active`, `Subject.is_active`,
  `Teacher.is_active` propagate to child LRs on every save
- Cleaned: Form 4 forbidden subjects removed (COMP, MUSD, CRA, CSL, ICT,
  PPI)
- Cleaned: duplicate STANDALONE + BLOCK rows for the same subject removed
- Cleaned: Form 4 practicals folded into parent subject rows
- Cleaned: EMCM split into ESS (East) / CORE (West)
- Corrected: LR `lessons_per_week` values per business contract
- Corrected: Grade 9E trimmed from 42 to 34 periods
- Seeded: Grade 11E / 11W with 20 students each

### Performance
- Analytics: `grade_for()` now caches grading bands (67s → 4s on teacher
  view, 22s → 1.7s on school view)
- Analytics: `.values()` queries replace model instances
- Analytics: `_by_teacher` rewritten from O(N×M) to single-pass
- Analytics: teacher view at 2.7s after further optimization

### Features
- Teacher management: free-afternoon dropdown, Retire / Reactivate,
  delete-guard on active LRs, ROLE_OPTIONS synced with backend
- Duty Roster: weekly model, day/night shifts, day-only preferences,
  auto-rotate
- Merge Teachers: scan + FK-relink + deactivate
- Teacher analytics: class drill-down with radar + breakdown
- Student drill-down with chart-type switcher
- Live activity with WebSocket push
- ConfirmDialog floating modal
- Toast bridge for axios

### Security
- `DEFAULT_PERMISSION_CLASSES` now `IsAuthenticated` (fail-closed)
- Global throttles: `AnonRateThrottle`, `UserRateThrottle`
- `LoginRateThrottle` class (3/min) created, wiring pending
- Prod security block gated on `DEBUG=False`

### Documentation
- Initial `docs/PROJECT_STATUS.md`
- Initial `docs/REQUIREMENTS_REGISTER.md`
- Initial `docs/CHANGELOG.md`
