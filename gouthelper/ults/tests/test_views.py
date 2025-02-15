import random  # type: ignore
from decimal import Decimal

import pytest  # type: ignore
from django.contrib.auth.models import AnonymousUser  # type: ignore
from django.contrib.sessions.middleware import SessionMiddleware  # pylint: disable=e0401 # type: ignore
from django.db.models import Q, QuerySet  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore

from ...contents.models import Content
from ...dateofbirths.models import DateOfBirth
from ...genders.choices import Genders
from ...genders.models import Gender
from ...labs.models import BaselineCreatinine
from ...medhistorydetails.choices import Stages
from ...medhistorydetails.models import CkdDetail
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.models import Ckd, Erosions, Hyperuricemia, Tophi, Uratestones
from ...utils.forms import forms_print_response_errors
from ...utils.test_helpers import dummy_get_response
from ..choices import FlareFreqs, FlareNums
from ..models import Ult
from ..views import UltAbout, UltCreate, UltDetail, UltUpdate
from .factories import create_ult, get_freq_flares, ult_data_factory

pytestmark = pytest.mark.django_db


class TestUltAbout(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltAbout = UltAbout()

    def test__get(self):
        response = self.client.get(reverse("ults:about"))
        self.assertEqual(response.status_code, 200)

    def test__get_context_data(self):
        response = self.client.get(reverse("ults:about"))
        self.assertIn("content", response.context_data)

    def test__content(self):
        self.assertEqual(self.view.content, Content.objects.get(context=Content.Contexts.ULT, slug="about", tag=None))


class TestUltCreate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltCreate = UltCreate()

    def test__get_context_data(self):
        request = self.factory.get("ults/create")
        request.user = AnonymousUser()
        SessionMiddleware(dummy_get_response).process_request(request)
        response = UltCreate.as_view()(request)
        self.assertIn("dateofbirth_form", response.context_data)
        self.assertIn("gender_form", response.context_data)
        self.assertIn(f"{MedHistoryTypes.CKD}_form", response.context_data)
        self.assertIn("ckddetail_form", response.context_data)
        self.assertIn("baselinecreatinine_form", response.context_data)
        self.assertIn(f"{MedHistoryTypes.EROSIONS}_form", response.context_data)
        self.assertIn(f"{MedHistoryTypes.HYPERURICEMIA}_form", response.context_data)
        self.assertIn(f"{MedHistoryTypes.TOPHI}_form", response.context_data)
        self.assertIn(f"{MedHistoryTypes.URATESTONES}_form", response.context_data)

    def test__post_creates_ult_and_related_objects(self):
        ult_data = {
            "num_flares": FlareNums.ONE,
            "dateofbirth-value": 50,
            "gender-value": Genders.FEMALE,
            f"{MedHistoryTypes.CKD}-value": True,
            "baselinecreatinine-value": Decimal("2.0"),
            "dialysis": False,
            "stage": Stages.THREE,
            f"{MedHistoryTypes.EROSIONS}-value": True,
            f"{MedHistoryTypes.HYPERURICEMIA}-value": True,
            f"{MedHistoryTypes.TOPHI}-value": True,
            f"{MedHistoryTypes.URATESTONES}-value": True,
        }
        response = self.client.post(reverse("ults:create"), ult_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Ult.objects.all().exists())
        ult = Ult.related_objects.order_by("created").last()
        self.assertEqual(ult.num_flares, FlareNums.ONE)
        self.assertTrue(hasattr(ult, "dateofbirth"))
        self.assertEqual(ult.dateofbirth, DateOfBirth.objects.order_by("created").last())
        self.assertTrue(hasattr(ult, "gender"))
        self.assertEqual(ult.gender, Gender.objects.order_by("created").last())
        ckd = Ckd.objects.order_by("created").last()
        self.assertIn(ckd, ult.medhistorys_qs)
        baselinecreatinine = BaselineCreatinine.objects.order_by("created").last()
        ckddetail = CkdDetail.objects.order_by("created").last()
        self.assertEqual(ckddetail.medhistory, ckd)
        self.assertEqual(ckddetail.stage, Stages.THREE)
        self.assertEqual(baselinecreatinine.value, Decimal("2.0"))
        self.assertEqual(baselinecreatinine.medhistory, ckd)
        self.assertIn(Erosions.objects.order_by("created").last(), ult.medhistorys_qs)
        self.assertIn(Hyperuricemia.objects.order_by("created").last(), ult.medhistorys_qs)
        self.assertIn(Tophi.objects.order_by("created").last(), ult.medhistorys_qs)
        self.assertIn(Uratestones.objects.order_by("created").last(), ult.medhistorys_qs)

    def test__post_returns_errors(self):
        """Test that the post() method returns a 200 response with errors
        attached to the forms when they are present."""
        ult_data = ult_data_factory()
        ult_data["num_flares"] = FlareNums.ONE
        ult_data["freq_flares"] = FlareFreqs.TWOORMORE
        response = self.client.post(reverse("ults:create"), ult_data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data["form"].errors)
        self.assertIn("freq_flares", response.context_data["form"].errors)


class TestUltDetail(TestCase):
    def setUp(self):
        self.ult = create_ult(num_flares=FlareNums.TWOPLUS, freq_flares=FlareFreqs.TWOORMORE)
        self.factory = RequestFactory()
        self.view: UltDetail = UltDetail
        self.content_qs = Content.objects.filter(
            Q(tag=Content.Tags.EXPLANATION) | Q(tag=Content.Tags.WARNING),
            context=Content.Contexts.ULT,
            slug__isnull=False,
        ).all()
        self.anon_user = AnonymousUser()

    def test__dispatch_redirects_ult_with_user(self):
        ult = create_ult(user=True)
        request = self.factory.get(reverse("ults:detail", kwargs={"pk": ult.pk}))
        request.user = ult.user
        response = self.view.as_view()(request, pk=ult.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("ults:pseudopatient-detail", kwargs={"pseudopatient": ult.user.pk}))

    def test__get_queryset(self):
        qs = self.view(kwargs={"pk": self.ult.pk}).get_queryset()
        self.assertTrue(isinstance(qs, QuerySet))
        ult = qs.get()
        self.assertEqual(ult, self.ult)
        self.assertTrue(hasattr(ult, "medhistorys_qs"))
        self.assertTrue(hasattr(ult, "ckddetail"))
        self.assertTrue(hasattr(ult, "baselinecreatinine"))
        self.assertTrue(hasattr(ult, "dateofbirth"))
        self.assertTrue(hasattr(ult, "gender"))

    def test__get_object_updates(self):
        self.assertEqual(self.ult.indication, self.ult.Indications.NOTINDICATED)
        request = self.factory.get(reverse("ults:detail", kwargs={"pk": self.ult.pk}))
        request.user = self.anon_user
        self.view.as_view()(request, pk=self.ult.pk)
        # This needs to be manually refetched from the db
        self.assertIsNotNone(
            Ult.objects.get().indication,
            Ult.Indications.INDICATED,
        )

    def test__get_object_does_not_update(self):
        self.assertEqual(self.ult.indication, self.ult.Indications.NOTINDICATED)
        request = self.factory.get(reverse("ults:detail", kwargs={"pk": self.ult.pk}) + "?updated=True")
        request.user = self.anon_user
        self.view.as_view()(request, pk=self.ult.pk)
        # This needs to be manually refetched from the db
        self.assertEqual(Ult.objects.get().indication, self.ult.Indications.NOTINDICATED)


class TestUltUpdate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltUpdate = UltUpdate()
        self.ult = create_ult(mhs=[])

    def test__post_changes_ult_fields(self):
        """Test that post modifies the num_flares and freq_flares Ult fields."""
        init_num_flares = FlareNums(self.ult.num_flares)
        ult_data = ult_data_factory(ult=self.ult)
        ult_data.update(
            {
                "num_flares": random.choice([num for num in FlareNums.values if num != init_num_flares]),
            }
        )
        new_freq_flares = get_freq_flares(ult_data["num_flares"])
        ult_data.update({"freq_flares": new_freq_flares if new_freq_flares is not None else ""})
        response = self.client.post(reverse("ults:update", kwargs={"pk": self.ult.pk}), ult_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.ult.refresh_from_db()
        self.assertNotEqual(self.ult.num_flares, init_num_flares)
        self.assertEqual(self.ult.num_flares, ult_data["num_flares"])
        self.assertEqual(self.ult.freq_flares, ult_data["freq_flares"] if ult_data["freq_flares"] != "" else None)

    def test__post_with_ckd_ckddetail(self):
        """Test that a POST request creates a Ckd and associated CkdDetail."""
        self.assertFalse(self.ult.ckd)
        self.assertFalse(self.ult.ckddetail)
        ult_data = ult_data_factory(ult=self.ult, mhs=[MedHistoryTypes.CKD])
        response = self.client.post(reverse("ults:update", kwargs={"pk": self.ult.pk}), ult_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.ult.refresh_from_db()
        delattr(self.ult, "medhistorys_qs")
        delattr(self.ult, "ckd")
        delattr(self.ult, "ckddetail")
        self.assertTrue(self.ult.ckd)
        self.assertTrue(self.ult.ckddetail)

    def test__post_creates_baselinecreatinine(self):
        """Test that a POST request creates a BaselineCreatinine."""
        self.assertFalse(self.ult.baselinecreatinine)
        ult_data = ult_data_factory(
            ult=self.ult,
            mhs=[MedHistoryTypes.CKD],
            mh_dets={MedHistoryTypes.CKD: {"baselinecreatinine": Decimal("2.0")}},
        )

        self.assertIn("baselinecreatinine-value", ult_data)
        response = self.client.post(reverse("ults:update", kwargs={"pk": self.ult.pk}), ult_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.ult.refresh_from_db()
        delattr(self.ult, "medhistorys_qs")
        delattr(self.ult, "ckd")
        delattr(self.ult, "baselinecreatinine")
        self.assertTrue(BaselineCreatinine.objects.filter(medhistory=self.ult.ckd).exists())
        self.assertTrue(self.ult.baselinecreatinine)

    def test__post_returns_errors(self):
        """Test that the post() method returns a 200 response with errors
        attached to the forms when they are present."""
        ult_data = ult_data_factory(ult=self.ult)
        ult_data["num_flares"] = FlareNums.ONE
        ult_data["freq_flares"] = FlareFreqs.TWOORMORE
        response = self.client.post(reverse("ults:update", kwargs={"pk": self.ult.pk}), ult_data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data["form"].errors)
        self.assertIn("freq_flares", response.context_data["form"].errors)

        ult_data.update(
            {
                "freq_flares": "",
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": "",
                "stage": Stages.THREE,
            }
        )
        response = self.client.post(reverse("ults:update", kwargs={"pk": self.ult.pk}), ult_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data["ckddetail_form"].errors)
        self.assertIn("dialysis", response.context_data["ckddetail_form"].errors)
