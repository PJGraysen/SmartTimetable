# Approved Timetable Reference (2026)

These are the actual approved timetables used at the school, treated as
the ground truth for what a valid generation output looks like.

## Common structure
- 10 periods/day, 5 days = 50 slots/week
- Monday P1 = Assembly (non-teaching)
- Tea Break (10:40–11:00) and Lunch (1:00–2:00) between periods
- Daily: P13 = Prayers, P14 = Activities

## Senior school period grid (per day)
| # | Time |
|---|---|
| P1 | 8:00 – 8:40 |
| P2 | 8:40 – 9:20 |
| P3 | 9:20 – 10:00 |
| P4 | 10:00 – 10:40 |
| Tea | 10:40 – 11:00 |
| P5 | 11:00 – 11:40 |
| P6 | 11:40 – 12:20 |
| P7 | 12:20 – 1:00 |
| Lunch | 1:00 – 2:00 |
| P8 | 2:00 – 2:40 |
| P9 | 2:40 – 3:20 |
| P10 | 3:20 – 4:00 |

## Per-class observations
- **Grade 10E / 10W**: 49 lessons, 4 elective blocks, sciences appear in
  elective cells (e.g. `COM/CHE`, `BIO/GEO/HIS`, `PHY/LIT/MD`, `AGR/BST`)
- **Grade 8E**: 34 lessons, no blocks, co-curricular in afternoons
- **Form 3E / 3W**: 49 lessons, GEO/HIS + AGR/BST blocks only

## Teacher-code annotation
Every cell in the approved timetables shows `SUBJECT / TEACHER_CODE`.
That is the school's visual convention. Frontend should render the same.