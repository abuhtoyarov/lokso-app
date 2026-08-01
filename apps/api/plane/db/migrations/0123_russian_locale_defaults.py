# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models


def apply_russian_defaults(apps, schema_editor):
    """Move profiles still sitting on the old defaults over to the new ones.

    Only rows that still hold the previous default are touched. Someone who
    deliberately picked English keeps it — there is no way to tell that apart
    from the default having been written for them, so the narrower rule is the
    safer one.
    """
    Profile = apps.get_model("db", "Profile")
    Profile.objects.filter(language="en").update(language="ru")
    Profile.objects.filter(start_of_the_week=0).update(start_of_the_week=1)


def revert_russian_defaults(apps, schema_editor):
    Profile = apps.get_model("db", "Profile")
    Profile.objects.filter(language="ru").update(language="en")
    Profile.objects.filter(start_of_the_week=1).update(start_of_the_week=0)


class Migration(migrations.Migration):
    dependencies = [("db", "0122_worklog")]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="language",
            field=models.CharField(default="ru", max_length=255),
        ),
        migrations.AlterField(
            model_name="profile",
            name="start_of_the_week",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, "Sunday"),
                    (1, "Monday"),
                    (2, "Tuesday"),
                    (3, "Wednesday"),
                    (4, "Thursday"),
                    (5, "Friday"),
                    (6, "Saturday"),
                ],
                default=1,
            ),
        ),
        migrations.RunPython(apply_russian_defaults, revert_russian_defaults),
    ]
