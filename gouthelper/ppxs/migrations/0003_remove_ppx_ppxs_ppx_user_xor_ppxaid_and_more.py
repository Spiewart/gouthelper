# Generated by Django 4.2.6 on 2024-08-07 19:05

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ppxs", "0002_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="ppx",
            name="ppxs_ppx_user_xor_ppxaid",
        ),
        migrations.RemoveField(
            model_name="historicalppx",
            name="goalurate",
        ),
        migrations.RemoveField(
            model_name="ppx",
            name="goalurate",
        ),
        migrations.AddConstraint(
            model_name="ppx",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("ppxaid__isnull", True), ("user__isnull", False)),
                    ("user__isnull", True),
                    _connector="OR",
                ),
                name="ppxs_ppx_user_xor_ppxaid",
            ),
        ),
    ]
