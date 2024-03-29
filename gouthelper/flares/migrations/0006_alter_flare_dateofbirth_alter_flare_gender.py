# Generated by Django 4.2.6 on 2024-01-10 12:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("genders", "0005_alter_gender_value_alter_historicalgender_value"),
        ("dateofbirths", "0004_alter_dateofbirth_value_and_more"),
        ("flares", "0005_alter_flare_dateofbirth_alter_flare_gender_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="flare",
            name="dateofbirth",
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="dateofbirths.dateofbirth"
            ),
        ),
        migrations.AlterField(
            model_name="flare",
            name="gender",
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="genders.gender"
            ),
        ),
    ]
