from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
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
from ...labs.tests.factories import BaselineCreatinineFactory
from ...medallergys.models import MedAllergy
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
from ...medhistorydetails.models import CkdDetail
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.choices import Contraindications, MedHistoryTypes
from ...medhistorys.lists import FLAREAID_MEDHISTORYS
from ...medhistorys.models import MedHistory
from ...medhistorys.tests.factories import MedHistoryFactory
from ...treatments.choices import ColchicineDoses, FlarePpxChoices, NsaidChoices, Treatments
from ...users.models import Pseudopatient
from ...users.tests.factories import PseudopatientFactory, PseudopatientPlusFactory
from ...utils.helpers.test_helpers import (
    form_data_colchicine_contra,
    form_data_nsaid_contra,
    tests_print_response_form_errors,
)
from ..models import FlareAid
from ..views import (
    FlareAidAbout,
    FlareAidCreate,
    FlareAidDetail,
    FlareAidPatientCreate,
    FlareAidPatientUpdate,
    FlareAidUpdate,
)
from .factories import FlareAidFactory, FlareAidUserFactory, create_flareaid_data

pytestmark = pytest.mark.django_db


User = get_user_model()


class TestFlareAidAbout(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: FlareAidAbout = FlareAidAbout()

    def test__get(self):
        response = self.client.get(reverse("flareaids:about"))
        self.assertEqual(response.status_code, 200)

    def test__get_context_data(self):
        response = self.client.get(reverse("flareaids:about"))
        self.assertIn("content", response.context_data)

    def test__content(self):
        self.assertEqual(
            self.view.content, Content.objects.get(context=Content.Contexts.FLAREAID, slug="about", tag=None)
        )


class TestFlareAidCreate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: FlareAidCreate = FlareAidCreate()
        self.flareaid_data = {
            "dateofbirth-value": age_calc(timezone.now() - timedelta(days=365 * 50)),
            "gender-value": Genders.FEMALE,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
        }

    def test__successful_post(self):
        response = self.client.post(reverse("flareaids:create"), self.flareaid_data)
        tests_print_response_form_errors(response)
        self.assertTrue(FlareAid.objects.get())
        self.assertEqual(response.status_code, 302)

    def test__post_creates_medhistory(self):
        self.flareaid_data.update({f"{MedHistoryTypes.STROKE}-value": True})
        response = self.client.post(reverse("flareaids:create"), self.flareaid_data)
        tests_print_response_form_errors(response)
        self.assertTrue(FlareAid.objects.get())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.STROKE).exists())
        self.assertEqual(MedHistory.objects.count(), 1)
        self.assertIn(
            MedHistoryTypes.STROKE, FlareAid.objects.get().medhistorys.values_list("medhistorytype", flat=True)
        )

    def test__post_creates_medhistorys(self):
        self.flareaid_data.update({f"{MedHistoryTypes.STROKE}-value": True})
        self.flareaid_data.update({f"{MedHistoryTypes.DIABETES}-value": True})
        response = self.client.post(reverse("flareaids:create"), self.flareaid_data)
        tests_print_response_form_errors(response)
        self.assertTrue(FlareAid.objects.get())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.STROKE).exists())
        self.assertTrue(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.DIABETES).exists())
        self.assertEqual(MedHistory.objects.count(), 2)
        self.assertIn(
            MedHistoryTypes.STROKE, FlareAid.objects.get().medhistorys.values_list("medhistorytype", flat=True)
        )
        self.assertIn(
            MedHistoryTypes.DIABETES, FlareAid.objects.get().medhistorys.values_list("medhistorytype", flat=True)
        )

    def test__post_creates_ckddetail(self):
        self.flareaid_data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": True,
                "dialysis_duration": DialysisDurations.LESSTHANSIX,
                "dialysis_type": DialysisChoices.PERITONEAL,
            }
        )
        response = self.client.post(reverse("flareaids:create"), self.flareaid_data)
        tests_print_response_form_errors(response)
        self.assertTrue(CkdDetail.objects.get())
        self.assertTrue(FlareAid.objects.get().ckddetail)

    def test__post_creates_baselinecreatinine(self):
        self.flareaid_data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": False,
                "baselinecreatinine-value": Decimal("2.2"),
                "dateofbirth-value": age_calc(timezone.now() - timedelta(days=365 * 50)),
                "gender-value": Genders.MALE,
            }
        )
        response = self.client.post(reverse("flareaids:create"), self.flareaid_data)
        tests_print_response_form_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(BaselineCreatinine.objects.get())
        self.assertEqual(FlareAid.objects.get().ckd.baselinecreatinine.value, Decimal("2.2"))
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
        self.flareaid_data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": False,
                "baselinecreatinine-value": Decimal("2.2"),
                "dateofbirth-value": "",
                "gender-value": Genders.MALE,
            }
        )
        response = self.client.post(reverse("flareaids:create"), self.flareaid_data)
        self.assertEqual(response.status_code, 200)
        # Assert that the response context contains a field error for dateofbirth
        self.assertTrue("value" in response.context["dateofbirth_form"].errors)

    def test__post_does_not_raise_error_no_gender(self):
        self.flareaid_data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": False,
                "gender-value": "",
            }
        )
        response = self.client.post(reverse("flareaids:create"), self.flareaid_data)
        self.assertEqual(response.status_code, 302)

    def test__post_raises_ValidationError_baselinecreatinine_no_gender(self):
        self.flareaid_data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": False,
                "baselinecreatinine-value": Decimal("2.2"),
                "gender-value": "",
            }
        )
        response = self.client.post(reverse("flareaids:create"), self.flareaid_data)
        self.assertEqual(response.status_code, 200)
        # Assert that the response context contains a field error for dateofbirth
        self.assertTrue("value" in response.context["gender_form"].errors)
        # Check the error message includes the baseline creatinine
        self.assertIn("baseline creatinine", response.context["gender_form"].errors["value"][0])

    def test__post_adds_medallergys(self):
        self.flareaid_data.update(
            {
                f"medallergy_{Treatments.COLCHICINE}": True,
                f"medallergy_{Treatments.PREDNISONE}": True,
                f"medallergy_{Treatments.NAPROXEN}": True,
            }
        )
        response = self.client.post(reverse("flareaids:create"), self.flareaid_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MedAllergy.objects.filter(treatment=Treatments.COLCHICINE).exists())
        self.assertTrue(MedAllergy.objects.filter(treatment=Treatments.PREDNISONE).exists())
        self.assertTrue(MedAllergy.objects.filter(treatment=Treatments.NAPROXEN).exists())
        self.assertEqual(MedAllergy.objects.count(), 3)


class TestFlareAidPatientCreate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = FlareAidPatientCreate
        self.user = PseudopatientPlusFactory()
        for _ in range(10):
            PseudopatientPlusFactory()
        self.psp = PseudopatientFactory()

    def test__check_user_onetoones(self):
        """Tests that the view checks for the User's related models."""
        empty_user = PseudopatientFactory(dateofbirth=None, gender=None)
        with self.assertRaises(AttributeError) as exc:
            self.view().check_user_onetoones(empty_user)
        self.assertEqual(
            exc.exception.args[0], "Baseline information is needed to use GoutHelper Decision and Treatment Aids."
        )
        assert self.view().check_user_onetoones(self.user) is None

    def test__ckddetail(self):
        """Tests the ckddetail cached_property."""
        self.assertTrue(self.view().ckddetail)

    def test__get_form_kwargs(self):
        # Create a fake request
        request = self.factory.get("/fake-url/")
        view = self.view(request=request)
        form_kwargs = view.get_form_kwargs()
        self.assertIn("medallergys", form_kwargs)

    def test__goutdetail(self):
        """Tests the goutdetail cached_property."""
        self.assertFalse(self.view().goutdetail)

    def test__get(self):
        """Test the get() method for the view. Should redirect to detailview when
        the user already has a FlareAid. Should redirect to Pseudopatient Update
        view when the user doesn't have the required 1to1 related models."""
        request = self.factory.get("/fake-url/")
        kwargs = {"username": self.user.username}
        view = self.view()
        # https://stackoverflow.com/questions/33645780/how-to-unit-test-methods-inside-djangos-class-based-views
        view.setup(request, **kwargs)
        response = view.get(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(hasattr(view, "user"))
        self.assertEqual(view.user, self.user)
        # Create a new FlareAid and test that the view redirects to the detailview
        flareaid = FlareAidUserFactory(user=self.user)
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("flareaids:patient-create", kwargs={"username": self.user.username}), follow=True
        )
        self.assertEqual(view.user, self.user)
        self.assertRedirects(response, flareaid.get_absolute_url())
        # Check that the response message is correct
        message = list(response.context.get("messages"))[0]
        self.assertEqual(message.tags, "error")
        self.assertEqual(message.message, f"FlareAid already exists for {self.user.username}")
        # Create empty user and test that the view redirects to the user update view
        empty_user = PseudopatientFactory(dateofbirth=None)
        self.client.force_login(empty_user)
        response = self.client.get(
            reverse("flareaids:patient-create", kwargs={"username": empty_user.username}), follow=True
        )
        self.assertRedirects(response, reverse("users:pseudopatient-update", kwargs={"username": empty_user.username}))
        message = list(response.context.get("messages"))[0]
        self.assertEqual(message.tags, "error")
        self.assertEqual(
            message.message, "Baseline information is needed to use GoutHelper Decision and Treatment Aids."
        )

    def test__get_user_queryset(self):
        """Test the get_user_queryset() method for the view."""
        request = self.factory.get("/fake-url/")
        kwargs = {"username": self.user.username}
        view = self.view()
        # https://stackoverflow.com/questions/33645780/how-to-unit-test-methods-inside-djangos-class-based-views
        view.setup(request, **kwargs)
        qs = view.get_user_queryset(view.kwargs["username"])
        self.assertTrue(isinstance(qs, QuerySet))
        qs = qs.get()
        self.assertTrue(isinstance(qs, User))
        self.assertTrue(hasattr(qs, "medhistorys_qs"))
        self.assertTrue(hasattr(qs, "medallergys_qs"))
        self.assertTrue(hasattr(qs, "dateofbirth"))
        self.assertTrue(hasattr(qs, "gender"))

    def test__get_context_data_onetoones(self):
        """Test that the context data includes the user's
        related models."""
        for user in Pseudopatient.objects.all():
            request = self.factory.get("/fake-url/")
            kwargs = {"username": user.username}
            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            assert "age" in response.context_data
            assert response.context_data["age"] == age_calc(user.dateofbirth.value)
            assert "gender" in response.context_data
            assert response.context_data["gender"] == user.gender.value

    def test__get_context_data_medhistorys(self):
        """Test that the context data includes the user's
        related models."""
        for user in Pseudopatient.objects.all():
            request = self.factory.get("/fake-url/")
            kwargs = {"username": user.username}
            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            for mh in user.medhistory_set.all():
                if mh.medhistorytype in FLAREAID_MEDHISTORYS:
                    assert f"{mh.medhistorytype}_form" in response.context_data
                    assert response.context_data[f"{mh.medhistorytype}_form"].instance == mh
                    assert response.context_data[f"{mh.medhistorytype}_form"].instance._state.adding is False
                    assert response.context_data[f"{mh.medhistorytype}_form"].initial == {
                        f"{mh.medhistorytype}-value": True
                    }
                else:
                    assert f"{mh.medhistorytype}_form" not in response.context_data
            for mhtype in FLAREAID_MEDHISTORYS:
                assert f"{mhtype}_form" in response.context_data
                if mhtype not in user.medhistory_set.values_list("medhistorytype", flat=True):
                    assert response.context_data[f"{mhtype}_form"].instance._state.adding is True
                    assert response.context_data[f"{mhtype}_form"].initial == {f"{mhtype}-value": None}
            assert "ckddetail_form" in response.context_data
            if user.ckd:
                if getattr(user.ckd, "ckddetail", None):
                    assert response.context_data["ckddetail_form"].instance == user.ckd.ckddetail
                    assert response.context_data["ckddetail_form"].instance._state.adding is False
                else:
                    assert response.context_data["ckddetail_form"].instance._state.adding is True
                if getattr(user.ckd, "baselinecreatinine", None):
                    assert response.context_data["baselinecreatinine_form"].instance == user.ckd.baselinecreatinine
                    assert response.context_data["baselinecreatinine_form"].instance._state.adding is False
                else:
                    assert response.context_data["baselinecreatinine_form"].instance._state.adding is True
            else:
                assert response.context_data["ckddetail_form"].instance._state.adding is True
                assert response.context_data["baselinecreatinine_form"].instance._state.adding is True
            assert "goutdetail_form" not in response.context_data

    def test__get_context_data_medallergys(self):
        """Test that the context data includes the user's
        related models."""
        for user in Pseudopatient.objects.all():
            request = self.factory.get("/fake-url/")
            kwargs = {"username": user.username}
            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            for ma in user.medallergy_set.filter(Q(treatment__in=FlarePpxChoices.values)).all():
                assert f"medallergy_{ma.treatment}_form" in response.context_data
                assert response.context_data[f"medallergy_{ma.treatment}_form"].instance == ma
                assert response.context_data[f"medallergy_{ma.treatment}_form"].instance._state.adding is False
                assert response.context_data[f"medallergy_{ma.treatment}_form"].initial == {
                    f"medallergy_{ma.treatment}": True
                }
            for treatment in FlarePpxChoices.values:
                assert f"medallergy_{treatment}_form" in response.context_data
                if treatment not in user.medallergy_set.values_list("treatment", flat=True):
                    assert response.context_data[f"medallergy_{treatment}_form"].instance._state.adding is True
                    assert response.context_data[f"medallergy_{treatment}_form"].initial == {
                        f"medallergy_{treatment}": None
                    }

    def test__post(self):
        """Test the post() method for the view."""
        request = self.factory.post("/fake-url/")
        kwargs = {"username": self.user.username}
        response = self.view.as_view()(request, **kwargs)
        assert response.status_code == 200

    def test__post_sets_object_user(self):
        """Test that the post() method for the view sets the
        user on the object."""
        # Create some fake data for a User's FlareAid
        data = create_flareaid_data(self.user)
        response = self.client.post(
            reverse("flareaids:patient-create", kwargs={"username": self.user.username}), data=data
        )
        tests_print_response_form_errors(response)
        assert response.status_code == 302
        assert FlareAid.objects.filter(user=self.user).exists()

    def test__post_creates_medhistorys(self):
        self.assertFalse(MedHistory.objects.filter(user=self.psp).exists())
        data = {
            "dateofbirth-value": age_calc(self.psp.dateofbirth.value),
            "gender-value": self.psp.gender.value,
            f"{MedHistoryTypes.CAD}-value": True,
            f"{MedHistoryTypes.CHF}-value": True,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
        }
        response = self.client.post(
            reverse("flareaids:patient-create", kwargs={"username": self.psp.username}), data=data
        )
        assert response.status_code == 302
        self.assertTrue(MedHistory.objects.filter(user=self.psp).exists())
        self.assertTrue(MedHistory.objects.filter(user=self.psp, medhistorytype=MedHistoryTypes.CAD).exists())
        self.assertTrue(MedHistory.objects.filter(user=self.psp, medhistorytype=MedHistoryTypes.CHF).exists())

    def test__post_deletes_medhistorys(self):
        MedHistoryFactory(user=self.psp, medhistorytype=MedHistoryTypes.DIABETES)
        MedHistoryFactory(user=self.psp, medhistorytype=MedHistoryTypes.CKD)
        self.assertTrue(MedHistory.objects.filter(user=self.psp).exists())
        self.assertTrue(MedHistory.objects.filter(user=self.psp, medhistorytype=MedHistoryTypes.DIABETES).exists())
        self.assertTrue(MedHistory.objects.filter(user=self.psp, medhistorytype=MedHistoryTypes.CKD).exists())
        data = {
            "dateofbirth-value": age_calc(self.psp.dateofbirth.value),
            "gender-value": self.psp.gender.value,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
        }
        response = self.client.post(
            reverse("flareaids:patient-create", kwargs={"username": self.psp.username}), data=data
        )
        assert response.status_code == 302
        self.assertFalse(MedHistory.objects.filter(user=self.psp, medhistorytype=MedHistoryTypes.DIABETES).exists())
        self.assertFalse(MedHistory.objects.filter(user=self.psp, medhistorytype=MedHistoryTypes.CKD).exists())

    def test__post_create_medallergys(self):
        """Test that the view creates MedAllergy objects."""
        self.assertFalse(MedAllergy.objects.filter(user=self.psp).exists())
        data = {
            "dateofbirth-value": age_calc(self.psp.dateofbirth.value),
            "gender-value": self.psp.gender.value,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            # Create data for a colchicine allergy
            f"medallergy_{Treatments.COLCHICINE}": True,
        }
        # Call the view with the data
        response = self.client.post(
            reverse("flareaids:patient-create", kwargs={"username": self.psp.username}), data=data
        )
        assert response.status_code == 302
        self.assertTrue(MedAllergy.objects.filter(user=self.psp).exists())
        self.assertTrue(MedAllergy.objects.filter(user=self.psp, treatment=Treatments.COLCHICINE).exists())

    def test__post_delete_medallergys(self):
        """Test that the view deletes MedAllergy objects."""
        MedAllergyFactory(user=self.psp, treatment=Treatments.COLCHICINE)
        MedAllergyFactory(user=self.psp, treatment=Treatments.PREDNISONE)
        self.assertTrue(MedAllergy.objects.filter(user=self.psp).exists())
        self.assertTrue(MedAllergy.objects.filter(user=self.psp, treatment=Treatments.COLCHICINE).exists())
        self.assertTrue(MedAllergy.objects.filter(user=self.psp, treatment=Treatments.PREDNISONE).exists())
        data = {
            "dateofbirth-value": age_calc(self.psp.dateofbirth.value),
            "gender-value": self.psp.gender.value,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            # Create data for a colchicine allergy
            f"medallergy_{Treatments.COLCHICINE}": "",
            f"medallergy_{Treatments.PREDNISONE}": "",
        }
        response = self.client.post(
            reverse("flareaids:patient-create", kwargs={"username": self.psp.username}), data=data
        )
        assert response.status_code == 302
        self.assertFalse(MedAllergy.objects.filter(user=self.psp).exists())
        self.assertFalse(MedAllergy.objects.filter(user=self.psp, treatment=Treatments.COLCHICINE).exists())
        self.assertFalse(MedAllergy.objects.filter(user=self.psp, treatment=Treatments.PREDNISONE).exists())

    def test__post_creates_medhistorydetails(self):
        """Test that the view creates the User's MedHistoryDetails objects."""
        self.assertFalse(MedHistory.objects.filter(user=self.psp, medhistorytype=MedHistoryTypes.CKD).exists())
        data = {
            # Steal some data from self.psp to create gender and dateofbirth
            "dateofbirth-value": age_calc(self.psp.dateofbirth.value),
            "gender-value": self.psp.gender.value,
            f"{MedHistoryTypes.CKD}-value": True,
            # Create data for CKD
            "dialysis": False,
            "baselinecreatinine-value": Decimal("2.2"),
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
        }
        response = self.client.post(
            reverse("flareaids:patient-create", kwargs={"username": self.psp.username}), data=data
        )
        assert response.status_code == 302
        self.assertTrue(CkdDetail.objects.filter(medhistory=self.psp.ckd).exists())
        self.assertTrue(BaselineCreatinine.objects.filter(medhistory=self.psp.ckd).exists())

    def test__post_deletes_medhistorydetail(self):
        ckd = MedHistoryFactory(user=self.psp, medhistorytype=MedHistoryTypes.CKD)
        CkdDetailFactory(
            medhistory=self.psp.ckd,
            dialysis=False,
            stage=labs_stage_calculator(
                labs_eGFR_calculator(
                    creatinine=BaselineCreatinineFactory(medhistory=ckd, value=Decimal("2.2")),
                    age=age_calc(self.psp.dateofbirth.value),
                    gender=self.psp.gender.value,
                )
            ),
        )
        self.assertTrue(MedHistory.objects.filter(user=self.psp, medhistorytype=MedHistoryTypes.CKD).exists())
        self.assertTrue(
            CkdDetail.objects.filter(medhistory=self.psp.ckd).exists()
            and BaselineCreatinine.objects.filter(medhistory=self.psp.ckd).exists()
        )
        data = {
            # Steal some data from self.psp to create gender and dateofbirth
            "dateofbirth-value": age_calc(self.psp.dateofbirth.value),
            "gender-value": self.psp.gender.value,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
        }
        response = self.client.post(
            reverse("flareaids:patient-create", kwargs={"username": self.psp.username}), data=data
        )
        assert response.status_code == 302
        self.assertFalse(CkdDetail.objects.filter(medhistory=self.psp.ckd).exists())
        self.assertFalse(BaselineCreatinine.objects.filter(medhistory=self.psp.ckd).exists())

    def test__post_creates_flareaids_with_correct_recommendations(self):
        """Test that the view creates the User's FlareAid object with the correct
        recommendations."""
        for user in Pseudopatient.objects.all():
            data = create_flareaid_data(user)
            if user.profile.provider:
                self.client.force_login(user.profile.provider)
            response = self.client.post(
                reverse("flareaids:patient-create", kwargs={"username": user.username}), data=data
            )
            tests_print_response_form_errors(response)
            assert response.status_code == 302
            # Get the FlareAid
            flareaid = FlareAid.objects.get(user=user)
            # Test the FlareAid logic on the recommendations and options for the FlareAid
            # Check NSAID contraindications first
            if form_data_nsaid_contra(data=data):
                for nsaid in NsaidChoices.values:
                    assert nsaid not in flareaid.recommendation and nsaid not in flareaid.options
            # Check colchicine contraindications
            colch_contra = form_data_colchicine_contra(data=data, user=user)
            if colch_contra is not None:
                if colch_contra == Contraindications.ABSOLUTE or colch_contra == Contraindications.RELATIVE:
                    assert Treatments.COLCHICINE not in flareaid.recommendation if flareaid.recommendation else True
                    assert Treatments.COLCHICINE not in flareaid.options if flareaid.options else True
                elif colch_contra == Contraindications.DOSEADJ:
                    assert Treatments.COLCHICINE in flareaid.options if flareaid.options else True
                    assert (
                        flareaid.options[Treatments.COLCHICINE]["dose"] == ColchicineDoses.POINTTHREE
                        if flareaid.options
                        else True
                    )
                    assert (
                        flareaid.options[Treatments.COLCHICINE]["dose2"] == ColchicineDoses.POINTSIX
                        if flareaid.options
                        else True
                    )
                    assert (
                        flareaid.options[Treatments.COLCHICINE]["dose3"] == ColchicineDoses.POINTTHREE
                        if flareaid.options
                        else True
                    )
            else:
                assert Treatments.COLCHICINE in flareaid.options
                assert flareaid.options[Treatments.COLCHICINE]["dose"] == ColchicineDoses.POINTSIX
                assert flareaid.options[Treatments.COLCHICINE]["dose2"] == ColchicineDoses.ONEPOINTTWO
                assert flareaid.options[Treatments.COLCHICINE]["dose3"] == ColchicineDoses.POINTSIX

    def test__post_returns_errors(self):
        """Test that post returns errors for some common scenarios where the
        data is invalid. Typically, these are scenarios that should be prevented by
        the form or javascript."""
        # Test that the view returns errors when the baselinecreatinine and
        # stage are not congruent
        data = create_flareaid_data(user=self.psp)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": False,
                "baselinecreatinine-value": Decimal("9.9"),
                "stage": Stages.ONE,
            }
        )
        self.client.force_login(self.psp)
        response = self.client.post(
            reverse("flareaids:patient-create", kwargs={"username": self.psp.username}), data=data
        )
        assert response.status_code == 200
        assert "form" in response.context_data
        assert "ckddetail_form" in response.context_data
        assert "stage" in response.context_data["ckddetail_form"].errors
        assert "baselinecreatinine_form" in response.context_data
        assert "value" in response.context_data["baselinecreatinine_form"].errors
        # Test that the view returns errors when CKD is True and dialysis is left blank
        data = create_flareaid_data(user=self.psp)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": "",
            }
        )
        self.client.force_login(self.psp)
        response = self.client.post(
            reverse("flareaids:patient-create", kwargs={"username": self.psp.username}), data=data
        )
        assert response.status_code == 200
        assert "ckddetail_form" in response.context_data
        assert "dialysis" in response.context_data["ckddetail_form"].errors


class TestFlareAidPatientUpdate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = FlareAidPatientUpdate
        self.user = PseudopatientPlusFactory()
        for _ in range(10):
            PseudopatientPlusFactory()
        self.psp = PseudopatientFactory()
        for psp in Pseudopatient.objects.all():
            FlareAidUserFactory(user=psp)

    def test__check_user_onetoones(self):
        """Tests that the view checks for the User's related models."""
        empty_user = PseudopatientFactory(dateofbirth=None, gender=None)
        with self.assertRaises(AttributeError) as exc:
            self.view().check_user_onetoones(empty_user)
        self.assertEqual(
            exc.exception.args[0], "Baseline information is needed to use GoutHelper Decision and Treatment Aids."
        )
        assert self.view().check_user_onetoones(self.user) is None

    def test__ckddetail(self):
        """Tests the ckddetail cached_property."""
        self.assertTrue(self.view().ckddetail)

    def test__get_form_kwargs(self):
        # Create a fake request
        request = self.factory.get("/fake-url/")
        view = self.view(request=request)
        form_kwargs = view.get_form_kwargs()
        self.assertIn("medallergys", form_kwargs)

    def test__goutdetail(self):
        """Tests the goutdetail cached_property."""
        self.assertFalse(self.view().goutdetail)

    def test__get(self):
        """Test the get() method for the view. Should redirect to Pseudopatient Update
        view when the user doesn't have the required 1to1 related models."""
        request = self.factory.get("/fake-url/")
        kwargs = {"username": self.user.username}
        view = self.view()
        # https://stackoverflow.com/questions/33645780/how-to-unit-test-methods-inside-djangos-class-based-views
        view.setup(request, **kwargs)
        response = view.get(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(hasattr(view, "user"))
        self.assertEqual(view.user, self.user)
        # Create empty user and test that the view redirects to the user update view
        empty_user = PseudopatientFactory(dateofbirth=None)
        FlareAidUserFactory(user=empty_user)
        self.client.force_login(empty_user)
        response = self.client.get(
            reverse("flareaids:patient-update", kwargs={"username": empty_user.username}), follow=True
        )
        self.assertRedirects(response, reverse("users:pseudopatient-update", kwargs={"username": empty_user.username}))
        message = list(response.context.get("messages"))[0]
        self.assertEqual(message.tags, "error")
        self.assertEqual(
            message.message, "Baseline information is needed to use GoutHelper Decision and Treatment Aids."
        )

    def test__get_user_queryset(self):
        """Test the get_user_queryset() method for the view."""
        request = self.factory.get("/fake-url/")
        kwargs = {"username": self.user.username}
        view = self.view()
        # https://stackoverflow.com/questions/33645780/how-to-unit-test-methods-inside-djangos-class-based-views
        view.setup(request, **kwargs)
        qs = view.get_user_queryset(view.kwargs["username"])
        self.assertTrue(isinstance(qs, QuerySet))
        qs = qs.get()
        self.assertTrue(isinstance(qs, User))
        self.assertTrue(hasattr(qs, "medhistorys_qs"))
        self.assertTrue(hasattr(qs, "medallergys_qs"))
        self.assertTrue(hasattr(qs, "dateofbirth"))
        self.assertTrue(hasattr(qs, "gender"))

    def test__get_context_data_onetoones(self):
        """Test that the context data includes the user's
        related models."""
        for user in Pseudopatient.objects.all():
            request = self.factory.get("/fake-url/")
            kwargs = {"username": user.username}
            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            assert "age" in response.context_data
            assert response.context_data["age"] == age_calc(user.dateofbirth.value)
            assert "gender" in response.context_data
            assert response.context_data["gender"] == user.gender.value

    def test__get_context_data_medhistorys(self):
        """Test that the context data includes the user's
        related models."""
        for user in Pseudopatient.objects.all():
            request = self.factory.get("/fake-url/")
            kwargs = {"username": user.username}
            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            for mh in user.medhistory_set.all():
                if mh.medhistorytype in FLAREAID_MEDHISTORYS:
                    assert f"{mh.medhistorytype}_form" in response.context_data
                    assert response.context_data[f"{mh.medhistorytype}_form"].instance == mh
                    assert response.context_data[f"{mh.medhistorytype}_form"].instance._state.adding is False
                    assert response.context_data[f"{mh.medhistorytype}_form"].initial == {
                        f"{mh.medhistorytype}-value": True
                    }
                else:
                    assert f"{mh.medhistorytype}_form" not in response.context_data
            for mhtype in FLAREAID_MEDHISTORYS:
                assert f"{mhtype}_form" in response.context_data
                if mhtype not in user.medhistory_set.values_list("medhistorytype", flat=True):
                    assert response.context_data[f"{mhtype}_form"].instance._state.adding is True
                    assert response.context_data[f"{mhtype}_form"].initial == {f"{mhtype}-value": False}
            assert "ckddetail_form" in response.context_data
            if user.ckd:
                if getattr(user.ckd, "ckddetail", None):
                    assert response.context_data["ckddetail_form"].instance == user.ckd.ckddetail
                    assert response.context_data["ckddetail_form"].instance._state.adding is False
                else:
                    assert response.context_data["ckddetail_form"].instance._state.adding is True
                if getattr(user.ckd, "baselinecreatinine", None):
                    assert response.context_data["baselinecreatinine_form"].instance == user.ckd.baselinecreatinine
                    assert response.context_data["baselinecreatinine_form"].instance._state.adding is False
                else:
                    assert response.context_data["baselinecreatinine_form"].instance._state.adding is True
            else:
                assert response.context_data["ckddetail_form"].instance._state.adding is True
                assert response.context_data["baselinecreatinine_form"].instance._state.adding is True
            assert "goutdetail_form" not in response.context_data

    def test__get_context_data_medallergys(self):
        """Test that the context data includes the user's
        related models."""
        for user in Pseudopatient.objects.all():
            request = self.factory.get("/fake-url/")
            kwargs = {"username": user.username}
            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            for ma in user.medallergy_set.filter(Q(treatment__in=FlarePpxChoices.values)).all():
                assert f"medallergy_{ma.treatment}_form" in response.context_data
                assert response.context_data[f"medallergy_{ma.treatment}_form"].instance == ma
                assert response.context_data[f"medallergy_{ma.treatment}_form"].instance._state.adding is False
                assert response.context_data[f"medallergy_{ma.treatment}_form"].initial == {
                    f"medallergy_{ma.treatment}": True
                }
            for treatment in FlarePpxChoices.values:
                assert f"medallergy_{treatment}_form" in response.context_data
                if treatment not in user.medallergy_set.values_list("treatment", flat=True):
                    assert response.context_data[f"medallergy_{treatment}_form"].instance._state.adding is True
                    assert response.context_data[f"medallergy_{treatment}_form"].initial == {
                        f"medallergy_{treatment}": None
                    }

    def test__post(self):
        """Test the post() method for the view."""
        request = self.factory.post("/fake-url/")
        kwargs = {"username": self.user.username}
        response = self.view.as_view()(request, **kwargs)
        assert response.status_code == 200

    def test__post_updates_medhistorys(self):
        psp = Pseudopatient.objects.last()
        for mh in FLAREAID_MEDHISTORYS:
            setattr(self, f"{mh}_bool", psp.medhistory_set.filter(medhistorytype=mh).exists())
        data = create_flareaid_data(psp)
        data.update(
            {
                **{
                    f"{mh}-value": not getattr(self, f"{mh}_bool")
                    for mh in FLAREAID_MEDHISTORYS
                    # Need to exclude CKD because of related CkdDetail fields throwing errors
                    if mh != MedHistoryTypes.CKD
                },
            }
        )
        response = self.client.post(
            reverse("flareaids:patient-update", kwargs={"username": self.psp.username}), data=data
        )
        tests_print_response_form_errors(response)
        assert response.status_code == 302
        for mh in [mh for mh in FLAREAID_MEDHISTORYS if mh != MedHistoryTypes.CKD]:
            self.assertEqual(psp.medhistory_set.filter(medhistorytype=mh).exists(), not getattr(self, f"{mh}_bool"))

    def test__post_updates_medallergys(self):
        psp = Pseudopatient.objects.last()
        for ma in FlarePpxChoices.values:
            setattr(self, f"{ma}_bool", psp.medallergy_set.filter(treatment=ma).exists())
        data = create_flareaid_data(psp)
        data.update(
            {
                **{f"medallergy_{ma}": not getattr(self, f"{ma}_bool") for ma in FlarePpxChoices.values},
            }
        )
        response = self.client.post(
            reverse("flareaids:patient-update", kwargs={"username": self.psp.username}), data=data
        )
        tests_print_response_form_errors(response)
        assert response.status_code == 302
        for ma in FlarePpxChoices.values:
            self.assertEqual(psp.medallergy_set.filter(treatment=ma).exists(), not getattr(self, f"{ma}_bool"))

    def test__post_creates_medhistorydetails(self):
        """Test that the view creates the User's MedHistoryDetails objects."""
        # Create user without ckd
        psp = PseudopatientFactory()
        FlareAidUserFactory(user=psp)
        self.assertFalse(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.CKD).exists())
        data = {
            # Steal some data from self.psp to create gender and dateofbirth
            "dateofbirth-value": age_calc(self.psp.dateofbirth.value),
            "gender-value": self.psp.gender.value,
            f"{MedHistoryTypes.CKD}-value": True,
            # Create data for CKD
            "dialysis": False,
            "baselinecreatinine-value": Decimal("2.2"),
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
        }
        response = self.client.post(
            reverse("flareaids:patient-update", kwargs={"username": self.psp.username}), data=data
        )
        assert response.status_code == 302
        self.assertTrue(CkdDetail.objects.filter(medhistory=self.psp.ckd).exists())
        self.assertTrue(BaselineCreatinine.objects.filter(medhistory=self.psp.ckd).exists())

    def test__post_deletes_medhistorydetail(self):
        psp = PseudopatientFactory()
        FlareAidUserFactory(user=psp)
        ckd = MedHistoryFactory(user=psp, medhistorytype=MedHistoryTypes.CKD)
        CkdDetailFactory(
            medhistory=psp.ckd,
            dialysis=False,
            stage=labs_stage_calculator(
                labs_eGFR_calculator(
                    creatinine=BaselineCreatinineFactory(medhistory=ckd, value=Decimal("2.2")),
                    age=age_calc(psp.dateofbirth.value),
                    gender=psp.gender.value,
                )
            ),
        )
        self.assertTrue(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.CKD).exists())
        self.assertTrue(
            CkdDetail.objects.filter(medhistory=psp.ckd).exists()
            and BaselineCreatinine.objects.filter(medhistory=psp.ckd).exists()
        )
        data = {
            # Steal some data from self.psp to create gender and dateofbirth
            "dateofbirth-value": age_calc(psp.dateofbirth.value),
            "gender-value": psp.gender.value,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
        }
        response = self.client.post(reverse("flareaids:patient-update", kwargs={"username": psp.username}), data=data)
        assert response.status_code == 302
        self.assertFalse(CkdDetail.objects.filter(medhistory=psp.ckd).exists())
        self.assertFalse(BaselineCreatinine.objects.filter(medhistory=psp.ckd).exists())

    def test__post_creates_flareaids_with_correct_recommendations(self):
        """Test that the view creates the User's FlareAid object with the correct
        recommendations."""
        for user in Pseudopatient.objects.all():
            if not hasattr(user, "flareaid"):
                FlareAidUserFactory(user=user)
            data = create_flareaid_data(user)
            if user.profile.provider:
                self.client.force_login(user.profile.provider)
            response = self.client.post(
                reverse("flareaids:patient-update", kwargs={"username": user.username}), data=data
            )
            tests_print_response_form_errors(response)
            assert response.status_code == 302
            # Get the FlareAid
            flareaid = FlareAid.objects.get(user=user)
            # Test the FlareAid logic on the recommendations and options for the FlareAid
            # Check NSAID contraindications first
            if form_data_nsaid_contra(data=data):
                for nsaid in NsaidChoices.values:
                    assert nsaid not in flareaid.recommendation and nsaid not in flareaid.options
            # Check colchicine contraindications
            colch_contra = form_data_colchicine_contra(data=data, user=user)
            if colch_contra is not None:
                if colch_contra == Contraindications.ABSOLUTE or colch_contra == Contraindications.RELATIVE:
                    assert Treatments.COLCHICINE not in flareaid.recommendation if flareaid.recommendation else True
                    assert Treatments.COLCHICINE not in flareaid.options if flareaid.options else True
                elif colch_contra == Contraindications.DOSEADJ:
                    assert Treatments.COLCHICINE in flareaid.options if flareaid.options else True
                    assert (
                        flareaid.options[Treatments.COLCHICINE]["dose"] == ColchicineDoses.POINTTHREE
                        if flareaid.options
                        else True
                    )
                    assert (
                        flareaid.options[Treatments.COLCHICINE]["dose2"] == ColchicineDoses.POINTSIX
                        if flareaid.options
                        else True
                    )
                    assert (
                        flareaid.options[Treatments.COLCHICINE]["dose3"] == ColchicineDoses.POINTTHREE
                        if flareaid.options
                        else True
                    )
            else:
                assert Treatments.COLCHICINE in flareaid.options
                assert flareaid.options[Treatments.COLCHICINE]["dose"] == ColchicineDoses.POINTSIX
                assert flareaid.options[Treatments.COLCHICINE]["dose2"] == ColchicineDoses.ONEPOINTTWO
                assert flareaid.options[Treatments.COLCHICINE]["dose3"] == ColchicineDoses.POINTSIX

    def test__post_returns_errors(self):
        """Test that post returns errors for some common scenarios where the
        data is invalid. Typically, these are scenarios that should be prevented by
        the form or javascript."""
        # Test that the view returns errors when the baselinecreatinine and
        # stage are not congruent
        data = create_flareaid_data(user=self.psp)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": False,
                "baselinecreatinine-value": Decimal("9.9"),
                "stage": Stages.ONE,
            }
        )
        self.client.force_login(self.psp)
        response = self.client.post(
            reverse("flareaids:patient-update", kwargs={"username": self.psp.username}), data=data
        )
        assert response.status_code == 200
        assert "form" in response.context_data
        assert "ckddetail_form" in response.context_data
        assert "stage" in response.context_data["ckddetail_form"].errors
        assert "baselinecreatinine_form" in response.context_data
        assert "value" in response.context_data["baselinecreatinine_form"].errors
        # Test that the view returns errors when CKD is True and dialysis is left blank
        data = create_flareaid_data(user=self.psp)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": "",
            }
        )
        self.client.force_login(self.psp)
        response = self.client.post(
            reverse("flareaids:patient-update", kwargs={"username": self.psp.username}), data=data
        )
        assert response.status_code == 200
        assert "ckddetail_form" in response.context_data
        assert "dialysis" in response.context_data["ckddetail_form"].errors


class TestFlareAidDetail(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: FlareAidDetail = FlareAidDetail
        self.content_qs = Content.objects.filter(
            Q(tag=Tags.EXPLANATION) | Q(tag=Tags.WARNING), context=Content.Contexts.FLAREAID, slug__isnull=False
        ).all()
        self.flareaid = FlareAidFactory()

    def test__contents(self):
        self.assertTrue(self.view().contents)
        self.assertTrue(isinstance(self.view().contents, QuerySet))
        for content in self.view().contents:
            self.assertIn(content, self.content_qs)
        for content in self.content_qs:
            self.assertIn(content, self.view().contents)

    def test__get_context_data(self):
        response = self.client.get(reverse("flareaids:detail", kwargs={"pk": self.flareaid.pk}))
        context = response.context_data
        for content in self.content_qs:
            self.assertIn(content.slug, context)
            self.assertEqual(context[content.slug], {content.tag: content})

    def test__get_queryset(self):
        qs = self.view(kwargs={"pk": self.flareaid.pk}).get_queryset()
        self.assertTrue(isinstance(qs, QuerySet))
        self.assertEqual(qs.first(), self.flareaid)
        self.assertTrue(hasattr(qs.first(), "medhistorys_qs"))
        self.assertTrue(hasattr(qs.first(), "medallergys_qs"))
        self.assertTrue(hasattr(qs.first(), "ckddetail"))
        self.assertTrue(hasattr(qs.first(), "baselinecreatinine"))
        self.assertTrue(hasattr(qs.first(), "dateofbirth"))
        self.assertTrue(hasattr(qs.first(), "gender"))

    def test__get_object_updates(self):
        self.assertTrue(self.flareaid.recommendation[0] == Treatments.NAPROXEN)
        medallergy = MedAllergyFactory(treatment=Treatments.NAPROXEN)
        self.flareaid.medallergys.add(medallergy)
        request = self.factory.get(reverse("flareaids:detail", kwargs={"pk": self.flareaid.pk}))
        self.view.as_view()(request, pk=self.flareaid.pk)
        # This needs to be manually refetched from the db
        self.assertFalse(FlareAid.objects.get().recommendation[0] == Treatments.NAPROXEN)

    def test__get_object_does_not_update(self):
        self.assertTrue(self.flareaid.recommendation[0] == Treatments.NAPROXEN)
        request = self.factory.get(reverse("flareaids:detail", kwargs={"pk": self.flareaid.pk}) + "?updated=True")
        self.view.as_view()(request, pk=self.flareaid.pk)
        # This needs to be manually refetched from the db
        self.assertTrue(FlareAid.objects.get().recommendation[0] == Treatments.NAPROXEN)


class TestFlareAidUpdate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: FlareAidUpdate = FlareAidUpdate()

    def test__post_unchanged_medallergys(self):
        flareaid = FlareAidFactory()
        medallergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        flareaid.medallergys.add(medallergy)
        flareaid_data = {
            "dateofbirth-value": age_calc(flareaid.dateofbirth.value),
            "gender-value": "",
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"medallergy_{Treatments.COLCHICINE}": True,
        }
        response = self.client.post(reverse("flareaids:update", kwargs={"pk": flareaid.pk}), flareaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MedAllergy.objects.filter(treatment=Treatments.COLCHICINE).exists())

    def test__post_add_medallergys(self):
        flareaid = FlareAidFactory()
        medallergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        flareaid.medallergys.add(medallergy)
        flareaid_data = {
            "dateofbirth-value": age_calc(flareaid.dateofbirth.value),
            "gender-value": "",
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"medallergy_{Treatments.COLCHICINE}": True,
            f"medallergy_{Treatments.PREDNISONE}": True,
            f"medallergy_{Treatments.NAPROXEN}": True,
        }
        response = self.client.post(reverse("flareaids:update", kwargs={"pk": flareaid.pk}), flareaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MedAllergy.objects.filter(treatment=Treatments.PREDNISONE).exists())
        self.assertTrue(MedAllergy.objects.filter(treatment=Treatments.NAPROXEN).exists())
        self.assertEqual(MedAllergy.objects.count(), 3)

    def test__post_delete_medallergys(self):
        flareaid = FlareAidFactory()
        medallergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        flareaid.medallergys.add(medallergy)
        flareaid_data = {
            "dateofbirth-value": age_calc(flareaid.dateofbirth.value),
            "gender-value": "",
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"medallergy_{Treatments.COLCHICINE}": "",
        }
        response = self.client.post(reverse("flareaids:update", kwargs={"pk": flareaid.pk}), flareaid_data)
        self.assertEqual(response.status_code, 302)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertFalse(MedAllergy.objects.filter(treatment=Treatments.COLCHICINE).exists())
        self.assertEqual(MedAllergy.objects.count(), 0)

    def test__post_unchanged_medhistorys(self):
        flareaid = FlareAidFactory()
        medhistory = MedHistoryFactory(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION)
        flareaid.medhistorys.add(medhistory)
        flareaid_data = {
            "dateofbirth-value": age_calc(flareaid.dateofbirth.value),
            "gender-value": "",
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": True,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
        }
        response = self.client.post(reverse("flareaids:update", kwargs={"pk": flareaid.pk}), flareaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION).exists())
        self.assertEqual(MedHistory.objects.count(), 1)

    def test__post_delete_medhistorys(self):
        flareaid = FlareAidFactory()
        medhistory = MedHistoryFactory(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION)
        flareaid.medhistorys.add(medhistory)
        flareaid_data = {
            "dateofbirth-value": age_calc(flareaid.dateofbirth.value),
            "gender-value": "",
            f"{MedHistoryTypes.CKD}-value": False,
            # Need to mark Colchicineinteraction as False to delete it, required by form.
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
        }
        response = self.client.post(reverse("flareaids:update", kwargs={"pk": flareaid.pk}), flareaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION).exists())
        self.assertEqual(MedHistory.objects.count(), 0)

    def test__post_add_medhistorys(self):
        flareaid = FlareAidFactory()
        medhistory = MedHistoryFactory(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION)
        flareaid.medhistorys.add(medhistory)
        flareaid_data = {
            "dateofbirth-value": age_calc(flareaid.dateofbirth.value),
            "gender-value": "",
            f"{MedHistoryTypes.CKD}-value": False,
            # Need to mark Colchicineinteraction as False to delete it, required by form.
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": True,
            f"{MedHistoryTypes.DIABETES}-value": True,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"{MedHistoryTypes.STROKE}-value": True,
        }
        response = self.client.post(reverse("flareaids:update", kwargs={"pk": flareaid.pk}), flareaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION).exists())
        self.assertTrue(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.DIABETES).exists())
        self.assertTrue(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.STROKE).exists())
        self.assertEqual(MedHistory.objects.count(), 3)
