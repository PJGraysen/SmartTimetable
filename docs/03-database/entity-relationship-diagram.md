# SmartTimetable Pro — Entity Relationship Diagram

**Project:** SmartTimetable Pro
**Institution:** Queen of Apostles Seminary Senior School
**Phase:** Phase 2 — System Architecture and Design
**Section:** 2.3 — Entity Relationship Diagram
**Version:** 1.0
**Status:** Design Baseline
**Database:** PostgreSQL 18.4
**ORM:** Django ORM

---

# 1. Purpose

This document defines the Entity Relationship Diagram (ERD) for SmartTimetable Pro.

The ERD provides a logical representation of the major entities required by the system and the relationships between those entities.

It serves as the bridge between:

- The approved system requirements
- The logical database architecture
- The physical PostgreSQL database model
- The Django ORM implementation
- The scheduling engine

The ERD is a design specification and does not itself create database tables.

---

# 2. Core Academic Structure

The principal academic hierarchy is:

```text
SCHOOL
   |
   | 1:N
   v
ACADEMIC_YEAR
   |
   | 1:N
   v
TERM


GRADE
   |
   | 1:N
   v
STREAM
   |
   | 1:N
   v
TEACHING_GROUP
   |
   | 1:N
   v
LESSON_REQUIREMENT
   |
   | N:1
   v
SUBJECT
