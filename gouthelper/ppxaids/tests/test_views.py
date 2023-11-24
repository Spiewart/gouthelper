from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.db.models import Q, QuerySet  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils import timezone  # type: ignore

from ...contents.models import Content, Tags
from ...dateofbirths.helpers import age_calc
from ...dateofbirths.models import DateOfBirth
from ...genders.choices import Genders
from ...genders.models import Gender
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...labs.models import BaselineCreatinine
from ...medallergys.models import MedAllergy
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.choices import DialysisChoices, DialysisDurations
from ...medhistorydetails.models import CkdDetail
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.models import MedHistory
from ...medhistorys.tests.factories import MedHistoryFactory
from ...treatments.choices import Treatments
from ...utils.helpers.test_helpers import tests_print_response_form_errors
from ..models import PpxAid
from ..views import PpxAidAbout, PpxAidCreate, PpxAidDetail, PpxAidUpdate
from .factories import PpxAidFactory

pytestmark = pytest.mark.django_db


@pytest.mark.usefixtures("contents_setup")
class TestPpxAidAbout(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: PpxAidAbout = PpxAidAbout()

    def test__get(self):
        response = self.client.get(reverse("ppxaids:about"))
        self.assertEqual(response.status_code, 200)

    def test__get_context_data(self):
        response = self.client.get(reverse("ppxaids:about"))
        self.assertIn("content", response.context_data)

    def test__content(self):
        self.assertEqual(
            self.view.content, Content.objects.get(context=Content.Contexts.PPXAID, slug="about", tag=None)
        )


class TestPpxAidCreate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: PpxAidCreate = PpxAidCreate()
        self.ppxaid_data = {
            "dateofbirth-value": (timezone.now() - timedelta(days=365 * 50)).date(),
            "gender-value": Genders.FEMALE,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
        }

    def test__successful_post(self):
        response = self.client.post(reverse("ppxaids:create"), self.ppxaid_data)
        tests_print_response_form_errors(response)
        self.assertTrue(PpxAid.objects.get())
        self.assertEqual(response.status_code, 302)

    def test__post_creates_medhistory(self):
        self.ppxaid_data.update({f"{MedHistoryTypes.STROKE}-value": True})
        response = self.client.post(reverse("ppxaids:create"), self.ppxaid_data)
        tests_print_response_form_errors(response)
        self.assertTrue(PpxAid.objects.get())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.STROKE).exists())
        self.assertEqual(MedHistory.objects.count(), 1)
        self.assertIn(
            MedHistoryTypes.STROKE, PpxAid.objects.get().medhistorys.values_list("medhistorytype", flat=True)
        )

    def test__post_creates_medhistorys(self):
        self.ppxaid_data.update({f"{MedHistoryTypes.STROKE}-value": True})
        self.ppxaid_data.update({f"{MedHistoryTypes.DIABETES}-value": True})
        response = self.client.post(reverse("ppxaids:create"), self.ppxaid_data)
        tests_print_response_form_errors(response)
        self.assertTrue(PpxAid.objects.get())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.STROKE).exists())
        self.assertTrue(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.DIABETES).exists())
        self.assertEqual(MedHistory.objects.count(), 2)
        self.assertIn(
            MedHistoryTypes.STROKE, PpxAid.objects.get().medhistorys.values_list("medhistorytype", flat=True)
        )
        self.assertIn(
            MedHistoryTypes.DIABETES, PpxAid.objects.get().medhistorys.values_list("medhistorytype", flat=True)
        )

    def test__post_creates_ckddetail(self):
        self.ppxaid_data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": True,
                "dialysis_duration": DialysisDurations.LESSTHANSIX,
                "dialysis_type": DialysisChoices.PERITONEAL,
            }
        )
        response = self.client.post(reverse("ppxaids:create"), self.ppxaid_data)
        tests_print_response_form_errors(response)
        self.assertTrue(CkdDetail.objects.get())
        self.assertTrue(PpxAid.objects.get().ckddetail)

    def test__post_creates_baselinecreatinine(self):
        self.ppxaid_data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": False,
                "baselinecreatinine-value": Decimal("2.2"),
                "dateofbirth-value": (timezone.now() - timedelta(days=365 * 50)).date(),
                "gender-value": Genders.MALE,
            }
        )
        response = self.client.post(reverse("ppxaids:create"), self.ppxaid_data)
        tests_print_response_form_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(BaselineCreatinine.objects.get())
        self.assertEqual(PpxAid.objects.get().ckd.baselinecreatinine.value, Decimal("2.2"))
        self.assertEqual(BaselineCreatinine.objects.count(), 1)
        self.assertEqual(
            CkdDetail.objects.get().stage,
            labs_stage_calculator(
                labs_eGFR_calculator(
                    BaselineCreatinine.objects.get(),
                    age_calc(DateOfBirth.objects.get().value),
                    Gender.objects.get().value,
                )
            ),
        )

    def test__post_raises_ValidationError_no_dateofbirth(self):
        self.ppxaid_data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": False,
                "baselinecreatinine-value": Decimal("2.2"),
                "dateofbirth-value": "",
                "gender-value": Genders.MALE,
            }
        )
        response = self.client.post(reverse("ppxaids:create"), self.ppxaid_data)
        self.assertEqual(response.status_code, 200)
        # Assert that the response context contains a field error for dateofbirth
        self.assertTrue("value" in response.context["dateofbirth_form"].errors)

    def test__post_does_not_raise_error_no_gender(self):
        self.ppxaid_data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": False,
                "gender-value": "",
            }
        )
        response = self.client.post(reverse("ppxaids:create"), self.ppxaid_data)
        self.assertEqual(response.status_code, 302)

    def test__post_raises_ValidationError_baselinecreatinine_no_gender(self):
        self.ppxaid_data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": False,
                "baselinecreatinine-value": Decimal("2.2"),
                "gender-value": "",
            }
        )
        response = self.client.post(reverse("ppxaids:create"), self.ppxaid_data)
        self.assertEqual(response.status_code, 200)
        # Assert that the response context contains a field error for dateofbirth
        self.assertTrue("value" in response.context["gender_form"].errors)
        # Check the error message includes the baseline creatinine
        self.assertIn("baseline creatinine", response.context["gender_form"].errors["value"][0])

    def test__post_adds_medallergys(self):
        self.ppxaid_data.update(
            {
                f"medallergy_{Treatments.COLCHICINE}": True,
                f"medallergy_{Treatments.PREDNISONE}": True,
                f"medallergy_{Treatments.NAPROXEN}": True,
            }
        )
        response = self.client.post(reverse("ppxaids:create"), self.ppxaid_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MedAllergy.objects.filter(treatment=Treatments.COLCHICINE).exists())
        self.assertTrue(MedAllergy.objects.filter(treatment=Treatments.PREDNISONE).exists())
        self.assertTrue(MedAllergy.objects.filter(treatment=Treatments.NAPROXEN).exists())
        self.assertEqual(MedAllergy.objects.count(), 3)


@pytest.mark.usefixtures("contents_setup")
class TestPpxAidDetail(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: PpxAidDetail = PpxAidDetail
        self.content_qs = Content.objects.filter(
            Q(tag=Tags.EXPLANATION) | Q(tag=Tags.WARNING), context=Content.Contexts.PPXAID, slug__isnull=False
        ).all()
        self.ppxaid = PpxAidFactory()

    def test__contents(self):
        self.assertTrue(self.view().contents)
        self.assertTrue(isinstance(self.view().contents, QuerySet))
        for content in self.view().contents:
            self.assertIn(content, self.content_qs)
        for content in self.content_qs:
            self.assertIn(content, self.view().contents)

    def test__get_context_data(self):
        response = self.client.get(reverse("ppxaids:detail", kwargs={"pk": self.ppxaid.pk}))
        context = response.context_data
        for content in self.content_qs:
            self.assertIn(content.slug, context)
            self.assertEqual(context[content.slug], {content.tag: content})

    def test__get_queryset(self):
        qs = self.view(kwargs={"pk": self.ppxaid.pk}).get_queryset()
        self.assertTrue(isinstance(qs, QuerySet))
        self.assertEqual(qs.first(), self.ppxaid)
        self.assertTrue(hasattr(qs.first(), "medhistorys_qs"))
        self.assertTrue(hasattr(qs.first(), "medallergys_qs"))
        self.assertTrue(hasattr(qs.first(), "ckddetail"))
        self.assertTrue(hasattr(qs.first(), "baselinecreatinine"))
        self.assertTrue(hasattr(qs.first(), "dateofbirth"))
        self.assertTrue(hasattr(qs.first(), "gender"))

    def test__get_object_updates(self):
        self.assertTrue(self.ppxaid.recommendation[0] == Treatments.NAPROXEN)
        medallergy = MedAllergyFactory(treatment=Treatments.NAPROXEN)
        self.ppxaid.medallergys.add(medallergy)
        request = self.factory.get(reverse("ppxaids:detail", kwargs={"pk": self.ppxaid.pk}))
        self.view.as_view()(request, pk=self.ppxaid.pk)
        # This needs to be manually refetched from the db
        self.assertFalse(PpxAid.objects.get().recommendation[0] == Treatments.NAPROXEN)

    def test__get_object_does_not_update(self):
        self.assertTrue(self.ppxaid.recommendation[0] == Treatments.NAPROXEN)
        request = self.factory.get(reverse("ppxaids:detail", kwargs={"pk": self.ppxaid.pk}) + "?updated=True")
        self.view.as_view()(request, pk=self.ppxaid.pk)
        # This needs to be manually refetched from the db
        self.assertTrue(PpxAid.objects.get().recommendation[0] == Treatments.NAPROXEN)


class TestPpxAidUpdate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: PpxAidUpdate = PpxAidUpdate()

    def test__post_unchanged_medallergys(self):
        ppxaid = PpxAidFactory()
        medallergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        ppxaid.medallergys.add(medallergy)
        ppxaid_data = {
            "dateofbirth-value": ppxaid.dateofbirth.value,
            "gender-value": "",
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"medallergy_{Treatments.COLCHICINE}": True,
        }
        response = self.client.post(reverse("ppxaids:update", kwargs={"pk": ppxaid.pk}), ppxaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MedAllergy.objects.filter(treatment=Treatments.COLCHICINE).exists())

    def test__post_add_medallergys(self):
        ppxaid = PpxAidFactory()
        medallergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        ppxaid.medallergys.add(medallergy)
        ppxaid_data = {
            "dateofbirth-value": ppxaid.dateofbirth.value,
            "gender-value": "",
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"medallergy_{Treatments.COLCHICINE}": True,
            f"medallergy_{Treatments.PREDNISONE}": True,
            f"medallergy_{Treatments.NAPROXEN}": True,
        }
        response = self.client.post(reverse("ppxaids:update", kwargs={"pk": ppxaid.pk}), ppxaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MedAllergy.objects.filter(treatment=Treatments.PREDNISONE).exists())
        self.assertTrue(MedAllergy.objects.filter(treatment=Treatments.NAPROXEN).exists())
        self.assertEqual(MedAllergy.objects.count(), 3)

    def test__post_delete_medallergys(self):
        ppxaid = PpxAidFactory()
        medallergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        ppxaid.medallergys.add(medallergy)
        ppxaid_data = {
            "dateofbirth-value": ppxaid.dateofbirth.value,
            "gender-value": "",
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"medallergy_{Treatments.COLCHICINE}": "",
        }
        response = self.client.post(reverse("ppxaids:update", kwargs={"pk": ppxaid.pk}), ppxaid_data)
        self.assertEqual(response.status_code, 302)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertFalse(MedAllergy.objects.filter(treatment=Treatments.COLCHICINE).exists())
        self.assertEqual(MedAllergy.objects.count(), 0)

    def test__post_unchanged_medhistorys(self):
        ppxaid = PpxAidFactory()
        medhistory = MedHistoryFactory(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION)
        ppxaid.medhistorys.add(medhistory)
        ppxaid_data = {
            "dateofbirth-value": ppxaid.dateofbirth.value,
            "gender-value": "",
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": True,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
        }
        response = self.client.post(reverse("ppxaids:update", kwargs={"pk": ppxaid.pk}), ppxaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION).exists())
        self.assertEqual(MedHistory.objects.count(), 1)

    def test__post_delete_medhistorys(self):
        ppxaid = PpxAidFactory()
        medhistory = MedHistoryFactory(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION)
        ppxaid.medhistorys.add(medhistory)
        ppxaid_data = {
            "dateofbirth-value": ppxaid.dateofbirth.value,
            "gender-value": "",
            f"{MedHistoryTypes.CKD}-value": False,
            # Need to mark Colchicineinteraction as False to delete it, required by form.
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
        }
        response = self.client.post(reverse("ppxaids:update", kwargs={"pk": ppxaid.pk}), ppxaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION).exists())
        self.assertEqual(MedHistory.objects.count(), 0)

    def test__post_add_medhistorys(self):
        ppxaid = PpxAidFactory()
        medhistory = MedHistoryFactory(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION)
        ppxaid.medhistorys.add(medhistory)
        ppxaid_data = {
            "dateofbirth-value": ppxaid.dateofbirth.value,
            "gender-value": "",
            f"{MedHistoryTypes.CKD}-value": False,
            # Need to mark Colchicineinteraction as False to delete it, required by form.
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": True,
            f"{MedHistoryTypes.DIABETES}-value": True,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"{MedHistoryTypes.STROKE}-value": True,
        }
        response = self.client.post(reverse("ppxaids:update", kwargs={"pk": ppxaid.pk}), ppxaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION).exists())
        self.assertTrue(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.DIABETES).exists())
        self.assertTrue(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.STROKE).exists())
        self.assertEqual(MedHistory.objects.count(), 3)
