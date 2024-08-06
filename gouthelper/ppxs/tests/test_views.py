from datetime import timedelta
from decimal import Decimal

import pytest  # pylint: disable=e0401 # type: ignore
from django.contrib.auth import get_user_model  # pylint: disable=e0401 # type: ignore
from django.contrib.auth.models import AnonymousUser  # pylint: disable=e0401 # type: ignore
from django.contrib.messages.middleware import MessageMiddleware  # pylint: disable=e0401 # type: ignore
from django.contrib.sessions.middleware import SessionMiddleware  # pylint: disable=e0401 # type: ignore
from django.core.exceptions import ObjectDoesNotExist  # pylint: disable=e0401 # type: ignore
from django.db.models import QuerySet  # pylint: disable=e0401 # type: ignore
from django.test import RequestFactory, TestCase  # pylint: disable=e0401 # type: ignore
from django.urls import reverse  # pylint: disable=e0401 # type: ignore
from django.utils import timezone  # pylint: disable=e0401 # type: ignore

from ...contents.models import Content
from ...goalurates.choices import GoalUrates
from ...labs.helpers import labs_urate_within_last_month, labs_urates_last_at_goal
from ...labs.tests.factories import UrateFactory
from ...medhistorydetails.models import GoutDetail
from ...medhistorydetails.tests.factories import GoutDetailFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.helpers import medhistory_attr
from ...medhistorys.lists import PPX_MEDHISTORYS
from ...medhistorys.models import Gout
from ...medhistorys.tests.factories import GoutFactory
from ...ppxaids.tests.factories import create_ppxaid
from ...ults.choices import Indications
from ...users.models import Pseudopatient
from ...users.tests.factories import AdminFactory, UserFactory, create_psp
from ...utils.factories import count_data_deleted
from ...utils.forms import forms_print_response_errors
from ...utils.test_helpers import dummy_get_response
from ..models import Ppx
from ..selectors import ppx_user_qs, ppx_userless_qs
from ..views import (
    PpxAbout,
    PpxCreate,
    PpxDetail,
    PpxPseudopatientCreate,
    PpxPseudopatientDetail,
    PpxPseudopatientUpdate,
    PpxUpdate,
)
from .factories import create_ppx, ppx_data_factory

pytestmark = pytest.mark.django_db


User = get_user_model()


class TestPpxAbout(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: PpxAbout = PpxAbout()

    def test__get(self):
        response = self.client.get(reverse("ppxs:about"))
        self.assertEqual(response.status_code, 200)

    def test__get_context_data(self):
        response = self.client.get(reverse("ppxs:about"))
        self.assertIn("content", response.context_data)

    def test__content(self):
        self.assertEqual(self.view.content, Content.objects.get(context=Content.Contexts.PPX, slug="about", tag=None))


class TestPpxCreate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: PpxCreate = PpxCreate

    def test__ckddetail(self):
        """Tests the ckddetail cached_property."""
        self.assertFalse(self.view().ckddetail)

    def test__get_context_data(self):
        """Test that the view returns the correct context data."""
        response = self.client.get(reverse("ppxs:create"))

        # Assert that the response context data contains the correct keys
        for mh in PPX_MEDHISTORYS:
            if mh == MedHistoryTypes.GOUT:
                self.assertIn(f"{mh}_form", response.context_data)
                self.assertTrue(
                    response.context_data[f"{mh}_form"].instance._state.adding
                )  # pylint: disable=w0212, line-too-long # noqa: E501
                # Form should be hidden and the value set to True
                self.assertTrue(response.context_data[f"{mh}_form"].initial)
                self.assertEqual(response.context_data[f"{mh}_form"].initial, {f"{mh}-value": True})
                # Test that the form is hidden
                self.assertIn("hidden", response.context_data[f"{mh}_form"].as_p())
            else:
                self.assertIn(f"{mh}_form", response.context_data)
                self.assertTrue(
                    response.context_data[f"{mh}_form"].instance._state.adding
                )  # pylint: disable=w0212, line-too-long # noqa: E501
                self.assertFalse(response.context_data[f"{mh}_form"].initial)
        self.assertIn("goutdetail_form", response.context_data)
        self.assertIn("urate_formset", response.context_data)

    def test__get_form_kwargs(self):
        # Create a fake request
        request = self.factory.get("/fake-url/")
        request.user = AnonymousUser()
        view = self.view(request=request)

        # Set the user on the view, as this would be done by dispatch()
        view.setup(request)
        view.set_forms()
        view.object = view.get_object()

        # Call the get_form_kwargs() method and assert that the correct kwargs are returned
        form_kwargs = view.get_form_kwargs()
        self.assertNotIn("medallergys", form_kwargs)
        self.assertIn("patient", form_kwargs)
        self.assertFalse(form_kwargs["patient"])

    def test__get_permission_object(self):
        """Test that the get_permission_object() method returns None."""
        request = self.factory.get("/fake-url/")
        request.user = AnonymousUser()
        view = self.view()
        view.setup(request)
        permission_object = view.get_permission_object()  # pylint: disable=assignment-from-none
        self.assertIsNone(permission_object)

    def test__goutdetail(self):
        """Tests the goutdetail cached_property."""
        view = self.view()
        view.kwargs = {}
        view.set_forms()
        self.assertTrue(view.goutdetail)

    def test__post_creates_ppx(self):
        """Tests that a POST request creates a Ppx object."""
        # Count the number of existing Ppx, Gout, and GoutDetail objects
        ppx_count = Ppx.objects.count()
        gout_count = Gout.objects.count()
        goutdetail_count = GoutDetail.objects.count()

        # Create fake post() data and POST it
        ppx_data = ppx_data_factory(urates=None)
        response = self.client.post(reverse("ppxs:create"), ppx_data)
        # NOTE: Will print errors for all forms in the context_data.
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        # Assert that the number of Ppx, Gout, and GoutDetail objects has increased by 1
        self.assertEqual(Ppx.objects.count(), ppx_count + 1)
        self.assertEqual(Gout.objects.count(), gout_count + 1)
        self.assertEqual(GoutDetail.objects.count(), goutdetail_count + 1)

        # Test that the created Gout and GoutDetail objects have the correct fields
        ppx = ppx_userless_qs(pk=Ppx.objects.order_by("created").last().pk).get()
        gout = ppx.gout
        goutdetail = ppx.goutdetail
        # Assert that the GoutDetail object attrs are correct
        self.assertEqual(goutdetail.medhistory, gout)
        self.assertEqual(goutdetail.on_ult, ppx_data["on_ult"])
        if labs_urates_last_at_goal(ppx.urates_qs, GoalUrates.SIX) and labs_urate_within_last_month(ppx.urates_qs):
            self.assertEqual(goutdetail.at_goal, True)
        elif ppx_data["at_goal"]:
            self.assertEqual(goutdetail.at_goal, True)
        elif ppx_data["at_goal"] is False:
            self.assertEqual(goutdetail.at_goal, False)
        else:
            self.assertIsNone(goutdetail.at_goal)
        if getattr(ppx, "urates_qs", None):
            for urate in ppx.urates_qs:
                # Assert that the urate value and date_drawn are present in the ppx_data
                self.assertIn(urate.value, ppx_data.values())

    def test__post_creates_ppx_with_related_ppxaid(self):
        """Tests that a POST request creates a Ppx object with a related PpxAid object."""
        # Create a PpxAid object
        ppxaid = create_ppxaid()
        # Create fake post() data and POST it
        ppx_data = ppx_data_factory(urates=None)
        response = self.client.post(reverse("ppxs:ppxaid-create", kwargs={"ppxaid": ppxaid.pk}), ppx_data)
        # NOTE: Will print errors for all forms in the context_data.
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        # Test that the created Ppx object has the correct related PpxAid object
        ppx = ppx_userless_qs(pk=Ppx.objects.order_by("created").last().pk).get()
        self.assertEqual(ppx.ppxaid, ppxaid)

    def test__post_creates_urate(self):
        """Test that post() method creates a single Urate object"""
        # Create some fake data that indicates new urates are to be created
        data = ppx_data_factory(
            mh_dets={MedHistoryTypes.GOUT: {"at_goal": False, "at_goal_long_term": False}},
            urates=[Decimal("9.1"), Decimal("14.5")],
        )
        # POST the data
        response = self.client.post(reverse("ppxs:create"), data)
        # NOTE: Will print errors for all forms in the context_data.
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        # Get the new ppx and its urates
        ppx = ppx_userless_qs(pk=Ppx.objects.order_by("created").last().pk).get()
        urates = ppx.urates_qs

        assert urates

        assert next(iter([urate for urate in urates if urate.value == Decimal("9.1")]), None)
        assert next(iter([urate for urate in urates if urate.value == Decimal("14.5")]), None)

        for urate in urates:
            assert urate.date_drawn
            assert urate.ppx == ppx

    def test__post_returns_errors(self):
        """Test that post returns errors for some common scenarios where the
        data is invalid. Typically, these are scenarios that should be prevented by
        the form or javascript."""
        # Test that the view returns errors when the baselinecreatinine and
        # stage are not congruent
        data = ppx_data_factory()
        data.update(
            {
                "starting_ult": "",
            }
        )
        response = self.client.post(reverse("ppxs:create"), data=data)
        assert response.status_code == 200
        assert "form" in response.context_data
        assert "starting_ult" in response.context_data["goutdetail_form"].errors

        # Create some data with data for urates
        data = ppx_data_factory(urates=[Decimal("5.9"), Decimal("7.9"), Decimal("9.9")])

        # Update the data to invalidate one of the urates
        data.update(
            {
                "urate-0-date_drawn": "",
            }
        )

        # POST the data
        response = self.client.post(reverse("ppxs:create"), data=data)
        assert response.status_code == 200
        assert "urate_formset" in response.context_data
        assert response.context_data["urate_formset"].errors
        assert response.context_data["urate_formset"].errors[0]["date_drawn"]


class TestPpxDetail(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: PpxDetail = PpxDetail
        self.ppx = create_ppx()

    def test__dispatch_redirects_if_ppx_user(self):
        """Test that the dispatch() method redirects to the Pseudopatient DetailView if the
        Ppx has a user."""
        user_ppx = create_ppx(user=True)
        request = self.factory.get("/fake-url/")
        request.user = AnonymousUser()
        response = self.view.as_view()(request, pk=user_ppx.pk)
        assert response.status_code == 302
        assert response.url == reverse("ppxs:pseudopatient-detail", kwargs={"pseudopatient": user_ppx.user.pk})

    def test__get_queryset(self):
        qs = self.view(kwargs={"pk": self.ppx.pk}).get_queryset()
        self.assertTrue(isinstance(qs, QuerySet))
        self.assertEqual(qs.first(), self.ppx)
        self.assertTrue(hasattr(qs.first(), "medhistorys_qs"))
        self.assertTrue(hasattr(qs.first(), "urates_qs"))

    def test__get_object_updates(self):
        """Test that calling the view without the updated=True query param updates the Ppx."""
        # Create a blank Ppx and assert that it has vanilla recommendations
        self.assertEqual(self.ppx.indication, self.ppx.Indications.NOTINDICATED)

        # Change the starting_ult field to True
        self.ppx.goutdetail.starting_ult = True
        self.ppx.goutdetail.save()

        # Re-POST the view and check to see if if the recommendation has been updated
        request = self.factory.get(reverse("ppxs:detail", kwargs={"pk": self.ppx.pk}))
        request.user = AnonymousUser()
        self.view.as_view()(request, pk=self.ppx.pk)

        # Refresh the ppxaid from the db
        self.ppx.refresh_from_db()
        self.assertEqual(self.ppx.indication, self.ppx.Indications.INDICATED)

    def test__get_object_does_not_update(self):
        # Create a blank Ppx and assert that it has vanilla recommendations
        self.assertEqual(self.ppx.indication, self.ppx.Indications.NOTINDICATED)

        # Change the starting_ult field to True
        self.ppx.goutdetail.starting_ult = True
        self.ppx.goutdetail.save()

        # POST the view with the updated=True query param
        # and check to see if if the recommendation has not been updated
        request = self.factory.get(reverse("ppxs:detail", kwargs={"pk": self.ppx.pk}) + "?updated=True")
        request.user = AnonymousUser()
        self.view.as_view()(request, pk=self.ppx.pk)

        # Refresh the ppxaid from the db
        self.ppx.refresh_from_db()
        self.assertEqual(self.ppx.indication, self.ppx.Indications.NOTINDICATED)

        # Call without the updated=True query param and assert that the recommendation has been updated
        request = self.factory.get(reverse("ppxs:detail", kwargs={"pk": self.ppx.pk}))
        request.user = AnonymousUser()
        self.view.as_view()(request, pk=self.ppx.pk)

        # Refresh the ppxaid from the db
        self.ppx.refresh_from_db()
        self.assertEqual(self.ppx.indication, self.ppx.Indications.INDICATED)

    def test__rules(self):
        # Test that when the view is called with a Ppx that has a User and the requesting User
        # does not have permission, a 404 is returned
        nefarious_admin = AdminFactory()
        psp_with_provider = create_psp(provider=True)
        user_ppx = create_ppx(user=psp_with_provider)
        request = self.factory.get("/fake-url/")
        request.user = AnonymousUser()
        response = self.view.as_view()(request, pk=user_ppx.pk)
        assert response.status_code == 302

        # Log in a User that is nefariously trying to access it
        self.client.force_login(nefarious_admin)
        response = self.client.get(reverse("ppxs:detail", kwargs={"pk": user_ppx.pk}))
        # Should redirect to the Pseudopatient DetailView
        assert response.status_code == 302
        # Permission for that view should be denied
        assert response.url == reverse("ppxs:pseudopatient-detail", kwargs={"pseudopatient": user_ppx.user.pk})
        response_2 = self.client.get(response.url, follow=True)
        assert response_2.status_code == 403


class TestPpxPseudopatientCreate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = PpxPseudopatientCreate
        self.anon_user = AnonymousUser()
        self.user = create_psp(plus=True)
        for _ in range(10):
            create_psp(plus=True)
        self.psp = create_psp()

    def test__ckddetail(self):
        """Tests the ckddetail cached_property."""
        self.assertFalse(self.view().ckddetail)

    def test__get_form_kwargs(self):
        # Create a fake request
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        view = self.view(request=request)

        # Set the user on the view, as this would be done by dispatch()
        view.setup(request, pseudopatient=self.user.pk)
        view.set_forms()
        view.object = view.get_object()

        # Call the get_form_kwargs() method and assert that the correct kwargs are returned
        form_kwargs = view.get_form_kwargs()
        self.assertNotIn("medallergys", form_kwargs)
        self.assertIn("patient", form_kwargs)
        self.assertTrue(form_kwargs["patient"])

    def test__goutdetail(self):
        """Tests the goutdetail cached_property."""
        view = self.view()
        view.set_forms()
        self.assertTrue(view.goutdetail)

    def test__dispatch(self):
        """Test the dispatch() method for the view. Should redirect to detailview when
        the user already has a Ppx. Should redirect to Pseudopatient Update
        view when the user doesn't have the required 1to1 related models."""
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        SessionMiddleware(dummy_get_response).process_request(request)
        kwargs = {"pseudopatient": self.user.pk}
        view = self.view()
        view.setup(request, **kwargs)
        response = view.dispatch(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(hasattr(view, "user"))
        self.assertEqual(view.user, self.user)

        # Create a new Ppx and test that the view redirects to the Update view
        create_ppx(user=self.user)
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("ppxs:pseudopatient-create", kwargs={"pseudopatient": self.user.pk}), follow=True
        )
        self.assertEqual(view.user, self.user)
        self.assertRedirects(response, reverse("ppxs:pseudopatient-update", kwargs={"pseudopatient": self.user.pk}))

        # Check that the response message is correct
        message = list(response.context.get("messages"))[0]
        self.assertEqual(message.tags, "error")
        self.assertEqual(message.message, f"{self.user} already has a Ppx. Please update it instead.")

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
        self.assertTrue(hasattr(qs, "urates_qs"))

    def test__get_context_data_medhistorys(self):
        """Test that the context data includes the user's
        related models."""
        for user in (
            Pseudopatient.objects.select_related("pseudopatientprofile").prefetch_related("medhistory_set").all()
        ):
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
                if mh.medhistorytype in PPX_MEDHISTORYS:
                    if mh.medhistorytype == MedHistoryTypes.GOUT:
                        assert f"{mh.medhistorytype}_form" not in response.context_data
                    else:
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
            for mhtype in PPX_MEDHISTORYS:
                if mhtype == MedHistoryTypes.GOUT:
                    assert not response.context_data.get(f"{mhtype}_form", False)
                else:
                    assert f"{mhtype}_form" in response.context_data
                    if mhtype not in user.medhistory_set.values_list("medhistorytype", flat=True):
                        assert (
                            response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                                f"{mhtype}_form"
                            ].instance._state.adding
                            is True
                        )
                        assert response.context_data[f"{mhtype}_form"].initial == {f"{mhtype}-value": None}
            assert "goutdetail_form" in response.context_data

    def test__get_context_data_urates(self):
        """Test that the context data includes the user's Urates."""
        user = Pseudopatient.objects.first()
        UrateFactory.create_batch(2, user=user)
        request = self.factory.get("/fake-url/")
        if user.profile.provider:
            request.user = user.profile.provider
        else:
            request.user = self.anon_user
        SessionMiddleware(dummy_get_response).process_request(request)
        kwargs = {"pseudopatient": user.pk}
        response = self.view.as_view()(request, **kwargs)
        assert response.status_code == 200
        assert "urate_formset" in response.context_data
        assert response.context_data["urate_formset"].queryset.count() == user.urate_set.count()
        for urate in user.urate_set.all():
            assert urate in response.context_data["urate_formset"].queryset

    def test__get_context_data_patient(self):
        """Test that the context data includes the user."""
        user = Pseudopatient.objects.first()
        request = self.factory.get("/fake-url/")
        if user.profile.provider:
            request.user = user.profile.provider
        else:
            request.user = self.anon_user
        SessionMiddleware(dummy_get_response).process_request(request)
        kwargs = {"pseudopatient": user.pk}
        response = self.view.as_view()(request, **kwargs)
        assert response.status_code == 200
        assert "patient" in response.context_data
        assert response.context_data["patient"] == user

    def test__get_permission_object(self):
        """Test the get_permission_object() method for the view."""
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        kwargs = {"pseudopatient": self.user.pk}
        view = self.view()
        view.setup(request, **kwargs)
        view.user = self.user

        permission_object = view.get_permission_object()
        self.assertEqual(permission_object, self.user)

    def test__post(self):
        """Test the post() method for the view."""
        data = ppx_data_factory(user=self.user, urates=None)
        request = self.factory.post("/fake-url/", data=data)
        request.htmx = False
        if self.user.profile.provider:  # type: ignore
            request.user = self.user.profile.provider  # type: ignore
        else:
            request.user = self.anon_user
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)
        kwargs = {"pseudopatient": self.user.pk}
        response = self.view.as_view()(request, **kwargs)
        assert response.status_code == 302
        assert (
            response.url
            == reverse("ppxs:pseudopatient-detail", kwargs={"pseudopatient": self.user.pk}) + "?updated=True"
        )

    def test__post_sets_object_user(self):
        """Test that the post() method for the view sets the user on the object."""
        # Create some fake data for a User's Ppx
        data = ppx_data_factory(user=self.user, urates=None)

        # POST the data
        response = self.client.post(
            reverse("ppxs:pseudopatient-create", kwargs={"pseudopatient": self.user.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302

        assert Ppx.objects.filter(user=self.user).exists()
        ppx = Ppx.objects.last()
        assert ppx.user
        assert ppx.user == self.user

    def test__post_updates_goutdetail(self):
        """Test that the view updates the User's GoutDetail."""
        goutdetail = self.psp.goutdetail
        data = ppx_data_factory(user=self.psp, urates=None)

        # Modify the data to ensure changes to the GoutDetail are being made
        data.update(
            {
                "flaring": not goutdetail.flaring,
                "on_ppx": not goutdetail.on_ppx,
            }
        )
        # POST the data
        response = self.client.post(
            reverse("ppxs:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302

        # Refresh the goutdetail from the db
        goutdetail.refresh_from_db()
        # Assert that the goutdetail fields are the same as in the data dict
        self.assertEqual(goutdetail.flaring, data["flaring"])
        self.assertEqual(goutdetail.on_ppx, data["on_ppx"])

    def test__post_creates_ppx(self):
        """Test that the view creates the User's Ppx."""
        data = ppx_data_factory(user=self.psp, urates=None)

        # POST the data
        response = self.client.post(
            reverse("ppxs:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        assert response.status_code == 302

        # Assert that the Ppx was created
        assert Ppx.objects.filter(user=self.psp).exists()

        # Get the Ppx
        ppx = Ppx.objects.get(user=self.psp)

        # Assert that the Ppx fields are the same as in the data dict
        self.assertEqual(ppx.starting_ult, data["starting_ult"])

    def test__post_creates_urates(self):
        """Test that the view creates the User's Urate objects."""
        data = ppx_data_factory(
            user=self.psp,
            mh_dets={MedHistoryTypes.GOUT: {"at_goal": False, "at_goal_long_term": False}},
            urates=[Decimal("10.9"), Decimal("7.9"), Decimal("9.9")],
        )

        # POST the data
        response = self.client.post(
            reverse("ppxs:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302

        # Get the urates
        urates = self.psp.urate_set.all()

        # Assert that the urates were created
        self.assertEqual(urates.count(), 3)
        self.assertIn(Decimal("10.9"), [urate.value for urate in urates])
        self.assertIn(Decimal("7.9"), [urate.value for urate in urates])
        self.assertIn(Decimal("9.9"), [urate.value for urate in urates])

    def test__post_deletes_urates(self):
        """Test that the view deletes the User's Urate objects."""
        # Create some urates for the User
        UrateFactory.create_batch(3, user=self.psp)

        # Create some data without urates
        data = ppx_data_factory(user=self.psp, urates=None)

        # POST the data
        response = self.client.post(
            reverse("ppxs:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        assert response.status_code == 302

        # Get the urates
        urates = self.psp.urate_set.all()

        # Assert that the urates were deleted
        self.assertEqual(urates.count(), 0)

    def test__post_creates_ppxs_with_correct_indication(self):
        """Test that the view creates the User's Ppx object with the correct indication."""
        for user in Pseudopatient.objects.all():
            data = ppx_data_factory(user, urates=None)

            if user.profile.provider:
                self.client.force_login(user.profile.provider)
            response = self.client.post(
                reverse("ppxs:pseudopatient-create", kwargs={"pseudopatient": user.pk}), data=data
            )
            forms_print_response_errors(response)
            assert response.status_code == 302

            # Get the Ppx
            ppx = Ppx.objects.get(user=user)

            # Test the view logic for setting the indication
            if ppx.starting_ult:
                assert ppx.indication == ppx.Indications.INDICATED
            elif ppx.goutdetail.on_ult:
                if (ppx.goutdetail.flaring or not ppx.goutdetail.at_goal) and not (
                    ppx.at_goal_long_term and ppx.urate_within_90_days
                ):
                    assert ppx.indication == ppx.Indications.CONDITIONAL
                else:
                    assert ppx.indication == ppx.Indications.NOTINDICATED
            else:
                assert ppx.indication == ppx.Indications.NOTINDICATED

    def test__post_returns_errors(self):
        """Test that post returns errors for some common scenarios where the
        data is invalid. Typically, these are scenarios that should be prevented by
        the form or javascript."""

        # Create some data with data for urates
        data = ppx_data_factory(user=self.psp, urates=[Decimal("5.9"), Decimal("7.9"), Decimal("9.9")])

        # Update the data to invalidate one of the urates
        data.update(
            {
                "urate-0-date_drawn": "",
            }
        )

        # POST the data
        response = self.client.post(
            reverse("ppxs:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        assert response.status_code == 200
        assert "urate_formset" in response.context_data
        assert response.context_data["urate_formset"].errors
        assert response.context_data["urate_formset"].errors[0]["date_drawn"]

    def test__rules(self):
        """Tests for whether the rules appropriately allow or restrict access to the view."""
        psp = create_psp()
        provider = UserFactory()
        provider_psp = create_psp(provider=provider)
        admin = AdminFactory()
        admin_psp = create_psp(provider=admin)
        # Test that any User can create an anonymous Pseudopatient's Ppx
        response = self.client.get(reverse("ppxs:pseudopatient-create", kwargs={"pseudopatient": psp.pk}))
        assert response.status_code == 200
        # Test that an anonymous User can't create a Provider's Ppx
        response = self.client.get(reverse("ppxs:pseudopatient-create", kwargs={"pseudopatient": provider_psp.pk}))
        # 302 because PermissionDenied will redirect to the login page
        assert response.status_code == 302
        # Test that an anonymous User can't create an Admin's Ppx
        response = self.client.get(reverse("ppxs:pseudopatient-create", kwargs={"pseudopatient": admin_psp.pk}))
        # Test that a Provider can create his or her own Pseudopatient's Ppx
        response = self.client.get(
            reverse("ppxs:pseudopatient-create", kwargs={"pseudopatient": psp.pk}),
        )
        assert response.status_code == 200
        # Test that a Provider can create an anonymous Pseudopatient's Ppx
        response = self.client.get(
            reverse("ppxs:pseudopatient-create", kwargs={"pseudopatient": psp.pk}),
        )
        assert response.status_code == 200
        self.client.force_login(admin)
        response = self.client.get(
            reverse("ppxs:pseudopatient-create", kwargs={"pseudopatient": admin_psp.pk}),
        )
        assert response.status_code == 200
        # Test that only a Pseudopatient's Provider can add their Ppx if they have a Provider
        response = self.client.get(
            reverse("ppxs:pseudopatient-create", kwargs={"pseudopatient": provider_psp.pk}),
        )
        assert response.status_code == 403
        self.client.force_login(provider)
        # Test that a Provider can't create another provider's Pseudopatient's Ppx
        response = self.client.get(
            reverse("ppxs:pseudopatient-create", kwargs={"pseudopatient": admin_psp.pk}),
        )
        assert response.status_code == 403
        self.client.force_login(admin)
        # Test that an Admin can create an anonymous Pseudopatient's Ppx
        response = self.client.get(
            reverse("ppxs:pseudopatient-create", kwargs={"pseudopatient": psp.pk}),
        )
        assert response.status_code == 200


class TestPpxPseudopatientDetail(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = PpxPseudopatientDetail
        self.anon_user = AnonymousUser()
        self.psp = create_psp(plus=True)
        UrateFactory.create_batch(3, user=self.psp)
        for psp in Pseudopatient.objects.all():
            create_ppx(user=psp)
        self.empty_psp = create_psp(plus=True)

    def test__get_context_data(self):
        response = self.client.get(reverse("ppxs:pseudopatient-detail", kwargs={"pseudopatient": self.psp.pk}))
        context = response.context_data
        # Assert that "patient" is in the context data
        self.assertIn("patient", context)
        self.assertEqual(context["patient"], self.psp)

    def test__assign_ppx_attrs_from_user(self):
        """Test that the assign_ppx_attrs_from_user() method for the view
        transfers attributes from the QuerySet, which started with a User,
        to the Ppx object."""
        ppx = Ppx.objects.get(user=self.psp)
        view = self.view()
        request = self.factory.get("/fake-url/")
        view.setup(request, pseudopatient=self.psp.pk)
        assert not hasattr(ppx, "medhistorys_qs")
        assert not hasattr(ppx, "urates_qs")
        view.assign_ppx_attrs_from_user(ppx=ppx, user=ppx_user_qs(self.psp.pk).get())
        assert hasattr(ppx, "medhistorys_qs")
        assert hasattr(ppx, "urates_qs")

    def test__dispatch(self):
        """Test the dispatch() method for the view. Should redirect to CreateView when
        the User doesn't have a Ppx."""
        response = self.client.get(reverse("ppxs:pseudopatient-detail", kwargs={"pseudopatient": self.psp.pk}))
        self.assertEqual(response.status_code, 200)
        # Test that dispatch redirects to the pseudopatient-create Ppx view when the user doesn't have a Ppx
        self.assertRedirects(
            self.client.get(reverse("ppxs:pseudopatient-detail", kwargs={"pseudopatient": self.empty_psp.pk})),
            reverse("ppxs:pseudopatient-create", kwargs={"pseudopatient": self.empty_psp.pk}),
        )

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
        doesn't have a Ppx."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, pseudopatient=self.empty_psp.pk)
        with self.assertRaises(ObjectDoesNotExist):
            view.get_object()

    def test__get_object_assigns_user_qs_attrs_to_ppx(self):
        """Test that the get_object method transfers required attributes from the
        User QuerySet to the Ppx object."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, pseudopatient=self.psp.pk)
        ppx = view.get_object()
        assert hasattr(ppx, "medhistorys_qs")
        assert getattr(ppx, "medhistorys_qs") == view.user.medhistorys_qs
        assert hasattr(ppx, "urates_qs")
        assert getattr(ppx, "urates_qs") == view.user.urates_qs

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
        assert hasattr(qs, "ppx") and qs.ppx == self.psp.ppx
        assert hasattr(qs, "medhistorys_qs")
        psp_mhs = self.psp.medhistory_set.filter(medhistorytype__in=PPX_MEDHISTORYS).all()
        for mh in qs.medhistorys_qs:
            assert mh in psp_mhs
        assert hasattr(qs, "urates_qs")
        psp_urates = self.psp.urate_set.all()
        for urate in qs.urates_qs:
            assert urate in psp_urates

    def test__get_updates_ppxaid(self):
        """Test that the get method updates the object when called with the
        correct url parameters."""
        # Create Pseuduopatient and Ppx that should evaluate to indicated
        psp = create_psp(ppx_indicated=Indications.INDICATED)
        ppx = create_ppx(user=psp, mh_dets={MedHistoryTypes.GOUT: {"on_ult": True, "starting_ult": True}})

        # Assert that the un-updated Ppx is not indicated
        self.assertEqual(ppx.indication, ppx.Indications.NOTINDICATED)

        # GET the view with the updated=False url parameter
        self.client.get(reverse("ppxs:pseudopatient-detail", kwargs={"pseudopatient": psp.pk}))

        ppx.refresh_from_db()

        # Assert that the Ppx is now indicated
        self.assertEqual(ppx.indication, ppx.Indications.INDICATED)

    def test__get_does_not_update_ppxaid(self):
        """Test that the get method doesn't update the object when called with the
        ?updated=True url parameter."""
        # Create Pseuduopatient and Ppx that should evaluate to indicated
        psp = create_psp(ppx_indicated=Indications.INDICATED)
        ppx = create_ppx(user=psp, mh_dets={MedHistoryTypes.GOUT: {"on_ult": True, "starting_ult": True}})

        # Assert that the un-updated Ppx is not indicated
        self.assertEqual(ppx.indication, ppx.Indications.NOTINDICATED)

        # GET the view with the updated=True url parameter
        self.client.get(reverse("ppxs:pseudopatient-detail", kwargs={"pseudopatient": psp.pk}) + "?updated=True")

        ppx.refresh_from_db()

        # Assert that the Ppx is now indicated
        self.assertEqual(ppx.indication, ppx.Indications.NOTINDICATED)

    def test__rules(self):
        psp = create_psp()
        create_ppx(user=psp)
        provider = UserFactory()
        provider_psp = create_psp(provider=provider)
        create_ppx(user=provider_psp)
        admin = AdminFactory()
        admin_psp = create_psp(provider=admin)
        create_ppx(user=admin_psp)
        # Test that any User can view an anonymous Pseudopatient's Ppx
        response = self.client.get(reverse("ppxs:pseudopatient-detail", kwargs={"pseudopatient": psp.pk}))
        assert response.status_code == 200
        # Test that an anonymous User can't view a Provider's Ppx
        response = self.client.get(reverse("ppxs:pseudopatient-detail", kwargs={"pseudopatient": provider_psp.pk}))
        # 302 because PermissionDenied will redirect to the login page
        assert response.status_code == 302
        # Test that an anonymous User can't view an Admin's Ppx
        response = self.client.get(reverse("ppxs:pseudopatient-detail", kwargs={"pseudopatient": admin_psp.pk}))
        assert response.status_code == 302
        # Test that a Provider can view their own Pseudoatient's Ppx
        self.client.force_login(provider)
        response = self.client.get(
            reverse("ppxs:pseudopatient-detail", kwargs={"pseudopatient": provider_psp.pk}),
        )
        assert response.status_code == 200
        # Test that a Provider can view an anonymous Pseudopatient's Ppx
        response = self.client.get(
            reverse("ppxs:pseudopatient-detail", kwargs={"pseudopatient": psp.pk}),
        )
        assert response.status_code == 200
        # Test that Provider can't view Admin's Pseudopatient's Ppx
        response = self.client.get(
            reverse("ppxs:pseudopatient-detail", kwargs={"pseudopatient": admin_psp.pk}),
        )
        assert response.status_code == 403
        self.client.force_login(admin)
        # Test that an Admin can view their own Pseudopatient's Ppx
        response = self.client.get(
            reverse("ppxs:pseudopatient-detail", kwargs={"pseudopatient": admin_psp.pk}),
        )
        assert response.status_code == 200
        # Test that an Admin can view an anonymous Pseudopatient's Ppx
        response = self.client.get(
            reverse("ppxs:pseudopatient-detail", kwargs={"pseudopatient": psp.pk}),
        )
        assert response.status_code == 200
        # Test that Admin can't view Provider's Pseudopatient's Ppx
        response = self.client.get(
            reverse("ppxs:pseudopatient-detail", kwargs={"pseudopatient": provider_psp.pk}),
        )
        assert response.status_code == 403


class TestPpxPseudopatientUpdate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = PpxPseudopatientUpdate
        self.anon_user = AnonymousUser()
        self.user = create_psp(plus=True)
        for _ in range(10):
            create_psp(plus=True)
        self.psp = create_psp()
        for psp in Pseudopatient.objects.all():
            create_ppx(user=psp)
        self.empty_user = create_psp()

    def test__ckddetail(self):
        """Tests the ckddetail cached_property."""
        self.assertFalse(self.view().ckddetail)

    def test__get_form_kwargs(self):
        # Create a fake request
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        view = self.view(request=request)

        # Set the user on the view, as this would be done by dispatch()
        view.setup(request, pseudopatient=self.user.pk)
        view.set_forms()
        view.object = view.get_object()

        # Call the get_form_kwargs() method and assert that the correct kwargs are returned
        form_kwargs = view.get_form_kwargs()
        self.assertNotIn("medallergys", form_kwargs)
        self.assertIn("patient", form_kwargs)
        self.assertTrue(form_kwargs["patient"])

    def test__goutdetail(self):
        """Tests the goutdetail cached_property."""
        view = self.view()
        view.set_forms()
        self.assertTrue(view.goutdetail)

    def test__dispatch_redirects_to_create(self):
        """Test that the dispatch() method redirects to the Pseudopatient create view when the view
        has a user and the user doesn't have a Ppx."""

        self.assertRedirects(
            self.client.get(reverse("ppxs:pseudopatient-update", kwargs={"pseudopatient": self.empty_user.pk})),
            reverse("ppxs:pseudopatient-create", kwargs={"pseudopatient": self.empty_user.pk}),
        )

    def test__dispatch(self):
        """Test that dispatch() works when the user has a Ppx."""
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)
        kwargs = {"pseudopatient": self.user.pk}
        view = self.view()
        view.setup(request, **kwargs)
        response = view.dispatch(request, **kwargs)
        self.assertEqual(response.status_code, 200)

    def test__get_object(self):
        """Test get_object() method."""

        request = self.factory.get("/fake-url/")
        SessionMiddleware(dummy_get_response).process_request(request)
        kwargs = {"pseudopatient": self.user.pk}
        view = self.view()
        view.setup(request, **kwargs)

        view_obj = view.get_object()
        self.assertTrue(isinstance(view_obj, Ppx))

        # Test that view sets the user attribute
        self.assertTrue(hasattr(view, "user"))
        self.assertEqual(view.user, self.user)

        # Repeat the test for a User w/o a PpxAid
        user_no_ppxaid = create_psp()
        view = self.view()
        view.setup(request, pseudopatient=user_no_ppxaid.pk)
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
        self.assertTrue(hasattr(qs, "urates_qs"))

    def test__get_context_data_medhistorys(self):
        """Test that the context data includes the user's
        related models."""
        for ppx in (
            Ppx.objects.select_related("user__pseudopatientprofile")
            .prefetch_related("user__medhistory_set")
            .filter(user__isnull=False)
            .all()
        ):
            request = self.factory.get("/fake-url/")
            if ppx.user.profile.provider:
                request.user = ppx.user.profile.provider
            else:
                request.user = self.anon_user
            kwargs = {"pseudopatient": ppx.user.pk}

            SessionMiddleware(dummy_get_response).process_request(request)
            MessageMiddleware(dummy_get_response).process_request(request)

            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            for mh in ppx.user.medhistory_set.all():
                if mh.medhistorytype in PPX_MEDHISTORYS:
                    if mh.medhistorytype == MedHistoryTypes.GOUT:
                        assert f"{mh.medhistorytype}_form" not in response.context_data
                    else:
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
            for mhtype in PPX_MEDHISTORYS:
                if mhtype == MedHistoryTypes.GOUT:
                    assert not response.context_data.get(f"{mhtype}_form", False)
                else:
                    assert f"{mhtype}_form" in response.context_data
                    if mhtype not in ppx.user.medhistory_set.values_list("medhistorytype", flat=True):
                        assert (
                            response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                                f"{mhtype}_form"
                            ].instance._state.adding
                            is True
                        )
                        assert response.context_data[f"{mhtype}_form"].initial == {f"{mhtype}-value": None}
            assert "goutdetail_form" in response.context_data
            assert (
                response.context_data["goutdetail_form"].instance
                == medhistory_attr(MedHistoryTypes.GOUT, ppx.user, "goutdetail").goutdetail
            )

    def test__get_context_data_patient(self):
        """Test that the context data includes the user."""
        user = Pseudopatient.objects.first()
        request = self.factory.get("/fake-url/")
        if user.profile.provider:
            request.user = user.profile.provider
        else:
            request.user = self.anon_user
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)
        kwargs = {"pseudopatient": user.pk}
        response = self.view.as_view()(request, **kwargs)
        forms_print_response_errors(response)
        assert response.status_code == 200
        assert "patient" in response.context_data
        assert response.context_data["patient"] == user

    def test__get_context_data_urates(self):
        """Test that the context data includes the user's Urates."""
        user = Pseudopatient.objects.select_related("ppx").exclude(ppx__isnull=True).first()
        UrateFactory.create_batch(2, user=user)
        request = self.factory.get("/fake-url/")
        if user.profile.provider:
            request.user = user.profile.provider
        else:
            request.user = self.anon_user
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)
        kwargs = {"pseudopatient": user.pk}
        response = self.view.as_view()(request, **kwargs)
        assert response.status_code == 200
        assert "urate_formset" in response.context_data
        assert response.context_data["urate_formset"].queryset.count() == user.urate_set.count()
        for urate in user.urate_set.all():
            assert urate in response.context_data["urate_formset"].queryset

    def test__post(self):
        """Test the post() method for the view."""
        data = ppx_data_factory(user=self.user, urates=None)
        request = self.factory.post(
            "/fake-url/",
            data=data,
        )
        request.htmx = False
        if hasattr(self.user, "profile") and self.user.profile.provider:
            request.user = self.user.profile.provider
        else:
            request.user = self.anon_user
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)
        kwargs = {"pseudopatient": self.user.pk}
        response = self.view.as_view()(request, **kwargs)
        assert response.status_code == 302
        assert (
            response.url
            == reverse("ppxs:pseudopatient-detail", kwargs={"pseudopatient": self.user.pk}) + "?updated=True"
        )

    def test__post_updates_goutdetail(self):
        """Test that the view updates the User's GoutDetail."""
        goutdetail = self.psp.goutdetail
        data = ppx_data_factory(user=self.psp, urates=None)

        # Modify the data to ensure changes to the GoutDetail are being made
        data.update(
            {
                "flaring": not goutdetail.flaring,
                "on_ppx": not goutdetail.on_ppx,
                "on_ult": not goutdetail.on_ult,
            }
        )

        # POST the data
        response = self.client.post(
            reverse("ppxs:pseudopatient-update", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        assert response.status_code == 302

        # Refresh the goutdetail from the db
        goutdetail.refresh_from_db()

        # Assert that the goutdetail fields are the same as in the data dict
        self.assertEqual(goutdetail.flaring, data["flaring"])
        self.assertEqual(goutdetail.on_ppx, data["on_ppx"])
        self.assertEqual(goutdetail.on_ult, data["on_ult"])

    def test__post_updates_ppx(self):
        """Test that the view updates the User's Ppx."""
        # Create fake form data for the User's Ppx
        data = ppx_data_factory(ppx=self.psp.ppx, urates=None)

        # Update the data to change the ppx
        data.update(
            {
                "on_ult": not self.psp.ppx.on_ult,
                "starting_ult": not self.psp.ppx.starting_ult,
            }
        )

        # POST the data
        response = self.client.post(
            reverse("ppxs:pseudopatient-update", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302

        # Get the Ppx
        ppx = Ppx.objects.get(user=self.psp)

        # Assert that the Ppx fields are the same as in the data dict
        self.assertEqual(ppx.starting_ult, data["starting_ult"])

    def test__post_creates_urates(self):
        """Test that the view creates the User's Urate objects."""
        # Create data based on the User's Ppx
        data = ppx_data_factory(ppx=self.psp.ppx, urates=None)

        # Count the User's urates
        # urate_count = self.psp.urate_set.count()

        # Add data to the form for extra urates
        total_urates = data["urate-TOTAL_FORMS"]
        data.update(
            {
                f"urate-{total_urates}-date_drawn": "2021-01-01",
                f"urate-{total_urates}-value": "15.9",
                f"urate-{total_urates}-id": "",
                f"urate-{total_urates+1}-date_drawn": "2021-02-02",
                f"urate-{total_urates+1}-value": "7.9",
                f"urate-{total_urates+1}-id": "",
                "urate-TOTAL_FORMS": total_urates + 2,
                "at_goal": False,
                "at_goal_long_term": False,
            }
        )

        # POST the data
        response = self.client.post(
            reverse("ppxs:pseudopatient-update", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302

        # Get the urates
        urates = self.psp.urate_set.all()
        # Assert that the urates were created
        self.assertIn(Decimal("15.9"), [urate.value for urate in urates])
        self.assertIn(Decimal("7.9"), [urate.value for urate in urates])

    def test__post_deletes_urates(self):
        """Test that the view deletes the User's Urate objects."""
        # Create some urates for the User
        UrateFactory.create_batch(3, user=self.psp)

        # Create some data without urates
        data = ppx_data_factory(user=self.psp, urates=None)

        # POST the data
        response = self.client.post(
            reverse("ppxs:pseudopatient-update", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        assert response.status_code == 302

        # Get the urates
        urates = self.psp.urate_set.all()

        # Assert that the urates were deleted
        self.assertEqual(urates.count(), 0)

    def test__post_creates_ppxs_with_correct_indication(self):
        """Test that the view creates the User's Ppx object with the correct indication."""
        for ppx in Ppx.objects.select_related("user__pseudopatientprofile").filter(user__isnull=False).all():
            data = ppx_data_factory(ppx=ppx, urates=None)

            if ppx.user.profile.provider:
                self.client.force_login(ppx.user.profile.provider)
            response = self.client.post(
                reverse("ppxs:pseudopatient-update", kwargs={"pseudopatient": ppx.user.pk}), data=data
            )
            forms_print_response_errors(response)
            assert response.status_code == 302

            # Refresh the ppx from the db
            ppx.refresh_from_db()

            # Test the view logic for setting the indication
            if ppx.starting_ult:
                assert ppx.indication == ppx.Indications.INDICATED
            elif ppx.goutdetail.on_ult:
                if (ppx.goutdetail.flaring or not ppx.goutdetail.at_goal) and not (
                    ppx.at_goal_long_term and ppx.urate_within_90_days
                ):
                    assert ppx.indication == ppx.Indications.CONDITIONAL
                else:
                    assert ppx.indication == ppx.Indications.NOTINDICATED
            else:
                assert ppx.indication == ppx.Indications.NOTINDICATED

    def test__post_returns_errors(self):
        """Test that post returns errors for some common scenarios where the
        data is invalid. Typically, these are scenarios that should be prevented by
        the form or javascript."""
        # Test that the view returns errors when the baselinecreatinine and
        # stage are not congruent
        data = ppx_data_factory(user=self.psp)
        data.update(
            {
                "on_ppx": "",
            }
        )
        response = self.client.post(
            reverse("ppxs:pseudopatient-update", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        assert response.status_code == 200
        assert "form" in response.context_data
        assert "goutdetail_form" in response.context_data
        assert "on_ppx" in response.context_data["goutdetail_form"].errors

    def test__rules(self):
        """Test that django-rules permissions are set correctly and working for the view."""
        # Create a Provider and Admin, each with their own Pseudopatient + Flare
        provider = UserFactory()
        prov_psp = create_psp(provider=provider)
        create_ppx(user=prov_psp)
        prov_psp_url = reverse("ppxs:pseudopatient-update", kwargs={"pseudopatient": prov_psp.pk})
        next_url = reverse("ppxs:pseudopatient-update", kwargs={"pseudopatient": prov_psp.pk})
        prov_psp_redirect_url = f"{reverse('account_login')}?next={next_url}"
        admin = AdminFactory()
        admin_psp = create_psp(provider=admin)
        create_ppx(user=admin_psp)
        admin_psp_url = reverse("ppxs:pseudopatient-update", kwargs={"pseudopatient": admin_psp.pk})
        redirect_url = reverse("ppxs:pseudopatient-update", kwargs={"pseudopatient": admin_psp.pk})
        admin_psp_redirect_url = f"{reverse('account_login')}?next={redirect_url}"
        # Create an anonymous Pseudopatient + Flare
        anon_psp = create_psp()
        create_ppx(user=anon_psp)
        anon_psp_url = reverse("ppxs:pseudopatient-update", kwargs={"pseudopatient": anon_psp.pk})
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


class TestPpxUpdate(TestCase):
    """Tests for the PpxUpdateView"""

    def setUp(self):
        self.factory = RequestFactory()
        self.view: PpxUpdate = PpxUpdate()
        # Create a Ppx object
        self.gout = GoutFactory()
        self.goutdetail = GoutDetailFactory(medhistory=self.gout, on_ult=False)
        self.urate1 = UrateFactory(date_drawn=timezone.now() - timedelta(days=45), value=Decimal("5.9"))
        self.urate2 = UrateFactory(date_drawn=timezone.now() - timedelta(days=180), value=Decimal("7.9"))
        self.urate3 = UrateFactory(date_drawn=timezone.now() - timedelta(days=360), value=Decimal("9.9"))
        self.ppx = create_ppx(
            mh_dets={MedHistoryTypes.GOUT: {"at_goal": False, "at_goal_long_term": False}},
            labs=[self.urate1, self.urate2, self.urate3],
        )

    def test__post_updates_ppx(self):
        """Tests that a POST request updates a Ppx object."""
        # Create some fake post() data based off the existing Ppx object
        data = ppx_data_factory(ppx=self.ppx, urates=None)

        # Make a couple data fields the opposite
        data.update(
            {
                "on_ult": not self.goutdetail.on_ult,
                "flaring": not self.goutdetail.flaring,
            }
        )
        # POST the data
        response = self.client.post(reverse("ppxs:update", kwargs={"pk": self.ppx.pk}), data)
        forms_print_response_errors(response)

        self.assertEqual(response.status_code, 302)

        # Assert that the changes were made
        ppx = ppx_userless_qs(pk=self.ppx.pk).get()
        self.assertNotEqual(ppx.goutdetail.on_ult, self.goutdetail.on_ult)
        self.assertNotEqual(ppx.goutdetail.flaring, self.goutdetail.flaring)

    def test__post_adds_urate(self):
        """Test that post() adds a Urate to the 3 that already exist for the Ppx."""
        # Create fake data with data for an extra urate
        data = ppx_data_factory(
            ppx=self.ppx, urates=[UrateFactory(value=Decimal("11.5"), date_drawn=timezone.now() - timedelta(days=180))]
        )
        # Count the number of urates that are going to be deleted
        urates_deleted = count_data_deleted(data)

        # Count the total number of urates for the Ppx
        urates_count = self.ppx.urate_set.count()

        # POST the data
        response = self.client.post(reverse("ppxs:update", kwargs={"pk": self.ppx.pk}), data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        ppx = Ppx.objects.order_by("created").last()
        urates = ppx.urate_set.order_by("-date_drawn").all()

        self.assertEqual(urates.count(), urates_count - urates_deleted + 1)
        self.assertIn(Decimal("11.5"), [urate.value for urate in urates])

    def test__post_removes_multiple_urates(self):
        """Test that post() removes 3 existing Urates for the Ppx."""
        # Create fake data with data for 3 urates to be deleted
        data = ppx_data_factory(ppx=self.ppx, urates=None)

        # Post the data
        response = self.client.post(reverse("ppxs:update", kwargs={"pk": self.ppx.pk}), data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        # Test that the urates were deleted
        self.assertEqual(self.ppx.urate_set.count(), 0)

    def test__post_removes_multiple_but_not_all_urates(self):
        """Test that post() removes 3 existing Urates for the Ppx."""
        # Create fake data with data for 3 urates to be deleted and a new one to be added
        data = ppx_data_factory(
            ppx=self.ppx,
            at_goal=False,
            urates=[Decimal("18.9"), *[(urate, {"DELETE": True}) for urate in self.ppx.urate_set.all()]],
        )

        # Post the data
        response = self.client.post(reverse("ppxs:update", kwargs={"pk": self.ppx.pk}), data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        # Test that the urates were deleted
        self.assertEqual(self.ppx.urate_set.count(), 1)
        self.assertIn(Decimal("18.9"), [urate.value for urate in self.ppx.urate_set.all()])

    def test__post_partial_urate_form_raises_ValidationError(self):
        """Test that a partially filled out Urate form raises a ValidationError."""
        # Create fake post() data with a partially filled out Urate form
        data = ppx_data_factory(ppx=self.ppx, urates=[])

        # Modify the first urate date_drawn to be an invalid value
        data.update(
            {
                "urate-0-value": "5.9",
                "urate-0-date_drawn": "",
            }
        )
        if data.get("urate-0-DELETE"):
            data.pop("urate-0-DELETE")

        # Test that a partially filled out Urate form returns a 200 status code
        response = self.client.post(reverse("ppxs:update", kwargs={"pk": self.ppx.pk}), data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 200)

        # Test that the response contains the erroneous UrateForm with errors
        self.assertTrue("urate_formset" in response.context_data)
        self.assertTrue(response.context_data["urate_formset"].errors)
        # Test that the response has the correct error message
        error_list = response.context_data["urate_formset"].errors
        self.assertTrue(any(error_list))
        for error_dict in error_list:
            if error_dict:
                self.assertIn("date_drawn", error_dict)
                self.assertEqual(error_dict["date_drawn"], ["We need to know when this was drawn."])

    def test__post_updates_goutdetail(self):
        """Tests that a POST request updates a Ppx object's related GoutDetail."""
        # Create fake data
        data = ppx_data_factory(ppx=self.ppx, urates=None)

        # Set GoutDetail fields as attrs on the test to test against later
        data.update(
            {
                "on_ult": not self.goutdetail.on_ult,
                "flaring": not self.goutdetail.flaring,
                "starting_ult": not self.ppx.starting_ult,
            }
        )

        # POST the data
        response = self.client.post(reverse("ppxs:update", kwargs={"pk": self.ppx.pk}), data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        # Test that the GoutDetail object attrs are correct
        goutdetail = GoutDetail.objects.order_by("created").last()
        self.assertEqual(goutdetail.on_ult, data["on_ult"])
        self.assertEqual(goutdetail.flaring, data["flaring"])
