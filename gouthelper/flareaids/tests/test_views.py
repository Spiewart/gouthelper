from datetime import timedelta
from decimal import Decimal

import pytest  # pylint: disable=e0401 # type: ignore
from django.contrib.auth import get_user_model  # pylint: disable=e0401 # type: ignore
from django.contrib.auth.models import AnonymousUser  # pylint: disable=e0401 # type: ignore
from django.contrib.messages.middleware import MessageMiddleware  # pylint: disable=e0401 # type: ignore
from django.contrib.sessions.middleware import SessionMiddleware  # pylint: disable=e0401 # type: ignore
from django.core.exceptions import ObjectDoesNotExist  # pylint: disable=e0401 # type: ignore
from django.db.models import Q, QuerySet  # pylint: disable=e0401 # type: ignore
from django.http import HttpResponse  # pylint: disable=e0401 # type: ignore
from django.test import RequestFactory, TestCase  # pylint: disable=e0401 # type: ignore
from django.urls import reverse  # pylint: disable=e0401 # type: ignore
from django.utils import timezone  # pylint: disable=e0401 # type: ignore

from ...contents.models import Content, Tags
from ...dateofbirths.helpers import age_calc
from ...flares.tests.factories import create_flare
from ...genders.choices import Genders
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
from ...users.tests.factories import AdminFactory, UserFactory, create_psp
from ...utils.factories import (
    form_data_colchicine_contra,
    form_data_nsaid_contra,
    medallergy_diff_obj_data,
    medhistory_diff_obj_data,
)
from ...utils.forms import forms_print_response_errors
from ...utils.test_helpers import dummy_get_response
from ..models import FlareAid
from ..selectors import flareaid_user_qs
from ..views import (
    FlareAidAbout,
    FlareAidCreate,
    FlareAidDetail,
    FlareAidPseudopatientCreate,
    FlareAidPseudopatientDetail,
    FlareAidPseudopatientUpdate,
    FlareAidUpdate,
)
from .factories import create_flareaid, flareaid_data_factory

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
        self.view = FlareAidCreate
        self.flareaid_data = {
            "dateofbirth-value": age_calc(timezone.now() - timedelta(days=365 * 50)),
            "gender-value": Genders.FEMALE,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"{MedHistoryTypes.STROKE}-value": True,
            f"{MedHistoryTypes.CAD}-value": True,
            f"{MedHistoryTypes.CHF}-value": True,
            f"{MedHistoryTypes.DIABETES}-value": True,
        }
        self.flare = create_flare()

    def test__dispatch_redirects_for_flare_with_flareaid(self):
        """Test that the dispatch() method redirects to the flareaids:update view when the view is called with
        the pk for a flare that already has a flareaid field."""
        flare = create_flare()
        flare.flareaid = create_flareaid(dateofbirth=flare.dateofbirth, gender=flare.gender)
        flare.save()
        response = self.client.get(reverse("flareaids:flare-create", kwargs={"flare": flare.pk}))
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("flareaids:update", kwargs={"pk": flare.flareaid.pk}))

    def test__get_context_data_with_flare(self):
        response = self.client.get(reverse("flareaids:flare-create", kwargs={"flare": self.flare.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertIn("flare", response.context_data)
        self.assertEqual(response.context_data["flare"], self.flare)
        self.assertIn("age", response.context_data)
        self.assertEqual(response.context_data["age"], age_calc(self.flare.dateofbirth.value))
        self.assertIn("gender", response.context_data)
        self.assertEqual(response.context_data["gender"], self.flare.gender.value)
        self.assertNotIn("dateofbirth_form", response.context_data)
        self.assertNotIn("gender_form", response.context_data)
        for mh in self.flare.medhistorys_qs:
            if mh.medhistorytype in FLAREAID_MEDHISTORYS:
                self.assertIn(f"{mh.medhistorytype}_form", response.context_data)
                self.assertEqual(response.context_data[f"{mh.medhistorytype}_form"].instance, mh)
                self.assertFalse(response.context_data[f"{mh.medhistorytype}_form"].instance._state.adding)
                self.assertEqual(
                    response.context_data[f"{mh.medhistorytype}_form"].initial, {f"{mh.medhistorytype}-value": True}
                )

    def test__get_permission_object_with_flare(self):
        request = self.factory.get("/fake-url/")
        request.user = AnonymousUser()
        SessionMiddleware(dummy_get_response).process_request(request)
        kwargs = {"flare": self.flare.pk}
        view = self.view()
        # https://stackoverflow.com/questions/33645780/how-to-unit-test-methods-inside-djangos-class-based-views
        view.setup(request, **kwargs)
        permission_object = view.get_permission_object()
        self.assertEqual(permission_object, self.flare.user)
        self.assertTrue(hasattr(view, "flare"))
        self.assertEqual(view.flare, self.flare)

    def test__get_permission_object_with_flare_with_user_raises_ValueError(self):
        user_flare = create_flare(user=True)
        request = self.factory.get("/fake-url/")
        request.user = AnonymousUser()
        SessionMiddleware(dummy_get_response).process_request(request)
        kwargs = {"flare": user_flare.pk}
        view = self.view()
        # https://stackoverflow.com/questions/33645780/how-to-unit-test-methods-inside-djangos-class-based-views
        view.setup(request, **kwargs)
        with self.assertRaises(PermissionError) as exc:
            view.get_permission_object()
            self.assertEqual(exc.msg, "Trying to create a FlareAid for a Flare with a user with an anonymous view.")

    def test__related_object(self):
        request = self.factory.get("/fake-url/")
        request.user = AnonymousUser()
        SessionMiddleware(dummy_get_response).process_request(request)
        kwargs = {"flare": self.flare.pk}
        view = self.view()
        # https://stackoverflow.com/questions/33645780/how-to-unit-test-methods-inside-djangos-class-based-views
        view.setup(request, **kwargs)
        self.assertEqual(view.related_object, self.flare)
        view = self.view()
        view.setup(request)
        self.assertIsNone(view.related_object)

    def test__successful_post(self):
        response = self.client.post(reverse("flareaids:create"), self.flareaid_data)
        forms_print_response_errors(response)
        self.assertTrue(FlareAid.objects.order_by("created").last())
        self.assertEqual(response.status_code, 302)

    def test__successful_post_with_flare(self):
        response = self.client.post(
            reverse("flareaids:flare-create", kwargs={"flare": self.flare.pk}), self.flareaid_data
        )
        forms_print_response_errors(response)
        self.assertTrue(FlareAid.objects.order_by("created").last())
        self.assertEqual(response.status_code, 302)
        flareaid = FlareAid.objects.order_by("created").last()
        self.flare.refresh_from_db()
        self.assertIsNotNone(self.flare.flareaid)
        self.assertEqual(self.flare.flareaid, flareaid)

    def test__post_with_flare_assigns_medhistorys(self):
        initial_flare_medhistorys = list(
            self.flare.medhistory_set.filter(medhistorytype__in=FLAREAID_MEDHISTORYS).values_list(
                "medhistorytype", flat=True
            )
        ).copy()
        response = self.client.post(
            reverse("flareaids:flare-create", kwargs={"flare": self.flare.pk}), self.flareaid_data
        )
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        flareaid = FlareAid.objects.order_by("created").last()
        for mh in self.flare.medhistory_set.filter(medhistorytype__in=FLAREAID_MEDHISTORYS):
            mhtype = mh.medhistorytype
            if self.flareaid_data.get(f"{mhtype}-value", None):
                self.assertEqual(
                    flareaid.medhistory_set.get(medhistorytype=mhtype),
                    mh,
                )
        for mhtype in initial_flare_medhistorys:
            if self.flareaid_data.get(f"{mhtype}-value", None):
                self.assertTrue(self.flare.medhistory_set.filter(medhistorytype=mhtype).exists())
                self.assertTrue(flareaid.medhistory_set.filter(medhistorytype=mhtype).exists())
            else:
                self.assertFalse(self.flare.medhistory_set.filter(medhistorytype=mhtype).exists())
                self.assertFalse(flareaid.medhistory_set.filter(medhistorytype=mhtype).exists())

    def test__post_creates_medhistorys(self):
        response = self.client.post(reverse("flareaids:create"), self.flareaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        qs = MedHistory.objects.filter(flareaid=FlareAid.objects.order_by("created").last())
        self.assertTrue(qs.filter(medhistorytype=MedHistoryTypes.STROKE).exists())
        self.assertTrue(qs.filter(medhistorytype=MedHistoryTypes.DIABETES).exists())
        self.assertEqual(qs.count(), 4)
        self.assertIn(
            MedHistoryTypes.STROKE,
            FlareAid.objects.order_by("created").last().medhistory_set.values_list("medhistorytype", flat=True),
        )
        self.assertIn(
            MedHistoryTypes.DIABETES,
            FlareAid.objects.order_by("created").last().medhistory_set.values_list("medhistorytype", flat=True),
        )

    def test__post_creates_ckddetail(self):
        # Count the number of CkdDetails
        ckddetail_count = CkdDetail.objects.count()
        self.flareaid_data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": True,
                "dialysis_duration": DialysisDurations.LESSTHANSIX,
                "dialysis_type": DialysisChoices.PERITONEAL,
            }
        )
        response = self.client.post(reverse("flareaids:create"), self.flareaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CkdDetail.objects.count(), ckddetail_count + 1)
        self.assertTrue(FlareAid.objects.order_by("created").last().ckddetail)

    def test__post_creates_baselinecreatinine(self):
        """Test that the view creates a BaselineCreatinine object."""
        # Count the number of BaselineCreatinines
        baselinecreatinine_count = BaselineCreatinine.objects.count()

        # Create some fake data and post() it
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
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        # Test that a BaselineCreatinine was created
        self.assertEqual(BaselineCreatinine.objects.count(), baselinecreatinine_count + 1)

        # Test that the baseline creatinine was properly created
        flareaid = FlareAid.objects.order_by("created").last()
        bc = BaselineCreatinine.objects.order_by("created").last()
        ckddetail = CkdDetail.objects.order_by("created").last()

        self.assertEqual(bc.value, Decimal("2.2"))
        self.assertEqual(flareaid.ckd.baselinecreatinine, bc)
        self.assertEqual(
            ckddetail.stage,
            labs_stage_calculator(
                labs_eGFR_calculator(
                    bc,
                    age_calc(flareaid.dateofbirth.value),
                    flareaid.gender.value,
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
        """Test that the view creates MedAllergy objects."""
        # Count the number of MedAllergys
        medallergy_count = MedAllergy.objects.count()

        # Create some fake data and post() it
        self.flareaid_data.update(
            {
                f"medallergy_{Treatments.COLCHICINE}": True,
                f"medallergy_{Treatments.PREDNISONE}": True,
                f"medallergy_{Treatments.NAPROXEN}": True,
            }
        )
        response = self.client.post(reverse("flareaids:create"), self.flareaid_data)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(MedAllergy.objects.count(), medallergy_count + 3)

        flareaid = FlareAid.objects.order_by("created").last()
        colch_allergy = MedAllergy.objects.order_by("created").filter(treatment=Treatments.COLCHICINE).last()
        pred_allergy = MedAllergy.objects.order_by("created").filter(treatment=Treatments.PREDNISONE).last()
        naproxen_allergy = MedAllergy.objects.order_by("created").filter(treatment=Treatments.NAPROXEN).last()

        # Test that the medallergys are in the flareaid's medallergys field
        flareaid_medallergys = flareaid.medallergy_set.all()
        self.assertIn(colch_allergy, flareaid_medallergys)
        self.assertIn(pred_allergy, flareaid_medallergys)
        self.assertIn(naproxen_allergy, flareaid_medallergys)


class TestFlareAidPseudopatientCreate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = FlareAidPseudopatientCreate
        self.anon_user = AnonymousUser()
        self.user = create_psp(plus=True)
        for _ in range(10):
            create_psp(plus=True)
        self.psp = create_psp()

    def test__check_user_onetoones(self):
        """Tests that the view checks for the User's related models."""
        empty_user = create_psp(dateofbirth=False, gender=False)
        view = self.view()
        view.user = empty_user
        self.assertFalse(view.user_has_required_otos)

    def test__ckddetail(self):
        """Tests the ckddetail cached_property."""
        view = self.view()
        view.set_forms()
        self.assertTrue(view.ckddetail)

    def test__get_form_kwargs(self):
        # Create a fake request
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        view = self.view()
        view.setup(request=request, pseudopatient=self.user.pk)
        view.set_forms()
        view.object = view.get_object()
        form_kwargs = view.get_form_kwargs()
        self.assertIn("medallergys", form_kwargs)

    def test__goutdetail(self):
        """Tests the goutdetail cached_property."""
        self.assertFalse(self.view().goutdetail)

    def test__dispatch(self):
        """Test the dispatch() method for the view. Should redirect to detailview when
        the user already has a FlareAid. Should redirect to Pseudopatient Update
        view when the user doesn't have the required 1to1 related models."""
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        SessionMiddleware(dummy_get_response).process_request(request)
        kwargs = {"pseudopatient": self.user.pk}
        view = self.view()
        # https://stackoverflow.com/questions/33645780/how-to-unit-test-methods-inside-djangos-class-based-views
        view.setup(request, **kwargs)
        response = view.dispatch(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(hasattr(view, "user"))
        self.assertEqual(view.user, self.user)
        # Create a new FlareAid and test that the view redirects to the detailview
        create_flareaid(user=self.user)
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": self.user.pk}), follow=True
        )
        self.assertEqual(view.user, self.user)
        self.assertRedirects(
            response,
            reverse("flareaids:pseudopatient-update", kwargs={"pseudopatient": self.user.pk}),
        )
        # Check that the response message is correct
        message = list(response.context.get("messages"))[0]
        self.assertEqual(message.tags, "error")
        self.assertEqual(message.message, f"{self.user} already has a FlareAid. Please update it instead.")
        # Create empty user and test that the view redirects to the user update view
        empty_user = create_psp(dateofbirth=False, ethnicity=False, gender=False)
        self.client.force_login(empty_user)
        response = self.client.get(
            reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": empty_user.pk}), follow=True
        )
        self.assertRedirects(response, reverse("users:pseudopatient-update", kwargs={"pseudopatient": empty_user.pk}))
        message = list(response.context.get("messages"))[0]
        self.assertEqual(message.tags, "error")
        self.assertEqual(message.message, f"{empty_user} is missing required information.")

    def test__get_user_queryset(self):
        """Test the get_user_queryset() method for the view."""
        request = self.factory.get("/fake-url/")
        kwargs = {"pseudopatient": self.user.pk}
        view = self.view()
        # https://stackoverflow.com/questions/33645780/how-to-unit-test-methods-inside-djangos-class-based-views
        view.setup(request, **kwargs)
        qs = view.get_user_queryset(view.kwargs["pseudopatient"])
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
            if user.profile.provider:
                request.user = user.profile.provider
            else:
                request.user = self.anon_user
            SessionMiddleware(dummy_get_response).process_request(request)
            kwargs = {"pseudopatient": user.pk}
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
            if user.profile.provider:
                request.user = user.profile.provider
            else:
                request.user = self.anon_user
            SessionMiddleware(dummy_get_response).process_request(request)
            kwargs = {"pseudopatient": user.pk}
            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            for mh in user.medhistory_set.all():
                if mh.medhistorytype in FLAREAID_MEDHISTORYS:
                    assert f"{mh.medhistorytype}_form" in response.context_data
                    assert response.context_data[f"{mh.medhistorytype}_form"].instance == mh
                    assert (
                        response.context_data[f"{mh.medhistorytype}_form"].instance._state.adding is False
                    )  # pylint: disable=w0212, line-too-long # noqa: E501
                    assert response.context_data[f"{mh.medhistorytype}_form"].initial == {
                        f"{mh.medhistorytype}-value": True
                    }
                else:
                    assert f"{mh.medhistorytype}_form" not in response.context_data
            for mhtype in FLAREAID_MEDHISTORYS:
                assert f"{mhtype}_form" in response.context_data
                if mhtype not in user.medhistory_set.values_list("medhistorytype", flat=True):
                    assert (
                        response.context_data[f"{mhtype}_form"].instance._state.adding
                        is True  # pylint: disable=w0212, line-too-long # noqa: E501
                    )
                    assert response.context_data[f"{mhtype}_form"].initial == {f"{mhtype}-value": None}
            assert "ckddetail_form" in response.context_data
            if user.ckd:
                if getattr(user.ckd, "ckddetail", None):
                    assert response.context_data["ckddetail_form"].instance == user.ckd.ckddetail
                    assert (
                        response.context_data["ckddetail_form"].instance._state.adding
                        is False  # pylint: disable=w0212, line-too-long # noqa: E501
                    )
                else:
                    assert (
                        response.context_data["ckddetail_form"].instance._state.adding
                        is True  # pylint: disable=w0212, line-too-long # noqa: E501
                    )
                if getattr(user.ckd, "baselinecreatinine", None):
                    assert response.context_data["baselinecreatinine_form"].instance == user.ckd.baselinecreatinine
                    assert (
                        response.context_data["baselinecreatinine_form"].instance._state.adding
                        is False  # pylint: disable=w0212, line-too-long # noqa: E501
                    )
                else:
                    assert (
                        response.context_data["baselinecreatinine_form"].instance._state.adding
                        is True  # pylint: disable=w0212, line-too-long # noqa: E501
                    )
            else:
                assert (
                    response.context_data["ckddetail_form"].instance._state.adding
                    is True  # pylint: disable=w0212, line-too-long # noqa: E501
                )
                assert (
                    response.context_data["baselinecreatinine_form"].instance._state.adding
                    is True  # pylint: disable=w0212, line-too-long # noqa: E501
                )
            assert "goutdetail_form" not in response.context_data

    def test__get_context_data_medallergys(self):
        """Test that the context data includes the user's
        related models."""
        for user in Pseudopatient.objects.all():
            request = self.factory.get("/fake-url/")
            if user.profile.provider:
                request.user = user.profile.provider
            else:
                request.user = self.anon_user
            SessionMiddleware(dummy_get_response).process_request(request)
            kwargs = {"pseudopatient": user.pk}
            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            for ma in user.medallergy_set.filter(Q(treatment__in=FlarePpxChoices.values)).all():
                assert f"medallergy_{ma.treatment}_form" in response.context_data
                assert response.context_data[f"medallergy_{ma.treatment}_form"].instance == ma
                assert (
                    response.context_data[f"medallergy_{ma.treatment}_form"].instance._state.adding
                    is False  # pylint: disable=w0212, line-too-long # noqa: E501
                )
                assert response.context_data[f"medallergy_{ma.treatment}_form"].initial == {
                    f"medallergy_{ma.treatment}": True,
                    f"{ma.treatment}_matype": None,
                }
            for treatment in FlarePpxChoices.values:
                assert f"medallergy_{treatment}_form" in response.context_data
                if treatment not in user.medallergy_set.values_list("treatment", flat=True):
                    assert (
                        response.context_data[f"medallergy_{treatment}_form"].instance._state.adding
                        is True  # pylint: disable=w0212, line-too-long # noqa: E501
                    )
                    assert response.context_data[f"medallergy_{treatment}_form"].initial == {
                        f"medallergy_{treatment}": None,
                        f"{treatment}_matype": None,
                    }

    def test__get_permission_object(self):
        """Test the get_permission_object() method for the view."""
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        kwargs = {"pseudopatient": self.user.pk}
        view = self.view()
        # https://stackoverflow.com/questions/33645780/how-to-unit-test-methods-inside-djangos-class-based-views
        view.setup(request, **kwargs)
        view.user = self.user
        permission_object = view.get_permission_object()
        self.assertEqual(permission_object, self.user)

    def test__post(self):
        """Test the post() method for the view."""
        request = self.factory.post("/fake-url/")
        if self.user.profile.provider:  # type: ignore
            request.user = self.user.profile.provider  # type: ignore
        else:
            request.user = self.anon_user
        SessionMiddleware(dummy_get_response).process_request(request)
        kwargs = {"pseudopatient": self.user.pk}
        response = self.view.as_view()(request, **kwargs)
        assert response.status_code == 200

    def test__post_sets_object_user(self):
        """Test that the post() method for the view sets the
        user on the object."""
        # Create some fake data for a User's FlareAid
        data = flareaid_data_factory(self.user)
        response = self.client.post(
            reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": self.user.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302
        assert FlareAid.objects.filter(user=self.user).exists()
        flareaid = FlareAid.objects.last()
        assert flareaid.user
        assert flareaid.user == self.user

    def test__post_creates_medhistorys(self):
        mh_count = self.psp.medhistory_set.count()
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
        mh_diff = medhistory_diff_obj_data(self.psp, data, FLAREAID_MEDHISTORYS)
        response = self.client.post(
            reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        assert response.status_code == 302
        # (+) 1 because the view also creates a Gout MedHistory for the User behind the scenes
        self.assertEqual(self.psp.medhistory_set.count(), mh_count + mh_diff + 1)
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
            reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), data=data
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
            reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), data=data
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
            reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        assert response.status_code == 302
        self.assertFalse(MedAllergy.objects.filter(user=self.psp).exists())
        self.assertFalse(MedAllergy.objects.filter(user=self.psp, treatment=Treatments.COLCHICINE).exists())
        self.assertFalse(MedAllergy.objects.filter(user=self.psp, treatment=Treatments.PREDNISONE).exists())

    def test__post_creates_medhistorydetails(self):
        """Test that the view creates the User's MedHistoryDetails objects."""
        self.assertFalse(MedHistory.objects.filter(user=self.psp, medhistorytype=MedHistoryTypes.CKD).exists())
        data = {
            f"{MedHistoryTypes.CKD}-value": True,
            # Create data for CKD
            "dialysis": False,
            "baselinecreatinine-value": Decimal("2.2"),
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
        }
        response = self.client.post(
            reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), data=data
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
            reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        assert response.status_code == 302
        self.assertFalse(CkdDetail.objects.filter(medhistory=self.psp.ckd).exists())
        self.assertFalse(BaselineCreatinine.objects.filter(medhistory=self.psp.ckd).exists())

    def test__post_creates_flareaids_with_correct_recommendations(self):
        """Test that the view creates the User's FlareAid object with the correct
        recommendations."""
        for user in Pseudopatient.objects.all():
            data = flareaid_data_factory(user)
            if user.profile.provider:
                self.client.force_login(user.profile.provider)
            response = self.client.post(
                reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": user.pk}), data=data
            )
            forms_print_response_errors(response)
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
        data = flareaid_data_factory(user=self.psp)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": False,
                "baselinecreatinine-value": Decimal("9.9"),
                "stage": Stages.ONE,
            }
        )
        response = self.client.post(
            reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        assert response.status_code == 200
        assert "form" in response.context_data
        assert "ckddetail_form" in response.context_data
        assert "stage" in response.context_data["ckddetail_form"].errors
        assert "baselinecreatinine_form" in response.context_data
        assert "value" in response.context_data["baselinecreatinine_form"].errors
        # Test that the view returns errors when CKD is True and dialysis is left blank
        data = flareaid_data_factory(user=self.psp)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": "",
            }
        )
        response = self.client.post(
            reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        assert response.status_code == 200
        assert "ckddetail_form" in response.context_data
        assert "dialysis" in response.context_data["ckddetail_form"].errors

    def test__rules(self):
        """Tests for whether the rules appropriately allow or restrict
        access to the view."""
        psp = create_psp()
        provider = UserFactory()
        provider_psp = create_psp(provider=provider)
        admin = AdminFactory()
        admin_psp = create_psp(provider=admin)
        # Test that any User can create an anonymous Pseudopatient's FlareAid
        response = self.client.get(reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": psp.pk}))
        assert response.status_code == 200
        # Test that an anonymous User can't create a Provider's FlareAid
        response = self.client.get(
            reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": provider_psp.pk})
        )
        # 302 because PermissionDenied will redirect to the login page
        assert response.status_code == 302
        # Test that an anonymous User can't create an Admin's FlareAid
        response = self.client.get(reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": admin_psp.pk}))
        # Test that a Provider can create his or her own Pseudopatient's FlareAid
        response = self.client.get(
            reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": psp.pk}),
        )
        assert response.status_code == 200
        # Test that a Provider can create an anonymous Pseudopatient's FlareAid
        response = self.client.get(
            reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": psp.pk}),
        )
        assert response.status_code == 200
        self.client.force_login(admin)
        response = self.client.get(
            reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": admin_psp.pk}),
        )
        assert response.status_code == 200
        # Test that only a Pseudopatient's Provider can add their FlareAid if they have a Provider
        response = self.client.get(
            reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": provider_psp.pk}),
        )
        assert response.status_code == 403
        self.client.force_login(provider)
        # Test that a Provider can't create another provider's Pseudopatient's FlareAid
        response = self.client.get(
            reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": admin_psp.pk}),
        )
        assert response.status_code == 403
        self.client.force_login(admin)
        # Test that an Admin can create an anonymous Pseudopatient's FlareAid
        response = self.client.get(
            reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": psp.pk}),
        )
        assert response.status_code == 200


class TestFlareAidPseudopatientDetail(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = FlareAidPseudopatientDetail
        self.anon_user = AnonymousUser()
        self.psp = create_psp(plus=True)
        for psp in Pseudopatient.objects.all():
            create_flareaid(user=psp)
        self.empty_psp = create_psp(plus=True)

    def test__dispatch(self):
        """Test the dispatch() method for the view. Should redirect to Pseudopatient Update
        view when the user doesn't have the required 1to1 related models."""
        response = self.client.get(reverse("flareaids:pseudopatient-detail", kwargs={"pseudopatient": self.psp.pk}))
        self.assertEqual(response.status_code, 200)
        # Test that dispatch redirects to the pseudopatient-create FlareAid view when the user doesn't have a FlareAid
        self.assertRedirects(
            self.client.get(reverse("flareaids:pseudopatient-detail", kwargs={"pseudopatient": self.empty_psp.pk})),
            reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": self.empty_psp.pk}),
        )
        self.psp.dateofbirth.delete()
        # Test that dispatch redirects to the User Update view when the user doesn't have a dateofbirth
        self.assertRedirects(
            self.client.get(
                reverse("flareaids:pseudopatient-detail", kwargs={"pseudopatient": self.psp.pk}),
            ),
            reverse("users:pseudopatient-update", kwargs={"pseudopatient": self.psp.pk}),
        )

    def test__assign_flareaid_attrs_from_user(self):
        """Test that the assign_flareaid_attrs_from_user() method for the view
        transfers attributes from the QuerySet, which started with a User,
        to the FlareAid object."""
        flareaid = FlareAid.objects.get(user=self.psp)
        view = self.view()
        request = self.factory.get("/fake-url/")
        view.setup(request, pseudopatient=self.psp.pk)
        assert not getattr(flareaid, "dateofbirth")
        assert not getattr(flareaid, "gender")
        assert not hasattr(flareaid, "medhistorys_qs")
        assert not hasattr(flareaid, "medallergys_qs")
        view.assign_flareaid_attrs_from_user(flareaid=flareaid, user=flareaid_user_qs(self.psp.pk).get())
        assert getattr(flareaid, "dateofbirth") == self.psp.dateofbirth
        assert getattr(flareaid, "gender") == self.psp.gender
        assert hasattr(flareaid, "medhistorys_qs")
        assert hasattr(flareaid, "medallergys_qs")

    def test__rules(self):
        psp = create_psp()
        create_flareaid(user=psp)
        provider = UserFactory()
        provider_psp = create_psp(provider=provider)
        create_flareaid(user=provider_psp)
        admin = AdminFactory()
        admin_psp = create_psp(provider=admin)
        create_flareaid(user=admin_psp)
        # Test that any User can view an anonymous Pseudopatient's FlareAid
        response = self.client.get(reverse("flareaids:pseudopatient-detail", kwargs={"pseudopatient": psp.pk}))
        assert response.status_code == 200
        # Test that an anonymous User can't view a Provider's FlareAid
        response = self.client.get(
            reverse("flareaids:pseudopatient-detail", kwargs={"pseudopatient": provider_psp.pk})
        )
        # 302 because PermissionDenied will redirect to the login page
        assert response.status_code == 302
        # Test that an anonymous User can't view an Admin's FlareAid
        response = self.client.get(reverse("flareaids:pseudopatient-detail", kwargs={"pseudopatient": admin_psp.pk}))
        assert response.status_code == 302
        # Test that a Provider can view their own Pseudoatient's FlareAid
        self.client.force_login(provider)
        response = self.client.get(
            reverse("flareaids:pseudopatient-detail", kwargs={"pseudopatient": provider_psp.pk}),
        )
        assert response.status_code == 200
        # Test that a Provider can view an anonymous Pseudopatient's FlareAid
        response = self.client.get(
            reverse("flareaids:pseudopatient-detail", kwargs={"pseudopatient": psp.pk}),
        )
        assert response.status_code == 200
        # Test that Provider can't view Admin's Pseudopatient's FlareAid
        response = self.client.get(
            reverse("flareaids:pseudopatient-detail", kwargs={"pseudopatient": admin_psp.pk}),
        )
        assert response.status_code == 403
        self.client.force_login(admin)
        # Test that an Admin can view their own Pseudopatient's FlareAid
        response = self.client.get(
            reverse("flareaids:pseudopatient-detail", kwargs={"pseudopatient": admin_psp.pk}),
        )
        assert response.status_code == 200
        # Test that an Admin can view an anonymous Pseudopatient's FlareAid
        response = self.client.get(
            reverse("flareaids:pseudopatient-detail", kwargs={"pseudopatient": psp.pk}),
        )
        assert response.status_code == 200
        # Test that Admin can't view Provider's Pseudopatient's FlareAid
        response = self.client.get(
            reverse("flareaids:pseudopatient-detail", kwargs={"pseudopatient": provider_psp.pk}),
        )
        assert response.status_code == 403

    def test__get_object_sets_user(self):
        """Test that the get_object() method sets the user attribute."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, pseudopatient=self.psp.pk)
        view.get_object()
        assert hasattr(view, "user")
        assert view.user == self.psp

    def test__get_object_raises_DoesNotExist(self):
        """Test that the get_object() method raises DoesNotExist when the user
        doesn't have a FlareAid."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, pseudopatient=self.empty_psp.pk)
        with self.assertRaises(ObjectDoesNotExist):
            view.get_object()

    def test__get_object_assigns_user_qs_attrs_to_flareaid(self):
        """Test that the get_object method transfers required attributes from the
        User QuerySet to the FlareAid object."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, pseudopatient=self.psp.pk)
        flareaid = view.get_object()
        assert hasattr(flareaid, "dateofbirth")
        assert getattr(flareaid, "dateofbirth") == view.user.dateofbirth
        assert hasattr(flareaid, "gender")
        assert getattr(flareaid, "gender") == view.user.gender
        assert hasattr(flareaid, "medhistorys_qs")
        assert getattr(flareaid, "medhistorys_qs") == view.user.medhistorys_qs
        assert hasattr(flareaid, "medallergys_qs")
        assert getattr(flareaid, "medallergys_qs") == view.user.medallergys_qs

    def test__get_permission_object(self):
        """Test that the get_permission_object() method returns the
        view's object, which must have already been set."""
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user

        # Add the session/message middleware to the request
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        view = self.view()
        view.setup(request, pseudopatient=self.psp.pk)
        view.dispatch(request, pseudopatient=self.psp.pk)
        pm_obj = view.get_permission_object()
        assert pm_obj == view.object

    def test__get_queryset(self):
        """Test the get_queryset() method for the view."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, pseudopatient=self.psp.pk)
        with self.assertNumQueries(4):
            qs = view.get_queryset().get()
        assert qs == self.psp
        assert hasattr(qs, "flareaid") and qs.flareaid == self.psp.flareaid
        assert hasattr(qs, "dateofbirth") and qs.dateofbirth == self.psp.dateofbirth
        if hasattr(qs, "gender"):
            assert qs.gender == self.psp.gender
        assert hasattr(qs, "medhistorys_qs")
        psp_mhs = self.psp.medhistory_set.filter(medhistorytype__in=FLAREAID_MEDHISTORYS).all()
        for mh in qs.medhistorys_qs:
            assert mh in psp_mhs
        assert hasattr(qs, "medallergys_qs")
        psp_mas = self.psp.medallergy_set.filter(treatment__in=FlarePpxChoices.values).all()
        for ma in qs.medallergys_qs:
            assert ma in psp_mas

    def test__get_updates_FlareAid(self):
        """Test that the get method updates the object when called with the
        correct url parameters."""
        psp = create_psp()
        flareaid = create_flareaid(user=psp)
        self.assertIn(Treatments.COLCHICINE, flareaid.options)
        medallergy = MedAllergyFactory(treatment=Treatments.COLCHICINE, user=psp)
        self.assertIn(medallergy, psp.medallergy_set.all())
        self.client.get(reverse("flareaids:pseudopatient-detail", kwargs={"pseudopatient": psp.pk}))
        # This needs to be manually refetched from the db
        self.assertNotIn(Treatments.COLCHICINE, FlareAid.objects.get(user=psp).options)

    def test__get_does_not_update_FlareAid(self):
        """Test that the get method doesn't update the object when called with the
        ?updated=True url parameter."""
        psp = create_psp()
        flareaid = create_flareaid(user=psp)
        self.assertIn(Treatments.COLCHICINE, flareaid.options)
        medallergy = MedAllergyFactory(treatment=Treatments.COLCHICINE, user=psp)
        self.assertIn(medallergy, psp.medallergy_set.all())
        self.client.get(reverse("flareaids:pseudopatient-detail", kwargs={"pseudopatient": psp.pk}) + "?updated=True")
        # This needs to be manually refetched from the db
        self.assertIn(Treatments.COLCHICINE, FlareAid.objects.get(user=psp).options)


class TestFlareAidPseudopatientUpdate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = FlareAidPseudopatientUpdate
        self.anon_user = AnonymousUser()
        self.user = create_psp(plus=True)
        for _ in range(10):
            create_psp(plus=True)
        self.psp = create_psp()
        for psp in Pseudopatient.objects.all():
            create_flareaid(user=psp)

    def test__check_user_onetoones(self):
        """Tests that the view checks for the User's related models."""
        empty_user = create_psp(dateofbirth=False)
        view = self.view()
        view.user = empty_user
        self.assertFalse(view.user_has_required_otos)

    def test__ckddetail(self):
        """Tests the ckddetail cached_property."""
        view = self.view()
        view.set_forms()
        self.assertTrue(view.ckddetail)

    def test__get_form_kwargs(self):
        # Create a fake request
        request = self.factory.get("/fake-url/")
        request.user = AnonymousUser()
        view = self.view()
        view.setup(request=request, pseudopatient=self.user.pk)
        view.set_forms()
        view.object = None
        form_kwargs = view.get_form_kwargs()
        self.assertIn("medallergys", form_kwargs)

    def test__goutdetail(self):
        """Tests the goutdetail cached_property."""
        self.assertFalse(self.view().goutdetail)

    def test__dispatch(self):
        """Test the dispatch() method for the view. Should redirect to Pseudopatient Update
        view when the user doesn't have the required 1to1 related models."""
        request = self.factory.get("/fake-url/")
        request.user = AnonymousUser()
        SessionMiddleware(dummy_get_response).process_request(request)
        kwargs = {"pseudopatient": self.user.pk}
        view = self.view()
        # https://stackoverflow.com/questions/33645780/how-to-unit-test-methods-inside-djangos-class-based-views
        view.setup(request, **kwargs)
        view.set_forms()
        response = view.dispatch(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(hasattr(view, "user"))
        self.assertEqual(view.user, self.user)
        self.assertTrue(hasattr(view, "object"))
        self.assertEqual(view.object, FlareAid.objects.get(user=self.user))
        # Create empty user and test that the view redirects to the user update view
        empty_user = create_psp()
        empty_user.dateofbirth.delete()
        create_flareaid(user=empty_user)
        self.client.force_login(empty_user)
        response = self.client.get(
            reverse("flareaids:pseudopatient-update", kwargs={"pseudopatient": empty_user.pk}), follow=True
        )
        self.assertRedirects(response, reverse("users:pseudopatient-update", kwargs={"pseudopatient": empty_user.pk}))
        message = list(response.context.get("messages"))[0]
        self.assertEqual(message.tags, "error")
        self.assertIn("is missing required information.", message.message)
        # Assert that requesting the view for a User w/o a FlareAid redirects to the create view
        user_no_flareaid = create_psp()
        self.client.force_login(user_no_flareaid)
        response = self.client.get(
            reverse("flareaids:pseudopatient-update", kwargs={"pseudopatient": user_no_flareaid.pk}), follow=True
        )
        self.assertRedirects(
            response, reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": user_no_flareaid.pk})
        )

    def test__get_object(self):
        """Test get_object() method."""

        request = self.factory.get("/fake-url/")
        kwargs = {"pseudopatient": self.user.pk}
        view = self.view()
        view.setup(request, **kwargs)
        view_obj = view.get_object()
        self.assertTrue(isinstance(view_obj, FlareAid))
        # Test that view sets the user attribute
        self.assertTrue(hasattr(view, "user"))
        self.assertEqual(view.user, self.user)
        # Repeat the test for a User w/o a FlareAid
        user_no_flareaid = create_psp()
        view = self.view()
        view.setup(request, pseudopatient=user_no_flareaid.pk)
        with self.assertRaises(ObjectDoesNotExist):
            view.get_object()

    def test__get_user_queryset(self):
        """Test the get_user_queryset() method for the view."""
        request = self.factory.get("/fake-url/")
        kwargs = {"pseudopatient": self.user.pk}
        view = self.view()
        view.setup(request, **kwargs)
        qs = view.get_user_queryset(view.kwargs["pseudopatient"])
        self.assertTrue(isinstance(qs, QuerySet))
        qs = qs.get()
        self.assertTrue(isinstance(qs, User))
        self.assertTrue(hasattr(qs, "medhistorys_qs"))
        self.assertTrue(hasattr(qs, "medallergys_qs"))
        self.assertTrue(hasattr(qs, "dateofbirth"))
        if hasattr(qs, "gender"):
            self.assertIn(qs.gender.value, Genders.values)

    def test__get_context_data_onetoones(self):
        """Test that the context data includes the user's
        related models."""
        for user in Pseudopatient.objects.select_related("pseudopatientprofile").all():
            request = self.factory.get("/fake-url/")
            if hasattr(user, "profile") and user.profile.provider:
                request.user = user.profile.provider
            else:
                request.user = self.anon_user
            SessionMiddleware(dummy_get_response).process_request(request)
            kwargs = {"pseudopatient": user.pk}
            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            assert "age" in response.context_data
            assert response.context_data["age"] == age_calc(user.dateofbirth.value)
            assert "gender" in response.context_data
            assert response.context_data["gender"] == user.gender.value

    def test__get_context_data_medhistorys(self):
        """Test that the context data includes the user's
        related models."""
        for user in Pseudopatient.objects.prefetch_related("medhistory_set").all():
            request = self.factory.get("/fake-url/")
            request.user = self.anon_user if not user.profile.provider else user.profile.provider
            SessionMiddleware(dummy_get_response).process_request(request)
            kwargs = {"pseudopatient": user.pk}
            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            for mh in user.medhistory_set.all():
                if mh.medhistorytype in FLAREAID_MEDHISTORYS:
                    assert f"{mh.medhistorytype}_form" in response.context_data
                    assert response.context_data[f"{mh.medhistorytype}_form"].instance == mh
                    assert (
                        response.context_data[
                            f"{mh.medhistorytype}_form"
                        ].instance._state.adding  # pylint: disable=w0212, line-too-long # noqa: E501
                        is False
                    )
                    assert response.context_data[f"{mh.medhistorytype}_form"].initial == {
                        f"{mh.medhistorytype}-value": True
                    }
                else:
                    assert f"{mh.medhistorytype}_form" not in response.context_data
            for mhtype in FLAREAID_MEDHISTORYS:
                assert f"{mhtype}_form" in response.context_data
                if mhtype not in user.medhistory_set.values_list("medhistorytype", flat=True):
                    assert (
                        response.context_data[f"{mhtype}_form"].instance._state.adding
                        is True  # pylint: disable=w0212, line-too-long # noqa: E501
                    )
                    assert response.context_data[f"{mhtype}_form"].initial == {f"{mhtype}-value": False}
            assert "ckddetail_form" in response.context_data
            if user.ckd:
                if getattr(user.ckd, "ckddetail", None):
                    assert response.context_data["ckddetail_form"].instance == user.ckd.ckddetail
                    assert (
                        response.context_data["ckddetail_form"].instance._state.adding is False
                    )  # pylint: disable=w0212, line-too-long # noqa: E501
                else:
                    assert (
                        response.context_data["ckddetail_form"].instance._state.adding is True
                    )  # pylint: disable=w0212, line-too-long # noqa: E501
                if getattr(user.ckd, "baselinecreatinine", None):
                    assert response.context_data["baselinecreatinine_form"].instance == user.ckd.baselinecreatinine
                    assert (
                        response.context_data["baselinecreatinine_form"].instance._state.adding is False
                    )  # pylint: disable=w0212, line-too-long # noqa: E501
                else:
                    assert (
                        response.context_data["baselinecreatinine_form"].instance._state.adding is True
                    )  # pylint: disable=w0212, line-too-long # noqa: E501
            else:
                assert (
                    response.context_data["ckddetail_form"].instance._state.adding is True
                )  # pylint: disable=w0212, line-too-long # noqa: E501
                assert (
                    response.context_data["baselinecreatinine_form"].instance._state.adding is True
                )  # pylint: disable=w0212, line-too-long # noqa: E501
            assert "goutdetail_form" not in response.context_data

    def test__get_context_data_medallergys(self):
        """Test that the context data includes the user's
        related models."""
        for user in Pseudopatient.objects.select_related("pseudopatientprofile").all():
            request = self.factory.get("/fake-url/")
            if hasattr(user, "profile") and user.profile.provider:
                request.user = user.profile.provider
            else:
                request.user = self.anon_user
            SessionMiddleware(dummy_get_response).process_request(request)
            kwargs = {"pseudopatient": user.pk}
            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            for ma in user.medallergy_set.filter(Q(treatment__in=FlarePpxChoices.values)).all():
                assert f"medallergy_{ma.treatment}_form" in response.context_data
                assert response.context_data[f"medallergy_{ma.treatment}_form"].instance == ma
                assert (
                    response.context_data[f"medallergy_{ma.treatment}_form"].instance._state.adding is False
                )  # pylint: disable=w0212, line-too-long # noqa: E501
                assert response.context_data[f"medallergy_{ma.treatment}_form"].initial == {
                    f"medallergy_{ma.treatment}": True,
                    f"{ma.treatment}_matype": None,
                }
            for treatment in FlarePpxChoices.values:
                assert f"medallergy_{treatment}_form" in response.context_data
                if treatment not in user.medallergy_set.values_list("treatment", flat=True):
                    assert (
                        response.context_data[f"medallergy_{treatment}_form"].instance._state.adding is True
                    )  # pylint: disable=w0212, line-too-long # noqa: E501
                    assert response.context_data[f"medallergy_{treatment}_form"].initial == {
                        f"medallergy_{treatment}": None,
                        f"{treatment}_matype": None,
                    }

    def test__post(self):
        """Test the post() method for the view."""
        request = self.factory.post("/fake-url/")
        if hasattr(self.user, "profile") and self.user.profile.provider:
            request.user = self.user.profile.provider
        else:
            request.user = self.anon_user
        SessionMiddleware(dummy_get_response).process_request(request)
        kwargs = {"pseudopatient": self.user.pk}
        response = self.view.as_view()(request, **kwargs)
        assert response.status_code == 200

    def test__post_updates_medhistorys(self):
        for mh in FLAREAID_MEDHISTORYS:
            setattr(self, f"{mh}_bool", self.psp.medhistory_set.filter(medhistorytype=mh).exists())
        data = flareaid_data_factory(self.psp)
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
            reverse("flareaids:pseudopatient-update", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302
        assert (
            response.url
            == f"{reverse('flareaids:pseudopatient-detail', kwargs={'pseudopatient': self.psp.pk})}?updated=True"
        )
        for mh in [mh for mh in FLAREAID_MEDHISTORYS if mh != MedHistoryTypes.CKD]:
            self.assertEqual(
                self.psp.medhistory_set.filter(medhistorytype=mh).exists(), not getattr(self, f"{mh}_bool")
            )

    def test__post_updates_medallergys(self):
        for ma in FlarePpxChoices.values:
            setattr(self, f"{ma}_bool", self.psp.medallergy_set.filter(treatment=ma).exists())
        data = flareaid_data_factory(self.psp)
        data.update(
            {
                **{f"medallergy_{ma}": not getattr(self, f"{ma}_bool") for ma in FlarePpxChoices.values},
            }
        )
        response = self.client.post(
            reverse("flareaids:pseudopatient-update", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302
        assert (
            response.url
            == f"{reverse('flareaids:pseudopatient-detail', kwargs={'pseudopatient': self.psp.pk})}?updated=True"
        )
        for ma in FlarePpxChoices.values:
            self.assertEqual(self.psp.medallergy_set.filter(treatment=ma).exists(), not getattr(self, f"{ma}_bool"))

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
            reverse("flareaids:pseudopatient-update", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        assert response.status_code == 302
        self.assertTrue(CkdDetail.objects.filter(medhistory=self.psp.ckd).exists())
        self.assertTrue(BaselineCreatinine.objects.filter(medhistory=self.psp.ckd).exists())

    def test__post_deletes_medhistorydetail(self):
        psp = create_psp()
        create_flareaid(user=psp)
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
        response = self.client.post(
            reverse("flareaids:pseudopatient-update", kwargs={"pseudopatient": psp.pk}), data=data
        )
        assert response.status_code == 302
        self.assertFalse(CkdDetail.objects.filter(medhistory=psp.ckd).exists())
        self.assertFalse(BaselineCreatinine.objects.filter(medhistory=psp.ckd).exists())

    def test__post_creates_flareaids_with_correct_recommendations(self):
        """Test that the view creates the User's FlareAid object with the correct
        recommendations."""
        for user in Pseudopatient.objects.select_related("pseudopatientprofile").all():
            if not hasattr(user, "flareaid"):
                create_flareaid(user=user)
            data = flareaid_data_factory(user)
            if hasattr(user, "profile") and user.profile.provider:
                self.client.force_login(user.profile.provider)
            response = self.client.post(
                reverse("flareaids:pseudopatient-update", kwargs={"pseudopatient": user.pk}), data=data
            )
            forms_print_response_errors(response)
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
        data = flareaid_data_factory(user=self.psp)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": False,
                "baselinecreatinine-value": Decimal("9.9"),
                "stage": Stages.ONE,
            }
        )
        response = self.client.post(
            reverse("flareaids:pseudopatient-update", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 200
        assert "form" in response.context_data
        assert "ckddetail_form" in response.context_data
        assert "stage" in response.context_data["ckddetail_form"].errors
        assert "baselinecreatinine_form" in response.context_data
        assert "value" in response.context_data["baselinecreatinine_form"].errors
        # Test that the view returns errors when CKD is True and dialysis is left blank
        data = flareaid_data_factory(user=self.psp)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": "",
            }
        )
        response = self.client.post(
            reverse("flareaids:pseudopatient-update", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        assert response.status_code == 200
        assert "ckddetail_form" in response.context_data
        assert "dialysis" in response.context_data["ckddetail_form"].errors

    def test__rules(self):
        """Test that django-rules permissions are set correctly and working for the view."""
        # Create a Provider and Admin, each with their own Pseudopatient + Flare
        provider = UserFactory()
        prov_psp = create_psp(provider=provider)
        create_flareaid(user=prov_psp)
        prov_psp_url = reverse("flareaids:pseudopatient-update", kwargs={"pseudopatient": prov_psp.pk})
        next_url = reverse("flareaids:pseudopatient-update", kwargs={"pseudopatient": prov_psp.pk})
        prov_psp_redirect_url = f"{reverse('account_login')}?next={next_url}"
        admin = AdminFactory()
        admin_psp = create_psp(provider=admin)
        create_flareaid(user=admin_psp)
        admin_psp_url = reverse("flareaids:pseudopatient-update", kwargs={"pseudopatient": admin_psp.pk})
        redirect_url = reverse("flareaids:pseudopatient-update", kwargs={"pseudopatient": admin_psp.pk})
        admin_psp_redirect_url = f"{reverse('account_login')}?next={redirect_url}"
        # Create an anonymous Pseudopatient + Flare
        anon_psp = create_psp()
        create_flareaid(user=anon_psp)
        anon_psp_url = reverse("flareaids:pseudopatient-update", kwargs={"pseudopatient": anon_psp.pk})
        # Test that an anonymous user who is not logged in can't see any Pseudopatient
        # with a provider but can see the anonymous Pseudopatient
        self.assertRedirects(self.client.get(prov_psp_url), prov_psp_redirect_url)
        self.assertRedirects(self.client.get(admin_psp_url), admin_psp_redirect_url)
        response = self.client.get(anon_psp_url)
        assert response.status_code == 200
        # Test that the Provider can access the view for his or her own Pseudopatient
        self.client.force_login(provider)
        response = self.client.get(prov_psp_url)
        assert response.status_code == 200
        # Test that the Provider can't access the view for the Admin's Pseudopatient
        response = self.client.get(admin_psp_url)
        assert response.status_code == 403
        # Test that the logged in Provider can see an anonymous Pseudopatient
        response = self.client.get(anon_psp_url)
        assert response.status_code == 200
        # Test that the Admin can access the view for his or her own Pseudopatient
        self.client.force_login(admin)
        response = self.client.get(admin_psp_url)
        assert response.status_code == 200
        # Test that the Admin can't access the view for the Provider's Pseudopatient
        response = self.client.get(prov_psp_url)
        assert response.status_code == 403
        # Test that the logged in Admin can see an anonymous Pseudopatient
        response = self.client.get(anon_psp_url)
        assert response.status_code == 200


class TestFlareAidDetail(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: FlareAidDetail = FlareAidDetail
        self.content_qs = Content.objects.filter(
            Q(tag=Tags.EXPLANATION) | Q(tag=Tags.WARNING), context=Content.Contexts.FLAREAID, slug__isnull=False
        ).all()
        self.flareaid = create_flareaid(mas=[], mhs=[])

    def test__dispatch_redirects_if_flareaid_user(self):
        """Test that the dispatch() method redirects to the Pseudopatient DetailView if the
        FlareAid has a user."""
        user_fa = create_flareaid(user=True)
        request = self.factory.get("/fake-url/")
        request.user = AnonymousUser()
        response = self.view.as_view()(request, pk=user_fa.pk)
        assert response.status_code == 302
        assert response.url == reverse("flareaids:pseudopatient-detail", kwargs={"pseudopatient": user_fa.user.pk})

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
        self.flareaid.medallergy_set.add(medallergy)
        request = self.factory.get(reverse("flareaids:detail", kwargs={"pk": self.flareaid.pk}))
        request.user = AnonymousUser()
        self.view.as_view()(request, pk=self.flareaid.pk)
        # This needs to be manually refetched from the db
        self.assertFalse(FlareAid.objects.get().recommendation[0] == Treatments.NAPROXEN)

    def test__get_object_does_not_update(self):
        self.assertTrue(self.flareaid.recommendation[0] == Treatments.NAPROXEN)
        medallergy = MedAllergyFactory(treatment=Treatments.NAPROXEN)
        self.flareaid.medallergy_set.add(medallergy)
        request = self.factory.get(reverse("flareaids:detail", kwargs={"pk": self.flareaid.pk}) + "?updated=True")
        request.user = AnonymousUser()
        self.view.as_view()(request, pk=self.flareaid.pk)
        # This needs to be manually refetched from the db
        self.assertTrue(FlareAid.objects.get().recommendation[0] == Treatments.NAPROXEN)


class TestFlareAidUpdate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: FlareAidUpdate = FlareAidUpdate
        self.anon_user = AnonymousUser()

    def test__dispatch_redirects_if_flareaid_user(self):
        """Test that the dispatch() method redirects to the Pseudopatient DetailView if the
        FlareAid has a user."""
        user_fa = create_flareaid(user=True)
        request = self.factory.get("/fake-url/")
        request.user = AnonymousUser()
        response = self.view.as_view()(request, pk=user_fa.pk)
        assert response.status_code == 302
        assert response.url == reverse("flareaids:pseudopatient-update", kwargs={"pseudopatient": user_fa.user.pk})

    def test__dispatch_returns_HttpResponse(self):
        """Test that the overwritten dispatch() method returns an HttpResponse."""
        fa = create_flareaid()
        request = self.factory.get("/fake-url/")
        request.user = AnonymousUser()
        SessionMiddleware(dummy_get_response).process_request(request)
        view = self.view()
        kwargs = {"pk": fa.pk}
        view.setup(request, **kwargs)
        response = view.dispatch(request, **kwargs)
        assert response.status_code == 200
        assert isinstance(response, HttpResponse)

    def test__post_unchanged_medallergys(self):
        flareaid = create_flareaid(mas=[Treatments.COLCHICINE])
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
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(flareaid.medallergy_set.filter(treatment=Treatments.COLCHICINE).exists())

    def test__post_add_medallergys(self):
        """Test that the view creates the User's MedAllergy object."""
        # Create a FlareAid with a single medallergy
        flareaid = create_flareaid(mas=[Treatments.COLCHICINE])

        # Count the medallergys
        ma_count = MedAllergy.objects.count()

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
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        self.assertTrue(flareaid.medallergy_set.filter(treatment=Treatments.PREDNISONE).exists())
        self.assertTrue(flareaid.medallergy_set.filter(treatment=Treatments.NAPROXEN).exists())
        self.assertEqual(MedAllergy.objects.count(), ma_count + 2)

    def test__post_delete_medallergys(self):
        """Test that the view deletes the User's MedAllergy object."""
        # Create a FlareAid and a MedAllergy
        flareaid = create_flareaid(mas=[Treatments.COLCHICINE])

        # Create fake data
        data = flareaid_data_factory()

        # Count the medallergy difference between the FlareAid and the data and the number of all medallergys
        ma_count = MedAllergy.objects.count()
        ma_diff = medallergy_diff_obj_data(obj=flareaid, data=data, medallergys=Treatments)

        # Post the data
        response = self.client.post(reverse("flareaids:update", kwargs={"pk": flareaid.pk}), data)
        self.assertEqual(response.status_code, 302)
        forms_print_response_errors(response)

        # Assert that the medallergy was deleted
        self.assertEqual(MedAllergy.objects.count(), ma_count + ma_diff)

    def test__post_unchanged_medhistorys(self):
        # Create a FlareAid with a single medhistory
        flareaid = create_flareaid(mhs=[MedHistoryTypes.COLCHICINEINTERACTION])

        # Create some fake data
        data = flareaid_data_factory()

        # Count medhistorys, medhistorys historys, and the anticipated change between the data and the current flareaid
        mh_count = MedHistory.objects.count()
        mh_diff = medhistory_diff_obj_data(obj=flareaid, data=data, medhistorys=FLAREAID_MEDHISTORYS)

        # POST the data
        response = self.client.post(reverse("flareaids:update", kwargs={"pk": flareaid.pk}), data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        # Assert that the medhistory number changed correctly
        self.assertEqual(MedHistory.objects.count(), mh_count + mh_diff)

    def test__post_delete_medhistorys(self):
        """Test that the view deletes the User's MedHistory object."""
        # Create a FlareAid and a MedHistory and add the new medhistory to the FlareAid
        flareaid = create_flareaid(mhs=[MedHistoryTypes.COLCHICINEINTERACTION])

        # Create fake data
        data = flareaid_data_factory()

        # Count the medhistorys and medhistorys.historys before post()
        mh_count = MedHistory.objects.count()
        mh_diff = medhistory_diff_obj_data(obj=flareaid, data=data, medhistorys=FLAREAID_MEDHISTORYS)

        # Post the data
        response = self.client.post(reverse("flareaids:update", kwargs={"pk": flareaid.pk}), data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        # Assert that the correct number of medhistorys were created/deleted
        self.assertEqual(MedHistory.objects.count(), mh_count + mh_diff)

    def test__post_add_medhistorys(self):
        """Test that the view adds the User's MedHistory object."""
        # Create a FlareAid and count its medhistorys
        flareaid = create_flareaid()

        # Create fake data
        data = flareaid_data_factory()

        # Count the medhistory difference between the FlareAid and the data and the number of all medhistorys
        mh_diff = medhistory_diff_obj_data(obj=flareaid, data=data, medhistorys=FLAREAID_MEDHISTORYS)
        mh_count = MedHistory.objects.count()

        # Post the data
        response = self.client.post(reverse("flareaids:update", kwargs={"pk": flareaid.pk}), data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        # Assert that the number of medhistorys was increased or decreased correctly by the view
        self.assertEqual(MedHistory.objects.count(), mh_count + mh_diff)
