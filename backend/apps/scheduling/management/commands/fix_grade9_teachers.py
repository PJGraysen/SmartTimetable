from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m


class Command(BaseCommand):
    help = "Assign teachers to Grade 9 CBC LRs (mirroring Grade 8) + clean stale TAs"
    def add_arguments(self, p):
        p.add_argument("--apply", action="store_true")
    def handle(self, *a, **kw):
        LR = M("LessonRequirement")
        TA = M("TeacherAssignment")
        IG = M("InstructionalGroup")
        Subject = M("Subject")

        apply = kw["apply"]

        # ---------- PART 1: mirror Grade 8 teachers onto Grade 9 ----------
        # Build a (subject_code -> teacher) map from Grade 8E/8W.
        print("=== PART 1: mirror Grade 8 teachers -> Grade 9 ===")
        g8_ig_codes = ["Grade 8E", "Grade 8W"]
        g9_ig_codes = ["Grade 9E", "Grade 9W"]

        mirror = {}  # subject_code -> teacher_id
        for gname in g8_ig_codes:
            ig = IG.objects.filter(name=gname).first()
            if not ig: continue
            for r in LR.objects.filter(instructional_group=ig, is_active=True).select_related("subject"):
                if r.subject and r.teacher_id:
                    mirror[r.subject.code] = r.teacher_id
        print("  Grade 8 teacher map:")
        for sc, tid in sorted(mirror.items()):
            print(f"    {sc:10s} -> teacher_id={tid}")

        # CAS may not be on Grade 8's teacher map because we activated it later.
        # Assign T014 (Ms. Erambi) — she teaches Creative Arts per the doc.
        Teacher = M("Teacher")
        if "CAS" not in mirror:
            t14 = Teacher.objects.filter(employee_code="T014").first()
            if t14:
                mirror["CAS"] = t14.pk
                print(f"  CAS -> T014 (Ms. Erambi, assigned manually)")

        # Assign
        n_assigned = 0
        for gname in g9_ig_codes:
            ig = IG.objects.filter(name=gname).first()
            if not ig: continue
            for r in LR.objects.filter(instructional_group=ig, is_active=True, teacher__isnull=True):
                if r.subject and r.subject.code in mirror:
                    tid = mirror[r.subject.code]
                    print(f"  {gname}: assign {r.subject.code} -> teacher_id={tid}")
                    if apply:
                        r.teacher_id = tid
                        r.save(update_fields=["teacher"])
                    n_assigned += 1
        print(f"  would assign: {n_assigned}")

        # ---------- PART 2: deactivate TAs whose LR is inactive ----------
        print()
        print("=== PART 2: deactivate stale TAs (LR inactive) ===")
        stale = list(TA.objects.filter(is_active=True, lesson_requirement__is_active=False)
                     .select_related("lesson_requirement__instructional_group",
                                     "lesson_requirement__subject", "teacher"))
        print(f"  count: {len(stale)}")
        for ta in stale[:20]:
            r = ta.lesson_requirement
            ig = r.instructional_group.name if r and r.instructional_group else "?"
            sc = r.subject.code if r and r.subject else "?"
            print(f"    TA={str(ta.pk)[:8]} {ig:12s} {sc:8s} teacher={ta.teacher}")

        # ---------- PART 3: create TAs for the newly-assigned Grade 9 LRs ----------
        print()
        print("=== PART 3: create TeacherAssignments for Grade 9 LRs that lack one ===")
        to_create = []
        for gname in g9_ig_codes:
            ig = IG.objects.filter(name=gname).first()
            if not ig: continue
            for r in LR.objects.filter(instructional_group=ig, is_active=True):
                # after Part 1, r.teacher should be set; check if TA exists
                if r.teacher_id is None:
                    continue
                exists = TA.objects.filter(teacher_id=r.teacher_id,
                                            lesson_requirement=r,
                                            is_active=True).exists()
                if not exists:
                    to_create.append((r, r.teacher_id))
        print(f"  to create: {len(to_create)}")
        for r, tid in to_create[:20]:
            sc = r.subject.code if r.subject else "?"
            print(f"    {r.instructional_group.name:12s} {sc:8s} teacher_id={tid}")

        if not apply:
            print()
            print(">> DRY RUN. Re-run with --apply to persist.")
            return

        with transaction.atomic():
            for ta in stale:
                ta.is_active = False
                ta.save(update_fields=["is_active"])
            n_stale = len(stale)
            for r, tid in to_create:
                TA.objects.create(teacher_id=tid, lesson_requirement=r, is_active=True)
            print()
            print(f"Deactivated {n_stale} stale TAs")
            print(f"Created {len(to_create)} new TAs")
