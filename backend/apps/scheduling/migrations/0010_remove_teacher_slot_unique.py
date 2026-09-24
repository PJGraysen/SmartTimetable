from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0009_schedulingerrorlog"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="timetableentry",
            name="uq_timetable_entry_teacher_slot",
        ),
    ]
