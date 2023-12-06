# Generated by Django 4.2.6 on 2023-12-05 19:33

from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("goalurates", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ultaids", "0001_initial"),
        ("medhistorys", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalgoalurate",
            name="history_user",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name="historicalgoalurate",
            name="ultaid",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="ultaids.ultaid",
            ),
        ),
        migrations.AddField(
            model_name="goalurate",
            name="medhistorys",
            field=models.ManyToManyField(to="medhistorys.medhistory"),
        ),
        migrations.AddField(
            model_name="goalurate",
            name="ultaid",
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="ultaids.ultaid"
            ),
        ),
        migrations.AddConstraint(
            model_name="goalurate",
            constraint=models.CheckConstraint(
                check=models.Q(("goal_urate__in", [Decimal("6"), Decimal("5")])),
                name="goalurates_goalurate_goal_urate_valid",
            ),
        ),
    ]