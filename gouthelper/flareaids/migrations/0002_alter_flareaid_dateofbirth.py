# Generated by Django 4.2.6 on 2023-11-07 00:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("dateofbirths", "0002_remove_dateofbirth_dateofbirth_18_years_or_older_and_more"),
        ("flareaids", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="flareaid",
            name="dateofbirth",
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to="dateofbirths.dateofbirth"),
        ),
    ]