# SmartTimetable Pro — Scheduling Architecture

**Project:** SmartTimetable Pro  
**Institution:** Queen of Apostles Seminary Senior School  
**Phase:** Phase 2 — System Architecture and Design  
**Section:** 2.4 — Scheduling Architecture  
**Version:** 1.0  
**Status:** Design Baseline  
**Scheduling Engine:** Google OR-Tools  
**Backend:** Django  
**Database:** PostgreSQL 18.4  

---

# 1. Purpose

This document defines the scheduling architecture of SmartTimetable Pro.

The scheduling engine is responsible for automatically generating school timetables while satisfying mandatory requirements and optimizing desirable scheduling preferences.

The engine will use Google OR-Tools Constraint Programming, specifically the CP-SAT solver.

The scheduling architecture separates:

1. Scheduling data
2. Scheduling variables
3. Scheduling domains
4. Hard constraints
5. Soft constraints
6. Optimization objectives
7. Solution generation
8. Solution validation
9. Timetable persistence

---

# 2. Scheduling Problem

School timetable generation is a constraint satisfaction and optimization problem.

The system must assign lessons to available time slots while simultaneously considering:

- Teachers
- Teaching groups
- Subjects
- Rooms
- Days
- Periods
- Weekly lesson requirements
- Teacher availability
- Room availability
- Teacher qualifications
- Teacher free afternoons
- Subject distribution
- Workload balancing
- Other institutional requirements

A valid timetable must satisfy every mandatory constraint.

The optimization engine will then attempt to produce the best timetable according to the defined soft constraints.

---

# 3. Scheduling Architecture

The scheduling workflow is:

```text
                    DATABASE
                       |
                       v
              +------------------+
              | Scheduling Data  |
              |     Loader       |
              +--------+---------+
                       |
                       v
              +------------------+
              | Constraint      |
              | Configuration    |
              +--------+---------+
                       |
                       v
              +------------------+
              | Scheduling Model |
              |   Construction   |
              +--------+---------+
                       |
                       v
              +------------------+
              | Google OR-Tools  |
              |     CP-SAT       |
              +--------+---------+
                       |
             +---------+---------+
             |                   |
          SOLUTION           NO SOLUTION
             |                   |
             v                   v
     +---------------+    +---------------+
     | Solution      |    | Constraint    |
     | Validation    |    | Diagnostics   |
     +-------+-------+    +---------------+
             |
             v
     +---------------+
     | Timetable     |
     | Version       |
     +-------+-------+
             |
             v
        PostgreSQL