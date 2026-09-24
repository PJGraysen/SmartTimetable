# SmartTimetable — Locked Business Rules
**Locked:** 2026-09-20 · **Status:** Authoritative

Every layer — database, solver, API, frontend — MUST implement these rules.
If database state conflicts with these rules, THE DATABASE IS WRONG.

---

## A. Grade 8 (Junior Secondary, CBE)

**Instructional groups:** Grade 8E, Grade 8W

**Weekly teaching:** 34 lessons
- Mon = 6 (P1 is Assembly — non-teaching)
- Tue/Wed/Thu/Fri = 7 each

**Non-teaching slots (never satisfied by a lesson):**
- Mon P1 = Assembly
- Daily P8 = Prayers / PPI
- Daily P9–P10 = Co-curricular / CAS / Study

**Subject allocation (per class):**
| Code | Subject | Lessons/week |
|---|---|---|
| MAT | Mathematics | 5 |
| ENG | English | 5 |
| KIS | Kiswahili | 5 |
| SST | Social Studies | 5 |
| INT | Integrated Science | 5 |
| AGR | Agriculture | 5 |
| CAS | Creative Arts & Sports | 5 |
| CRE | Christian Religious Education | 3 |
| PPI | Pastoral Programme | 1 |
| | **TOTAL** | **34** |

**Free afternoons:** none.

---

## B. Grade 10 (Senior CBC)

**Instructional groups:** Grade 10E, Grade 10W

**Weekly teaching:** 49 lessons
- Mon = 9, Tue–Fri = 10 each

**Core standalone (per class):**
| Code | Subject | Lessons/week |
|---|---|---|
| ENG | English | 5 |
| KIS | Kiswahili | 5 |
| EMCM | Essential / Core Mathematics | 5 |
| CRE | Christian Religious Education | 4 |
| PE | Physical Education | 3 |
| CSL | Community Service Learning | 3 |
| ICT | ICT Skills | 2 |
| PRP | Pastoral Programme | 1 |
| | **Subtotal** | **28** |

**Four elective blocks — each 5 shared slots/week:**

| Block | Members (run simultaneously) |
|---|---|
| OPTION_1 | COM (Computer Studies) / CHEM (Chemistry) |
| OPTION_2 | BIO (Biology) / GEO (Geography) / HIS (History) |
| OPTION_3 | PHY (Physics) / LIT (Literature) / MD (Music & Dance) |
| OPTION_4 | AGR (Agriculture) / BST (Business Studies) |

**Elective rule:** every block member must have the SAME weekly quota (5).
**Stream sync:** Grade 10E and 10W take elective blocks at identical day/period.

**Free afternoons:** Tue–Fri, max 5 teachers per day.

---

## C. Form 3 / Form 4 (8-4-4)

**Instructional groups:** Form 3E, Form 3W — treated identically to Form 4E, Form 4W.

**Weekly teaching:** 49 lessons
- Mon = 9 (P1 is Assembly), Tue–Fri = 10 each

**Standalone subjects (per class):**
| Code | Subject | Lessons/week |
|---|---|---|
| MAT | Mathematics | 6 |
| ENG | English | 5 |
| KIS | Kiswahili | 5 |
| CHEM | Chemistry | 5 |
| PHY | Physics | 4 |
| BIO | Biology | 4 |
| CRE | Christian Religious Education | 3 |
| | **Subtotal** | **32** |

**Two elective blocks:**

| Block | Members (run simultaneously) | Slots/week |
|---|---|---|
| GEO/HIS | GEO (Geography) / HIS (History) | 5 |
| AGR/BST | AGR (Agriculture) / BST (Business Studies) | 4 |

**Elective rule:** members of a block share the same day/period.
**Free afternoons:** Tue–Fri, max 5 teachers per day.

---

## D. Cross-cutting rules

1. **Every lesson has a teacher.** No LR may be scheduled without an assigned teacher.
2. **Block simultaneity.** All members of a block occupy the same day + period across all participating streams.
3. **No class exceeds 49 lessons/week** (Grade 8: 34).
4. **Teacher anti-clash.** A teacher cannot be in two sessions in one slot.
5. **Free afternoons (Tue–Fri, max 5/day).** No teacher is scheduled on their free afternoon.
6. **Non-teaching slots** (Assembly, Prayers, Co-curricular, Study) must NOT satisfy any LessonRequirement.

---

## E. Naming convention

The code already uses these codes — locked as canonical:
- Class codes: `G8E`, `G8W`, `G10E`, `G10W`, `F3E`, `F3W`, `F4E`, `F4W`
- Block codes (Grade 10): `OPTION_1`, `OPTION_2`, `OPTION_3`, `OPTION_4`
- Block codes (Form): `GEO_HIS`, `AGR_BST`