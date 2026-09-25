from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m
    raise LookupError(n)

DAYS = ["MON", "TUE", "WED", "THU", "FRI"]

class Command(BaseCommand):
    help = "Fill empty cells of a version with GST (Group Study). Prefer afternoon."
    def add_arguments(self, p):
        p.add_argument("--timetable-version", type=int, default=None,
                       dest="timetable_version",
                       help="version_number; default = latest")
        p.add_argument("--version-id", type=str, default=None,
                       dest="version_id",
                       help="exact TimetableVersion.id; takes precedence")
        p.add_argument("--apply", action="store_true")
    def handle(self, *a, **kw):
        TV = M("TimetableVersion")
        TE = M("TimetableEntry")
        IG = M("InstructionalGroup")
        Per = M("Period")
        Subj = M("Subject")
        LR = M("LessonRequirement")
        Room = M("Room")

        vid = kw.get("version_id")
        vn = kw.get("timetable_version")
        if vid:
            v = TV.objects.filter(pk=vid).first()
        elif vn:
            v = TV.objects.filter(version_number=vn).first()
        else:
            v = TV.objects.order_by("-version_number").first()
        if not v:
            print("no version"); return
        print(f"Version v{v.version_number} {v.name}")

        gst = Subj.objects.filter(code="GST").first()
        if not gst:
            print("ABORT: GST subject missing. Run setup_gst first."); return

        periods = list(Per.objects.filter(is_teaching_period=True, number__lte=10).order_by("number"))
        igs = list(IG.objects.filter(is_active=True).order_by("name"))

        filled = set()
        for e in TE.objects.filter(timetable_version=v).only(
            "day", "period_id", "instructional_group_id"
        ):
            filled.add((str(e.instructional_group_id), str(e.day), str(e.period_id)))
        print(f"Filled cells: {len(filled)}")

        rooms_by_code = {r.code: r for r in Room.objects.filter(is_active=True)}
        HOME_ROOM = {
            "Form 4E": "F4E", "Form 4W": "F4W",
            "Grade 10E": "G10E", "Grade 10W": "G10W",
            "Grade 8E": "G8E", "Grade 8W": "G8W",
            "Grade 9E": "G9E", "Grade 9W": "G9W",
        }

        gst_req = {}
        for ig in igs:
            r = LR.objects.filter(instructional_group=ig, subject=gst).first()
            if r: gst_req[str(ig.pk)] = r

        def is_locked(ig_name, day, period_num):
            if day == "MON" and period_num == 1:
                return True
            g = ig_name.upper()
            if (("8E" in g or "8W" in g or "9E" in g or "9W" in g
                 or "GRADE 8" in g or "GRADE 9" in g)
                and period_num in (8, 9, 10)):
                return True
            return False

        to_add = []
        for ig in igs:
            req = gst_req.get(str(ig.pk))
            if not req:
                print(f"  skip {ig.name}: no GST requirement"); continue
            home = rooms_by_code.get(HOME_ROOM.get(ig.name, ""))
            ordered_periods = sorted(periods, key=lambda p: -(p.number or 0))
            for day in DAYS:
                for p in ordered_periods:
                    key = (str(ig.pk), day, str(p.pk))
                    if key in filled: continue
                    if is_locked(ig.name, day, p.number or 0): continue
                    to_add.append((ig, day, p, req, home))

        print(f"To fill with GST: {len(to_add)}")
        for ig, day, p, req, home in to_add[:8]:
            print(f"  {ig.name:14s} {day} P{p.number} -> GST")
        if len(to_add) > 8:
            print(f"  ... and {len(to_add)-8} more")

        if not kw["apply"]:
            print()
            print("Dry run. Add --apply to persist.")
            return

        with transaction.atomic():
            TE.objects.bulk_create([
                TE(
                    timetable_version=v,
                    day=day,
                    period_id=p.pk,
                    instructional_group_id=ig.pk,
                    teacher_id=None,
                    lesson_requirement_id=req.pk,
                    room_id=home.pk if home else None,
                )
                for (ig, day, p, req, home) in to_add
            ])
        print(f"Added {len(to_add)} GST entries to v{v.version_number}")
