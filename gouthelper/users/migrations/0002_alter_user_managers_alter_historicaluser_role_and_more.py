# Generated by Django 4.2.6 on 2023-12-20 19:50

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelManagers(
            name="user",
            managers=[],
        ),
        migrations.AlterField(
            model_name="historicaluser",
            name="role",
            field=models.CharField(
                choices=[
                    ("PATIENT", "Patient"),
                    ("PROVIDER", "Provider"),
                    ("PSEUDOPATIENT", "Pseudopatient"),
                    ("ADMIN", "Admin"),
                ],
                default="PROVIDER",
                max_length=50,
                verbose_name="Role",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("PATIENT", "Patient"),
                    ("PROVIDER", "Provider"),
                    ("PSEUDOPATIENT", "Pseudopatient"),
                    ("ADMIN", "Admin"),
                ],
                default="PROVIDER",
                max_length=50,
                verbose_name="Role",
            ),
        ),
    ]