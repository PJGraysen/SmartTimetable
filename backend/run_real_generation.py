import django

django.setup()

from apps.scheduling.models import SchedulingRun, TimetableVersion
from apps.scheduling.engine.application.scheduling_application import (
    SchedulingApplicationService,
)
from apps.core.models import Term


term = Term.objects.get(is_active=True)

last_version = (
    TimetableVersion.objects
    .filter(term=term)
    .order_by("-version_number")
    .first()
)

next_number = (last_version.version_number + 1) if last_version else 1
next_name = f"Generated Timetable v{next_number}"

run = SchedulingRun.objects.create(term=term)

print("RUN CREATED:", run.id)
print("TERM:", term.id)
print("VERSION:", next_number)
print("VERSION NAME:", next_name)

result = SchedulingApplicationService().execute(
    scheduling_run=run,
    version_name=next_name,
    version_number=next_number,
)

run.refresh_from_db()

print("")
print("============================================================")
print("GENERATION RESULT")
print("============================================================")
print("RUN STATUS:", run.status)
print("SOLVER STATUS:", run.solver_status)
print("TIMETABLE VERSION:", run.timetable_version_id)
print("RESULT OBJECT:", result)

if hasattr(result, "solver_result"):
    solver_result = result.solver_result

    print("SOLVER RESULT:", solver_result.status)
    print("ASSIGNMENTS:", len(solver_result.assignments))
    print("STATISTICS:", solver_result.statistics)
    print("ERROR:", solver_result.error_message)

if run.timetable_version_id:
    print("")
    print("SUCCESS: TIMETABLE VERSION PERSISTED")
else:
    print("")
    print("FAILURE: NO TIMETABLE VERSION WAS PERSISTED")
    raise SystemExit(1)