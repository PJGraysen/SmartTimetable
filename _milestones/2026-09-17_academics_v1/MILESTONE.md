# Milestone: Academics Module v1

**Date:** 2026-09-17

## Backend (apps/academics)

**Models**
- Student, StudentEnrollment
- Assessment, Result, ResultStatus, AssessmentType, AssessmentStatus
- GradingScheme, GradingBand (versioned)
- ReportComment (per student/term)
- RankingRule, RankingRun (versioned + snapshot)
- AcademicAuditEvent

**API** (mounted at /api/academics/)
- `students/` — CRUD + by-group + enrollments
- `assessments/` — CRUD + publish/archive/draft
- `results/roster/` `results/bulk/` — mark entry
- `grading-schemes/` `grading-bands/` — CRUD
- `report-comments/` + `report-comments/upsert/`
- `ranking-rules/` `ranking-runs/` + `ranking/preview/`
- `audit-events/`
- `analysis/dashboard/` `analysis/student-deep/<id>/` `analysis/classes/`
- `analysis/report-form/<id>/` `analysis/report-form-bulk/`

## Frontend

- `/academics` — management (existing)
- `/academics/students` — list + filter + edit
- `/academics/students/:id/analysis` — deep-dive
- `/academics/students/:id/report-card` — report card
- `/academics/students/:id/report-form` — school template
- `/academics/analysis` — statistical dashboard
- `/academics/classes` — class/stream comparison
- `/academics/assessments` — assessments CRUD
- `/academics/marks` — spreadsheet entry (editable total)
- `/academics/bulk-reports` — print whole class
- `/academics/audit` — audit trail
- `/academics/comments` — narrative comments
- `/academics/grading` — grading editor
- `/academics/ranking` — configurable ranking

## Data seeded

- 128 students × 5 classes (10E, 10W, 8E, 3E, 3W)
- 3 assessments × 8 subjects × 128 = 3,072 results
- 5 ranking rules, 1 grading scheme (5 bands)

## Architecture refactor (this milestone)

- Sidebar links extracted from `App.tsx` → `src/navigation.tsx`
- `App.tsx` becomes a stable shell — no future scripts need to patch it
- Adding a page = one line in `navigation.tsx` + one `<Route>` in `App.tsx`

## Known gaps (next milestones)

- Historical performance / cohort tracking (RoE §16)
- Early-warning system (RoE §24)
- Assessment workflow status transitions UI
- School branding config (name, logo per tenant)