# SmartTimetable Pro — Physical Database Model

**Project:** SmartTimetable Pro  
**Institution:** Queen of Apostles Seminary Senior School  
**Phase:** Phase 2 — System Architecture and Design  
**Section:** 2.3 — Physical Database Model  
**Version:** 1.0  
**Status:** Design Baseline  
**Database:** PostgreSQL 18.4  
**ORM:** Django ORM  

---

# 1. Purpose

This document defines the physical database model for SmartTimetable Pro.

The physical model translates the approved conceptual and logical database architecture into a PostgreSQL-oriented relational design.

It defines:

- Database tables
- Columns
- PostgreSQL data types
- Primary keys
- Foreign keys
- Unique constraints
- Check constraints
- Default values
- Indexing strategy
- Referential integrity
- Deletion behavior
- Audit fields
- Timetable-specific integrity requirements

The model will serve as the implementation specification for the PostgreSQL database and subsequent Django models.

---

# 2. Database Platform

SmartTimetable Pro will use:

| Component | Technology |
|---|---|
| Database | PostgreSQL |
| Version | PostgreSQL 18.4 |
| Port | 5432 |
| Application ORM | Django ORM |
| Backend | Django |
| Scheduling Engine | Google OR-Tools |

PostgreSQL is the authoritative persistent data store.

The scheduling engine will read scheduling configuration from the database, generate a timetable solution, validate the solution, and return the resulting timetable to the application.

---

# 3. Physical Database Design Principles

The database will follow the following principles:

1. Use relational normalization.
2. Use UUID primary keys for major entities.
3. Use foreign keys to preserve referential integrity.
4. Use explicit unique constraints where duplication is not permitted.
5. Use database-level check constraints where practical.
6. Use timestamps for auditability.
7. Prefer deactivation over destructive deletion for historical entities.
8. Keep generated timetable data separate from configuration data.
9. Maintain timetable version history.
10. Maintain scheduling-run history.
11. Keep authentication management primarily within Django.
12. Avoid storing derived data unnecessarily.
13. Keep scheduling constraints independently identifiable.
14. Design indexes around common scheduling and reporting queries.

---

# 4. Naming Convention

All database identifiers will use `snake_case`.

Examples:

```text
academic_year
teaching_group
lesson_requirement
teacher_assignment
teacher_availability
teacher_free_afternoon
timetable_version
timetable_entry
scheduling_run
validation_result