import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...akis.choices import Statuses
from ...flares.tests.factories import CustomFlareFactory
from ...genders.choices import Genders
from ...users.tests.factories import create_psp
from ...utils.test_helpers import date_years_ago
from ..selectors import akis_related_objects_qs, akis_related_objects_user_qs

pytestmark = pytest.mark.django_db


class TestAkiRelatedObjectsQS(TestCase):
    def setUp(self):
        self.flare = CustomFlareFactory(
            aki=Statuses.ONGOING,
            dateofbirth=date_years_ago(50),
            gender=Genders.MALE,
        ).create_object()
        self.aki = self.flare.aki
        self.patient = create_psp()
        self.patient_flare = CustomFlareFactory(aki=Statuses.ONGOING, user=self.patient).create_object()
        self.patient_aki = self.patient_flare.aki

    def test__queryset(self):
        qs = akis_related_objects_qs(self.aki.__class__.objects.all())
        self.assertEqual(qs.count(), 2)
        with self.assertNumQueries(3):
            self.assertEqual(qs.filter(id=self.aki.pk).get(), self.aki)
            self.assertTrue(hasattr(self.aki.flare, "medhistorys_qs"))
            self.assertTrue(self.aki.flare.dateofbirth)
            self.assertTrue(self.aki.flare.gender)
            self.assertEqual(self.aki.flare.gender.value, Genders.MALE)

    def test__queryset_with_user(self):
        qs = akis_related_objects_qs(self.patient_aki.__class__.objects.all())
        self.assertEqual(qs.count(), 2)
        with self.assertNumQueries(4):
            self.assertEqual(qs.filter(id=self.patient_aki.pk).get(), self.patient_aki)
            self.assertFalse(hasattr(self.patient_aki.flare, "medhistorys_qs"))
            self.assertTrue(hasattr(self.patient_aki.user, "medhistorys_qs"))
            self.assertTrue(self.patient_aki.user.dateofbirth)
            self.assertTrue(self.patient_aki.user.gender)


class TestAkiRelatedObjectsUserQS(TestCase):
    def setUp(self):
        self.patient = create_psp()
        self.flare = CustomFlareFactory(aki=Statuses.ONGOING, user=self.patient).create_object()
        self.aki = self.flare.aki

    def test__queryset(self):
        qs = akis_related_objects_user_qs(self.aki.__class__.objects.all())
        self.assertEqual(qs.count(), 1)
        with self.assertNumQueries(3):
            self.assertEqual(qs.first(), self.aki)
            self.assertFalse(hasattr(self.aki.flare, "medhistorys_qs"))
            self.assertTrue(hasattr(self.aki.user, "medhistorys_qs"))
            self.assertTrue(self.aki.user.dateofbirth)
            self.assertTrue(self.aki.user.gender)
