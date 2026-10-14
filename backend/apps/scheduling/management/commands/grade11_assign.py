from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Mirror Grade 10 -> Grade 11 LessonRequirements (field-for-field clone)"
    def add_arguments(self, p):
        p.add_argument("--commit", action="store_true")
        p.add_argument(
            "--term", dest="term_name", default=None,
            help="Term name to target (e.g. 'Term 3').",
        )

    def handle(self, *a, **kw):
        IG = M("InstructionalGroup"); LR = M("LessonRequirement"); T = M("Teacher")
        Term = M("Term")

        target_term = None
        term_name = kw.get("term_name")
        if term_name:
            target_term = Term.objects.filter(
                name__iexact=term_name.strip()
            ).first()
            if not target_term:
                avail = list(Term.objects.values_list("name", flat=True).order_by("name"))
                raise SystemExit(
                    f"Term {term_name!r} not found. Available: {avail}"
                )
            print(f"Target term: {target_term.name}")

        overrides = {
            ("11E", "ESS"): "T004",
            ("11W", "CORE"): "T013",
            ("11W", "ENG"):  "T015",
            ("11W", "LIT"):  "T015",
        }

        pairs = [("10E", "11E"), ("10W", "11W")]

        # Show required fields once so we can sanity-check
        print("LessonRequirement required fields:")
        for f in LR._meta.get_fields():
            if hasattr(f, "column") and not getattr(f, "null", False) and not getattr(f, "blank", False):
                print(f"  {f.name}: {type(f).__name__}")
        print()

        plan = []
        for src_name, dst_name in pairs:
            src = IG.objects.filter(code=src_name, is_active=True).first()
            dst = IG.objects.filter(code=dst_name, is_active=True).first()
            if not src or not dst:
                print(f"SKIP {src_name}->{dst_name}: group missing"); continue
            src_qs = LR.objects.filter(
                instructional_group=src, is_active=True
            ).select_related("subject")
            if target_term:
                src_qs = src_qs.filter(term=target_term)
            for r in src_qs:
                sc = r.subject.code if r.subject else "?"
                key = (dst_name, sc)
                new_t = T.objects.filter(employee_code=overrides[key]).first() if key in overrides else r.teacher
                plan.append((r, dst, new_t))

        print(f"{'Group':12s} {'Subj':6s} {'L/wk':4s} {'Term':10s} {'Type':12s} Teacher")
        print("-" * 70)
        for src, dst, t in plan:
            print(f"{dst.name:12s} {src.subject.code if src.subject else '?':6s} "
                  f"{src.lessons_per_week:4d} {str(src.term)[:10]:10s} "
                  f"{getattr(src, 'requirement_type', '?'):12s} "
                  f"{t.employee_code if t else '(none)'}")

        if not kw["commit"]:
            print("\nDRY RUN — pass --commit to write")
            return

        with transaction.atomic():
            created = updated = 0
            for src, dst, t in plan:
                # Look up existing target row (same group + subject + term)
                effective_term = target_term or src.term
                existing = LR.objects.filter(
                    instructional_group=dst,
                    subject=src.subject,
                    term=effective_term,
                ).first()
                if existing:
                    if existing.teacher_id != (t.pk if t else None):
                        existing.teacher = t
                        existing.is_active = True
                        existing.save()
                        updated += 1
                    continue
                # Clone every concrete field from source, override group + teacher
                clone = LR.objects.get(pk=src.pk)
                clone.pk = None
                clone.id = None
                clone.instructional_group = dst
                clone.teacher = t
                if target_term:
                    clone.term = target_term
                clone.save()
                created += 1
            print(f"\nCreated {created}, updated {updated}")
