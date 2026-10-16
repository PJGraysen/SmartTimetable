# Seed data

`data.json` is a curated Django fixture: minimum dataset for a fresh
checkout to boot with a working timetable.

Included:
- core: AcademicYear, Term, School, SchoolEvent
- academics: Subject, Stream, TeachingGroup, InstructionalGroup,
  LessonRequirement, GradingScheme, GradingBand, Grade, RankingRule
- scheduling: Period, Room, RoomAvailability, TeacherAssignment,
  TeacherAvailability, TeacherFreeAfternoon, DutyAssignment,
  SchedulingRuleConfig
- users: Teacher (phone stripped)
- One TimetableVersion ("Term 1 - Master (baseline)") and its entries

Excluded on purpose: Student, Result, StudentEnrollment (PII + bulk),
SchedulingRun history, SchedulingErrorLog, ValidationResult, audit
logs, finance/inventory/library data.

## Load
    python manage.py migrate
    python manage.py load_seed

## Regenerate
    python manage.py dump_seed
    python manage.py dump_seed --version-name "Term 2 - Master (baseline)"

## Force-load over existing data
    python manage.py load_seed --allow-existing
