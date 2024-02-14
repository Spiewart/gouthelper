from datetime import timedelta  # pylint: disable=E0015, E0013
from decimal import Decimal

import pytest  # pylint: disable=e0401 # type: ignore
from django.contrib.auth import get_user_model  # pylint: disable=e0401 # type: ignore
from django.contrib.auth.models import AnonymousUser  # pylint: disable=e0401 # type: ignore
from django.contrib.messages.middleware import MessageMiddleware  # pylint: disable=e0401 # type: ignore
from django.contrib.sessions.middleware import SessionMiddleware  # pylint: disable=e0401 # type: ignore
from django.core.exceptions import ObjectDoesNotExist  # pylint: disable=e0401 # type: ignore
from django.db.models import Q, QuerySet  # pylint: disable=e0401 # type: ignore
from django.http import HttpRequest, HttpResponse  # pylint: disable=e0401 # type: ignore
from django.test import RequestFactory, TestCase  # pylint: disable=e0401 # type: ignore
from django.urls import reverse  # pylint: disable=e0401 # type: ignore
from django.utils import timezone  # pylint: disable=e0401 # type: ignore

from ...contents.models import Content, Tags
from ...dateofbirths.helpers import age_calc
from ...genders.choices import Genders
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...labs.models import BaselineCreatinine
from ...labs.tests.factories import BaselineCreatinineFactory
from ...medallergys.models import MedAllergy
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
from ...medhistorydetails.models import CkdDetail
from ...medhistorydetails.tests.factories import create_ckddetail
from ...medhistorys.choices import Contraindications, MedHistoryTypes
from ...medhistorys.lists import PPXAID_MEDHISTORYS
from ...medhistorys.models import MedHistory
from ...medhistorys.tests.factories import MedHistoryFactory
from ...treatments.choices import ColchicineDoses, FlarePpxChoices, Freqs, NsaidChoices, Treatments
from ...users.models import Pseudopatient
from ...users.tests.factories import AdminFactory, UserFactory, create_psp
from ...utils.helpers.test_helpers import (
    form_data_colchicine_contra,
    form_data_nsaid_contra,
    medhistory_diff_obj_data,
    tests_print_response_form_errors,
)
from ..models import PpxAid
from ..selectors import ppxaid_user_qs
from ..views import (
    PpxAidAbout,
    PpxAidCreate,
    PpxAidDetail,
    PpxAidPseudopatientCreate,
    PpxAidPseudopatientDetail,
    PpxAidPseudopatientUpdate,
    PpxAidUpdate,
)
from .factories import create_ppxaid, ppxaid_data_factory

User = get_user_model()


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
        PPXAID_MEDHISTORYS = ppxaid.medhistory_set.all()
        stroke = MedHistory.objects.order_by("created").filter(medhistorytype=MedHistoryTypes.STROKE).last()
        diabetes = MedHistory.objects.order_by("created").filter(medhistorytype=MedHistoryTypes.DIABETES).last()
        self.assertIn(stroke, PPXAID_MEDHISTORYS)
        self.assertIn(diabetes, PPXAID_MEDHISTORYS)

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
        self.ppxaid = create_ppxaid()

    def test__contents(self):
        self.assertTrue(self.view().contents)
        self.assertTrue(isinstance(self.view().contents, QuerySet))
        for content in self.view().contents:
            self.assertIn(content, self.content_qs)
        for content in self.content_qs:
            self.assertIn(content, self.view().contents)

    def test__dispatch_redirects_if_flareaid_user(self):
        """Test that the dispatch() method redirects to the Pseudopatient DetailView if the
        PpxAid has a user."""
        user_fa = create_ppxaid(user=True)
        request = self.factory.get("/fake-url/")
        request.user = AnonymousUser()
        response = self.view.as_view()(request, pk=user_fa.pk)
        assert response.status_code == 302
        assert response.url == reverse("ppxaids:pseudopatient-detail", kwargs={"username": user_fa.user.username})

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
        request.user = AnonymousUser()
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
        request.user = AnonymousUser()
        self.view.as_view()(request, pk=self.ppxaid.pk)
        # This needs to be manually refetched from the db
        self.assertTrue(PpxAid.objects.order_by("created").last().recommendation[0] == Treatments.NAPROXEN)

        # Call without the updated=True query param and assert that the recommendation has been updated
        request = self.factory.get(reverse("ppxaids:detail", kwargs={"pk": ppxaid.pk}))
        request.user = AnonymousUser()
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

    def test__dispatch_redirects_if_flareaid_user(self):
        """Test that the dispatch() method redirects to the Pseudopatient DetailView if the
        FlareAid has a user."""
        user_fa = create_ppxaid(user=True)
        request = self.factory.get("/fake-url/")
        request.user = AnonymousUser()
        response = self.view.as_view()(request, pk=user_fa.pk)
        assert response.status_code == 302
        assert response.url == reverse("ppxaids:pseudopatient-update", kwargs={"username": user_fa.user.username})

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


class TestPpxAidPseudopatientCreate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = PpxAidPseudopatientCreate
        self.anon_user = AnonymousUser()
        self.user = create_psp(plus=True)
        for _ in range(10):
            create_psp(plus=True)
        self.psp = create_psp()

    def test__check_user_onetoones(self):
        """Tests that the view checks for the User's related models."""
        empty_user = create_psp(dateofbirth=False, gender=False)
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
        request.user = self.anon_user
        view = self.view(request=request)

        # Set the user on the view, as this would be done by dispatch()
        view.user = self.psp
        view.setup(request, username=self.psp.username)
        view.object = view.get_object()

        # Call the get_form_kwargs() method and assert that the correct kwargs are returned
        form_kwargs = view.get_form_kwargs()
        self.assertIn("medallergys", form_kwargs)
        self.assertEqual(form_kwargs["medallergys"], view.medallergys)
        self.assertIn("patient", form_kwargs)
        self.assertTrue(form_kwargs["patient"])

    def test__goutdetail(self):
        """Tests the goutdetail cached_property."""
        self.assertFalse(self.view().goutdetail)

    def test__dispatch(self):
        """Test the dispatch() method for the view. Should redirect to detailview when
        the user already has a PpxAid. Should redirect to Pseudopatient Update
        view when the user doesn't have the required 1to1 related models."""
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        kwargs = {"username": self.user.username}
        view = self.view()
        # https://stackoverflow.com/questions/33645780/how-to-unit-test-methods-inside-djangos-class-based-views
        view.setup(request, **kwargs)
        response = view.dispatch(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(hasattr(view, "user"))
        self.assertEqual(view.user, self.user)
        # Create a new PpxAid and test that the view redirects to the detailview
        create_ppxaid(user=self.user)
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("ppxaids:pseudopatient-create", kwargs={"username": self.user.username}), follow=True
        )
        self.assertEqual(view.user, self.user)
        self.assertRedirects(
            response, reverse("ppxaids:pseudopatient-update", kwargs={"username": self.user.username})
        )
        # Check that the response message is correct
        message = list(response.context.get("messages"))[0]
        self.assertEqual(message.tags, "error")
        self.assertEqual(message.message, f"{self.user} already has a PpxAid. Please update it instead.")
        # Create empty user and test that the view redirects to the user update view
        empty_user = create_psp(dateofbirth=False, ethnicity=False, gender=False)
        self.client.force_login(empty_user)
        response = self.client.get(
            reverse("ppxaids:pseudopatient-create", kwargs={"username": empty_user.username}), follow=True
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
        """Test that the context data includes the user's related models."""
        for user in Pseudopatient.objects.all():
            request = self.factory.get("/fake-url/")
            if user.profile.provider:
                request.user = user.profile.provider
            else:
                request.user = self.anon_user
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
            if user.profile.provider:
                request.user = user.profile.provider
            else:
                request.user = self.anon_user
            kwargs = {"username": user.username}
            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            for mh in user.medhistory_set.all():
                if mh.medhistorytype in PPXAID_MEDHISTORYS:
                    assert f"{mh.medhistorytype}_form" in response.context_data
                    assert response.context_data[f"{mh.medhistorytype}_form"].instance == mh
                    assert (
                        response.context_data[f"{mh.medhistorytype}_form"].instance._state.adding
                        is False  # pylint: disable=w0212, line-too-long # noqa: E501
                    )
                    assert response.context_data[f"{mh.medhistorytype}_form"].initial == {
                        f"{mh.medhistorytype}-value": True
                    }
                else:
                    assert f"{mh.medhistorytype}_form" not in response.context_data
            for mhtype in PPXAID_MEDHISTORYS:
                assert f"{mhtype}_form" in response.context_data
                if mhtype not in user.medhistory_set.values_list("medhistorytype", flat=True):
                    assert (
                        response.context_data[
                            f"{mhtype}_form"
                        ].instance._state.adding  # pylint: disable=w0212, line-too-long # noqa: E501
                        is True
                    )
                    assert response.context_data[f"{mhtype}_form"].initial == {f"{mhtype}-value": None}
            assert "ckddetail_form" in response.context_data
            if user.ckd:
                if getattr(user.ckd, "ckddetail", None):
                    assert response.context_data["ckddetail_form"].instance == user.ckd.ckddetail
                    assert (
                        response.context_data[
                            "ckddetail_form"
                        ].instance._state.adding  # pylint: disable=w0212, line-too-long # noqa: E501
                        is False
                    )
                else:
                    assert (
                        response.context_data[
                            "ckddetail_form"
                        ].instance._state.adding  # pylint: disable=w0212, line-too-long # noqa: E501
                        is True
                    )
                if getattr(user.ckd, "baselinecreatinine", None):
                    assert response.context_data["baselinecreatinine_form"].instance == user.ckd.baselinecreatinine
                    assert (
                        response.context_data[
                            "baselinecreatinine_form"
                        ].instance._state.adding  # pylint: disable=w0212, line-too-long # noqa: E501
                        is False
                    )
                else:
                    assert (
                        response.context_data[
                            "baselinecreatinine_form"
                        ].instance._state.adding  # pylint: disable=w0212, line-too-long # noqa: E501
                        is True
                    )
            else:
                assert (
                    response.context_data[
                        "ckddetail_form"
                    ].instance._state.adding  # pylint: disable=w0212, line-too-long # noqa: E501
                    is True
                )
                assert (
                    response.context_data[
                        "baselinecreatinine_form"
                    ].instance._state.adding  # pylint: disable=w0212, line-too-long # noqa: E501
                    is True
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
            kwargs = {"username": user.username}
            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            for ma in user.medallergy_set.filter(Q(treatment__in=FlarePpxChoices.values)).all():
                assert f"medallergy_{ma.treatment}_form" in response.context_data
                assert response.context_data[f"medallergy_{ma.treatment}_form"].instance == ma
                assert (
                    response.context_data[
                        f"medallergy_{ma.treatment}_form"
                    ].instance._state.adding  # pylint: disable=w0212, line-too-long # noqa: E501
                    is False
                )
                assert response.context_data[f"medallergy_{ma.treatment}_form"].initial == {
                    f"medallergy_{ma.treatment}": True
                }
            for treatment in FlarePpxChoices.values:
                assert f"medallergy_{treatment}_form" in response.context_data
                if treatment not in user.medallergy_set.values_list("treatment", flat=True):
                    assert (
                        response.context_data[
                            f"medallergy_{treatment}_form"
                        ].instance._state.adding  # pylint: disable=w0212, line-too-long # noqa: E501
                        is True
                    )
                    assert response.context_data[f"medallergy_{treatment}_form"].initial == {
                        f"medallergy_{treatment}": None
                    }

    def test__get_permission_object(self):
        """Test the get_permission_object() method for the view."""
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        kwargs = {"username": self.user.username}
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
        kwargs = {"username": self.user.username}
        response = self.view.as_view()(request, **kwargs)
        assert response.status_code == 200

    def test__post_sets_object_user(self):
        """Test that the post() method for the view sets the
        user on the object."""
        # Create some fake data for a User's PpxAid
        data = ppxaid_data_factory(user=self.user)
        response = self.client.post(
            reverse("ppxaids:pseudopatient-create", kwargs={"username": self.user.username}), data=data
        )
        tests_print_response_form_errors(response)
        assert response.status_code == 302
        assert PpxAid.objects.filter(user=self.user).exists()
        ppxaid = PpxAid.objects.last()
        assert ppxaid.user
        assert ppxaid.user == self.user

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
        mh_diff = medhistory_diff_obj_data(self.psp, data, PPXAID_MEDHISTORYS)
        response = self.client.post(
            reverse("ppxaids:pseudopatient-create", kwargs={"username": self.psp.username}), data=data
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
            reverse("ppxaids:pseudopatient-create", kwargs={"username": self.psp.username}), data=data
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
            reverse("ppxaids:pseudopatient-create", kwargs={"username": self.psp.username}), data=data
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
            reverse("ppxaids:pseudopatient-create", kwargs={"username": self.psp.username}), data=data
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
            reverse("ppxaids:pseudopatient-create", kwargs={"username": self.psp.username}), data=data
        )
        assert response.status_code == 302
        self.assertTrue(CkdDetail.objects.filter(medhistory=self.psp.ckd).exists())
        self.assertTrue(BaselineCreatinine.objects.filter(medhistory=self.psp.ckd).exists())

    def test__post_deletes_medhistorydetail(self):
        ckd = MedHistoryFactory(user=self.psp, medhistorytype=MedHistoryTypes.CKD)
        create_ckddetail(
            medhistory=self.psp.ckd,
            on_dialysis=False,
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
            reverse("ppxaids:pseudopatient-create", kwargs={"username": self.psp.username}), data=data
        )
        assert response.status_code == 302
        self.assertFalse(CkdDetail.objects.filter(medhistory=self.psp.ckd).exists())
        self.assertFalse(BaselineCreatinine.objects.filter(medhistory=self.psp.ckd).exists())

    def test__post_creates_ppxaids_with_correct_recommendations(self):
        """Test that the view creates the User's PpxAid object with the correct
        recommendations."""
        for user in Pseudopatient.objects.all():
            data = ppxaid_data_factory(user)
            if user.profile.provider:
                self.client.force_login(user.profile.provider)
            response = self.client.post(
                reverse("ppxaids:pseudopatient-create", kwargs={"username": user.username}), data=data
            )
            tests_print_response_form_errors(response)
            assert response.status_code == 302
            # Get the PpxAid
            ppxaid = PpxAid.objects.get(user=user)
            # Test the PpxAid logic on the recommendations and options for the PpxAid
            # Check NSAID contraindications first
            if form_data_nsaid_contra(data=data):
                for nsaid in NsaidChoices.values:
                    assert nsaid not in ppxaid.recommendation and nsaid not in ppxaid.options
            # Check colchicine contraindications
            colch_contra = form_data_colchicine_contra(data=data, user=user)
            if colch_contra is not None:
                if colch_contra == Contraindications.ABSOLUTE or colch_contra == Contraindications.RELATIVE:
                    assert Treatments.COLCHICINE not in ppxaid.recommendation if ppxaid.recommendation else True
                    assert Treatments.COLCHICINE not in ppxaid.options if ppxaid.options else True
                elif colch_contra == Contraindications.DOSEADJ:
                    assert Treatments.COLCHICINE in ppxaid.options if ppxaid.options else True
                    assert (
                        ppxaid.options[Treatments.COLCHICINE]["dose"] == ColchicineDoses.POINTTHREE
                        if ppxaid.options
                        else True
                    )
                    assert ppxaid.options[Treatments.COLCHICINE]["freq"] == Freqs.QDAY if ppxaid.options else True
            else:
                assert Treatments.COLCHICINE in ppxaid.options
                assert ppxaid.options[Treatments.COLCHICINE]["dose"] == ColchicineDoses.POINTSIX
                assert ppxaid.options[Treatments.COLCHICINE]["freq"] == Freqs.QDAY

    def test__post_returns_errors(self):
        """Test that post returns errors for some common scenarios where the
        data is invalid. Typically, these are scenarios that should be prevented by
        the form or javascript."""
        # Test that the view returns errors when the baselinecreatinine and
        # stage are not congruent
        data = ppxaid_data_factory(user=self.psp)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": False,
                "baselinecreatinine-value": Decimal("9.9"),
                "stage": Stages.ONE,
            }
        )
        response = self.client.post(
            reverse("ppxaids:pseudopatient-create", kwargs={"username": self.psp.username}), data=data
        )
        assert response.status_code == 200
        assert "form" in response.context_data
        assert "ckddetail_form" in response.context_data
        assert "stage" in response.context_data["ckddetail_form"].errors
        assert "baselinecreatinine_form" in response.context_data
        assert "value" in response.context_data["baselinecreatinine_form"].errors
        # Test that the view returns errors when CKD is True and dialysis is left blank
        data = ppxaid_data_factory(user=self.psp)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": "",
            }
        )
        response = self.client.post(
            reverse("ppxaids:pseudopatient-create", kwargs={"username": self.psp.username}), data=data
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
        # Test that any User can create an anonymous Pseudopatient's PpxAid
        response = self.client.get(reverse("ppxaids:pseudopatient-create", kwargs={"username": psp.username}))
        assert response.status_code == 200
        # Test that an anonymous User can't create a Provider's PpxAid
        response = self.client.get(reverse("ppxaids:pseudopatient-create", kwargs={"username": provider_psp.username}))
        # 302 because PermissionDenied will redirect to the login page
        assert response.status_code == 302
        # Test that an anonymous User can't create an Admin's PpxAid
        response = self.client.get(reverse("ppxaids:pseudopatient-create", kwargs={"username": admin_psp.username}))
        # Test that a Provider can create his or her own Pseudopatient's PpxAid
        response = self.client.get(
            reverse("ppxaids:pseudopatient-create", kwargs={"username": psp.username}),
        )
        assert response.status_code == 200
        # Test that a Provider can create an anonymous Pseudopatient's PpxAid
        response = self.client.get(
            reverse("ppxaids:pseudopatient-create", kwargs={"username": psp.username}),
        )
        assert response.status_code == 200
        self.client.force_login(admin)
        response = self.client.get(
            reverse("ppxaids:pseudopatient-create", kwargs={"username": admin_psp.username}),
        )
        assert response.status_code == 200
        # Test that only a Pseudopatient's Provider can add their PpxAid if they have a Provider
        response = self.client.get(
            reverse("ppxaids:pseudopatient-create", kwargs={"username": provider_psp.username}),
        )
        assert response.status_code == 403
        self.client.force_login(provider)
        # Test that a Provider can't create another provider's Pseudopatient's PpxAid
        response = self.client.get(
            reverse("ppxaids:pseudopatient-create", kwargs={"username": admin_psp.username}),
        )
        assert response.status_code == 403
        self.client.force_login(admin)
        # Test that an Admin can create an anonymous Pseudopatient's PpxAid
        response = self.client.get(
            reverse("ppxaids:pseudopatient-create", kwargs={"username": psp.username}),
        )
        assert response.status_code == 200


class TestppxaidPseudopatientDetail(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = PpxAidPseudopatientDetail
        self.anon_user = AnonymousUser()
        self.psp = create_psp(plus=True)
        for psp in Pseudopatient.objects.all():
            create_ppxaid(user=psp)
        self.empty_psp = create_psp(plus=True)

    def dummy_get_response(self, request: HttpRequest):
        return None

    def test__dispatch(self):
        """Test the dispatch() method for the view. Should redirect to Pseudopatient Update
        view when the user doesn't have the required 1to1 related models."""
        response = self.client.get(reverse("ppxaids:pseudopatient-detail", kwargs={"username": self.psp.username}))
        self.assertEqual(response.status_code, 200)
        # Test that dispatch redirects to the pseudopatient-create PpxAid view when the user doesn't have a PpxAid
        self.assertRedirects(
            self.client.get(reverse("ppxaids:pseudopatient-detail", kwargs={"username": self.empty_psp.username})),
            reverse("ppxaids:pseudopatient-create", kwargs={"username": self.empty_psp.username}),
        )
        self.psp.dateofbirth.delete()
        # Test that dispatch redirects to the User Update view when the user doesn't have a dateofbirth
        self.assertRedirects(
            self.client.get(
                reverse("ppxaids:pseudopatient-detail", kwargs={"username": self.psp.username}),
            ),
            reverse("users:pseudopatient-update", kwargs={"username": self.psp.username}),
        )

    def test__assign_ppxaid_attrs_from_user(self):
        """Test that the assign_ppxaid_attrs_from_user() method for the view
        transfers attributes from the QuerySet, which started with a User,
        to the PpxAid object."""
        ppxaid = PpxAid.objects.get(user=self.psp)
        view = self.view()
        request = self.factory.get("/fake-url/")
        view.setup(request, username=self.psp.username)
        assert not getattr(ppxaid, "dateofbirth")
        assert not getattr(ppxaid, "gender")
        assert not hasattr(ppxaid, "medhistorys_qs")
        assert not hasattr(ppxaid, "medallergys_qs")
        view.assign_ppxaid_attrs_from_user(ppxaid=ppxaid, user=ppxaid_user_qs(self.psp.username).get())
        assert getattr(ppxaid, "dateofbirth") == self.psp.dateofbirth
        assert getattr(ppxaid, "gender") == self.psp.gender
        assert hasattr(ppxaid, "medhistorys_qs")
        assert hasattr(ppxaid, "medallergys_qs")

    def test__rules(self):
        psp = create_psp()
        create_ppxaid(user=psp)
        provider = UserFactory()
        provider_psp = create_psp(provider=provider)
        create_ppxaid(user=provider_psp)
        admin = AdminFactory()
        admin_psp = create_psp(provider=admin)
        create_ppxaid(user=admin_psp)
        # Test that any User can view an anonymous Pseudopatient's PpxAid
        response = self.client.get(reverse("ppxaids:pseudopatient-detail", kwargs={"username": psp.username}))
        assert response.status_code == 200
        # Test that an anonymous User can't view a Provider's PpxAid
        response = self.client.get(reverse("ppxaids:pseudopatient-detail", kwargs={"username": provider_psp.username}))
        # 302 because PermissionDenied will redirect to the login page
        assert response.status_code == 302
        # Test that an anonymous User can't view an Admin's PpxAid
        response = self.client.get(reverse("ppxaids:pseudopatient-detail", kwargs={"username": admin_psp.username}))
        assert response.status_code == 302
        # Test that a Provider can view their own Pseudoatient's PpxAid
        self.client.force_login(provider)
        response = self.client.get(
            reverse("ppxaids:pseudopatient-detail", kwargs={"username": provider_psp.username}),
        )
        assert response.status_code == 200
        # Test that a Provider can view an anonymous Pseudopatient's PpxAid
        response = self.client.get(
            reverse("ppxaids:pseudopatient-detail", kwargs={"username": psp.username}),
        )
        assert response.status_code == 200
        # Test that Provider can't view Admin's Pseudopatient's PpxAid
        response = self.client.get(
            reverse("ppxaids:pseudopatient-detail", kwargs={"username": admin_psp.username}),
        )
        assert response.status_code == 403
        self.client.force_login(admin)
        # Test that an Admin can view their own Pseudopatient's PpxAid
        response = self.client.get(
            reverse("ppxaids:pseudopatient-detail", kwargs={"username": admin_psp.username}),
        )
        assert response.status_code == 200
        # Test that an Admin can view an anonymous Pseudopatient's PpxAid
        response = self.client.get(
            reverse("ppxaids:pseudopatient-detail", kwargs={"username": psp.username}),
        )
        assert response.status_code == 200
        # Test that Admin can't view Provider's Pseudopatient's PpxAid
        response = self.client.get(
            reverse("ppxaids:pseudopatient-detail", kwargs={"username": provider_psp.username}),
        )
        assert response.status_code == 403

    def test__get_object_sets_user(self):
        """Test that the get_object() method sets the user attribute."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, username=self.psp.username)
        view.get_object()
        assert hasattr(view, "user")
        assert view.user == self.psp

    def test__get_object_raises_DoesNotExist(self):
        """Test that the get_object() method raises DoesNotExist when the user
        doesn't have a PpxAid."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, username=self.empty_psp.username)
        with self.assertRaises(ObjectDoesNotExist):
            view.get_object()

    def test__get_object_assigns_user_qs_attrs_to_ppxaid(self):
        """Test that the get_object method transfers required attributes from the
        User QuerySet to the PpxAid object."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, username=self.psp.username)
        ppxaid = view.get_object()
        assert hasattr(ppxaid, "dateofbirth")
        assert getattr(ppxaid, "dateofbirth") == view.user.dateofbirth
        assert hasattr(ppxaid, "gender")
        assert getattr(ppxaid, "gender") == view.user.gender
        assert hasattr(ppxaid, "medhistorys_qs")
        assert getattr(ppxaid, "medhistorys_qs") == view.user.medhistorys_qs
        assert hasattr(ppxaid, "medallergys_qs")
        assert getattr(ppxaid, "medallergys_qs") == view.user.medallergys_qs

    def test__get_permission_object(self):
        """Test that the get_permission_object() method returns the
        view's object, which must have already been set."""
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = self.view()
        view.setup(request, username=self.psp.username)
        view.dispatch(request, username=self.psp.username)
        pm_obj = view.get_permission_object()
        assert pm_obj == view.object

    def test__get_queryset(self):
        """Test the get_queryset() method for the view."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, username=self.psp.username)
        with self.assertNumQueries(3):
            qs = view.get_queryset().get()
        assert qs == self.psp
        assert hasattr(qs, "ppxaid") and qs.ppxaid == self.psp.ppxaid
        assert hasattr(qs, "dateofbirth") and qs.dateofbirth == self.psp.dateofbirth
        if hasattr(qs, "gender"):
            assert qs.gender == self.psp.gender
        assert hasattr(qs, "medhistorys_qs")
        psp_mhs = self.psp.medhistory_set.filter(medhistorytype__in=PPXAID_MEDHISTORYS).all()
        for mh in qs.medhistorys_qs:
            assert mh in psp_mhs
        assert hasattr(qs, "medallergys_qs")
        psp_mas = self.psp.medallergy_set.filter(treatment__in=FlarePpxChoices.values).all()
        for ma in qs.medallergys_qs:
            assert ma in psp_mas

    def test__get_updates_ppxaid(self):
        """Test that the get method updates the object when called with the
        correct url parameters."""
        psp = create_psp()
        ppxaid = create_ppxaid(user=psp)
        self.assertIn(Treatments.COLCHICINE, ppxaid.options)
        medallergy = MedAllergyFactory(treatment=Treatments.COLCHICINE, user=psp)
        self.assertIn(medallergy, psp.medallergy_set.all())
        self.client.get(reverse("ppxaids:pseudopatient-detail", kwargs={"username": psp.username}))
        # This needs to be manually refetched from the db
        self.assertNotIn(Treatments.COLCHICINE, PpxAid.objects.get(user=psp).options)

    def test__get_does_not_update_ppxaid(self):
        """Test that the get method doesn't update the object when called with the
        ?updated=True url parameter."""
        psp = create_psp()
        ppxaid = create_ppxaid(user=psp)
        self.assertIn(Treatments.COLCHICINE, ppxaid.options)
        medallergy = MedAllergyFactory(treatment=Treatments.COLCHICINE, user=psp)
        self.assertIn(medallergy, psp.medallergy_set.all())
        self.client.get(reverse("ppxaids:pseudopatient-detail", kwargs={"username": psp.username}) + "?updated=True")
        # This needs to be manually refetched from the db
        self.assertIn(Treatments.COLCHICINE, PpxAid.objects.get(user=psp).options)


class TestppxaidPseudopatientUpdate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = PpxAidPseudopatientUpdate
        self.anon_user = AnonymousUser()
        self.user = create_psp(plus=True)
        for _ in range(10):
            create_psp(plus=True)
        self.psp = create_psp()
        for psp in Pseudopatient.objects.all():
            create_ppxaid(user=psp)

    def test__check_user_onetoones(self):
        """Tests that the view checks for the User's related models."""
        empty_user = create_psp(dateofbirth=False)
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
        view.setup(request, username=self.user.username)
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
        kwargs = {"username": self.user.username}
        view = self.view()
        # https://stackoverflow.com/questions/33645780/how-to-unit-test-methods-inside-djangos-class-based-views
        view.setup(request, **kwargs)
        response = view.dispatch(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(hasattr(view, "user"))
        self.assertEqual(view.user, self.user)
        self.assertTrue(hasattr(view, "object"))
        self.assertEqual(view.object, PpxAid.objects.get(user=self.user))
        # Create empty user and test that the view redirects to the user update view
        empty_user = create_psp()
        empty_user.dateofbirth.delete()
        create_ppxaid(user=empty_user)
        self.client.force_login(empty_user)
        response = self.client.get(
            reverse("ppxaids:pseudopatient-update", kwargs={"username": empty_user.username}), follow=True
        )
        self.assertRedirects(response, reverse("users:pseudopatient-update", kwargs={"username": empty_user.username}))
        message = list(response.context.get("messages"))[0]
        self.assertEqual(message.tags, "error")
        self.assertEqual(
            message.message, "Baseline information is needed to use GoutHelper Decision and Treatment Aids."
        )
        # Assert that requesting the view for a User w/o a PpxAid redirects to the create view
        user_no_ppxaid = create_psp()
        self.client.force_login(user_no_ppxaid)
        response = self.client.get(
            reverse("ppxaids:pseudopatient-update", kwargs={"username": user_no_ppxaid.username}), follow=True
        )
        self.assertRedirects(
            response, reverse("ppxaids:pseudopatient-create", kwargs={"username": user_no_ppxaid.username})
        )

    def test__get_object(self):
        """Test get_object() method."""

        request = self.factory.get("/fake-url/")
        kwargs = {"username": self.user.username}
        view = self.view()
        view.setup(request, **kwargs)
        view_obj = view.get_object()
        self.assertTrue(isinstance(view_obj, PpxAid))
        # Test that view sets the user attribute
        self.assertTrue(hasattr(view, "user"))
        self.assertEqual(view.user, self.user)
        # Repeat the test for a User w/o a PpxAid
        user_no_ppxaid = create_psp()
        view = self.view()
        view.setup(request, username=user_no_ppxaid.username)
        with self.assertRaises(ObjectDoesNotExist):
            view.get_object()

    def test__get_user_queryset(self):
        """Test the get_user_queryset() method for the view."""
        request = self.factory.get("/fake-url/")
        kwargs = {"username": self.user.username}
        view = self.view()
        view.setup(request, **kwargs)
        qs = view.get_user_queryset(view.kwargs["username"])
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
        for user in Pseudopatient.objects.prefetch_related("medhistory_set").all():
            request = self.factory.get("/fake-url/")
            request.user = self.anon_user if not user.profile.provider else user.profile.provider
            kwargs = {"username": user.username}
            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            for mh in user.medhistory_set.all():
                if mh.medhistorytype in PPXAID_MEDHISTORYS:
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
            for mhtype in PPXAID_MEDHISTORYS:
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
            kwargs = {"username": user.username}
            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            for ma in user.medallergy_set.filter(Q(treatment__in=FlarePpxChoices.values)).all():
                assert f"medallergy_{ma.treatment}_form" in response.context_data
                assert response.context_data[f"medallergy_{ma.treatment}_form"].instance == ma
                assert (
                    response.context_data[f"medallergy_{ma.treatment}_form"].instance._state.adding is False
                )  # pylint: disable=w0212, line-too-long # noqa: E501
                assert response.context_data[f"medallergy_{ma.treatment}_form"].initial == {
                    f"medallergy_{ma.treatment}": True
                }
            for treatment in FlarePpxChoices.values:
                assert f"medallergy_{treatment}_form" in response.context_data
                if treatment not in user.medallergy_set.values_list("treatment", flat=True):
                    assert (
                        response.context_data[f"medallergy_{treatment}_form"].instance._state.adding is True
                    )  # pylint: disable=w0212, line-too-long # noqa: E501
                    assert response.context_data[f"medallergy_{treatment}_form"].initial == {
                        f"medallergy_{treatment}": None
                    }

    def test__post(self):
        """Test the post() method for the view."""
        request = self.factory.post("/fake-url/")
        if hasattr(self.user, "profile") and self.user.profile.provider:
            request.user = self.user.profile.provider
        else:
            request.user = self.anon_user
        kwargs = {"username": self.user.username}
        response = self.view.as_view()(request, **kwargs)
        assert response.status_code == 200

    def test__post_updates_medhistorys(self):
        psp = Pseudopatient.objects.last()
        for mh in PPXAID_MEDHISTORYS:
            setattr(self, f"{mh}_bool", psp.medhistory_set.filter(medhistorytype=mh).exists())
        data = ppxaid_data_factory(psp)
        data.update(
            {
                **{
                    f"{mh}-value": not getattr(self, f"{mh}_bool")
                    for mh in PPXAID_MEDHISTORYS
                    # Need to exclude CKD because of related CkdDetail fields throwing errors
                    if mh != MedHistoryTypes.CKD
                },
            }
        )
        response = self.client.post(
            reverse("ppxaids:pseudopatient-update", kwargs={"username": self.psp.username}), data=data
        )
        tests_print_response_form_errors(response)
        assert response.status_code == 302
        assert (
            response.url
            == f"{reverse('ppxaids:pseudopatient-detail', kwargs={'username': self.psp.username})}?updated=True"
        )
        for mh in [mh for mh in PPXAID_MEDHISTORYS if mh != MedHistoryTypes.CKD]:
            self.assertEqual(psp.medhistory_set.filter(medhistorytype=mh).exists(), not getattr(self, f"{mh}_bool"))

    def test__post_updates_medallergys(self):
        psp = Pseudopatient.objects.last()
        for ma in FlarePpxChoices.values:
            setattr(self, f"{ma}_bool", psp.medallergy_set.filter(treatment=ma).exists())
        data = ppxaid_data_factory(psp)
        data.update(
            {
                **{f"medallergy_{ma}": not getattr(self, f"{ma}_bool") for ma in FlarePpxChoices.values},
            }
        )
        response = self.client.post(
            reverse("ppxaids:pseudopatient-update", kwargs={"username": self.psp.username}), data=data
        )
        tests_print_response_form_errors(response)
        assert response.status_code == 302
        assert (
            response.url
            == f"{reverse('ppxaids:pseudopatient-detail', kwargs={'username': self.psp.username})}?updated=True"
        )
        for ma in FlarePpxChoices.values:
            self.assertEqual(psp.medallergy_set.filter(treatment=ma).exists(), not getattr(self, f"{ma}_bool"))

    def test__post_creates_medhistorydetails(self):
        """Test that the view creates the User's MedHistoryDetails objects."""
        # Create user without ckd
        psp = create_psp()
        create_ppxaid(user=psp)
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
            reverse("ppxaids:pseudopatient-update", kwargs={"username": self.psp.username}), data=data
        )
        assert response.status_code == 302
        self.assertTrue(CkdDetail.objects.filter(medhistory=self.psp.ckd).exists())
        self.assertTrue(BaselineCreatinine.objects.filter(medhistory=self.psp.ckd).exists())

    def test__post_deletes_medhistorydetail(self):
        psp = create_psp()
        create_ppxaid(user=psp)
        ckd = MedHistoryFactory(user=psp, medhistorytype=MedHistoryTypes.CKD)
        create_ckddetail(
            medhistory=psp.ckd,
            on_dialysis=False,
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
            reverse("ppxaids:pseudopatient-update", kwargs={"username": psp.username}), data=data
        )
        assert response.status_code == 302
        self.assertFalse(CkdDetail.objects.filter(medhistory=psp.ckd).exists())
        self.assertFalse(BaselineCreatinine.objects.filter(medhistory=psp.ckd).exists())

    def test__post_creates_ppxaids_with_correct_recommendations(self):
        """Test that the view creates the User's PpxAid object with the correct
        recommendations."""
        for user in Pseudopatient.objects.select_related("pseudopatientprofile").all():
            if not hasattr(user, "ppxaid"):
                create_ppxaid(user=user)
            data = ppxaid_data_factory(user)
            if hasattr(user, "profile") and user.profile.provider:
                self.client.force_login(user.profile.provider)
            response = self.client.post(
                reverse("ppxaids:pseudopatient-update", kwargs={"username": user.username}), data=data
            )
            tests_print_response_form_errors(response)
            assert response.status_code == 302
            # Get the PpxAid
            ppxaid = PpxAid.objects.get(user=user)
            # Test the PpxAid logic on the recommendations and options for the PpxAid
            # Check NSAID contraindications first
            if form_data_nsaid_contra(data=data):
                for nsaid in NsaidChoices.values:
                    assert nsaid not in ppxaid.recommendation and nsaid not in ppxaid.options
            # Check colchicine contraindications
            colch_contra = form_data_colchicine_contra(data=data, user=user)
            if colch_contra is not None:
                if colch_contra == Contraindications.ABSOLUTE or colch_contra == Contraindications.RELATIVE:
                    assert Treatments.COLCHICINE not in ppxaid.recommendation if ppxaid.recommendation else True
                    assert Treatments.COLCHICINE not in ppxaid.options if ppxaid.options else True
                elif colch_contra == Contraindications.DOSEADJ:
                    assert Treatments.COLCHICINE in ppxaid.options if ppxaid.options else True
                    assert (
                        ppxaid.options[Treatments.COLCHICINE]["dose"] == ColchicineDoses.POINTTHREE
                        if ppxaid.options
                        else True
                    )
                    assert ppxaid.options[Treatments.COLCHICINE]["freq"] == Freqs.QDAY if ppxaid.options else True
            else:
                assert Treatments.COLCHICINE in ppxaid.options
                assert ppxaid.options[Treatments.COLCHICINE]["dose"] == ColchicineDoses.POINTSIX
                assert ppxaid.options[Treatments.COLCHICINE]["freq"] == Freqs.QDAY if ppxaid.options else True

    def test__post_returns_errors(self):
        """Test that post returns errors for some common scenarios where the
        data is invalid. Typically, these are scenarios that should be prevented by
        the form or javascript."""
        # Test that the view returns errors when the baselinecreatinine and
        # stage are not congruent
        data = ppxaid_data_factory(user=self.psp)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": False,
                "baselinecreatinine-value": Decimal("9.9"),
                "stage": Stages.ONE,
            }
        )
        response = self.client.post(
            reverse("ppxaids:pseudopatient-update", kwargs={"username": self.psp.username}), data=data
        )
        assert response.status_code == 200
        assert "form" in response.context_data
        assert "ckddetail_form" in response.context_data
        assert "stage" in response.context_data["ckddetail_form"].errors
        assert "baselinecreatinine_form" in response.context_data
        assert "value" in response.context_data["baselinecreatinine_form"].errors
        # Test that the view returns errors when CKD is True and dialysis is left blank
        data = ppxaid_data_factory(user=self.psp)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": "",
            }
        )
        response = self.client.post(
            reverse("ppxaids:pseudopatient-update", kwargs={"username": self.psp.username}), data=data
        )
        assert response.status_code == 200
        assert "ckddetail_form" in response.context_data
        assert "dialysis" in response.context_data["ckddetail_form"].errors

    def test__rules(self):
        """Test that django-rules permissions are set correctly and working for the view."""
        # Create a Provider and Admin, each with their own Pseudopatient + Flare
        provider = UserFactory()
        prov_psp = create_psp(provider=provider)
        create_ppxaid(user=prov_psp)
        prov_psp_url = reverse("ppxaids:pseudopatient-update", kwargs={"username": prov_psp.username})
        next_url = reverse("ppxaids:pseudopatient-update", kwargs={"username": prov_psp.username})
        prov_psp_redirect_url = f"{reverse('account_login')}?next={next_url}"
        admin = AdminFactory()
        admin_psp = create_psp(provider=admin)
        create_ppxaid(user=admin_psp)
        admin_psp_url = reverse("ppxaids:pseudopatient-update", kwargs={"username": admin_psp.username})
        redirect_url = reverse("ppxaids:pseudopatient-update", kwargs={"username": admin_psp.username})
        admin_psp_redirect_url = f"{reverse('account_login')}?next={redirect_url}"
        # Create an anonymous Pseudopatient + Flare
        anon_psp = create_psp()
        create_ppxaid(user=anon_psp)
        anon_psp_url = reverse("ppxaids:pseudopatient-update", kwargs={"username": anon_psp.username})
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
