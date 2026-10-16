"""Form 4 practicals (v3): adjacent double-lessons in P5–P12 only.

Rules:
  - Practical LRs default to is_active=True; user toggle is respected.
  - Each active practical becomes ONE double lesson (2 adjacent periods)
    in the window P5..P12 (start P5..P11).
  - P1..P4 forbidden.
  - Teacher = active LAB_TECH teacher (assigned on the LR if not already).
  - Room from subject code: BIOPRAC/CHEMPRAC -> CHEM/BIO LAB; PHYPRAC -> PHY-LAB.
  - Avoids LAB_TECH double-booking across all Form 4 classes.

Env kill switch: ST_DISABLE_PRACTICALS=1
"""
from __future__ import annotations

# Set to True to keep per-class practicals diagnostics in the
# generation log. Default is False: the solver already places
# practicals via its own hard constraint, so the post-solve
# insertion step usually has nothing to do and would only log
# a misleading 'no valid windows available' warning.
PRACTICALS_DEBUG = False

import os
import sys
import traceback


PRACTICAL_CODES = ("BIOPRAC", "CHEMPRAC", "PHYPRAC")
PRACTICAL_DAYS = ("MON", "TUE", "WED", "THU", "FRI")

# Room assignment per practical subject code
ROOM_BY_SUBJECT = {
    "BIOPRAC": "CHEM/BIO LAB",
    "CHEMPRAC": "CHEM/BIO LAB",
    "PHYPRAC": "PHY-LAB",
}

# Pair start periods must be within [START_MIN, START_MAX] inclusive
START_MIN = 5    # after morning break
START_MAX = 11   # so pair ends at P12


def insert_form4_practicals(scheduling_run) -> None:
    if os.environ.get("ST_DISABLE_PRACTICALS") == "1":
        print("[PRACTICALS] disabled via env var", file=sys.stderr)
        return

    try:
        from apps.scheduling.models import TimetableEntry, Period, Room
        from apps.academics.models import (
            InstructionalGroup, LessonRequirement, Subject,
        )
        from apps.users.models import Teacher
    except Exception as e:
        print(f"[PRACTICALS] import failed: {e}", file=sys.stderr)
        return

    tv = getattr(scheduling_run, "timetable_version", None)
    term = getattr(scheduling_run, "term", None)
    if tv is None or term is None:
        print("[PRACTICALS] no timetable_version or term", file=sys.stderr)
        return

    try:
        form4 = list(InstructionalGroup.objects.filter(
            name__in=["Form 4E", "Form 4W"], is_active=True,
        ))
        if not form4:
            print("[PRACTICALS] no active Form 4 classes", file=sys.stderr)
            return

        lab_tech = Teacher.objects.filter(role="LAB_TECH", is_active=True).first()
        if lab_tech is None:
            print("[PRACTICALS] no active LAB_TECH teacher found - continuing with teacher=None", file=sys.stderr)

        subjects = {}
        for code in PRACTICAL_CODES:
            subj, _ = Subject.objects.get_or_create(
                code=code,
                defaults={"name": f"{code[:-4]} Practical", "is_active": True},
            )
            subjects[code] = subj

        # Get-or-create LRs. Defaults are is_active=True. We do NOT force
        # deactivate existing ones - the toggle is the user's choice.
        lr_by_class = {}
        for ig in form4:
            lrs = []
            for code in PRACTICAL_CODES:
                lr, created = LessonRequirement.objects.get_or_create(
                    instructional_group=ig,
                    subject=subjects[code],
                    term=term,
                    requirement_type="PRACTICAL",
                    defaults={
                        "lessons_per_week": 2,
                        "is_active": True,
                        "teacher": lab_tech,
                    },
                )
                # Backfill teacher on existing LRs without one
                if not created and lr.teacher_id is None and lab_tech is not None:
                    lr.teacher = lab_tech
                    lr.save(update_fields=["teacher", "updated_at"])
                lrs.append(lr)
            lr_by_class[str(ig.pk)] = lrs

        periods = list(Period.objects.filter(
            is_teaching_period=True, number__lte=12,
        ).order_by("number"))
        period_by_num = {p.number: p for p in periods}

        rooms_by_code = {r.code: r for r in Room.objects.filter(is_active=True)}

        # Track LAB_TECH booked slots across the whole batch
        lab_tech_booked = set()

        total_inserted = 0
        for ig in form4:
            filled = set()
            for e in TimetableEntry.objects.filter(
                timetable_version=tv, instructional_group=ig,
            ).only("day", "period_id"):
                filled.add((str(e.day or "").upper(), str(e.period_id)))

            day_blanks = {}
            for day in PRACTICAL_DAYS:
                day_blanks[day] = sorted(
                    p.number for p in periods
                    if (day, str(p.pk)) not in filled
                )

            if PRACTICALS_DEBUG:
                print(
                    f"[PRACTICALS] {ig.name} blanks by day: "
                    + ", ".join(f"{d}=[{','.join(str(n) for n in day_blanks[d])}]" for d in PRACTICAL_DAYS),
                    file=sys.stderr,
                )

            # Candidate adjacent pairs in window, no lab-tech clash
            candidates = []
            for day in PRACTICAL_DAYS:
                blanks = day_blanks[day]
                for i in range(len(blanks) - 1):
                    if blanks[i + 1] != blanks[i] + 1:
                        continue
                    p1_num = blanks[i]
                    if p1_num < START_MIN or p1_num > START_MAX:
                        continue
                    p1 = period_by_num[p1_num]
                    p2 = period_by_num[p1_num + 1]
                    if (day, str(p1.pk)) in lab_tech_booked: continue
                    if (day, str(p2.pk)) in lab_tech_booked: continue
                    candidates.append((day, p1_num, p1_num + 1, p1, p2))

            picked = []
            used_days = set()
            used_slots = set()
            # Pass 1: prefer one per day
            for c in candidates:
                day, n1, n2, p1, p2 = c
                if day in used_days: continue
                if (day, n1) in used_slots or (day, n2) in used_slots: continue
                picked.append(c)
                used_days.add(day)
                used_slots.add((day, n1))
                used_slots.add((day, n2))
                if len(picked) == 3: break
            # Pass 2: fill remaining on any day
            if len(picked) < 3:
                for c in candidates:
                    if c in picked: continue
                    day, n1, n2, p1, p2 = c
                    if (day, n1) in used_slots or (day, n2) in used_slots: continue
                    picked.append(c)
                    used_slots.add((day, n1))
                    used_slots.add((day, n2))
                    if len(picked) == 3: break

            active_lrs = [lr for lr in lr_by_class[str(ig.pk)] if lr.is_active]
            if not active_lrs:
                if PRACTICALS_DEBUG:
                    print(f"[PRACTICALS] {ig.name}: all practical LRs inactive - skipped", file=sys.stderr)
                continue
            if not picked:
                if PRACTICALS_DEBUG:
                    print(f"[PRACTICALS] {ig.name}: no valid windows available", file=sys.stderr)
                continue

            for idx, c in enumerate(picked):
                if idx >= len(active_lrs): break
                day, n1, n2, p1, p2 = c
                lr = active_lrs[idx]
                subj_code = lr.subject.code
                room = rooms_by_code.get(ROOM_BY_SUBJECT.get(subj_code, ""))
                for pid in (p1.pk, p2.pk):
                    TimetableEntry.objects.create(
                        timetable_version=tv,
                        day=day,
                        period_id=pid,
                        instructional_group_id=ig.pk,
                        lesson_requirement_id=lr.pk,
                        teacher_id=lr.teacher_id,
                        room_id=room.pk if room else None,
                    )
                    total_inserted += 1
                    lab_tech_booked.add((day, str(pid)))

        if PRACTICALS_DEBUG:
            print(f"[PRACTICALS] inserted {total_inserted} entries across Form 4 classes", file=sys.stderr)
    except Exception as e:
        print(f"[PRACTICALS] FAILED: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)


def remove_existing_practicals(scheduling_run) -> None:
    from apps.scheduling.models import TimetableEntry
    from apps.academics.models import Subject
    tv = getattr(scheduling_run, "timetable_version", None)
    if tv is None: return
    codes = ("BIOPRAC", "CHEMPRAC", "PHYPRAC")
    subj_ids = list(Subject.objects.filter(code__in=codes).values_list("id", flat=True))
    if subj_ids:
        TimetableEntry.objects.filter(
            timetable_version=tv,
            lesson_requirement__subject_id__in=subj_ids,
        ).delete()
