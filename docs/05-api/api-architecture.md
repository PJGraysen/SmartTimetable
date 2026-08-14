# SmartTimetable Pro — API Architecture

**Project:** SmartTimetable Pro  
**Institution:** Queen of Apostles Seminary Senior School  
**Phase:** Phase 2 — System Architecture and Design  
**Section:** 2.5 — API Architecture  
**Version:** 1.0  
**Status:** Design Baseline  
**Backend:** Django  
**API Framework:** Django REST Framework  
**Database:** PostgreSQL 18.4  

---

# 1. Purpose

This document defines the API architecture for SmartTimetable Pro.

The API provides the communication layer between the frontend application and the Django backend.

It allows authorized users and system components to:

- Manage school data.
- Manage teachers.
- Manage subjects.
- Manage teaching groups.
- Manage rooms.
- Configure timetable periods.
- Configure teacher availability.
- Configure timetable constraints.
- Generate timetables.
- Validate timetables.
- Publish timetable versions.
- View timetable information.
- Manage timetable changes.

---

# 2. API Architectural Role

The API sits between the presentation layer and the backend application.

```text
+-----------------------+
|       FRONTEND        |
|   Web User Interface  |
+-----------+-----------+
            |
            | HTTPS / HTTP
            v
+-----------------------+
|       API LAYER       |
| Django REST Framework |
+-----------+-----------+
            |
            v
+-----------------------+
|   APPLICATION LAYER   |
|       Django          |
+-----------+-----------+
            |
     +------+------+
     |             |
     v             v
+---------+   +-------------+
|PostgreSQL|   | Scheduling  |
| Database |   |   Service   |
+---------+   +------+------+
                     |
                     v
              +-------------+
              | Google      |
              | OR-Tools    |
              +-------------+