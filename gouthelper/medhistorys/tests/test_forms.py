import pytest  # type: ignore
from django.forms import BooleanField, HiddenInput, TypedChoiceField
from django.test import TestCase  # type: ignore
from django.urls import reverse  # type: ignore

from ..choices import MedHistoryTypes
from ..forms import (
    AnginaForm,
    AnticoagulationForm,
    BleedForm,
    CadForm,
    ChfForm,
    CkdForm,
    ColchicineinteractionForm,
    DiabetesForm,
    ErosionsForm,
    GastricbypassForm,
    GoutForm,
    HeartattackForm,
    HepatitisForm,
    HypertensionForm,
    HyperuricemiaForm,
    IbdForm,
    MenopauseForm,
    OrgantransplantForm,
    PvdForm,
    StrokeForm,
    TophiForm,
    UratestonesForm,
    XoiinteractionForm,
)

pytestmark = pytest.mark.django_db


class TestAnginaForm(TestCase):
    def test___init__(self):
        form = AnginaForm()
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.ANGINA}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.ANGINA}-value"].label,
            "Angina",
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.ANGINA}-value"].help_text,
            "Exertional chest pain",
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.ANGINA}-value"],
                BooleanField,
            )
        )


class TestAnticoagulationForm(TestCase):
    def test___init__(self):
        form = AnticoagulationForm()
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.ANTICOAGULATION}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.ANTICOAGULATION}-value"].label,
            "Anticoagulation",
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.ANTICOAGULATION}-value"].help_text,
            "Is the patient on blood thinners (other than aspirin)?",
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.ANTICOAGULATION}-value"],
                BooleanField,
            )
        )


class TestBleedForm(TestCase):
    def test___init__(self):
        form = BleedForm()
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.BLEED}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.BLEED}-value"].label,
            "Bleed",
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.BLEED}-value"].help_text,
            "History of major bleeding without truama?",
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.BLEED}-value"],
                BooleanField,
            )
        )


class TestCadForm(TestCase):
    def test___init__(self):
        form = CadForm()
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.CAD}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.CAD}-value"].label,
            "Coronary Artery Disease",
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.CAD}-value"].help_text,
            "Blocked arteries in the heart",
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.CAD}-value"],
                BooleanField,
            )
        )


class TestChfForm(TestCase):
    def test___init__(self):
        form = ChfForm()
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.CHF}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.CHF}-value"].label,
            "CHF",
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.CHF}-value"].help_text,
            "Congestive Heart Failure",
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.CHF}-value"],
                BooleanField,
            )
        )


class TestCkdForm(TestCase):
    def test___init__with_ckddetail_kwarg(self):
        form = CkdForm(ckddetail=True)
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.CKD}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.CKD}-value"].label,
            "CKD",
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.CKD}-value"].help_text,
            "Does the patient have chronic kidney disease (CKD)?",
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.CKD}-value"],
                TypedChoiceField,
            )
        )
        # Test that CkdDetailForm is inserted
        response = self.client.get(reverse("flareaids:create"))
        self.assertIn("ckddetail-form", response.rendered_content)

    def test___init__without_ckddetail_kwarg(self):
        form = CkdForm(ckddetail=False)
        # render the form
        rendered_form = form.as_p()
        # Test that CkdDetailForm is not inserted
        self.assertNotIn("ckddetail-form", rendered_form)


class TestColchicineinteractionForm(TestCase):
    def test___init__(self):
        form = ColchicineinteractionForm()
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.COLCHICINEINTERACTION}-value"].label,
            "Colchicine Interaction",
        )
        self.assertIn(
            "medications that interact with colchicin",
            form.fields[f"{MedHistoryTypes.COLCHICINEINTERACTION}-value"].help_text,
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.COLCHICINEINTERACTION}-value"],
                TypedChoiceField,
            )
        )


class TestDiabetesForm(TestCase):
    def test___init__(self):
        form = DiabetesForm()
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.DIABETES}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.DIABETES}-value"].label,
            "Diabetes",
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.DIABETES}-value"].help_text,
            "Is the patient a diabetic?",
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.DIABETES}-value"],
                TypedChoiceField,
            )
        )


class TestErosionsForm(TestCase):
    def test___init__(self):
        form = ErosionsForm()
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.EROSIONS}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.EROSIONS}-value"].label,
            "Erosions",
        )
        self.assertIn(
            "erosions",
            form.fields[f"{MedHistoryTypes.EROSIONS}-value"].help_text,
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.EROSIONS}-value"],
                TypedChoiceField,
            )
        )


class TestGastricbypassForm(TestCase):
    def test___init__(self):
        form = GastricbypassForm()
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.GASTRICBYPASS}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.GASTRICBYPASS}-value"].label,
            "Gastric Bypass",
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.GASTRICBYPASS}-value"].help_text,
            "Sleave, roux-en-y, or duodenal switch?",
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.GASTRICBYPASS}-value"],
                BooleanField,
            )
        )


class TestGoutForm(TestCase):
    def test___init__goutdetail_False(self):
        form = GoutForm(goutdetail=False)
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.GOUT}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.GOUT}-value"].label,
            "Gout",
        )
        self.assertIn(
            "Has the patient had gout",
            form.fields[f"{MedHistoryTypes.GOUT}-value"].help_text,
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.GOUT}-value"],
                TypedChoiceField,
            )
        )
        # Test that GoutDetailForm is not inserted
        response = self.client.get(reverse("flares:create"))
        self.assertNotIn("goutdetail-form", response.rendered_content)

    def test___init__goutdetail_True(self):
        form = GoutForm(goutdetail=True)
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.GOUT}-value",
            form.fields,
        )
        # Label should be None because the form will be hidden
        self.assertIsNone(
            form.fields[f"{MedHistoryTypes.GOUT}-value"].label,
        )
        # Help text should be empty string because the form will be hidden
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.GOUT}-value"].help_text,
            "",
        )
        # Initial value should be true
        self.assertTrue(
            form.fields[f"{MedHistoryTypes.GOUT}-value"].initial,
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.GOUT}-value"].widget,
                HiddenInput,
            )
        )
        # Test that GoutDetailForm is inserted
        # PpxCreateView has goutdetail=True
        response = self.client.get(reverse("ppxs:create"))
        self.assertIn("goutdetail-form", response.rendered_content)


class TestHeartattackForm(TestCase):
    def test___init__(self):
        form = HeartattackForm()
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.HEARTATTACK}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.HEARTATTACK}-value"].label,
            "Heart Attack",
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.HEARTATTACK}-value"].help_text,
            "Myocardial infarction",
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.HEARTATTACK}-value"],
                BooleanField,
            )
        )


class TestHepatitisForm(TestCase):
    def test___init__(self):
        form = HepatitisForm()
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.HEPATITIS}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.HEPATITIS}-value"].label,
            "Hepatitis",
        )
        self.assertIn(
            "Does the patient have",
            form.fields[f"{MedHistoryTypes.HEPATITIS}-value"].help_text,
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.HEPATITIS}-value"],
                TypedChoiceField,
            )
        )


class TestHypertensionForm(TestCase):
    def test___init__(self):
        form = HypertensionForm()
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.HYPERTENSION}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.HYPERTENSION}-value"].label,
            "Hypertension",
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.HYPERTENSION}-value"].help_text,
            "High blood pressure",
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.HYPERTENSION}-value"],
                BooleanField,
            )
        )


class TestHyperuricemiaForm(TestCase):
    def test___init__(self):
        form = HyperuricemiaForm()
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.HYPERURICEMIA}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.HYPERURICEMIA}-value"].label,
            "Hyperuricemia",
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.HYPERURICEMIA}-value"].help_text,
            "Does the patient have an elevated serum uric acid (greater than 9.0 mg/dL)?",
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.HYPERURICEMIA}-value"],
                TypedChoiceField,
            )
        )


class TestIbdForm(TestCase):
    def test___init__(self):
        form = IbdForm()
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.IBD}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.IBD}-value"].label,
            "Inflammatory Bowel Disease",
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.IBD}-value"].help_text,
            "Crohn's disease or ulcerative colitis",
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.IBD}-value"],
                BooleanField,
            )
        )


class TestMenopauseForm(TestCase):
    def test___init__(self):
        form = MenopauseForm()
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.MENOPAUSE}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.MENOPAUSE}-value"].label,
            "Menopause",
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.MENOPAUSE}-value"].help_text,
            "Is the patient menopausal or post-menopausal?",
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.MENOPAUSE}-value"],
                TypedChoiceField,
            )
        )


class TestOrgantransplantForm(TestCase):
    def test___init__(self):
        form = OrgantransplantForm()
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.ORGANTRANSPLANT}-value"].label,
            "Organ Transplant",
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.ORGANTRANSPLANT}-value"].help_text,
            "Has the patient had an organ transplant?",
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.ORGANTRANSPLANT}-value"],
                TypedChoiceField,
            )
        )


class TestPvdForm(TestCase):
    def test___init__(self):
        form = PvdForm()
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.PVD}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.PVD}-value"].label,
            "Peripheral Arterial Disease",
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.PVD}-value"].help_text,
            "Blocked arteries in the legs or arms",
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.PVD}-value"],
                BooleanField,
            )
        )


class TestStrokeForm(TestCase):
    def test___init__(self):
        form = StrokeForm()
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.STROKE}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.STROKE}-value"].label,
            "Stroke",
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.STROKE}-value"].help_text,
            "Cerebrovascular accident",
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.STROKE}-value"],
                BooleanField,
            )
        )


class TestTophiForm(TestCase):
    def test___init__(self):
        form = TophiForm()
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.TOPHI}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.TOPHI}-value"].label,
            "Tophi",
        )
        self.assertIn(
            "Does the patient have gouty tophi?",
            form.fields[f"{MedHistoryTypes.TOPHI}-value"].help_text,
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.TOPHI}-value"],
                TypedChoiceField,
            )
        )


class TestUratestonesForm(TestCase):
    def test___init__(self):
        form = UratestonesForm()
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.URATESTONES}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.URATESTONES}-value"].label,
            "Urate Kidney Stones",
        )
        self.assertIn(
            "Does the patient have a history of",
            form.fields[f"{MedHistoryTypes.URATESTONES}-value"].help_text,
        )
        self.assertTrue(
            isinstance(
                form.fields[f"{MedHistoryTypes.URATESTONES}-value"],
                TypedChoiceField,
            )
        )


class TestXoiinteractionForm(TestCase):
    def test___init__(self):
        form = XoiinteractionForm()
        # Assert value field is correct
        self.assertIn(
            f"{MedHistoryTypes.XOIINTERACTION}-value",
            form.fields,
        )
        self.assertEqual(
            form.fields[f"{MedHistoryTypes.XOIINTERACTION}-value"].label,
            "Xanthine Oxidase Inhibitor Interaction",
        )
        self.assertIn(
            "Is the patient on",
            form.fields[f"{MedHistoryTypes.XOIINTERACTION}-value"].help_text,
        )
