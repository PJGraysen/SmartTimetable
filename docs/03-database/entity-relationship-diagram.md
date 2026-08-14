# SmartTimetable Pro — Entity Relationship Diagram

**Project:** SmartTimetable Pro  
**Institution:** Queen of Apostles Seminary Senior School  
**Phase:** Phase 2 — System Architecture and Design  
**Section:** 2.3 — Entity Relationship Diagram  
**Version:** 1.0  
**Status:** Design Baseline  
**Database:** PostgreSQL 18.4

---

# 1. Purpose

This document defines the Entity Relationship Diagram (ERD) for SmartTimetable Pro.

The ERD provides a visual representation of the major entities in the system and the relationships between them.

It serves as a bridge between the physical database model and the eventual Django ORM implementation.

---

# 2. Core Entity Relationship Model

The principal academic structure is:

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