# Generated by Django 4.2.6 on 2024-03-19 21:33

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("defaults", "0007_auto_20240316_1455"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="defaultmedhistory",
            name="defaults_defaultmedhistory_medhistorytype_valid",
        ),
        migrations.AlterField(
            model_name="defaultmedhistory",
            name="medhistorytype",
            field=models.CharField(
                choices=[
                    ("ALLOPURINOLHYPERSENSITIVITY", "Allopurinol Hypersensitivity Syndrome"),
                    ("ANGINA", "Angina"),
                    ("ANTICOAGULATION", "Anticoagulation"),
                    ("BLEED", "Bleed"),
                    ("CAD", "Coronary Artery Disease"),
                    ("CHF", "Congestive Heart Failure"),
                    ("CKD", "Chronic Kidney Disease"),
                    ("COLCHICINEINTERACTION", "Colchicine Medication Interaction"),
                    ("DIABETES", "Diabetes"),
                    ("EROSIONS", "Erosions"),
                    ("FEBUXOSTATHYPERSENSITIVITY", "Febuxostat Hypersensitivity Syndrome"),
                    ("GASTRICBYPASS", "Gastric Bypass"),
                    ("GOUT", "Gout"),
                    ("HEARTATTACK", "Heart Attack"),
                    ("HYPERTENSION", "Hypertension"),
                    ("HYPERURICEMIA", "Hyperuricemia"),
                    ("IBD", "Inflammatory Bowel Disease"),
                    ("MENOPAUSE", "Post-Menopausal"),
                    ("ORGANTRANSPLANT", "Organ Transplant"),
                    ("OSTEOPOROSIS", "Osteoporosis"),
                    ("PUD", "Peptic Ulcer Disease"),
                    ("PVD", "Peripheral Vascular Disease"),
                    ("STROKE", "Stroke"),
                    ("TOPHI", "Tophi"),
                    ("URATESTONES", "Urate kidney stones"),
                    ("XOIINTERACTION", "Xanthine Oxidase Inhibitor Medication Interaction"),
                ],
                max_length=30,
                verbose_name="History Type",
            ),
        ),
        migrations.AddConstraint(
            model_name="defaultmedhistory",
            constraint=models.CheckConstraint(
                check=models.Q(
                    (
                        "medhistorytype__in",
                        [
                            "ALLOPURINOLHYPERSENSITIVITY",
                            "ANGINA",
                            "ANTICOAGULATION",
                            "BLEED",
                            "CAD",
                            "CHF",
                            "CKD",
                            "COLCHICINEINTERACTION",
                            "DIABETES",
                            "EROSIONS",
                            "FEBUXOSTATHYPERSENSITIVITY",
                            "GASTRICBYPASS",
                            "GOUT",
                            "HEARTATTACK",
                            "HYPERTENSION",
                            "HYPERURICEMIA",
                            "IBD",
                            "MENOPAUSE",
                            "ORGANTRANSPLANT",
                            "OSTEOPOROSIS",
                            "PUD",
                            "PVD",
                            "STROKE",
                            "TOPHI",
                            "URATESTONES",
                            "XOIINTERACTION",
                        ],
                    )
                ),
                name="defaults_defaultmedhistory_medhistorytype_valid",
            ),
        ),
    ]
