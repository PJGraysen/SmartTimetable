# SmartTimetable Pro — Complete SDLC Migration & Technical Handoff

**Document purpose:** Authoritative technical handoff of the currently known SmartTimetable Pro project state from ChatGPT to Claude Code.

**Prepared:** 2026-08-27

**Primary development environment:** Windows 11 / PowerShell / VS Code

**Project root:** `C:\Projects\SmartTimetable`

**Backend:** `C:\Projects\SmartTimetable\backend`

**Frontend:** `C:\Projects\SmartTimetable\frontend`

---

# 1. PROJECT OVERVIEW & GOALS

## 1.1 Project Name

**SmartTimetable Pro**

Formal project description:

> **SmartTimetable Pro — Intelligent Automated School Timetable Generation & Management for Queen of Apostles Seminary.**

The project is an intelligent school timetable generation and management platform intended to automate timetable construction while enforcing complex academic, teacher, class, room, period, and scheduling constraints.

---

## 1.2 Core Purpose

SmartTimetable Pro combines:

* Django backend services
* PostgreSQL persistent storage
* React/TypeScript frontend
* Google OR-Tools CP-SAT scheduling
* REST-style API communication
* timetable versioning
* scheduling-run history
* timetable validation
* manual timetable management/editing
* academic/class/teacher/subject data management

The central objective is to replace manual timetable construction with a constraint-based scheduling engine capable of producing valid school timetables.

The system must not merely generate a mathematically feasible timetable. It must also expose the generated timetable correctly through the frontend and preserve the relationship between:

```text
Scheduling Run
    ↓
Generated Timetable Version
    ↓
Timetable Entries
    ↓
Day + Period + Class + Subject + Teacher
```

The frontend must display the actual authoritative backend result rather than constructing an independent or stale representation.

---

## 1.3 Value Proposition

The system is intended to provide:

1. Automated timetable generation.
2. Enforcement of mandatory scheduling constraints.
3. Reduced manual timetable preparation.
4. Versioned timetable generation.
5. Historical scheduling-run visibility.
6. Manual timetable editing.
7. Validation of timetable correctness.
8. Clear timetable visualization for school administrators and teachers.
9. Maintainable separation between academic data, scheduling logic, API/application logic, and presentation.
10. A foundation for increasingly sophisticated subject-combination and stream scheduling.

---

## 1.4 Primary Target Audience

The principal operational user is the school administration/timetable administrator at:

**Queen of Apostles Seminary Senior School**

Relevant users include:

* timetable administrators
* school administrators
* academic administrators
* teachers
* potentially students/learners in future read-only timetable views

The current development focus is the administrative timetable-generation and timetable-display workflow.

---

## 1.5 Known School Scheduling Requirements

The known timetable environment includes:

* Monday–Friday school week.
* 9 lessons/day was part of the established timetable configuration.
* Lessons are approximately 40 minutes each.
* Break periods:

  * 10:40–11:00
  * 1:00–2:00
* The last activity can extend to approximately 17:45 in the timetable design.
* Grade 10 initially consisted of one stream of approximately 45 learners.
* Form 3 and Form 4 are approximately 40 learners each.

A particularly important teacher constraint is:

> **Every teacher must have exactly one free afternoon per week.**

This is a hard scheduling requirement.

A teacher's free afternoon means that the teacher must have no class allocated during the applicable afternoon teaching periods on that day.

---

## 1.6 Academic Classes / Streams

The project has evolved toward explicitly representing additional class streams.

The requested timetable/class population includes:

* Grade 9E
* Grade 9W
* Grade 8E
* Grade 8W
* Grade 10E
* Grade 10W
* Form 4E
* Form 4W
* Form 3E
* Form 3W

Earlier data also contained Grade 10 as a single stream and references to Grade 10A.

The important architectural direction is that these classes/streams should be represented explicitly in the timetable and subsequently incorporated into solver logic.

Subject combinations are also being introduced, particularly for Grade 10.

---

## 1.7 Grade 10 Electives

Known Grade 10 elective subjects include:

* Music
* Computer Science
* Agriculture
* Business
* History
* Geography

Subject combinations and their correct timetable display are an important continuing feature.

The system should eventually schedule the correct learners/streams according to their subject combinations rather than treating every subject as universally applicable to every learner.

---

## 1.8 Current SDLC Phase

The project is in the **integration, validation, and stabilization phase**.

The scheduling engine has already generated timetable data successfully in the database.

The immediate work has shifted from fundamental solver construction to ensuring that:

1. the backend-generated result is authoritative;
2. the frontend selects the correct completed scheduling run;
3. the correct generated timetable version is selected;
4. actual timetable entries are loaded;
5. actual backend period numbers are used;
6. entries are mapped by the correct day/class/period;
7. the generated subjects and teachers are displayed correctly;
8. the timetable UI does not manufacture an independent timetable representation.

The latest major frontend problem was identified as a **data-selection/rendering problem**, not a solver-generation problem.

---

# 2. SYSTEM ARCHITECTURE & TECH STACK

## 2.1 Architectural Style

SmartTimetable Pro is currently a modular web application rather than a microservice system.

Known high-level structure:

```text
React/TypeScript Frontend
        │
        │ HTTP / REST-style API
        ▼
Django Backend
        │
        ├── Academic domain
        ├── Scheduling domain
        └── Scheduling/solver engine
                │
                ▼
        OR-Tools CP-SAT
                │
                ▼
           PostgreSQL
```

The backend follows a Django application/domain separation approach.

Known Django applications include:

```text
academics
scheduling
engine
```

---

## 2.2 Programming Languages

Known languages:

* Python
* TypeScript
* JavaScript
* HTML/CSS
* SQL
* PowerShell

The backend is Python/Django.

The frontend is React/TypeScript with Vite.

---

## 2.3 Backend Technology

Known backend stack:

```text
Python 3.13.14
Django
PostgreSQL 18.4
Google OR-Tools CP-SAT
```

The project also uses Django's testing ecosystem and `pytest` for automated testing.

Exact Django and OR-Tools package versions were not preserved in the available project context and must therefore be obtained from the actual environment rather than guessed.

Claude Code should inspect:

```powershell
C:\Projects\SmartTimetable\backend\requirements.txt
```

and/or:

```powershell
C:\Projects\SmartTimetable\backend\pyproject.toml
```

if present.

---

## 2.4 Frontend Technology

Known frontend stack:

```text
React
TypeScript
Vite
Axios
```

The frontend build has successfully completed previously.

A prior successful build produced:

```text
1870 modules
Vite production bundle generated
```

TypeScript compilation and Vite production build were therefore demonstrated successfully after the Timetable.tsx repair.

---

## 2.5 Database

Database:

```text
PostgreSQL 18.4
```

Known configuration:

```text
Port: 5432
```

PostgreSQL 17 was previously installed/configured but was disabled.

The active PostgreSQL service is PostgreSQL 18.4.

---

## 2.6 Development Environment

Known environment:

```text
Windows
PowerShell
VS Code 1.132.0
Git 2.55.0
Python 3.13.14
pip 26.1.2
PostgreSQL 18.4
```

Virtual environment:

```text
C:\Projects\SmartTimetable\.venv
```

---

## 2.7 Repository Structure

The complete filesystem tree has not been preserved verbatim in the available context, so the following is the **authoritative known tree**, not an invented claim of completeness.

```text
C:\Projects\SmartTimetable
│
├── .venv\
│
├── backend\
│   ├── manage.py
│   ├── config\
│   │   └── settings.py
│   │
│   ├── apps\
│   │   ├── academics\
│   │   ├── scheduling\
│   │   └── engine\
│   │
│   └── tests\
│       └── ...
│
├── frontend\
│   ├── src\
│   │   ├── api.ts
│   │   ├── App.tsx
│   │   ├── ...
│   │   ├── layouts\
│   │   │   └── AppLayout.tsx
│   │   ├── pages\
│   │   │   ├── SchedulingRuns.tsx
│   │   │   └── Timetable.tsx
│   │   └── services\
│   │       ├── core.ts
│   │       ├── scheduling.ts
│   │       └── api.ts       # historically present; targeted for removal
│   │
│   └── ...
│
├── docs\
│   ├── architecture
│   ├── database
│   ├── scheduling-engine
│   ├── API
│   ├── UI
│   ├── security
│   ├── testing
│   ├── deployment
│   └── user-manual
│
└── ...
```

The exact complete tree must be reconstructed from the repository itself rather than inferred from this handoff.

Recommended command:

```powershell
Set-Location "C:\Projects\SmartTimetable"
tree /F /A
```

---

## 2.8 Frontend API Architecture

There were historically two Axios clients.

### Canonical client

```text
frontend/src/api.ts
```

Its important configuration is:

```typescript
baseURL: "/api"
```

This is the canonical API client.

### Deprecated/hard-coded client

Historically:

```text
frontend/src/services/api.ts
```

used:

```typescript
baseURL: "http://127.0.0.1:8000/api"
```

This was identified as incorrect because the frontend is served through Vite and should use the relative `/api` path.

The architecture therefore requires:

```text
React
  ↓
/api
  ↓
Vite proxy
  ↓
http://127.0.0.1:8000
  ↓
Django
```

The frontend must not independently hard-code the backend origin.

---

## 2.9 Vite Proxy

The frontend uses Vite proxying to forward `/api` requests to Django.

The known intended flow is:

```text
Browser
   |
   | /api/...
   v
Vite development server
   |
   | proxy
   v
Django 127.0.0.1:8000
```

An earlier Django syntax error caused Django to fail to start, which in turn produced:

```text
Vite proxy ECONNREFUSED
```

and frontend `502` behavior.

Once the backend syntax error was removed, Django started correctly and API smoke testing succeeded.

---

# 3. DATA MODELS & LOGIC

## 3.1 Academic Domain

The system has an `academics` Django application.

Known domain concepts include:

* academic terms
* teachers
* subjects
* classes
* class streams
* rooms
* periods
* timetable-related academic definitions

The exact complete model schema should always be taken from the current Django models and migrations.

Do not reconstruct database structure from memory if the repository can provide the authoritative schema.

---

## 3.2 Teacher Model / Assignment Architecture

A crucial architectural decision was established:

> `LessonRequirement` does **not** contain a teacher field.

Teacher assignment is represented separately through:

```text
TeacherAssignment
```

Therefore the relationship is conceptually:

```text
LessonRequirement
        │
        │
        ▼
TeacherAssignment
        │
        ▼
Teacher
```

This separation is important and must not be collapsed by adding a teacher directly to `LessonRequirement` merely to simplify solver code.

---

## 3.3 Teacher Free Afternoon

The system contains:

```text
TeacherFreeAfternoon
```

This represents the hard teacher free-afternoon constraint.

The solver must enforce the requirement that each teacher has exactly one free afternoon per week.

This is not merely a UI preference.

It is a scheduling constraint.

---

## 3.4 Scheduling Domain

The `scheduling` application is responsible for scheduling-related entities and workflows.

Known concepts include:

* scheduling runs
* generated timetable versions
* timetable entries
* lesson requirements
* teacher assignments
* scheduling state
* generated timetable persistence

A scheduling run is associated with a generated timetable version.

Conceptually:

```text
SchedulingRun
       │
       ▼
TimetableVersion
       │
       ▼
TimetableEntry[]
```

---

## 3.5 Generated Timetable Versions

The database has demonstrated generated timetable versions such as:

```text
Generated Timetable v13
Generated Timetable v14
Generated Timetable v15
```

Version numbers observed:

```text
v13 → version no. 112
v14 → version no. 113
v15 → version no. 114
```

These should be treated as persisted generated timetable versions, not frontend-only constructs.

---

## 3.6 Actual Latest Completed Scheduling Result

The most important recent diagnostic result was:

```text
RUN ID:
af342554-71cb-466e-b549-1ed190655aff

COMPLETED:
2026-08-23T11:41:43.634349+03:00

VERSION ID:
b26479d4-44bc-475c-bb51-8bf606a74a90

VERSION NAME:
Generated Timetable v15

VERSION NO:
114

ENTRIES:
1

ENTRY:
MON
P12
Grade 10 - A - Grade 10A
Grade 10A
CS
EMP001
```

The immediately preceding run was:

```text
RUN ID:
3025bb93-1e40-4cc8-8b0e-18fbe1275b13

COMPLETED:
2026-08-23T11:40:51.384043+03:00

VERSION:
Generated Timetable v14

VERSION NO:
113

ENTRY:
MON P12
CS
EMP001
```

Another preceding run:

```text
RUN ID:
b6de3775-2b9d-4b07-b13d-cdbe1a73912b

COMPLETED:
2026-08-23T11:35:38.164524+03:00

VERSION:
Generated Timetable v13

VERSION NO:
112

ENTRY:
MON P12
CS
EMP001
```

Earlier generated versions had entries at P1.

This proved that the backend's actual period number was **P12**, not the P1–P10 assumptions previously embedded in the frontend.

---

## 3.7 Critical Timetable Rendering Rule

The frontend must not assume:

```text
P1
P2
P3
...
P10
```

as the authoritative timetable periods.

Instead:

> **The backend's actual returned period definitions and actual timetable entries are authoritative.**

The frontend must derive its grid from backend data.

This is one of the most important architectural corrections in the current project.

---

## 3.8 Timetable Entry Identity

The timetable display must match entries using the actual backend dimensions.

The relevant mapping is conceptually:

```text
day
+
class
+
period_number
```

The UI must not match based only on array position.

A robust conceptual key is:

```typescript
`${day}:${classId}:${periodNumber}`
```

or an equivalent canonical backend identity.

The previous implementation used a structure based around:

```typescript
groupedEntries
```

and keys similar to:

```typescript
`${entry.day}:${entry.period_number}`
```

The class dimension must be preserved wherever multiple classes are being rendered.

---

## 3.9 Solver Technology

The scheduling engine uses:

```text
Google OR-Tools CP-SAT
```

The solver is constraint-based.

The project has previously included:

* solver variables
* lesson instances
* constraint inspection/debugging
* objective modules
* teacher assignment logic
* timetable persistence
* scheduling-run persistence

The solver is a core backend component and should be treated as authoritative for timetable generation.

---

## 3.10 Solver Objective Architecture

Objective modules were added during development, along with tests.

The exact current objective module tree must be obtained from the repository.

Do not rewrite the solver merely to address frontend display issues.

---

## 3.11 Subject Combination Architecture

The project is transitioning from a simplistic "one class has all subjects" model toward subject combinations.

Grade 10 is particularly important because learners have elective combinations.

Known electives:

```text
Music
Computer Science
Agriculture
Business
History
Geography
```

The timetable must eventually be capable of representing which learners/streams take which subjects.

The current direction is to add explicit streams such as:

```text
Grade 10E
Grade 10W
```

and equivalent streams for other forms/grades.

The timetable UI must therefore be designed so that the addition of combinations does not require another fundamental rendering rewrite.

---

# 4. IMPLEMENTATION & CODE STATE

## 4.1 Completed / Working Areas

The following areas have demonstrated successful operation at various points.

### Backend startup

Django successfully started after repairing a syntax error.

### Django validation

The following command has successfully passed:

```powershell
python manage.py check
```

### Frontend build

The frontend has successfully passed:

```powershell
tsc -b
```

and:

```powershell
vite build
```

The Vite production build completed successfully with approximately:

```text
1870 modules
```

### API connectivity

The backend API was successfully reachable after Django startup was repaired.

### Scheduling runs

Completed scheduling runs are persisted and retrievable through:

```text
/api/scheduling/runs/
```

### Generated timetable versions

Scheduling runs can expose generated timetable version information and entries.

---

## 4.2 Major Backend Syntax Error Already Fixed

A critical backend issue was previously discovered in:

```text
apps/scheduling/engine/application/scheduling_application.py
```

A stray shell command had accidentally been embedded into Python source near the end of the file:

```text
python manage.py check
```

This produced a Python `SyntaxError`.

The resulting chain was:

```text
Invalid Python source
        ↓
Django failed to start
        ↓
Vite proxy could not connect
        ↓
ECONNREFUSED
        ↓
Frontend API requests failed
        ↓
502-style frontend failures
```

The stray command was removed automatically using PowerShell.

Afterward:

```powershell
python manage.py check
```

passed.

This issue must not be reintroduced.

---

## 4.3 Current Timetable.tsx State

The most recent frontend work focused on:

```text
frontend/src/pages/Timetable.tsx
```

The component was changed toward the following architecture:

1. obtain scheduling runs;
2. identify completed runs;
3. sort them by `completed_at`;
4. select the latest completed run;
5. obtain its timetable version;
6. obtain the actual timetable entries;
7. use actual backend periods;
8. place entries according to actual day/period/class data;
9. display real subjects and teacher identifiers.

The implementation was successfully compiled/built.

---

## 4.4 The Timetable Rendering Bug

The central historical bug was:

> The Timetable page was selecting/rendering a timetable version independently of the actual latest completed scheduling result, while its grid columns were not guaranteed to correspond to backend period numbers.

There were two separate problems.

### Problem A — Wrong version selection

The frontend could display a timetable version that was not necessarily the latest completed scheduling result.

The required behavior is:

```text
GET scheduling runs
       ↓
filter completed runs
       ↓
sort by completed_at descending
       ↓
select newest completed run
       ↓
follow its generated timetable version
       ↓
render that version
```

### Problem B — Hard-coded periods

The frontend had hard-coded columns resembling:

```text
Pd 1
Pd 2
Pd 3
...
Pd 10
```

while the backend actually returned an entry at:

```text
P12
```

Consequently, the backend had valid data but the UI could fail to display it.

---

## 4.5 Timetable Design Requirement

The timetable should retain its landscape weekly design.

The desired conceptual layout is:

```text
                 PERIODS →
       P1   P2   P3   ...   P12   ...
Mon
Tue
Wed
Thu
Fri
```

However, the actual columns must come from the backend period definitions.

The UI must not sacrifice the established visual design merely to solve the data-loading problem.

---

## 4.6 Correct Display Example

For the latest observed result, the UI must be capable of displaying:

```text
MON
P12
Grade 10A
CS
EMP001
```

It must **not** display:

```text
—
```

when the backend contains:

```text
CS
EMP001
```

The display should use the actual subject and teacher/employee data returned by the API.

---

## 4.7 Axios Convention

All frontend API access should use the canonical Axios client:

```text
frontend/src/api.ts
```

with:

```typescript
baseURL: "/api"
```

Existing service modules should import that client rather than creating separate backend-origin clients.

Known service modules include:

```text
frontend/src/services/core.ts
frontend/src/services/scheduling.ts
```

The historically incorrect:

```text
frontend/src/services/api.ts
```

was targeted for deletion because it used the hard-coded backend URL.

---

## 4.8 App-Level API Migration

`App.tsx` previously contained direct API access that was targeted for migration to the canonical service architecture.

A known intended abstraction is:

```text
getAcademicTerms()
```

from the core service.

The principle is:

```text
UI component
    ↓
service function
    ↓
canonical Axios client
    ↓
/api
```

rather than:

```text
UI component
    ↓
custom Axios client
    ↓
hard-coded Django URL
```

---

## 4.9 Code Style / Editing Conventions

The user has established strict implementation conventions.

### Whole-file replacements preferred

Do not provide tiny line-by-line patches when a clean whole-file replacement is practical.

### Automated PowerShell preferred

Changes should normally be implemented through executable PowerShell commands/scripts.

Example pattern:

```powershell
Set-Location "C:\Projects\SmartTimetable"

$ErrorActionPreference = "Stop"

# automated implementation here
```

### No manual editing workflow

The user specifically prefers deterministic automated edits rather than instructions such as:

> "Open the file and change line 127."

### Preserve existing working functionality

A fix must be scoped to the actual defect.

Do not rewrite unrelated working modules merely for stylistic reasons.

---

# 5. TESTING, DEPLOYMENT & DEVOPS

## 5.1 Backend Health Check

Standard Django validation:

```powershell
Set-Location "C:\Projects\SmartTimetable\backend"

python manage.py check
```

This must pass before proceeding.

---

## 5.2 Frontend Build

From:

```text
C:\Projects\SmartTimetable\frontend
```

the frontend build can be validated with:

```powershell
npm run build
```

The project has also been validated through TypeScript/Vite build commands equivalent to:

```powershell
tsc -b
vite build
```

---

## 5.3 Testing

The project has a substantial automated test suite.

Historical test counts included:

```text
81 passed
```

and later:

```text
95 collected
```

The exact current count must be obtained from the repository.

Tests include:

* unit tests
* integration tests
* scheduling-engine tests
* solver/objective tests

A previous attempted command against:

```text
tests\scheduling\engine
```

failed because that exact directory did not exist in the working tree at that point.

This failure should not be interpreted as "the scheduling engine has no tests."

The actual repository test tree must be inspected.

---

## 5.4 Recommended Initial Test Commands

Claude Code should begin by establishing the actual current test layout:

```powershell
Set-Location "C:\Projects\SmartTimetable"

Get-ChildItem -Recurse -Directory |
    Where-Object {
        $_.FullName -match '\\tests(\\|$)' -or
        $_.FullName -match '\\test(\\|$)'
    } |
    Select-Object FullName
```

Then run the repository's actual test command.

For the backend, likely candidates are:

```powershell
Set-Location "C:\Projects\SmartTimetable\backend"

pytest
```

and, where required:

```powershell
python manage.py test
```

Do not assume both are authoritative without inspecting project configuration.

---

## 5.5 API Smoke Testing

A known API endpoint is:

```text
/api/scheduling/runs/
```

A useful smoke test should verify:

1. API responds.
2. Completed runs are returned.
3. `completed_at` is present.
4. latest completed run can be identified.
5. associated timetable version exists.
6. entries exist.
7. period numbers are returned.
8. class information is returned.
9. subject information is returned.
10. teacher/employee information is returned.

---

## 5.6 Git / Change Management

Git is installed:

```text
Git 2.55.0
```

The user expects controlled commits after verified fixes.

Previous workflow included:

```text
inspect
→ patch
→ build/check
→ smoke test
→ git diff
→ commit
→ remove obsolete/unconfirmed duplicate files
```

The user has specifically emphasized that there should not be multiple competing/unconfirmed versions of important files such as:

```text
Timetable.tsx
```

The canonical source must remain singular.

---

## 5.7 Deployment

The project includes documentation areas for:

```text
deployment
security
testing
architecture
database
scheduling-engine
API
UI
user-manual
```

The exact production deployment configuration has not been preserved in this handoff and must be read from the repository before making deployment claims.

---

# 6. HISTORICAL CONTEXT & DECISION LOG (ADR)

## ADR-001 — Use Django + PostgreSQL

### Decision

Use Django as the backend application framework and PostgreSQL as the persistent relational database.

### Reason

The application has a relational academic domain involving:

```text
teachers
subjects
classes
streams
rooms
periods
lesson requirements
teacher assignments
timetable versions
timetable entries
scheduling runs
```

This domain benefits from relational integrity and Django's ORM.

---

## ADR-002 — Use OR-Tools CP-SAT

### Decision

Use Google OR-Tools CP-SAT for timetable generation.

### Reason

School timetable generation is a constraint optimization problem involving:

* teacher conflicts
* class conflicts
* room conflicts
* period allocation
* lesson requirements
* teacher free afternoons
* subject combinations
* stream constraints
* potentially optimization objectives

CP-SAT is therefore the established scheduling engine.

---

## ADR-003 — Keep Teacher Assignment Separate from LessonRequirement

### Decision

Do not add a teacher directly to `LessonRequirement`.

Use:

```text
TeacherAssignment
```

to associate teachers with lesson requirements.

### Reason

The existing domain model intentionally separates lesson requirements from teacher assignments.

This separation should be preserved.

---

## ADR-004 — Teacher Free Afternoon Is a Hard Constraint

### Decision

Every teacher must have exactly one free afternoon each week.

### Reason

This is a school operational requirement and not an optional optimization preference.

The solver must enforce it.

---

## ADR-005 — Frontend Uses Relative `/api`

### Decision

Use:

```typescript
baseURL: "/api"
```

in the canonical Axios client.

### Rejected approach

Do not use:

```typescript
baseURL: "http://127.0.0.1:8000/api"
```

inside frontend services.

### Reason

The Vite development server proxies `/api` to Django.

Relative API paths also keep the frontend decoupled from a particular backend host.

---

## ADR-006 — Do Not Modify the Solver to Fix a Frontend Rendering Defect

### Decision

When the generated timetable already exists correctly in the backend, fix the frontend rather than changing the solver.

### Reason

The investigation demonstrated that the backend contained a valid generated timetable entry:

```text
MON P12 CS EMP001
```

while the frontend was using assumptions that did not expose it.

Therefore changing the solver would have been an incorrect scope expansion.

---

## ADR-007 — Backend Timetable Data Is Authoritative

### Decision

The Timetable page must render actual backend-generated data.

### Rejected approach

Do not create an independently hard-coded frontend timetable model.

### Reason

The backend owns:

* generated timetable version
* actual periods
* actual period numbers
* entries
* subjects
* teachers
* classes

The frontend is a presentation layer.

---

## ADR-008 — Backend Period Definitions Are Authoritative

### Decision

The frontend must derive timetable columns from the backend period data.

### Historical defect

The frontend assumed:

```text
P1–P10
```

while the backend contained:

```text
P12
```

### Consequence

A valid backend result could disappear visually.

### Required principle

```text
API period definitions
        ↓
frontend grid
```

not:

```text
hard-coded frontend periods
        ↓
hope backend matches
```

---

## ADR-009 — Latest Completed Run Determines the Displayed Timetable

### Decision

The Timetable page must identify the newest completed scheduling run.

### Algorithm

```text
runs
 ↓
completed runs only
 ↓
sort completed_at descending
 ↓
first run
 ↓
associated timetable version
 ↓
associated timetable entries
 ↓
render
```

The UI must not arbitrarily choose an older timetable version.

---

## ADR-010 — Preserve Landscape Timetable UI

### Decision

Retain the existing landscape timetable design.

### Reason

The visual layout is already established and useful.

The data-loading correction should not become an unnecessary visual redesign.

---

## ADR-011 — Explicit Class Streams

### Decision

Represent class streams explicitly, including:

```text
Grade 9E
Grade 9W
Grade 8E
Grade 8W
Grade 10E
Grade 10W
Form 4E
Form 4W
Form 3E
Form 3W
```

### Reason

The school needs stream-level timetable scheduling and this will support the solver's eventual subject-combination model.

---

## ADR-012 — Subject Combinations Must Become First-Class Scheduling Data

### Decision

Grade 10 subject combinations must eventually be represented explicitly.

### Reason

Electives such as:

```text
Music
Computer Science
Agriculture
Business
History
Geography
```

cannot safely be represented as though every learner takes every subject.

The stream/combination architecture needs to support differentiated scheduling.

---

# 7. ATTEMPTED / DISCARDED APPROACHES

## 7.1 Hard-Coded Timetable Periods

### Attempt

The frontend used a hard-coded period array containing approximately:

```text
Pd 1 ... Pd 10
```

### Why it failed

The backend generated:

```text
P12
```

The UI consequently had no matching column.

### Status

**Discarded.**

### Replacement

Use backend period definitions.

---

## 7.2 Independent Timetable Version Selection

### Attempt

The Timetable page could select/render a timetable representation without guaranteeing that it corresponded to the latest completed scheduling run.

### Why it failed

The user could see a stale or different timetable than the backend diagnostic showed.

### Status

**Discarded.**

### Replacement

Resolve the latest completed scheduling run first.

---

## 7.3 Separate Hard-Coded Axios Backend URL

### Attempt

A frontend service used:

```text
http://127.0.0.1:8000/api
```

### Why it failed architecturally

It bypassed the intended Vite proxy abstraction and created two competing API configurations.

### Status

**Discarded.**

### Replacement

Use:

```text
/api
```

through the canonical Axios client.

---

## 7.4 Modifying Solver to Fix Timetable Rendering

### Attempt considered

Change the backend/solver because the frontend was not showing the generated timetable.

### Why rejected

The backend was already generating and persisting timetable data.

The defect was demonstrated to be in frontend selection/rendering.

### Status

**Do not pursue for this issue.**

---

## 7.5 Manual Line-by-Line Editing

### Attempt/style

Small manual edits were possible but were repeatedly undesirable.

### User requirement

Use deterministic automated PowerShell whole-file replacement where practical.

### Status

Avoid for future implementation work.

---

## 7.6 Stray Shell Command Inside Python Source

### Defect

A PowerShell/Django command accidentally existed in Python source:

```text
python manage.py check
```

### Result

Django failed to start.

### Resolution

Automated removal.

### Status

Fixed.

---

# 8. KNOWN BUGS, TECH DEBT & EDGE CASES

## 8.1 Timetable Version Selection

The Timetable page must never assume that a particular version ID or version number is current.

It must calculate:

```text
latest completed run
```

dynamically.

---

## 8.2 Period Number Mismatch

Period numbers are not necessarily contiguous or limited to P1–P10.

The observed backend result included:

```text
P12
```

Therefore the frontend must tolerate:

* P1
* P2
* ...
* P12
* future periods
* nonstandard period definitions
* potentially gaps, if backend supports them

---

## 8.3 Empty Timetable Entries

The UI must distinguish between:

```text
no entry exists
```

and:

```text
entry exists but subject/teacher display failed
```

An existing backend entry such as:

```text
CS EMP001
```

must never render as:

```text
—
```

simply because the frontend failed to resolve the associated data.

---

## 8.4 Multiple Classes

A key that only contains:

```text
day + period
```

is unsafe if the same period contains entries for multiple classes.

Class identity must be part of the rendering model wherever a class-specific timetable is displayed.

---

## 8.5 Multiple Streams

The architecture must support:

```text
Grade 10E
Grade 10W
```

and equivalent streams.

The UI must not collapse these into a single generic Grade 10 entry.

---

## 8.6 Subject Combinations

Elective combinations can produce cases where:

* one stream studies Computer Science;
* another studies Agriculture;
* another studies Business;
* etc.

The UI and backend data model must eventually support these distinctions.

---

## 8.7 Teacher Identity

The generated timetable has shown:

```text
EMP001
```

as a teacher/employee identifier.

The UI should display the authoritative teacher representation returned by the API.

Do not invent teacher mappings in the frontend.

---

## 8.8 Stale Frontend State

A timetable page must not retain stale state after a new scheduling run completes.

The page should reload the relevant completed run/version/entries rather than continuing to display an older result.

---

## 8.9 API Failure Handling

The frontend should distinguish among:

```text
loading
successful empty result
API failure
invalid response
no completed scheduling run
completed run with no timetable entries
```

These states should not all render as an indistinguishable empty timetable.

---

# 9. AUTHORITATIVE TEACHER MASTER DATA CURRENTLY KNOWN

The following teacher master information was established during project work and should be treated as project data requiring preservation when implementing teacher/subject assignments.

```text
T001 — Fr. Rector
Subjects/role: PPI

T002 — Fr. Samuel
Subjects: CRE
Assignment context: Form 4W

T003 — Fr. Mburu
Subjects/role: PPI

T004 — Mr. Wanjohi
Subjects:
  - EC/CM
  - Grade 10
  - Mathematics
  - Form 3E

T005 — Mr. Magother
Subjects:
  - Physics
  - Form 4
  - Chemistry
  - Form 3
  - Chemistry
  - Grade 10

T006 — Mr. Ogilo
Known subjects:
  - History
  - Form 3
  - CRE
```

The complete teacher master list extends beyond the portion preserved in the current context. Claude Code must inspect the authoritative project data/database before modifying teacher assignments.

Do not invent missing teacher mappings.

---

# 10. SECURITY / AUTHENTICATION / AUTHORIZATION

The project includes a dedicated security documentation area:

```text
docs/security
```

However, the exact current authentication and authorization implementation is not sufficiently preserved in the available project context to document implementation details without guessing.

Claude Code must inspect:

```text
backend/config/settings.py
```

and the authentication-related Django apps/routes before making claims about:

* authentication mechanism
* JWT/session authentication
* permissions
* roles
* CSRF
* CORS
* API authorization
* production security headers

Do not infer a security mechanism merely from Django being present.

---

# 11. ENVIRONMENT VARIABLES & CONFIGURATION

The exact environment-variable list is not fully preserved in the migration context.

Known database/server configuration includes:

```text
PostgreSQL
Port: 5432
```

Backend development server:

```text
127.0.0.1:8000
```

Frontend communicates through:

```text
/api
```

Claude Code must inspect the actual repository files for:

```text
.env
.env.example
backend/config/settings.py
frontend/vite.config.*
package.json
requirements.*
pyproject.toml
```

before documenting or changing environment configuration.

Never fabricate missing secrets or environment variables.

---

# 12. CURRENT DEVELOPMENT RULES / NON-NEGOTIABLES

These rules are critical.

## Rule 1 — Do not change the solver when fixing frontend rendering

The current frontend timetable problem is a presentation/data-selection problem unless repository evidence proves otherwise.

---

## Rule 2 — Backend-generated timetable is authoritative

Never replace actual generated timetable data with hard-coded frontend data.

---

## Rule 3 — Backend periods are authoritative

Never hard-code P1–P10 as the canonical timetable period definition.

---

## Rule 4 — Latest completed scheduling run is authoritative

The Timetable page must select the newest completed run based on `completed_at`.

---

## Rule 5 — Use canonical Axios

Use:

```text
frontend/src/api.ts
```

with:

```text
/api
```

---

## Rule 6 — No duplicate API clients

Do not reintroduce competing Axios clients with hard-coded backend URLs.

---

## Rule 7 — Preserve landscape timetable design

Fix data correctness without unnecessarily redesigning the established timetable UI.

---

## Rule 8 — Whole-file automated patches preferred

Use PowerShell automation for implementation.

---

## Rule 9 — Do not request already-known files unnecessarily

Claude Code has direct access to the repository and should inspect it itself.

Only ask the user for information that genuinely cannot be recovered from the repository.

---

## Rule 10 — Verify every implementation

After changes:

```text
build
→ tests
→ API smoke test
→ inspect git diff
```

Do not claim a fix is complete merely because the code looks correct.

---

## Rule 11 — Keep only one canonical implementation

Do not leave:

```text
Timetable.tsx
Timetable-old.tsx
Timetable-fixed.tsx
Timetable-final.tsx
```

as competing source files.

There should be one authoritative production component.

---

# 13. IMMEDIATE NEXT STEPS FOR CLAUDE CODE

## 13.1 Immediate Technical Goal

The immediate task is:

> **Perform a final repository-level audit and verification of the Timetable frontend implementation so that the Timetable page always displays the latest completed scheduling result using the backend's actual timetable periods and entries, without modifying the solver/backend scheduling logic.**

---

## 13.2 Step 1 — Establish Repository State

Run:

```powershell
Set-Location "C:\Projects\SmartTimetable"

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " SMARTTIMETABLE PRO — REPOSITORY STATE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

git status --short

Write-Host ""
Write-Host "=== CURRENT BRANCH ===" -ForegroundColor Yellow
git branch --show-current

Write-Host ""
Write-Host "=== RECENT COMMITS ===" -ForegroundColor Yellow
git log --oneline -10
```

---

## 13.3 Step 2 — Locate Timetable Implementation

Run:

```powershell
Set-Location "C:\Projects\SmartTimetable"

Get-ChildItem -Path . -Recurse -File |
    Where-Object {
        $_.Name -eq "Timetable.tsx" -or
        $_.Name -match "timetable"
    } |
    Select-Object FullName
```

Confirm that there is only one canonical:

```text
Timetable.tsx
```

implementation.

---

## 13.4 Step 3 — Inspect API Architecture

Run:

```powershell
Set-Location "C:\Projects\SmartTimetable\frontend"

Write-Host "=== AXIOS / API REFERENCES ===" -ForegroundColor Cyan

Get-ChildItem -Path src -Recurse -File -Include *.ts,*.tsx |
    Select-String -Pattern `
        'axios.create',
        'baseURL',
        '127.0.0.1:8000',
        'localhost:8000',
        '"/api"',
        "'/api'",
        'scheduling/runs' |
    Select-Object Path,LineNumber,Line
```

The expected architectural result is that the canonical client uses:

```text
/api
```

and frontend code does not create an unnecessary second hard-coded backend client.

---

## 13.5 Step 4 — Audit Timetable.tsx

Inspect the entire file.

The component must satisfy all of these conditions:

```text
[ ] Does not hard-code P1–P10 as authoritative periods.
[ ] Loads completed scheduling runs.
[ ] Filters to completed runs.
[ ] Sorts by completed_at descending.
[ ] Selects newest completed run.
[ ] Resolves its generated timetable version.
[ ] Loads actual timetable entries.
[ ] Uses backend period definitions.
[ ] Uses actual entry.period_number.
[ ] Uses day from backend data.
[ ] Uses class identity.
[ ] Displays actual subject.
[ ] Displays actual teacher/employee.
[ ] Handles empty states.
[ ] Handles loading state.
[ ] Handles API errors.
[ ] Preserves landscape UI.
```

---

## 13.6 Step 5 — Validate Backend Against Frontend

Start Django:

```powershell
Set-Location "C:\Projects\SmartTimetable\backend"

python manage.py check
```

Then run the backend normally.

Verify:

```text
/api/scheduling/runs/
```

and specifically verify the newest completed run.

The latest known expected historical result was:

```text
Generated Timetable v15
Version No: 114
Completed: 2026-08-23T11:41:43.634349+03:00
MON P12
Grade 10A
CS
EMP001
```

Do not assume these values remain current after subsequent development; query the live database/API.

---

## 13.7 Step 6 — Validate Period Handling

The critical regression test is:

> If the backend returns P12, the frontend must render P12.

A useful conceptual frontend assertion is:

```typescript
expect(renderedPeriodNumbers).toContain(12);
```

The exact test implementation should follow the repository's existing frontend testing architecture.

---

## 13.8 Step 7 — Validate Class Handling

The frontend must correctly distinguish:

```text
Grade 10E
Grade 10W
```

and eventually:

```text
Grade 8E
Grade 8W
Grade 9E
Grade 9W
Form 3E
Form 3W
Form 4E
Form 4W
```

The key used for timetable lookup must not accidentally merge different classes sharing the same day and period.

---

## 13.9 Step 8 — Run Frontend Build

From:

```text
C:\Projects\SmartTimetable\frontend
```

run the repository's normal build:

```powershell
npm run build
```

If the repository uses explicit TypeScript build configuration, also validate:

```powershell
npx tsc -b
```

---

## 13.10 Step 9 — Run Backend Tests

From:

```text
C:\Projects\SmartTimetable\backend
```

first inspect the actual test structure, then run the repository's authoritative suite.

Where configured:

```powershell
pytest
```

The target is zero regressions.

Historical successful suites reached:

```text
81 passed
```

and later:

```text
95 collected
```

The current result must be established from the repository rather than assumed.

---

## 13.11 Step 10 — Perform API Smoke Test

The smoke test should:

```text
GET scheduling runs
    ↓
filter completed
    ↓
sort by completed_at DESC
    ↓
identify latest run
    ↓
resolve version
    ↓
retrieve entries
    ↓
verify periods
    ↓
verify classes
    ↓
verify subjects
    ↓
verify teachers
```

The final output should clearly identify:

```text
LATEST COMPLETED RUN
VERSION
VERSION NUMBER
ENTRY COUNT
DAYS
PERIOD NUMBERS
CLASSES
SUBJECTS
TEACHERS
```

---

## 13.12 Step 11 — Verify No Backend/Solver Changes

Because the immediate defect is frontend-focused, inspect:

```powershell
Set-Location "C:\Projects\SmartTimetable"

git diff -- backend
```

If the task was only to correct Timetable rendering, unexpected solver/backend modifications must be investigated before commit.

---

## 13.13 Step 12 — Final Git Review

Run:

```powershell
Set-Location "C:\Projects\SmartTimetable"

git status --short

git diff --stat

git diff -- frontend/src/pages/Timetable.tsx
```

Ensure:

* only intended files changed;
* no duplicate Timetable implementations exist;
* no generated junk files were added;
* no accidental commands were inserted into source code;
* no backend solver changes were made for the frontend defect.

---

# 14. RECOMMENDED CLAUDE CODE WORKING PROTOCOL

Claude Code should operate in this sequence:

```text
1. Inspect repository.
2. Inspect current git state.
3. Inspect actual Timetable.tsx.
4. Inspect canonical API client.
5. Inspect scheduling service.
6. Inspect current backend scheduling endpoints.
7. Run Django checks.
8. Run API smoke test.
9. Compare API response with Timetable.tsx assumptions.
10. Apply the smallest complete whole-file frontend correction.
11. Build frontend.
12. Run relevant tests.
13. Run API smoke test again.
14. Inspect git diff.
15. Remove obsolete duplicate implementations if any.
16. Commit only after verification.
```

Do not skip the API comparison.

The central historical failure was caused by the frontend and backend having different assumptions about the authoritative timetable.

---

# 15. CRITICAL SYSTEM INVARIANTS

The following invariants should be treated as architectural acceptance criteria.

## Invariant 1

```text
Displayed timetable version
==
version belonging to latest completed scheduling run
```

---

## Invariant 2

```text
Displayed period columns
==
backend-defined periods
```

---

## Invariant 3

```text
Displayed timetable entry
==
actual backend timetable entry
```

---

## Invariant 4

```text
Timetable lookup identity
includes day + class + period
```

where the current UI requires class-specific rendering.

---

## Invariant 5

```text
Subject displayed
==
backend subject
```

---

## Invariant 6

```text
Teacher displayed
==
backend teacher/employee assignment
```

---

## Invariant 7

```text
No frontend hard-coded timetable period model
```

---

## Invariant 8

```text
No duplicate Axios backend configuration
```

---

## Invariant 9

```text
Frontend rendering fixes do not modify solver behavior
```

unless a future investigation establishes a genuine backend-generation defect.

---

## Invariant 10

```text
Every teacher
==
exactly one free afternoon per week
```

This remains a hard solver requirement.

---

# 16. CURRENT PROJECT STATUS — HANDOFF SUMMARY

At the point of migration, SmartTimetable Pro is **not a blank project** and the scheduling engine is not the primary blocker.

The backend has successfully:

* started under Django;
* passed Django checks after the syntax repair;
* exposed scheduling APIs;
* persisted completed scheduling runs;
* persisted generated timetable versions;
* persisted timetable entries;
* produced actual period assignments;
* produced subject/teacher information.

The frontend has successfully:

* compiled TypeScript;
* built through Vite;
* established a canonical Axios client;
* moved toward latest-completed-run selection;
* moved toward backend-driven period rendering;
* implemented the corrected Timetable rendering architecture.

The major historical defect was the mismatch between backend truth and frontend assumptions:

```text
BACKEND
Latest completed run
        ↓
Generated Timetable v15
        ↓
MON P12
        ↓
CS / EMP001


FRONTEND — OLD ASSUMPTION
        ↓
Hard-coded P1–P10
        ↓
No P12 column
        ↓
Valid backend entry invisible
```

The corrected architecture is:

```text
             BACKEND
                │
                ▼
      Completed Scheduling Runs
                │
                ▼
      Latest Completed Run
                │
                ▼
       Generated Timetable
                │
                ├───────────────┐
                ▼               ▼
        Period Definitions   Entries
                │               │
                └───────┬───────┘
                        ▼
                  Timetable.tsx
                        │
                        ▼
               Landscape UI
```

The key principle for the continuation of the project is:

> **The frontend must render the backend's timetable, not invent its own timetable.**

---

# 17. FINAL TAKEOVER DIRECTIVE FOR CLAUDE CODE

Treat the repository itself as the ultimate source of truth for exact current implementation details.

Treat this document as the preserved architectural/contextual handoff.

When the repository and this document disagree:

1. inspect the repository;
2. determine whether the code has intentionally evolved;
3. preserve the user's established architectural decisions unless there is concrete evidence they have been superseded;
4. do not silently rewrite working architecture;
5. do not reintroduce discarded approaches.

The immediate priority is:

```text
FINALIZE AND VERIFY TIMETABLE.TSX
```

with these exact goals:

```text
latest completed scheduling run
        ↓
associated timetable version
        ↓
actual timetable entries
        ↓
actual backend period definitions
        ↓
day + class + period mapping
        ↓
actual subject
        ↓
actual teacher
        ↓
correct landscape timetable display
```

Do **not** change the OR-Tools solver merely to make the frontend display data.

Do **not** hard-code P1–P10.

Do **not** select an arbitrary timetable version.

Do **not** create another Axios client.

Do **not** leave duplicate `Timetable.tsx` implementations.

Do **not** perform manual line-by-line editing when an automated whole-file implementation is practical.

After implementation, prove correctness with:

```text
Django check
+
backend/API smoke test
+
frontend TypeScript/build
+
relevant automated tests
+
git diff review
```

Only then consider the timetable-display milestone complete.

---

# END OF HANDOFF

**Project:** SmartTimetable Pro
**Current focus:** Timetable frontend/backend integration correctness
**Primary component:** `frontend/src/pages/Timetable.tsx`
**Backend authority:** Django + PostgreSQL + OR-Tools-generated timetable
**Frontend API authority:** `frontend/src/api.ts` using `/api`
**Critical rendering rule:** backend-defined periods and latest completed scheduling run are authoritative
**Solver status:** do not modify for the current frontend issue
**Next milestone:** fully verify and commit the authoritative timetable rendering implementation
