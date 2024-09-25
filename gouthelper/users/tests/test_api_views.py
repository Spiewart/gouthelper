import random
from datetime import date

import pytest
from django.db.models import Q
from rest_framework.test import APIClient, APIRequestFactory, APITestCase

from ...ethnicitys.choices import Ethnicitys
from ...genders.choices import Genders
from ..api.views import PseudopatientViewSet
from ..models import Pseudopatient
from ..tests.factories import UserFactory, create_psp

pytestmark = pytest.mark.django_db

client = APIClient()


def filter_pseudopatients_by_provider(user):
    return Pseudopatient.profile_objects.filter(
        Q(pseudopatientprofile__provider=user) | Q(pseudopatientprofile__provider=None)
    )


class TestPseudopatientViewSet(APITestCase):
    def setUp(self):
        self.provider = UserFactory()
        self.url = "/api/pseudopatients/"
        self.provider_url = "/api/pseudopatients/provider_create/"
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
        self.pseudopatient = create_psp(provider=self.provider)
        self.pseudopatient_url = f"{self.url}{self.pseudopatient.pk}/"
        self.anon_pseudopatient = create_psp()
        self.nefarious_provider = UserFactory()
        self.nefarious_provider_pseudopatient = create_psp(provider=self.nefarious_provider)

    def test__get_queryset(self):
        view = PseudopatientViewSet()
        request = APIRequestFactory().get(self.url)
        request.user = self.provider
        view.request = request
        self.assertEqual(
            list(view.get_queryset()),
            list(filter_pseudopatients_by_provider(self.provider)),
        )

    def test__create(self):
        current_pseudopatient_count = Pseudopatient.objects.count()
        self.client.force_authenticate(user=self.provider)
        response = self.client.post(self.url, data=self.data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Pseudopatient.objects.count(), current_pseudopatient_count + 1)

    def test__create_without_goutdetail_field_raises_400(self):
        self.client.force_authenticate(user=self.provider)
        self.data["goutdetail"].pop("at_goal_long_term")
        response = self.client.post(self.url, data=self.data, format="json")
        self.assertEqual(response.status_code, 400)

    def test__create_without_dateofbirth_raises_400(self):
        self.client.force_authenticate(user=self.provider)
        self.data.pop("dateofbirth")
        response = self.client.post(self.url, data=self.data, format="json")
        self.assertEqual(response.status_code, 400)

    def test__create_without_ethnicity_raises_400(self):
        self.client.force_authenticate(user=self.provider)
        self.data.pop("ethnicity")
        response = self.client.post(self.url, data=self.data, format="json")
        self.assertEqual(response.status_code, 400)

    def test__create_without_gender_raises_400(self):
        self.client.force_authenticate(user=self.provider)
        self.data.pop("gender")
        response = self.client.post(self.url, data=self.data, format="json")
        self.assertEqual(response.status_code, 400)

    def test__provider_create(self):
        # Only accepts POST requests
        self.client.force_authenticate(user=self.provider)
        self.data["provider_username"] = self.provider.username
        response = self.client.post(self.provider_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 201)
        test_qs = Pseudopatient.objects.select_related("pseudopatientprofile__provider").filter(
            pseudopatientprofile__provider=self.provider
        )
        self.assertTrue(test_qs.exists())
        new_pseudopatient = test_qs.first()
        self.assertEqual(new_pseudopatient.provider, self.provider)
        self.assertTrue(new_pseudopatient.pseudopatientprofile.provider_alias)

    def test__provider_create_without_provider_username_raises_400(self):
        # Only accepts POST requests
        self.client.force_authenticate(user=self.provider)
        response = self.client.post(self.provider_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 400)

    def test__update(self):
        self.client.force_authenticate(user=self.provider)
        response = self.client.put(self.pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 200)

    def test__update_dateofbirth(self):
        initial_dateofbirth = self.pseudopatient.dateofbirth.value
        self.client.force_authenticate(user=self.provider)
        self.data["dateofbirth"]["value"] = date(1981, 1, 1)
        response = self.client.put(self.pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 200)
        new_dateofbirth = Pseudopatient.objects.get(pk=self.pseudopatient.pk).dateofbirth.value
        self.assertNotEqual(new_dateofbirth, initial_dateofbirth)
        self.assertEqual(new_dateofbirth, date(1981, 1, 1))

    def test__update_gender(self):
        initial_gender = self.pseudopatient.gender.value
        self.client.force_authenticate(user=self.provider)
        self.data["gender"]["value"] = Genders.FEMALE if initial_gender == Genders.MALE else Genders.MALE
        response = self.client.put(self.pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 200)
        new_gender = Pseudopatient.objects.get(pk=self.pseudopatient.pk).gender.value
        self.assertNotEqual(initial_gender, new_gender)
        self.assertEqual(new_gender, self.data["gender"]["value"])

    def test__update_ethnicity(self):
        initial_ethnicity = self.pseudopatient.ethnicity.value
        self.client.force_authenticate(user=self.provider)
        self.data["ethnicity"]["value"] = random.choice([e for e in Ethnicitys if e != initial_ethnicity])
        response = self.client.put(self.pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 200)
        new_ethnicity = Pseudopatient.objects.get(pk=self.pseudopatient.pk).ethnicity.value
        self.assertNotEqual(initial_ethnicity, new_ethnicity)
        self.assertEqual(new_ethnicity, self.data["ethnicity"]["value"])

    def test__update_goutdetail_at_goal(self):
        initial_at_goal = self.pseudopatient.goutdetail.at_goal
        self.client.force_authenticate(user=self.provider)
        self.data["goutdetail"]["at_goal"] = not initial_at_goal
        response = self.client.put(self.pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 200)
        new_at_goal = Pseudopatient.objects.get(pk=self.pseudopatient.pk).goutdetail.at_goal
        self.assertNotEqual(initial_at_goal, new_at_goal)
        self.assertEqual(new_at_goal, self.data["goutdetail"]["at_goal"])

    def test__update_goutdetail_at_goal_long_term(self):
        initial_at_goal_long_term = self.pseudopatient.goutdetail.at_goal_long_term
        self.client.force_authenticate(user=self.provider)
        self.data["goutdetail"]["at_goal_long_term"] = not initial_at_goal_long_term
        response = self.client.put(self.pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 200)
        new_at_goal_long_term = Pseudopatient.objects.get(pk=self.pseudopatient.pk).goutdetail.at_goal_long_term
        self.assertNotEqual(initial_at_goal_long_term, new_at_goal_long_term)
        self.assertEqual(new_at_goal_long_term, self.data["goutdetail"]["at_goal_long_term"])

    def test__update_goutdetail_flaring(self):
        initial_flaring = self.pseudopatient.goutdetail.flaring
        self.client.force_authenticate(user=self.provider)
        self.data["goutdetail"]["flaring"] = not initial_flaring
        response = self.client.put(self.pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 200)
        new_flaring = Pseudopatient.objects.get(pk=self.pseudopatient.pk).goutdetail.flaring
        self.assertNotEqual(initial_flaring, new_flaring)
        self.assertEqual(new_flaring, self.data["goutdetail"]["flaring"])

    def test__update_goutdetail_on_ppx(self):
        initial_on_ppx = self.pseudopatient.goutdetail.on_ppx
        self.client.force_authenticate(user=self.provider)
        self.data["goutdetail"]["on_ppx"] = not initial_on_ppx
        response = self.client.put(self.pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 200)
        new_on_ppx = Pseudopatient.objects.get(pk=self.pseudopatient.pk).goutdetail.on_ppx
        self.assertNotEqual(initial_on_ppx, new_on_ppx)
        self.assertEqual(new_on_ppx, self.data["goutdetail"]["on_ppx"])

    def test__update_goutdetail_on_ult(self):
        initial_on_ult = self.pseudopatient.goutdetail.on_ult
        self.client.force_authenticate(user=self.provider)
        self.data["goutdetail"]["on_ult"] = not initial_on_ult
        response = self.client.put(self.pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 200)
        new_on_ult = Pseudopatient.objects.get(pk=self.pseudopatient.pk).goutdetail.on_ult
        self.assertNotEqual(initial_on_ult, new_on_ult)
        self.assertEqual(new_on_ult, self.data["goutdetail"]["on_ult"])

    def test__update_goutdetail_starting_ult(self):
        initial_starting_ult = self.pseudopatient.goutdetail.starting_ult
        self.client.force_authenticate(user=self.provider)
        self.data["goutdetail"]["starting_ult"] = not initial_starting_ult
        response = self.client.put(self.pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 200)
        new_starting_ult = Pseudopatient.objects.get(pk=self.pseudopatient.pk).goutdetail.starting_ult
        self.assertNotEqual(initial_starting_ult, new_starting_ult)
        self.assertEqual(new_starting_ult, self.data["goutdetail"]["starting_ult"])

    def test__update_without_goutdetail_field_raises_400(self):
        self.client.force_authenticate(user=self.provider)
        self.data["goutdetail"].pop("starting_ult")
        response = self.client.put(self.pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 400)

    def test__update_without_dateofbirth_raises_400(self):
        self.client.force_authenticate(user=self.provider)
        self.data.pop("dateofbirth")
        response = self.client.put(self.pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 400)

    def test__update_without_ethnicity_raises_400(self):
        self.client.force_authenticate(user=self.provider)
        self.data.pop("ethnicity")
        response = self.client.put(self.pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 400)

    def test__update_without_gender_raises_400(self):
        self.client.force_authenticate(user=self.provider)
        self.data.pop("gender")
        response = self.client.put(self.pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 400)

    def test__update_with_different_provider_raises_404(self):
        self.client.force_authenticate(user=self.nefarious_provider)
        response = self.client.put(self.pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 404)

    def test__get(self):
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(self.pseudopatient_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(self.pseudopatient.pk))

    def test__get_dateofbirth(self):
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(self.pseudopatient_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["dateofbirth"]["value"], str(self.pseudopatient.dateofbirth.value))

    def test__get_ethnicity(self):
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(self.pseudopatient_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["ethnicity"]["value"], self.pseudopatient.ethnicity.value)

    def test__get_gender(self):
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(self.pseudopatient_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["gender"]["value"], self.pseudopatient.gender.value)

    def test__get_provider(self):
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(self.pseudopatient_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["provider"]["username"], self.pseudopatient.provider.username)

    def test__get_goutdetail_at_goal(self):
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(self.pseudopatient_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["goutdetail"]["at_goal"], self.pseudopatient.goutdetail.at_goal)

    def test__get_goutdetail_at_goal_long_term(self):
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(self.pseudopatient_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["goutdetail"]["at_goal_long_term"], self.pseudopatient.goutdetail.at_goal_long_term
        )

    def test__get_goutdetail_flaring(self):
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(self.pseudopatient_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["goutdetail"]["flaring"], self.pseudopatient.goutdetail.flaring)

    def test__get_goutdetail_on_ppx(self):
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(self.pseudopatient_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["goutdetail"]["on_ppx"], self.pseudopatient.goutdetail.on_ppx)

    def test__get_goutdetail_on_ult(self):
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(self.pseudopatient_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["goutdetail"]["on_ult"], self.pseudopatient.goutdetail.on_ult)

    def test__get_goutdetail_starting_ult(self):
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(self.pseudopatient_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["goutdetail"]["starting_ult"], self.pseudopatient.goutdetail.starting_ult)

    def test__get_with_different_provider_raises_404(self):
        self.client.force_authenticate(user=self.nefarious_provider)
        response = self.client.put(self.pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 404)

    def test__list(self):
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), filter_pseudopatients_by_provider(self.provider).count())
        self.assertIn(str(self.pseudopatient.pk), [p["id"] for p in response.data])

    def test__list_includes_providers_and_providerless_pseudopatients(self):
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), filter_pseudopatients_by_provider(self.provider).count())
        self.assertIn(str(self.pseudopatient.pk), [p["id"] for p in response.data])
        self.assertIn(str(self.anon_pseudopatient.pk), [p["id"] for p in response.data])
        self.assertNotIn(str(self.nefarious_provider_pseudopatient.pk), [p["id"] for p in response.data])

    def test__delete(self):
        current_pseudopatient_count = Pseudopatient.objects.count()
        self.client.force_authenticate(user=self.provider)
        response = self.client.delete(self.pseudopatient_url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Pseudopatient.objects.count(), current_pseudopatient_count - 1)

    def test__delete_with_different_provider_raises_404(self):
        self.client.force_authenticate(user=self.nefarious_provider)
        response = self.client.delete(self.pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 404)


class TestPseudopatientViewSetRules(APITestCase):
    def setUp(self):
        self.provider = UserFactory()
        self.provider_url = "/api/pseudopatients/provider_create/"
        self.nefarious_provider = UserFactory()
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
        self.provider_pseudopatient = create_psp(provider=self.provider)
        self.provider_pseudopatient_url = f"/api/pseudopatients/{self.provider_pseudopatient.pk}/"
        self.anon_pseudopatient = create_psp()
        self.anon_pseudopatient_url = f"/api/pseudopatients/{self.anon_pseudopatient.pk}/"

    def test__create_without_provider_returns_201(self):
        self.client.force_authenticate(user=self.provider)
        response = self.client.post("/api/pseudopatients/", data=self.data, format="json")
        self.assertEqual(response.status_code, 201)

    def test__provider_create_with_different_provider_raises_403(self):
        self.client.force_authenticate(user=self.nefarious_provider)
        self.data["provider_username"] = self.provider.username
        response = self.client.post(self.provider_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 403)

    def test__provider_create_with_provider_returns_201(self):
        self.client.force_authenticate(user=self.provider)
        self.data["provider_username"] = self.provider.username
        response = self.client.post(self.provider_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 201)

    def test__update_without_provider_returns_200(self):
        self.client.force_authenticate(user=self.nefarious_provider)
        response = self.client.put(self.anon_pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 200)

    def test__update_with_provider_returns_200(self):
        self.client.force_authenticate(user=self.provider)
        response = self.client.put(self.provider_pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 200)

    def test__delete_with_provider_returns_204(self):
        self.client.force_authenticate(user=self.provider)
        response = self.client.delete(self.provider_pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 204)

    def test__delete_without_provider_returns_403(self):
        self.client.force_authenticate(user=self.nefarious_provider)
        response = self.client.delete(self.anon_pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 403)

    def test__get_with_provider_returns_200(self):
        self.client.force_authenticate(user=self.provider)
        response = self.client.put(self.provider_pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 200)

    def test__get_without_provider_returns_200(self):
        self.client.force_authenticate(user=self.nefarious_provider)
        response = self.client.put(self.anon_pseudopatient_url, data=self.data, format="json")
        self.assertEqual(response.status_code, 200)
