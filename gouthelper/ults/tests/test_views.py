from decimal import Decimal

import pytest  # type: ignore
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
from ..choices import FlareFreqs, FlareNums
from ..models import Ult
from ..views import UltAbout, UltCreate, UltDetail, UltUpdate
from .factories import UltFactory

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
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Ult.objects.all().exists())
        ult = Ult.objects.last()
        self.assertEqual(ult.num_flares, FlareNums.ONE)
        self.assertTrue(hasattr(ult, "dateofbirth"))
        self.assertEqual(ult.dateofbirth, DateOfBirth.objects.order_by("created").last())
        self.assertTrue(hasattr(ult, "gender"))
        self.assertEqual(ult.gender, Gender.objects.order_by("created").last())
        ckd = Ckd.objects.order_by("created").last()
        self.assertIn(ckd, ult.medhistorys.all())
        baselinecreatinine = BaselineCreatinine.objects.order_by("created").last()
        ckddetail = CkdDetail.objects.order_by("created").last()
        self.assertEqual(ckddetail.medhistory, ckd)
        self.assertEqual(ckddetail.stage, Stages.THREE)
        self.assertEqual(baselinecreatinine.value, Decimal("2.0"))
        self.assertEqual(baselinecreatinine.medhistory, ckd)
        self.assertIn(Erosions.objects.order_by("created").last(), ult.medhistorys.all())
        self.assertIn(Hyperuricemia.objects.order_by("created").last(), ult.medhistorys.all())
        self.assertIn(Tophi.objects.order_by("created").last(), ult.medhistorys.all())
        self.assertIn(Uratestones.objects.order_by("created").last(), ult.medhistorys.all())

    def test__post_uses_assigned_queryset(self):
        # This was a bad test (just tested # of queries, not the actual queries)
        pass


class TestUltDetail(TestCase):
    def setUp(self):
        self.ult = UltFactory(num_flares=FlareNums.TWOPLUS, freq_flares=FlareFreqs.TWOORMORE)
        self.factory = RequestFactory()
        self.view: UltDetail = UltDetail
        self.content_qs = Content.objects.filter(
            Q(tag=Content.Tags.EXPLANATION) | Q(tag=Content.Tags.WARNING),
            context=Content.Contexts.ULT,
            slug__isnull=False,
        ).all()

    def test__contents(self):
        self.assertTrue(self.view().contents)
        self.assertTrue(isinstance(self.view().contents, QuerySet))
        for content in self.view().contents:
            self.assertIn(content, self.content_qs)
        for content in self.content_qs:
            self.assertIn(content, self.view().contents)

    def test__get_context_data(self):
        response = self.client.get(reverse("ults:detail", kwargs={"pk": self.ult.pk}))
        context = response.context_data
        for content in self.content_qs:
            self.assertIn(content.slug, context)
            self.assertEqual(context[content.slug], {content.tag: content})

    def test__get_queryset(self):
        qs = self.view(kwargs={"pk": self.ult.pk}).get_queryset()
        self.assertTrue(isinstance(qs, QuerySet))
        self.assertEqual(qs.first(), self.ult)
        self.assertTrue(hasattr(qs.first(), "medhistorys_qs"))
        self.assertTrue(hasattr(qs.first(), "ckddetail"))
        self.assertTrue(hasattr(qs.first(), "baselinecreatinine"))
        self.assertTrue(hasattr(qs.first(), "dateofbirth"))
        self.assertTrue(hasattr(qs.first(), "gender"))

    def test__get_object_updates(self):
        self.assertEqual(self.ult.indication, self.ult.Indications.NOTINDICATED)
        request = self.factory.get(reverse("ults:detail", kwargs={"pk": self.ult.pk}))
        self.view.as_view()(request, pk=self.ult.pk)
        # This needs to be manually refetched from the db
        self.assertIsNotNone(
            Ult.objects.get().indication,
            Ult.Indications.INDICATED,
        )

    def test__get_object_does_not_update(self):
        self.assertEqual(self.ult.indication, self.ult.Indications.NOTINDICATED)
        request = self.factory.get(reverse("ults:detail", kwargs={"pk": self.ult.pk}) + "?updated=True")
        self.view.as_view()(request, pk=self.ult.pk)
        # This needs to be manually refetched from the db
        self.assertEqual(Ult.objects.get().indication, self.ult.Indications.NOTINDICATED)


class TestUltUpdate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltUpdate = UltUpdate()

    def test__post_uses_assigned_queryset(self):
        # This was a bad test (just tested # of queries, not the actual queries)
        pass
