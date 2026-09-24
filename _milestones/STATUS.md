# SmartTimetable · Project Status Report

**Updated:** 2026-09-20

---

## 1. Platform

| Component | Status |
|---|---|
| Django backend (SQLite dev / Postgres prod) | ✅ Running |
| Vite + React frontend | ✅ Running |
| Local AI via Ollama | ⚠️ Wired, chat model pending verification |
| Audit trail (`AcademicAuditEvent`) | ✅ Live |

---

## 2. Modules delivered

### 2.1 Timetable scheduling
- Backend scheduler engine + validation
- Frontend `/scheduling` page
- **Pending:** page layout restructure (this milestone), generation run itself

### 2.2 Academics (v1)
| Feature | Status |
|---|---|
| Students CRUD + enrollments | ✅ |
| Student deep analysis | ✅ |
| Class / stream comparison | ✅ |
| Statistical dashboard | ✅ |
| Assessments CRUD | ✅ |
| Marks entry (class-first, editable total) | ✅ |
| Report cards | ✅ |
| Report forms (KCSE / CBE Senior / CBE Junior templates) | ✅ |
| Bulk report printing | ✅ |
| Comments (per student / per term) | ✅ |
| Grading scheme editor | ✅ |
| Ranking (configurable rules, versioned) | ✅ |
| Audit trail viewer | ✅ |
| Admin console (Users / Roles / Health / Warnings) | ✅ |

### 2.3 Role model
| Role | Access |
|---|---|
| **Administrator** | Everything including Admin Console, Scheduling, all academics config |
| **Teacher** | Home, Dashboard, Timetables, Students, Analysis, Marks Entry (gated by assessment status), Class Comparison, Comments (own classes) |

---

## 3. Data seeded

| Dataset | Count |
|---|---|
| Students | 128 |
| Classes (teaching groups) | 5 (Grade 10E, 10W, 8E, Form 3E, 3W) |
| Subjects | ~45 |
| Assessments | 3 (Term 1) |
| Results | 3,072 |
| Teachers | 20 (T001–T020) with subject/class mappings |
| Lesson requirements | 30+ with teacher FKs |
| Grading schemes | 1 (KICD Default 2026, 5 bands) |
| Ranking rules | 5 |

---

## 4. In progress

### 4.1 Scheduling page restructure
**Goal:** compact header, live status panel, print suite, run history discipline.

**Top-left panel** shows:
- Timetable version
- Created at
- Last successful sync
- Current time / date
- Current term

**Top-right panel** (buttons):
- Refresh · Generate · Print · Print Preview · Approve · Edit

**Generate section** (below):
- Term selector: Term 1 / 2 / 3

**Live status strip** (above timetable):
- e.g. "Generated Timetable v87 • 5 Days • 10 Classes • Backend-defined Learning Periods, 281 backend entries loaded"

**Timetable display**:
- Master (all classes) — compact with zoom
- Junior school filter (Grade 7, 8, 9)
- Senior school filter (Grade 10, 11, 12)
- Form 4E / 4W addition

**Print options**:
- Master timetable (all active classes)
- Class timetables (one page per class)
- Teacher timetables (one page per teacher)
- Junior / Senior / Both

**Run history**:
- Default view: last 5 successful **approved** runs (green)
- Expandable scope for more
- Separate **failed runs** section (red) with reason + remediation hints
- **Admin-only** — hidden from teachers

### 4.2 Dashboard additions
- Recent Scheduling Runs (existing) — show last 5, plus link to full history
- **Assessment history** — new section showing latest assessment means / trends

### 4.3 AI Assistant
- `qwen2.5:3b` chat model wired (pending verification)
- `deepseek-coder:1.3b` code model, admin-only, audit-logged
- **Pending:** school-data context injection, quick actions, chat history persistence

---

## 5. Rules of engagement (frozen)

- **Whole-file writes** for `App.tsx`, `navigation.tsx`, `routes.tsx`, and any page with structural edits
- No regex surgery on JSX
- **Icon audit** runs before every build — catches undefined icon imports
- Backend `manage.py check` before restarting Django
- `vite build` must pass before restart — a build failure is a stop signal
- Sidebar links go in `navigation.tsx`; routes go in `routes.tsx`
- `App.tsx` is a stable shell — never edited by scripts
- Teachers see only their classes/subjects (Marks Entry gated by assessment status; Comments filtered by class)

---

## 6. Next milestones (in order)

1. **Scheduling page restructure** (this milestone)
2. **Scheduling generation run** — end-to-end timetable generation
3. **Print suite** — master / class / teacher formats
4. **AI school-data context** — make the assistant answer real questions
5. **Historical performance** — cohort tracking, term-over-term trends
6. **Early-warning system** — improving / declining / at-risk flags

---

## 7. Scheduling page restructure — data findings (2026-09-20)

### Current API surface (`/api/scheduling/`)
- `GET/POST runs/` — list + create
- `GET runs/<id>/` — detail
- `POST runs/<id>/execute/` — run the solver
- `GET runs/<id>/results/` — validation results

### Existing model fields (`SchedulingRun`)
- `term`, `timetable_version`
- `status` (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
- `solver_status` (NOT_RUN, FEASIBLE, OPTIMAL, INFEASIBLE, UNKNOWN, ERROR)
- `started_at`, `completed_at`
- `objective_value`, `error_message`, `statistics` (JSON)
- **No `approved` field** — for "last 5 approved runs" we need one of:
  (a) add `approved_at` + `approved_by` to `SchedulingRun`, OR
  (b) use `TimetableVersion.is_published` as the approval signal
  → Recommend (a) — keeps approval at the run level, aligns with audit

### Approval model recommendation
Add to `SchedulingRun`:
- `approved_at` (DateTimeField, nullable)
- `approved_by` (FK auth.User, nullable)
- `approval_note` (TextField, blank)

This is one migration, no data migration needed.

### Current Scheduling.tsx
- Full file ~700 lines
- Renders: scheduling controls + `<Timetable />` + run history table
- Needs restructure into: header panel (left) + action panel (right)
  + generate section + live status strip + timetable + disciplined history

### Missing data for the print suite
- Form 4E / Form 4W not yet in DB — need seeding for senior-school print
- Terms: verify Term 1/2/3 exist for the current academic year

### Access control
- Scheduling page is **admin-only** (already enforced in `navigation.tsx`)
- Backend endpoints currently allow any authenticated user — should add
  `IsAdmin` permission to `/api/scheduling/*` for defense in depth