# Generated by Django 4.2.6 on 2024-07-29 15:15

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("medhistorydetails", "0001_initial"),
        ("medhistorys", "0003_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalgoutdetail",
            name="history_user",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name="historicalgoutdetail",
            name="medhistory",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="medhistorys.medhistory",
            ),
        ),
        migrations.AddField(
            model_name="historicalckddetail",
            name="history_user",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name="historicalckddetail",
            name="medhistory",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="medhistorys.medhistory",
            ),
        ),
        migrations.AddField(
            model_name="goutdetail",
            name="medhistory",
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to="medhistorys.medhistory"),
        ),
        migrations.AddField(
            model_name="ckddetail",
            name="medhistory",
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to="medhistorys.medhistory"),
        ),
        migrations.AddConstraint(
            model_name="goutdetail",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("at_goal", False), ("at_goal_long_term", False)),
                    ("at_goal", True),
                    models.Q(("at_goal__isnull", True), ("at_goal_long_term", False)),
                    _connector="OR",
                ),
                name="medhistorydetails_goutdetail_at_goal_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="ckddetail",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        ("dialysis", False), ("dialysis_duration__isnull", True), ("dialysis_type__isnull", True)
                    ),
                    models.Q(
                        ("dialysis", True),
                        ("dialysis_duration__isnull", False),
                        ("dialysis_type__isnull", False),
                        ("stage", 5),
                    ),
                    _connector="OR",
                ),
                name="medhistorydetails_ckddetail_dialysis_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="ckddetail",
            constraint=models.CheckConstraint(
                check=models.Q(("dialysis_duration__in", ["", "LESSTHANSIX", "LESSTHANYEAR", "MORETHANYEAR"])),
                name="medhistorydetails_ckddetail_dialysis_duration_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="ckddetail",
            constraint=models.CheckConstraint(
                check=models.Q(("dialysis_type__in", ["HEMODIALYSIS", "PERITONEAL"])),
                name="medhistorydetails_ckddetail_dialysis_type_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="ckddetail",
            constraint=models.CheckConstraint(
                check=models.Q(("stage__in", [None, 1, 2, 3, 4, 5])), name="medhistorydetails_ckddetail_stage_valid"
            ),
        ),
    ]
