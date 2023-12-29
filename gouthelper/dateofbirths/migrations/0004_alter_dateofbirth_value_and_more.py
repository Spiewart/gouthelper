# Generated by Django 4.2.6 on 2023-12-28 21:00

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dateofbirths", "0003_dateofbirth_user_historicaldateofbirth_user"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dateofbirth",
            name="value",
            field=models.DateField(
                help_text='How old is the patient (range: 18-120)? <a href="/dateofbirths/about/" target="_next">Why do we need to know?</a>',
                verbose_name="Age",
            ),
        ),
        migrations.AlterField(
            model_name="historicaldateofbirth",
            name="value",
            field=models.DateField(
                help_text='How old is the patient (range: 18-120)? <a href="/dateofbirths/about/" target="_next">Why do we need to know?</a>',
                verbose_name="Age",
            ),
        ),
    ]
