from django.core.management.base import BaseCommand
from django.apps import apps

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

IDS = [
    # Form 4E
    "10f76dda-e064-4347-9a23-93f6a8c2d011",  # HIS
    "2147335d-4e6c-41f8-aaba-fd97e0a0bc61",  # BUS
    # Form 4W
    "23e23799-c4e8-4584-8c03-de7e80181532",  # GEO
    "27c5c460-3ced-484d-bdbd-763ea20e4a7f",  # AGR
    # Grade 10E
    "d464d97e-91c5-4872-9986-2b29c21bb5f0",  # CHEM
    "f722bd24-14eb-4fa9-9d8b-19ece0eade3c",  # BIO
    "91ed8c0f-108e-4e4b-b219-424501b725e2",  # HIS
    "eee2e2bd-399e-450d-87eb-48ecf52d49dd",  # PHY
    "c11140f0-ef5c-4d17-a26f-f259837d4403",  # LIT
    "dca507c6-ab3b-4a27-9d0a-6def8acb7e27",  # AGR
    # Grade 10W
    "0f0a822c-8488-4d6b-8f38-7b9db4e3d0f9",  # COMP
    "f26c525a-a69a-45c4-a545-3dd16b585ca7",  # GEO
    "24229ca2-5172-4ebb-a318-dab408cbf136",  # HIS
    "060e39c9-ba2b-4190-96b5-08343881b251",  # LIT
    "3ac94312-18d6-4a97-a778-74533dc643cd",  # MUSD
    "92d87cf2-f42a-4f12-9e44-e97b636159a2",  # BUS
]

class Command(BaseCommand):
    help = "Reactivate requirements deactivated by fix_block_requirements"
    def handle(self, *a, **kw):
        LR = M("LessonRequirement")
        n = 0
        for rid in IDS:
            try:
                r = LR.objects.get(pk=rid)
            except LR.DoesNotExist:
                print("MISSING:", rid); continue
            if not r.is_active:
                r.is_active = True
                r.save(update_fields=["is_active"])
                n += 1
                print("REACTIVATED:", r.instructional_group.name, r.subject.code, "n=", r.lessons_per_week)
        print()
        print("Total reactivated:", n)
        print("Active requirements now:", LR.objects.filter(is_active=True).count())
