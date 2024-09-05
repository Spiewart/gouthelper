from datetime import date

import pytest
from rest_framework.test import APIClient, APITestCase

from ...ethnicitys.choices import Ethnicitys
from ...genders.choices import Genders
from ..models import Pseudopatient
from ..tests.factories import UserFactory

pytestmark = pytest.mark.django_db

client = APIClient()


class TestPseudopatientViewSet(APITestCase):
    def setUp(self):
        self.provider = UserFactory()
        self.url = "/api/pseudopatients/"
        self.data = {
            "dateofbirth": {"value": date(1980, 1, 1)},
            "ethnicity": {"value": Ethnicitys.CAUCASIANAMERICAN},
            "gender": {"value": Genders.MALE},
            "goutdetail": {
                "at_goal": None,
                "at_goal_long_term": False,
                "flaring": True,
                "on_ppx": False,
                "on_ult": False,
                "starting_ult": False,
            },
        }
        self.nefarious_provider = UserFactory()

    def test__POST_and_create(self):
        self.assertFalse(Pseudopatient.objects.exists())
        self.client.force_authenticate(user=self.provider)
        response = self.client.post(self.url, data=self.data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Pseudopatient.objects.count(), 1)

    def test__post_and_create_with_provider(self):
        self.assertFalse(Pseudopatient.objects.exists())
        self.client.force_authenticate(user=self.provider)
        self.data["provider_id"] = self.provider.id
        response = self.client.post(self.url, data=self.data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Pseudopatient.objects.filter(pseudopatientprofile__provider=self.provider).exists())

    def test__POST_without_goutdetail_field_raises_400(self):
        self.client.force_authenticate(user=self.provider)
        self.data["goutdetail"].pop("at_goal_long_term")
        response = self.client.post(self.url, data=self.data, format="json")
        self.assertEqual(response.status_code, 400)

    def test__post_without_dateofbirth_raises_400(self):
        self.client.force_authenticate(user=self.provider)
        self.data.pop("dateofbirth")
        response = self.client.post(self.url, data=self.data, format="json")
        self.assertEqual(response.status_code, 400)

    def test__post_without_ethnicity_raises_500(self):
        self.client.force_authenticate(user=self.provider)
        self.data.pop("ethnicity")
        response = self.client.post(self.url, data=self.data, format="json")
        self.assertEqual(response.status_code, 400)

    def test__post_without_gender_raises_500(self):
        self.client.force_authenticate(user=self.provider)
        self.data.pop("gender")
        response = self.client.post(self.url, data=self.data, format="json")
        self.assertEqual(response.status_code, 400)


class TestPseudopatientViewSetRules(APITestCase):
    def setUp(self):
        self.provider = UserFactory()
        self.url = "/api/pseudopatients/"
        self.nefarious_provider = UserFactory()
