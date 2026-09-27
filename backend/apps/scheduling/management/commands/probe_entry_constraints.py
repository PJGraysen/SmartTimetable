from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connection

def M(n):
    for m in apps.get_models():
        if m.__name__ == n: return m

class Command(BaseCommand):
    help = "Show TimetableEntry constraints and unique rules"
    def handle(self, *a, **kw):
        TE = M("TimetableEntry")
        print(f"db_table: {TE._meta.db_table}")
        print(f"unique_together: {TE._meta.unique_together}")

        print("\n=== Meta.constraints ===")
        for c in getattr(TE._meta, "constraints", []):
            print(f"  {c.name}: {c}")

        print("\n=== DB constraints ===")
        with connection.cursor() as cur:
            cur.execute("""
                SELECT conname, pg_get_constraintdef(c.oid)
                FROM pg_constraint c
                JOIN pg_class t ON c.conrelid = t.oid
                WHERE t.relname = 'timetable_entry'
                ORDER BY conname
            """)
            for name, definition in cur.fetchall():
                print(f"  {name}: {definition}")

        print("\n=== DB indexes ===")
        with connection.cursor() as cur:
            cur.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'timetable_entry'
                ORDER BY indexname
            """)
            for name, definition in cur.fetchall():
                print(f"  {name}: {definition}")
