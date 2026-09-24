from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0010_remove_teacher_slot_unique"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="timetableentry",
            name="uq_timetable_entry_room_slot",
        ),
    ]
