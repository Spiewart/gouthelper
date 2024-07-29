# Generated by Django 4.2.6 on 2024-07-29 15:15

from decimal import Decimal
from django.db import migrations, models
import django_extensions.db.fields
import gouthelper.utils.models
import rules.contrib.models
import simple_history.models
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="GoalUrate",
            fields=[
                (
                    "created",
                    django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name="created"),
                ),
                (
                    "modified",
                    django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name="modified"),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True
                    ),
                ),
                (
                    "goal_urate",
                    models.DecimalField(
                        choices=[(Decimal("6"), "6.0 mg/dL"), (Decimal("5"), "5.0 mg/dL")],
                        decimal_places=1,
                        default=Decimal("6"),
                        help_text="What is the goal uric acid?",
                        max_digits=2,
                        verbose_name="Goal Uric Acid",
                    ),
                ),
            ],
            bases=(rules.contrib.models.RulesModelMixin, gouthelper.utils.models.GoutHelperBaseModel, models.Model),
        ),
        migrations.CreateModel(
            name="HistoricalGoalUrate",
            fields=[
                (
                    "created",
                    django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name="created"),
                ),
                (
                    "modified",
                    django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name="modified"),
                ),
                ("id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False)),
                (
                    "goal_urate",
                    models.DecimalField(
                        choices=[(Decimal("6"), "6.0 mg/dL"), (Decimal("5"), "5.0 mg/dL")],
                        decimal_places=1,
                        default=Decimal("6"),
                        help_text="What is the goal uric acid?",
                        max_digits=2,
                        verbose_name="Goal Uric Acid",
                    ),
                ),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField()),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1),
                ),
            ],
            options={
                "verbose_name": "historical goal urate",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": "history_date",
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
