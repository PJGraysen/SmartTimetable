# SmartTimetable Pro — Formal Scheduling Constraint Specification

**Project:** SmartTimetable Pro  
**Institution:** Queen of Apostles Seminary Senior School  
**Phase:** Phase 2 — System Architecture and Design  
**Section:** 2.4.1 — Formal Scheduling Constraint Specification  
**Version:** 1.0  
**Status:** Design Baseline  
**Scheduling Engine:** Google OR-Tools CP-SAT

---

# 1. Purpose

This document formally defines the scheduling constraints that will govern automatic timetable generation.

Each constraint is assigned a unique identifier and classified as either:

- HARD — must never be violated.
- SOFT — desirable but may be violated when necessary to obtain a feasible timetable.

This document will serve as the authoritative reference when implementing the scheduling engine, validation engine, and automated tests.

---

# 2. Constraint Classification

## 2.1 Hard Constraints

A hard constraint represents a mandatory institutional or logical requirement.

A timetable that violates a hard constraint is invalid.

The solver must therefore satisfy:

```text
ALL HARD CONSTRAINTS = TRUE