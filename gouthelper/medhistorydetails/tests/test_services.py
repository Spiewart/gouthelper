from datetime import timedelta
from decimal import Decimal

from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...dateofbirths.forms import DateOfBirthForm
from ...dateofbirths.helpers import age_calc
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.choices import Genders
from ...genders.forms import GenderForm
from ...genders.tests.factories import GenderFactory
from ...labs.forms import BaselineCreatinineForm
from ...labs.models import BaselineCreatinine
from ...labs.tests.factories import BaselineCreatinineFactory
from ...medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
from ...medhistorys.tests.factories import CkdFactory
from ..forms import CkdDetailForm
from ..models import CkdDetail
from ..services import CkdDetailFormProcessor
from .factories import CkdDetailFactory


class TestCkdProcessor(TestCase):
    def setUp(self):
        self.ckd = CkdFactory()
        self.ckddetail = CkdDetailFactory(medhistory=self.ckd, stage=Stages.TWO)
        self.baselinecreatinine = BaselineCreatinineFactory(medhistory=self.ckd)
        self.dateofbirth = DateOfBirthFactory()
        self.gender = GenderFactory()
        # Create some forms that can be modified in the tests
        self.ckddetail_form = CkdDetailForm(
            instance=self.ckddetail,
            data={
                "stage": "",
                "dialysis": True,
                "dialysis_type": DialysisChoices.PERITONEAL,
                "dialysis_duration": DialysisDurations.LESSTHANSIX,
            },
        )
        self.ckddetail_form.is_valid()
        self.baselinecreatinine_form = BaselineCreatinineForm(
            instance=self.baselinecreatinine, data={"baselinecreatinine-value": Decimal("1.2")}
        )
        self.baselinecreatinine_form.is_valid()
        self.dateofbirth_form = DateOfBirthForm(
            instance=self.dateofbirth, data={"dateofbirth-value": timezone.now() - timedelta(days=365 * 50)}
        )
        self.dateofbirth_form.is_valid()
        self.gender_form = GenderForm(instance=self.gender, data={"gender-value": Genders.MALE})
        self.gender_form.is_valid()

    def test___init__(self):
        service = CkdDetailFormProcessor(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        self.assertTrue(hasattr(service, "ckd"))
        self.assertTrue(hasattr(service, "ckddetail_form"))
        self.assertTrue(hasattr(service, "baselinecreatinine_form"))
        self.assertTrue(hasattr(service, "dateofbirth_form"))
        self.assertTrue(hasattr(service, "gender_form"))
        self.assertTrue(hasattr(service, "ckddetail"))
        self.assertTrue(hasattr(service, "baselinecreatinine"))
        self.assertTrue(hasattr(service, "baselinecreatinine_initial"))
        self.assertTrue(hasattr(service, "stage"))
        self.assertTrue(hasattr(service, "dialysis"))
        self.assertTrue(hasattr(service, "dialysis_type"))
        self.assertTrue(hasattr(service, "dialysis_duration"))
        self.assertTrue(hasattr(service, "dateofbirth"))
        self.assertTrue(hasattr(service, "age"))
        self.assertTrue(hasattr(service, "gender"))
        self.assertEqual(getattr(service, "ckd"), self.ckd)
        self.assertEqual(getattr(service, "ckddetail_form"), self.ckddetail_form)
        self.assertEqual(getattr(service, "dialysis"), self.ckddetail_form.cleaned_data["dialysis"])
        self.assertEqual(getattr(service, "dialysis_type"), self.ckddetail_form.cleaned_data["dialysis_type"])
        self.assertEqual(getattr(service, "dialysis_duration"), self.ckddetail_form.cleaned_data["dialysis_duration"])
        self.assertEqual(getattr(service, "stage"), self.ckddetail_form.cleaned_data["stage"])
        self.assertEqual(getattr(service, "baselinecreatinine_form"), self.baselinecreatinine_form)
        self.assertEqual(getattr(service, "baselinecreatinine"), self.baselinecreatinine_form.cleaned_data["value"])
        self.assertEqual(getattr(service, "baselinecreatinine_initial"), self.baselinecreatinine_form.initial["value"])
        self.assertEqual(getattr(service, "dateofbirth"), self.dateofbirth_form.cleaned_data["value"])
        self.assertEqual(getattr(service, "age"), age_calc(self.dateofbirth_form.cleaned_data["value"]))
        self.assertEqual(getattr(service, "gender"), self.gender_form.cleaned_data["value"])

    def test__process_removes_ckddetail_baselinecreatinine(self):
        """Test that CkdDetailFormProcessor.process() removes the CkdDetail and
        baseline creatinine object if dialysis and stage are both null"""
        # Modify the form to remove dialysis and stage
        self.ckddetail_form = CkdDetailForm(
            instance=self.ckddetail, data={"stage": "", "dialysis": "", "dialysis_type": "", "dialysis_duration": ""}
        )
        # Run is_is_valid() method on the CkdDetailForm
        self.ckddetail_form.is_valid()
        # Modify the baselinecreatinine_form to remove the instance and any data
        self.baselinecreatinine_form = BaselineCreatinineForm(instance=self.baselinecreatinine, data={})
        # Run is_is_valid() method on the BaselineCreatinineForm
        self.baselinecreatinine_form.is_valid()
        # Create a CkdDetailFormProcessor object
        service = CkdDetailFormProcessor(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        # Run the process() method and assign output to ckddetail, baselinecreatinine, and errors
        ckddetail, baselinecreatinine, errors = service.process()
        # Assert that ckddetail and baselinecreatinine are None
        self.assertIsNone(baselinecreatinine)
        self.assertIsNone(ckddetail)
        # Assert that errors is False
        self.assertFalse(errors)
        # Check that the CkdDetail and BaselineCreatinine objects have been removed from the database
        self.assertFalse(CkdDetail.objects.filter(pk=self.ckddetail.pk).exists())
        self.assertFalse(BaselineCreatinine.objects.filter(pk=self.baselinecreatinine.pk).exists())

    def test__process_adds_ckddetail(self):
        # Modify the ckddetail_form to create a new instance
        self.ckddetail_form = CkdDetailForm(
            instance=CkdDetail(),
            data={"stage": Stages.FOUR, "dialysis": False, "dialysis_type": "", "dialysis_duration": ""},
        )
        # Modify the baselinecreatinine_form to remove the instance and any data
        self.baselinecreatinine_form = BaselineCreatinineForm(instance=BaselineCreatinine(), data={})
        # Run is_is_valid() method on the CkdDetailForm and BaselineCreatinineForm
        self.ckddetail_form.is_valid()
        self.baselinecreatinine_form.is_valid()
        # Create a CkdDetailFormProcessor object
        service = CkdDetailFormProcessor(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        # Run the process() method and assign output to ckddetail, baselinecreatinine, and errors
        ckddetail, baselinecreatinine, errors = service.process()
        # Assert that ckddetail is not None
        self.assertIsNotNone(ckddetail)
        # Assert that baselinecreatinine is None
        self.assertIsNone(baselinecreatinine)
        # Assert that errors is False
        self.assertFalse(errors)
        # Check that the CkdDetail object has not been added to the database
        # This is because the CkdDetailForm is not saved in the process() method
        self.assertFalse(CkdDetail.objects.filter(pk=ckddetail.pk).exists())
