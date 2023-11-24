# Generated by Django 4.2.6 on 2023-11-12 23:29

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("flares", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="flare",
            name="flares_flare_diagnosed_valid",
        ),
        migrations.AddConstraint(
            model_name="flare",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("crystal_analysis__isnull", False), ("diagnosed", True)),
                    models.Q(("crystal_analysis__isnull", True), ("diagnosed", False)),
                    _connector="OR",
                ),
                name="flares_flare_diagnosed_valid",
            ),
        ),
    ]