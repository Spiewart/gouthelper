# Generated by Django 4.2.6 on 2024-04-06 13:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("flareaids", "0005_remove_flareaid_medallergys_and_more"),
        ("flares", "0012_flare_aki_historicalflare_aki"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="flare",
            name="flares_flare_valid",
        ),
        migrations.AddField(
            model_name="flare",
            name="flareaid",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="flareaids.flareaid"
            ),
        ),
        migrations.AddField(
            model_name="historicalflare",
            name="flareaid",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="flareaids.flareaid",
            ),
        ),
        migrations.AlterField(
            model_name="flare",
            name="likelihood",
            field=models.CharField(
                blank=True,
                choices=[("UNLIKELY", "Unlikely"), ("EQUIVOCAL", "Indeterminate"), ("LIKELY", "Likely")],
                default=None,
                max_length=20,
                null=True,
                verbose_name="Likelihood",
            ),
        ),
        migrations.AlterField(
            model_name="historicalflare",
            name="likelihood",
            field=models.CharField(
                blank=True,
                choices=[("UNLIKELY", "Unlikely"), ("EQUIVOCAL", "Indeterminate"), ("LIKELY", "Likely")],
                default=None,
                max_length=20,
                null=True,
                verbose_name="Likelihood",
            ),
        ),
        migrations.AddConstraint(
            model_name="flare",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        ("dateofbirth__isnull", True),
                        ("flareaid__isnull", True),
                        ("gender__isnull", True),
                        ("user__isnull", False),
                    ),
                    models.Q(("dateofbirth__isnull", False), ("gender__isnull", False), ("user__isnull", True)),
                    _connector="OR",
                ),
                name="flares_flare_valid",
            ),
        ),
    ]