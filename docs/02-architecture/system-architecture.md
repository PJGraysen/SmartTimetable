# SmartTimetable Pro — System Architecture

**Project:** SmartTimetable Pro
**Institution:** Queen of Apostles Seminary Senior School
**Phase:** Phase 2 — System Architecture and Design
**Document:** System Architecture Specification
**Version:** 1.0
**Status:** Baseline Architecture
**Date:** 2026-08-13

---

# 1. Introduction

## 1.1 Purpose

This document defines the system architecture for SmartTimetable Pro, an intelligent automated school timetable generation and management system being developed for Queen of Apostles Seminary Senior School.

The architecture establishes the major software components, application boundaries, data responsibilities, scheduling architecture, communication mechanisms, security boundaries, and deployment considerations that will guide subsequent development phases.

The architecture is designed to support the project's hybrid incremental development methodology. Components may therefore be refined, extended, or refactored as new requirements are discovered during implementation and testing.

---

# 2. Architectural Objectives

The architecture is designed to achieve the following objectives:

1. Provide a maintainable school timetable management platform.
2. Automate timetable generation using constraint programming and optimization.
3. Ensure mandatory timetable constraints cannot be violated.
4. Support manual timetable creation and modification.
5. Validate manually modified timetables.
6. Provide meaningful explanations when a timetable cannot be generated.
7. Maintain timetable versions and historical changes.
8. Separate timetable management from timetable optimization.
9. Provide secure role-based access.
10. Support future expansion of the system.
11. Maintain a clear separation between presentation, business logic, scheduling, and data storage.
12. Support both local development and eventual production deployment.

---

# 3. Architectural Style

SmartTimetable Pro will use a modular layered architecture combined with service-oriented components.

The major architectural layers are:

1. Presentation Layer
2. API Layer
3. Application/Business Logic Layer
4. Scheduling Layer
5. Data Layer
6. Security Layer

The architecture is intentionally modular so that individual components can be developed and tested independently.

---

# 4. High-Level System Architecture

The high-level architecture is:

```text
                         USERS
                           |
                           v
                +----------------------+
                |    PRESENTATION      |
                |    FRONTEND / UI     |
                +----------+-----------+
                           |
                           v
                +----------------------+
                |       API LAYER      |
                | Django REST Framework|
                +----------+-----------+
                           |
                           v
                +----------------------+
                |   DJANGO APPLICATION |
                |      CORE LAYER      |
                +----------+-----------+
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
   +-------------+  +-------------+  +-------------+
   | PostgreSQL  |  | Scheduling  |  |  Services   |
   |  Database   |  |   Engine    |  |   Layer     |
   +-------------+  | Google      |  +-------------+
                    | OR-Tools    |
                    +------+------+
                           |
                           v
                    +-------------+
                    | Validation  |
                    |   Engine    |
                    +-------------+
                           |
                           v
                    +-------------+
                    |  Timetable  |
                    |   Output    |
                    +-------------+