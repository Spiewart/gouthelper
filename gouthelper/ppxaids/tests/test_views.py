from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.contrib.auth.models import AnonymousUser  # type: ignore
from django.db.models import Q, QuerySet  # type: ignore
from django.http import HttpResponse  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils import timezone  # type: ignore

from ...contents.models import Content, Tags
from ...dateofbirths.helpers import age_calc
from ...genders.choices import Genders
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...labs.models import BaselineCreatinine
from ...medallergys.models import MedAllergy
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.choices import DialysisChoices, DialysisDurations
from ...medhistorydetails.models import CkdDetail
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.models import MedHistory
from ...treatments.choices import Treatments
from ...utils.helpers.test_helpers import tests_print_response_form_errors
from ..models import PpxAid
from ..views import PpxAidAbout, PpxAidCreate, PpxAidDetail, PpxAidUpdate
from .factories import create_ppxaid, ppxaid_data_factory

pytestmark = pytest.mark.django_db


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
            "dateofbirth-value": age_calc(timezone.now() - timedelta(days=365 * 50)),
            "gender-value": Genders.FEMALE,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
        }

    def test__successful_post(self):
        # Count the number of PpxAid objects before the POST
        ppxaid_count = PpxAid.objects.count()
        response = self.client.post(reverse("ppxaids:create"), self.ppxaid_data)
        tests_print_response_form_errors(response)
        self.assertEqual(response.status_code, 302)

        # Test that a PpxAid was created
        self.assertEqual(PpxAid.objects.count(), ppxaid_count + 1)

    def test__post_creates_medhistory(self):
        """Test that the post() method creates a MedHistory object."""

        # Count the number of MedHistory objects before the POST
        medhistory_count = MedHistory.objects.count()

        # Create some fake post() data with CKD and POST it
        self.ppxaid_data.update({f"{MedHistoryTypes.STROKE}-value": True})
        response = self.client.post(reverse("ppxaids:create"), self.ppxaid_data)
        tests_print_response_form_errors(response)

        self.assertEqual(response.status_code, 302)

        # Test that a MedHistory was created
        self.assertEqual(MedHistory.objects.count(), medhistory_count + 1)
        ppxaid = PpxAid.objects.order_by("created").last()
        mh = MedHistory.objects.order_by("created").last()
        self.assertIn(mh, ppxaid.medhistory_set.all())

    def test__post_creates_medhistorys(self):
        """Test that the post() method creates multiple MedHistory objects."""

        # Count the number of MedHistory objects before the POST
        medhistory_count = MedHistory.objects.count()

        # Create some fake post() data with CKD and POST it
        self.ppxaid_data.update({f"{MedHistoryTypes.STROKE}-value": True})
        self.ppxaid_data.update({f"{MedHistoryTypes.DIABETES}-value": True})
        response = self.client.post(reverse("ppxaids:create"), self.ppxaid_data)
        tests_print_response_form_errors(response)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(MedHistory.objects.count(), medhistory_count + 2)
        ppxaid = PpxAid.objects.order_by("created").prefetch_related("medhistory_set").last()
        ppxaid_medhistorys = ppxaid.medhistory_set.all()
        stroke = MedHistory.objects.order_by("created").filter(medhistorytype=MedHistoryTypes.STROKE).last()
        diabetes = MedHistory.objects.order_by("created").filter(medhistorytype=MedHistoryTypes.DIABETES).last()
        self.assertIn(stroke, ppxaid_medhistorys)
        self.assertIn(diabetes, ppxaid_medhistorys)

    def test__post_creates_ckddetail(self):
        """Test that the post() method creates a CkdDetail object."""
        # Count the number of CkdDetail objects before the POST
        ckddetail_count = CkdDetail.objects.count()

        # Create some fake post() data with CKD and POST it
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
        self.assertEqual(response.status_code, 302)

        # Test that a CkdDetail was created
        self.assertEqual(CkdDetail.objects.count(), ckddetail_count + 1)

        ppxaid = PpxAid.objects.order_by("created").last()
        ckddetail = CkdDetail.objects.order_by("created").last()
        self.assertEqual(ppxaid.ckddetail, ckddetail)

    def test__post_creates_baselinecreatinine(self):
        """Test that the post() method creates a BaselineCreatinine object."""
        # Count the number of BaselineCreatinine objects before the POST
        baselinecreatinine_count = BaselineCreatinine.objects.count()
        self.ppxaid_data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": False,
                "baselinecreatinine-value": Decimal("2.2"),
                "dateofbirth-value": age_calc(timezone.now() - timedelta(days=365 * 50)),
                "gender-value": Genders.MALE,
            }
        )
        response = self.client.post(reverse("ppxaids:create"), self.ppxaid_data)
        tests_print_response_form_errors(response)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(BaselineCreatinine.objects.count(), baselinecreatinine_count + 1)
        ppxaid = PpxAid.objects.order_by("created").last()
        bc = BaselineCreatinine.objects.order_by("created").last()
        ckddetail = CkdDetail.objects.order_by("created").last()
        self.assertEqual(ppxaid.ckd.baselinecreatinine.value, Decimal("2.2"))
        self.assertEqual(
            ckddetail.stage,
            labs_stage_calculator(
                labs_eGFR_calculator(
                    bc,
                    age_calc(ppxaid.dateofbirth.value),
                    ppxaid.gender.value,
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
        """Test that the post() method creates medallergys."""
        # Count the number of MedAllergy objects before the POST
        medallergy_count = MedAllergy.objects.count()

        # Create some fake post() data with medallergys and POST it
        self.ppxaid_data.update(
            {
                f"medallergy_{Treatments.COLCHICINE}": True,
                f"medallergy_{Treatments.PREDNISONE}": True,
                f"medallergy_{Treatments.NAPROXEN}": True,
            }
        )
        response = self.client.post(reverse("ppxaids:create"), self.ppxaid_data)
        self.assertEqual(response.status_code, 302)

        # Test that the MedAllergy objects have been created
        self.assertTrue(MedAllergy.objects.filter(treatment=Treatments.COLCHICINE).exists())
        self.assertTrue(MedAllergy.objects.filter(treatment=Treatments.PREDNISONE).exists())
        self.assertTrue(MedAllergy.objects.filter(treatment=Treatments.NAPROXEN).exists())
        self.assertEqual(MedAllergy.objects.count(), medallergy_count + 3)


class TestPpxAidDetail(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: PpxAidDetail = PpxAidDetail
        self.content_qs = Content.objects.filter(
            Q(tag=Tags.EXPLANATION) | Q(tag=Tags.WARNING), context=Content.Contexts.PPXAID, slug__isnull=False
        ).all()
        self.ppxaid = PpxAid.objects.filter(user__isnull=True).first()

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
        """Test that calling the view without the updated=True query param updates the ppxaid."""
        # Create a blank PpxAid and assert that it has vanilla recommendations
        ppxaid = create_ppxaid(medhistorys=[], medallergys=[])
        self.assertTrue(ppxaid.recommendation[0] == Treatments.NAPROXEN)

        # Add some contraindications that will be updated for
        medallergy = MedAllergyFactory(treatment=Treatments.NAPROXEN)
        ppxaid.medallergy_set.add(medallergy)

        # Re-POST the view and check to see if if the recommendation has been updated
        request = self.factory.get(reverse("ppxaids:detail", kwargs={"pk": ppxaid.pk}))
        self.view.as_view()(request, pk=ppxaid.pk)

        # Refresh the ppxaid from the db
        ppxaid.refresh_from_db()
        # Delete the cached_propertys so that the recommendation is recalculated
        del ppxaid.aid_dict
        del ppxaid.recommendation
        self.assertFalse(ppxaid.recommendation[0] == Treatments.NAPROXEN)

    def test__get_object_does_not_update(self):
        # Create an empty PpxAid
        ppxaid: PpxAid = create_ppxaid(medhistorys=[], medallergys=[])

        # Assert that it's recommendations are vanilla
        self.assertTrue(ppxaid.recommendation[0] == Treatments.NAPROXEN)

        # Create some contraindications that will not be updated for
        medallergy = MedAllergyFactory(treatment=Treatments.NAPROXEN)
        ppxaid.medallergy_set.add(medallergy)

        request = self.factory.get(reverse("ppxaids:detail", kwargs={"pk": self.ppxaid.pk}) + "?updated=True")
        self.view.as_view()(request, pk=self.ppxaid.pk)
        # This needs to be manually refetched from the db
        self.assertTrue(PpxAid.objects.order_by("created").last().recommendation[0] == Treatments.NAPROXEN)

        # Call without the updated=True query param and assert that the recommendation has been updated
        request = self.factory.get(reverse("ppxaids:detail", kwargs={"pk": ppxaid.pk}))
        self.view.as_view()(request, pk=ppxaid.pk)
        # Refresh the ppxaid from the db
        ppxaid.refresh_from_db()
        # Delete the cached_propertys so that the recommendation is recalculated
        del ppxaid.aid_dict
        del ppxaid.recommendation
        self.assertFalse(ppxaid.recommendation[0] == Treatments.NAPROXEN)


class TestPpxAidUpdate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: PpxAidUpdate = PpxAidUpdate

    def test__dispatch_returns_HttpResponse(self):
        """Test that the overwritten dispatch() method returns an HttpResponse."""
        ppxaid = create_ppxaid()
        request = self.factory.get("/fake-url/")
        request.user = AnonymousUser()
        view = self.view()
        kwargs = {"pk": ppxaid.pk}
        view.setup(request, **kwargs)
        response = view.dispatch(request, **kwargs)
        assert response.status_code == 200
        assert isinstance(response, HttpResponse)

    def test__post_updates_medallergys(self):
        for ppxaid in PpxAid.objects.filter(user__isnull=True).all()[:10]:
            data = ppxaid_data_factory()

            response = self.client.post(reverse("ppxaids:update", kwargs={"pk": ppxaid.pk}), data)

            tests_print_response_form_errors(response)
            self.assertEqual(response.status_code, 302)

            # Iterate over the data and check the medallergy values are reflected in the updated ppxaid
            for key, val in data.items():
                split_key = key.split("_")
                try:
                    trt = split_key[1]
                except IndexError:
                    continue
                if trt in Treatments.values:
                    if val:
                        self.assertTrue(ppxaid.medallergy_set.filter(treatment=trt).exists())
                    else:
                        self.assertFalse(ppxaid.medallergy_set.filter(treatment=trt).exists())

    def test__post_updates_medhistorys(self):
        for ppxaid in PpxAid.objects.filter(user__isnull=True).all()[:10]:
            data = ppxaid_data_factory()

            response = self.client.post(reverse("ppxaids:update", kwargs={"pk": ppxaid.pk}), data)

            tests_print_response_form_errors(response)
            self.assertEqual(response.status_code, 302)

            # Iterate over data and check medhistory values are reflected in the updated ppxaid
            for key, val in data.items():
                mh = key.split("-")[0]
                if mh in MedHistoryTypes.values:
                    if val:
                        self.assertTrue(ppxaid.medhistory_set.filter(medhistorytype=mh).exists())
                    else:
                        self.assertFalse(ppxaid.medhistory_set.filter(medhistorytype=mh).exists())
