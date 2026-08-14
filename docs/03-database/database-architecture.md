# SmartTimetable Pro — Database Architecture

**Project:** SmartTimetable Pro  
**Institution:** Queen of Apostles Seminary Senior School  
**Phase:** Phase 2 — System Architecture and Design  
**Document:** Database Architecture Specification  
**Version:** 1.0  
**Status:** Baseline Database Architecture  
**Date:** 2026-08-14

---

# 1. Introduction

## 1.1 Purpose

This document defines the database architecture for SmartTimetable Pro, an intelligent automated school timetable generation and management system for Queen of Apostles Seminary Senior School.

The database provides the persistent data foundation for:

- School administration
- Academic structures
- Teachers
- Subjects
- Classes and streams
- Teaching groups
- Teacher assignments
- Teacher availability
- Mandatory teacher free afternoons
- Rooms and resources
- Timetable periods
- Timetable generation
- Timetable versions
- Scheduling runs
- Constraint validation
- Users and permissions
- Audit and change history

The database architecture is designed to support both automated timetable generation and controlled manual timetable management.

---

# 2. Database Technology

SmartTimetable Pro will use:

**Database Management System:** PostgreSQL  
**Target Version:** PostgreSQL 18.x  
**Development Port:** 5432

PostgreSQL will serve as the authoritative persistent data store for the application.

The Django application will communicate with PostgreSQL through Django's database abstraction layer and ORM.

The scheduling engine will retrieve scheduling data from the application/database layer and return validated scheduling results to the application.

---

# 3. Database Architecture Principles

The database shall follow the following principles.

## 3.1 Single Source of Truth

PostgreSQL will be the authoritative source of persistent school and timetable data.

The scheduling engine must not become the permanent source of timetable information.

The general data flow is:

```text
PostgreSQL
    |
    v
Django Application
    |
    v
Scheduling Engine
    |
    v
Generated Solution
    |
    v
Validation
    |
    v
PostgreSQL