# Generated by Django 4.2.6 on 2024-07-28 22:32

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0006_historicalpseudopatientprofile_provider_alias_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="pseudopatientprofile",
            name="unique_provider_alias",
        ),
        migrations.RemoveConstraint(
            model_name="pseudopatientprofile",
            name="has_alias_if_has_provider",
        ),
        migrations.AlterField(
            model_name="historicalpseudopatientprofile",
            name="provider_alias",
            field=models.IntegerField(blank=True, default=None, null=True),
        ),
        migrations.AlterField(
            model_name="pseudopatientprofile",
            name="provider_alias",
            field=models.IntegerField(blank=True, default=None, null=True),
        ),
        migrations.AddConstraint(
            model_name="pseudopatientprofile",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("provider__isnull", False),
                    models.Q(("provider__isnull", True), ("provider_alias__isnull", True)),
                    _connector="OR",
                ),
                name="pseudopatientprofile_alias_requires_provider",
            ),
        ),
    ]
