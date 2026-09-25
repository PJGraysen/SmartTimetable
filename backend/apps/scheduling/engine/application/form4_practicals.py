"""Post-solve Form 4 practicals filler (v2, relaxed matching).

For each Form 4 class, insert 3 double-period practicals (BIO, CHEM, PHY).
- Prefers afternoon pairs (P8-P10), then mid-morning (P5-P7), then any.
- No different-day constraint; multiple pairs on the same day are allowed.
- Skips days that already have a practical pair.

Failures are swallowed so generation is never blocked.
Env kill switch: ST_DISABLE_PRACTICALS=1
"""
from __future__ import annotations

import os
import sys
import traceback


PRACTICAL_CODES = ("BIOPRAC", "CHEMPRAC", "PHYPRAC")
PRACTICAL_DAYS = ("MON", "TUE", "WED", "THU", "FRI")


def _period_pref(n: int) -> int:
    if n in (8, 9, 10):
        return 0
    if n in (5, 6, 7):
        return 1
    return 2


def insert_form4_practicals(scheduling_run) -> None:
    if os.environ.get("ST_DISABLE_PRACTICALS") == "1":
        print("[PRACTICALS] disabled via env var", file=sys.stderr)
        return

    try:
        from apps.scheduling.models import TimetableEntry, Period
        from apps.academics.models import (
            InstructionalGroup, LessonRequirement, Subject,
        )
    except Exception as e:
        print(f"[PRACTICALS] import failed: {e}", file=sys.stderr)
        return

    tv = getattr(scheduling_run, "timetable_version", None)
    term = getattr(scheduling_run, "term", None)
    if tv is None or term is None:
        print("[PRACTICALS] no timetable_version or term on run", file=sys.stderr)
        return

    try:
        form4 = list(InstructionalGroup.objects.filter(
            name__in=["Form 4E", "Form 4W"], is_active=True,
        ))
        if not form4:
            print("[PRACTICALS] no active Form 4 classes", file=sys.stderr)
            return

        subjects = {}
        for code in PRACTICAL_CODES:
            subj, _ = Subject.objects.get_or_create(
                code=code,
                defaults={"name": f"{code[:-4]} Practical", "is_active": True},
            )
            subjects[code] = subj

        lr_by_class = {}
        for ig in form4:
            lrs = []
            for code in PRACTICAL_CODES:
                lr, created = LessonRequirement.objects.get_or_create(
                    instructional_group=ig,
                    subject=subjects[code],
                    term=term,
                    defaults={
                        "lessons_per_week": 2,
                        "requirement_type": "STANDALONE",
                        "is_active": False,
                    },
                )
                if not created and lr.is_active:
                    lr.is_active = False
                    lr.save(update_fields=["is_active"])
                lrs.append(lr)
            lr_by_class[str(ig.pk)] = lrs

        periods = list(Period.objects.filter(
            is_teaching_period=True, number__lte=10,
        ).order_by("number"))
        period_by_num = {p.number: p for p in periods}

        total_inserted = 0
        for ig in form4:
            filled = set()
            for e in TimetableEntry.objects.filter(
                timetable_version=tv, instructional_group=ig,
            ).only("day", "period_id"):
                filled.add((str(e.day or "").upper(), str(e.period_id)))

            # Build per-day blank list
            day_blanks = {}
            for day in PRACTICAL_DAYS:
                day_blanks[day] = sorted(
                    p.number for p in periods
                    if (day, str(p.pk)) not in filled
                )

            print(
                f"[PRACTICALS] {ig.name} blanks by day: "
                + ", ".join(f"{d}=[{','.join(str(n) for n in day_blanks[d])}]" for d in PRACTICAL_DAYS),
                file=sys.stderr,
            )

            # Candidate adjacent pairs — no different-day restriction.
            candidates = []
            for day in PRACTICAL_DAYS:
                blanks = day_blanks[day]
                for i in range(len(blanks) - 1):
                    if blanks[i + 1] == blanks[i] + 1:
                        score = min(_period_pref(blanks[i]), _period_pref(blanks[i + 1]))
                        candidates.append((
                            score, PRACTICAL_DAYS.index(day), blanks[i],
                            day, blanks[i], blanks[i + 1],
                            str(period_by_num[blanks[i]].pk),
                            str(period_by_num[blanks[i + 1]].pk),
                        ))
            candidates.sort()

            picked = []
            used_days = set()
            used_slots = set()
            # Pass 1: prefer one per day
            for c in candidates:
                _, _, _, day, n1, n2, pid1, pid2 = c
                if day in used_days:
                    continue
                if (day, n1) in used_slots or (day, n2) in used_slots:
                    continue
                picked.append(c)
                used_days.add(day)
                used_slots.add((day, n1))
                used_slots.add((day, n2))
                if len(picked) == 3:
                    break
            # Pass 2: fill remaining on any day
            if len(picked) < 3:
                for c in candidates:
                    if c in picked:
                        continue
                    _, _, _, day, n1, n2, pid1, pid2 = c
                    if (day, n1) in used_slots or (day, n2) in used_slots:
                        continue
                    picked.append(c)
                    used_slots.add((day, n1))
                    used_slots.add((day, n2))
                    if len(picked) == 3:
                        break

            lrs = lr_by_class[str(ig.pk)]
            for idx, c in enumerate(picked):
                if idx >= len(lrs):
                    break
                _, _, _, day, _, _, pid1, pid2 = c
                lr = lrs[idx]
                for pid in (pid1, pid2):
                    TimetableEntry.objects.create(
                        timetable_version=tv,
                        day=day,
                        period_id=pid,
                        instructional_group_id=ig.pk,
                        lesson_requirement_id=lr.pk,
                        teacher_id=lr.teacher_id,
                        room_id=None,
                    )
                    total_inserted += 1

        print(
            f"[PRACTICALS] inserted {total_inserted} entries across Form 4 classes",
            file=sys.stderr,
        )
    except Exception as e:
        print(f"[PRACTICALS] FAILED: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)


def remove_existing_practicals(scheduling_run) -> None:
    """Utility to remove practicals for a version (idempotency helper)."""
    from apps.scheduling.models import TimetableEntry
    from apps.academics.models import Subject
    tv = getattr(scheduling_run, "timetable_version", None)
    if tv is None:
        return
    codes = ("BIOPRAC", "CHEMPRAC", "PHYPRAC")
    subj_ids = list(Subject.objects.filter(code__in=codes).values_list("id", flat=True))
    if subj_ids:
        TimetableEntry.objects.filter(
            timetable_version=tv,
            lesson_requirement__subject_id__in=subj_ids,
        ).delete()
