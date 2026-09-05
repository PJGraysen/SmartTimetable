# Generated migration - adds performance indexes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0005_alter_timetableentry_teacher'),
    ]

    operations = [
        # Index for frequently filtered scheduling runs
        migrations.AddIndex(
            model_name='schedulingrun',
            index=models.Index(
                fields=['term', 'status'],
                name='ix_scheduling_run_term_status_perf',
            ),
        ),
        # Index for timetable version lookups
        migrations.AddIndex(
            model_name='schedulingrun',
            index=models.Index(
                fields=['timetable_version', 'status'],
                name='ix_scheduling_run_version_status',
            ),
        ),
        # Index for timetable entry queries
        migrations.AddIndex(
            model_name='timetableentry',
            index=models.Index(
                fields=['timetable_version', 'day', 'period'],
                name='ix_timetable_entry_slot_perf',
            ),
        ),
        # Index for teacher availability queries
        migrations.AddIndex(
            model_name='teacheravailability',
            index=models.Index(
                fields=['term', 'teacher', 'day'],
                name='ix_teacher_availability_composite',
            ),
        ),
        # Index for room availability queries
        migrations.AddIndex(
            model_name='roomavailability',
            index=models.Index(
                fields=['term', 'room', 'day'],
                name='ix_room_availability_composite',
            ),
        ),
    ]
