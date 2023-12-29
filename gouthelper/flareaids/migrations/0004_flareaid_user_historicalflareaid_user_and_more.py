# Generated by Django 4.2.6 on 2023-12-29 16:09

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("dateofbirths", "0004_alter_dateofbirth_value_and_more"),
        ("flareaids", "0003_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="flareaid",
            name="user",
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name="historicalflareaid",
            name="user",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="flareaid",
            name="dateofbirth",
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="dateofbirths.dateofbirth"
            ),
        ),
        migrations.AddConstraint(
            model_name="flareaid",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("dateofbirth__isnull", True), ("gender__isnull", True), ("user__isnull", False)),
                    models.Q(("dateofbirth__isnull", False), ("user__isnull", True)),
                    _connector="OR",
                ),
                name="flareaids_flareaid_valid",
            ),
        ),
    ]
