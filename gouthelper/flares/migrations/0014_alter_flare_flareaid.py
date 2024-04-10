# Generated by Django 4.2.6 on 2024-04-07 21:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("flareaids", "0005_remove_flareaid_medallergys_and_more"),
        ("flares", "0013_remove_flare_flares_flare_valid_flare_flareaid_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="flare",
            name="flareaid",
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="flareaids.flareaid"
            ),
        ),
    ]
