# Generated by Django 4.2.6 on 2024-08-23 11:47

import django.contrib.postgres.constraints
import django.contrib.postgres.fields.ranges
from django.db import migrations
import gouthelper.flares.models


class Migration(migrations.Migration):
    dependencies = [
        ("flares", "0005_auto_20240823_1109"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="flare",
            constraint=django.contrib.postgres.constraints.ExclusionConstraint(
                expressions=[
                    (
                        gouthelper.flares.models.TsTzRange(
                            "date_started",
                            "date_ended",
                            django.contrib.postgres.fields.ranges.RangeBoundary(inclusive_upper=True),
                        ),
                        "&&",
                    ),
                    ("user", "="),
                ],
                name="flares_flare_exclude_user_overlapping",
            ),
        ),
    ]
