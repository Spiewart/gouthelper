import pytest  # type: ignore
from django.apps import apps
from django.contrib.auth import get_user_model  # type: ignore
from django.contrib.auth.models import AnonymousUser  # type: ignore
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import ObjectDoesNotExist  # type: ignore
from django.db.models import QuerySet  # type: ignore
from django.http import HttpRequest
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore

from ...contents.choices import Contexts, Tags
from ...contents.models import Content
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.forms import ErosionsForm, TophiForm
from ...medhistorys.lists import GOALURATE_MEDHISTORYS
from ...medhistorys.models import Erosions, MedHistory, Tophi
from ...medhistorys.tests.factories import ErosionsFactory, TophiFactory
from ...ultaids.tests.factories import UltAidFactory
from ...users.choices import Roles
from ...users.models import Pseudopatient
from ...users.tests.factories import PseudopatientPlusFactory, UserFactory
from ...utils.helpers.test_helpers import tests_print_response_form_errors
from ..choices import GoalUrates
from ..models import GoalUrate
from ..selectors import goalurate_user_qs
from ..views import (
    GoalUrateAbout,
    GoalUrateCreate,
    GoalUrateDetail,
    GoalUratePseudopatientCreate,
    GoalUratePseudopatientDetail,
    GoalUratePseudopatientUpdate,
    GoalUrateUpdate,
)
from .factories import GoalUrateFactory, GoalUrateUserFactory, create_goalurate_data

pytestmark = pytest.mark.django_db

User = get_user_model()


class TestGoalUrateAbout(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: GoalUrateAbout = GoalUrateAbout()

    def test__get(self):
        response = self.client.get(reverse("goalurates:about"))
        self.assertEqual(response.status_code, 200)

    def test__get_context_data(self):
        response = self.client.get(reverse("goalurates:about"))
        self.assertIn("content", response.context_data)

    def test__content(self):
        self.assertEqual(
            self.view.content, Content.objects.get(context=Content.Contexts.GOALURATE, slug="about", tag=None)
        )


class TestGoalUrateCreate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: GoalUrateCreate = GoalUrateCreate
        self.request = self.factory.get(reverse("goalurates:create"))
        # Set the request's htmx attr to False to test the non-htmx code path.
        self.request.htmx = False
        self.response = self.view.as_view()(self.request)
        self.ultaid = UltAidFactory()

    def test__view_attrs(self):
        self.assertEqual(self.view.model, GoalUrate)
        self.assertEqual(self.view.form_class, GoalUrateCreate.form_class)
        self.assertIn(MedHistoryTypes.EROSIONS, self.view.medhistorys)
        self.assertEqual(self.view.medhistorys[MedHistoryTypes.EROSIONS]["form"], ErosionsForm)
        self.assertEqual(self.view.medhistorys[MedHistoryTypes.EROSIONS]["model"], Erosions)
        self.assertIn(MedHistoryTypes.TOPHI, self.view.medhistorys)
        self.assertEqual(self.view.medhistorys[MedHistoryTypes.TOPHI]["form"], TophiForm)
        self.assertEqual(self.view.medhistorys[MedHistoryTypes.TOPHI]["model"], Tophi)

    def test__get_context_data(self):
        for medhistory in GOALURATE_MEDHISTORYS:
            self.assertIn(f"{medhistory}_form", self.response.context_data)  # type: ignore
            self.assertIsInstance(
                self.response.context_data[f"{medhistory}_form"],
                self.view.medhistorys[medhistory]["form"],  # type: ignore
            )
            self.assertIsInstance(
                self.response.context_data[f"{medhistory}_form"].instance,  # type: ignore
                self.view.medhistorys[medhistory]["model"],
            )
        # Test that the ultaid is None
        self.assertFalse(self.response.context_data.get("ultaid"))

    def test__get_context_data_with_ultaid(self):
        request = self.factory.get(reverse("goalurates:ultaid-create", kwargs={"ultaid": self.ultaid.id}))
        request.htmx = False
        response = self.view.as_view()(request, ultaid=self.ultaid.id)
        self.assertEqual(response.context_data.get("ultaid"), self.ultaid.id)

    def test__get_form_kwargs(self):
        view = self.view(request=self.request)
        kwargs = view.get_form_kwargs()
        self.assertFalse(kwargs.get("htmx"))

    def test__get_form_kwargs_htmx(self):
        self.request.htmx = True
        view = self.view(request=self.request)
        kwargs = view.get_form_kwargs()
        self.assertTrue(kwargs.get("htmx"))

    def test__get_template_name(self):
        self.assertEqual(self.response.template_name, ["goalurates/goalurate_form.html"])

    def test__get_template_name_htmx(self):
        request = self.factory.get(reverse("goalurates:create"))
        request.htmx = True
        response = self.view.as_view()(request)
        self.assertEqual(response.template_name, ["goalurates/partials/goalurate_form.html"])

    def test__post_no_medhistorys(self):
        data = {
            f"{MedHistoryTypes.EROSIONS}-value": False,
            f"{MedHistoryTypes.TOPHI}-value": False,
        }
        response = self.client.post(reverse("goalurates:create"), data=data)
        tests_print_response_form_errors(response)
        self.assertEqual(response.status_code, 302)
        goal_urate = GoalUrate.objects.first()
        self.assertEqual(response.url, reverse("goalurates:detail", kwargs={"pk": goal_urate.id}))
        self.assertEqual(goal_urate.ultaid, None)
        self.assertFalse(goal_urate.medhistorys.all())

    def test__post_creates_medhistorys(self):
        data = {
            f"{MedHistoryTypes.EROSIONS}-value": True,
            f"{MedHistoryTypes.TOPHI}-value": True,
        }
        response = self.client.post(reverse("goalurates:create"), data=data)
        tests_print_response_form_errors(response)
        self.assertEqual(response.status_code, 302)
        goal_urate = GoalUrate.objects.first()
        erosions = Erosions.objects.first()
        tophi = Tophi.objects.first()
        self.assertIn(erosions, goal_urate.medhistorys.all())
        self.assertIn(tophi, goal_urate.medhistorys.all())

    def test__post_creates_goalurate_with_ultaid(self):
        data = {
            f"{MedHistoryTypes.EROSIONS}-value": True,
            f"{MedHistoryTypes.TOPHI}-value": True,
        }
        response = self.client.post(reverse("goalurates:ultaid-create", kwargs={"ultaid": self.ultaid.id}), data=data)
        tests_print_response_form_errors(response)
        self.assertEqual(response.status_code, 302)
        goal_urate = GoalUrate.objects.first()
        self.assertTrue(goal_urate.ultaid)
        self.assertEqual(goal_urate.ultaid, self.ultaid)

    def test__post_returns_errors(self):
        data = {
            f"{MedHistoryTypes.EROSIONS}-value": "",
            f"{MedHistoryTypes.TOPHI}-value": "",
        }
        response = self.client.post(reverse("goalurates:create"), data=data)
        self.assertEqual(response.status_code, 200)
        # Assert that the form is returned with errors
        self.assertIn("form", response.context)
        self.assertTrue(response.context[f"{MedHistoryTypes.EROSIONS}_form"].errors)
        self.assertTrue(response.context[f"{MedHistoryTypes.TOPHI}_form"].errors)


class TestGoalUrateDetail(TestCase):
    def setUp(self):
        self.goalurate = GoalUrateFactory()
        self.view: GoalUrateDetail = GoalUrateDetail
        self.request = RequestFactory().get(reverse("goalurates:detail", kwargs={"pk": self.goalurate.id}))
        self.response = self.view.as_view()(self.request, pk=self.goalurate.id)
        self.content_qs = Content.objects.filter(context=Contexts.GOALURATE, tag=Tags.EXPLANATION, slug__isnull=False)
        self.factory = RequestFactory()

    def test__contents(self):
        view_instance = self.view()
        self.assertTrue(isinstance(view_instance.contents, QuerySet))
        for content in view_instance.contents:
            self.assertIn(content, self.content_qs)
        for content in self.content_qs:
            self.assertIn(content, view_instance.contents)

    def test__dispatch_redirects_if_goalurate_user(self):
        """Test that the dispatch() method redirects to the Pseudopatient DetailView if the
        GoalUrate has a user."""
        user_gu = GoalUrateUserFactory()
        request = self.factory.get("/fake-url/")
        request.user = AnonymousUser()
        response = self.view.as_view()(request, pk=user_gu.pk)
        assert response.status_code == 302
        assert response.url == reverse("goalurates:pseudopatient-detail", kwargs={"username": user_gu.user.username})

    def test__get_context_data(self):
        view_instance = self.view()
        for content in view_instance.contents:
            self.assertIn(content.slug, self.response.context_data)
            self.assertEqual(self.response.context_data[content.slug], {content.tag: content})

    def test__get_queryset(self):
        qs = self.view(kwargs={"pk": self.goalurate.pk}).get_queryset()
        self.assertTrue(isinstance(qs, QuerySet))
        self.assertEqual(qs.first(), self.goalurate)
        self.assertTrue(hasattr(qs.first(), "medhistorys_qs"))


class TestGoalUrateUpdate(TestCase):
    def setUp(self):
        self.goalurate = GoalUrateFactory(erosions=True, tophi=True)
        self.view: GoalUrateUpdate = GoalUrateUpdate
        self.request = RequestFactory().get(reverse("goalurates:update", kwargs={"pk": self.goalurate.id}))
        self.request.htmx = False
        self.response = self.view.as_view()(self.request, pk=self.goalurate.id)
        self.ultaid = UltAidFactory()
        self.factory = RequestFactory()

    def test__get_context_data(self):
        for medhistory in GOALURATE_MEDHISTORYS:
            self.assertIn(f"{medhistory}_form", self.response.context_data)  # type: ignore
            self.assertIsInstance(
                self.response.context_data[f"{medhistory}_form"],
                self.view.medhistorys[medhistory]["form"],  # type: ignore
            )
            self.assertEqual(
                self.response.context_data[f"{medhistory}_form"].instance,  # type: ignore
                apps.get_model(f"medhistorys.{medhistory.value}").objects.get(),
            )

    def test__dispatch_redirects_if_goalurate_user(self):
        """Test that the dispatch() method redirects to the Pseudopatient DetailView if the
        GoalUrate has a user."""
        user_gu = GoalUrateUserFactory()
        request = self.factory.get("/fake-url/")
        request.user = AnonymousUser()
        response = self.view.as_view()(request, pk=user_gu.pk)
        assert response.status_code == 302
        assert response.url == reverse("goalurates:pseudopatient-update", kwargs={"username": user_gu.user.username})

    def test__get_form_kwargs(self):
        view = self.view(request=self.request)
        kwargs = view.get_form_kwargs()
        self.assertFalse(kwargs.get("htmx"))

    def test__get_form_kwargs_htmx(self):
        self.request.htmx = True
        view = self.view(request=self.request)
        kwargs = view.get_form_kwargs()
        self.assertTrue(kwargs.get("htmx"))

    def test__get_queryset(self):
        qs = self.view(kwargs={"pk": self.goalurate.pk}).get_queryset()
        self.assertTrue(isinstance(qs, QuerySet))
        self.assertEqual(qs.first(), self.goalurate)
        self.assertTrue(hasattr(qs.first(), "medhistorys_qs"))

    def test__get_template_names(self):
        self.assertEqual(self.response.template_name, ["goalurates/goalurate_form.html"])

    def test__get_template_names_htmx(self):
        self.request.htmx = True
        response = self.view.as_view()(self.request, pk=self.goalurate.id)
        self.assertEqual(response.template_name, ["goalurates/partials/goalurate_form.html"])

    def test__post_deletes_medhistorys(self):
        data = {
            f"{MedHistoryTypes.EROSIONS}-value": False,
            f"{MedHistoryTypes.TOPHI}-value": False,
        }
        response = self.client.post(reverse("goalurates:update", kwargs={"pk": self.goalurate.id}), data=data)
        tests_print_response_form_errors(response)
        self.assertEqual(response.status_code, 302)
        goal_urate = GoalUrate.objects.first()
        self.assertEqual(response.url, reverse("goalurates:detail", kwargs={"pk": goal_urate.id}) + "?updated=True")
        self.assertIsNone(goal_urate.ultaid)
        self.assertFalse(goal_urate.medhistorys.all())
        self.assertFalse(Erosions.objects.all())
        self.assertFalse(Tophi.objects.all())
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)

    def test__post_adds_medhistorys(self):
        goalurate = GoalUrateFactory()
        self.assertEqual(goalurate.goal_urate, GoalUrates.SIX)
        data = {
            f"{MedHistoryTypes.EROSIONS}-value": True,
            f"{MedHistoryTypes.TOPHI}-value": True,
        }
        response = self.client.post(reverse("goalurates:update", kwargs={"pk": goalurate.id}), data=data)
        tests_print_response_form_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(goalurate.medhistorys.all())
        self.assertTrue(goalurate.medhistorys.get(medhistorytype=MedHistoryTypes.EROSIONS))
        self.assertTrue(goalurate.medhistorys.get(medhistorytype=MedHistoryTypes.TOPHI))
        goalurate.refresh_from_db()
        self.assertEqual(goalurate.goal_urate, GoalUrates.FIVE)


class TestGoalUratePseudopatientCreate(TestCase):
    """Tests for the GoalUratePseudopatientCreate view."""

    def setUp(self):
        self.anon_psp = PseudopatientPlusFactory()
        self.provider = UserFactory()
        self.admin = UserFactory(role=Roles.ADMIN)
        self.prov_psp = PseudopatientPlusFactory(provider=self.provider)
        self.admin_psp = PseudopatientPlusFactory(provider=self.admin)
        self.anon = AnonymousUser()
        self.view = GoalUratePseudopatientCreate
        self.factory = RequestFactory()
        for _ in range(5):
            PseudopatientPlusFactory()

    def dummy_get_response(self, request: HttpRequest):
        return None

    def test__ckddetail(self):
        """Tests the ckddetail cached_property."""
        self.assertFalse(self.view().ckddetail)

    def test__goutdetail(self):
        """Tests the goutdetail cached_property."""
        self.assertFalse(self.view().goutdetail)

    def test__dispatch(self):
        """Test that the dispatch method sets the object to the GoalUrate model and
        redirects to the DetailView if a User already has a GoalUrate."""
        # Create a GoalUrate for the User
        GoalUrateFactory(user=self.anon_psp)
        # Create a request and set the user to the provider
        request = self.factory.get(
            reverse("goalurates:pseudopatient-create", kwargs={"username": self.anon_psp.username})
        )
        # Set the request's user
        request.user = self.anon
        # Instantiate the view
        view = self.view()
        # Set up the view
        view.setup(request, username=self.anon_psp.username)
        # Add messaging middleware
        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)
        # Call the dispatch method
        response = view.dispatch(request, username=self.anon_psp.username)
        # Assert that dispatch() set the object attr on the view
        self.assertTrue(hasattr(view, "object"))
        self.assertEqual(view.object, GoalUrate)
        # Assert that dispatch() redirected to the DetailView
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, reverse("goalurates:pseudopatient-detail", kwargs={"username": self.anon_psp.username})
        )

    def test__get_context_data_medhistorys(self):
        """Test that the context data includes the user's related models."""
        for user in Pseudopatient.objects.all():
            request = self.factory.get("/fake-url/")
            if user.profile.provider:
                request.user = user.profile.provider
            else:
                request.user = self.anon
            kwargs = {"username": user.username}
            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            for mh in user.medhistory_set.all():
                if mh.medhistorytype in GOALURATE_MEDHISTORYS:
                    assert f"{mh.medhistorytype}_form" in response.context_data
                    assert response.context_data[f"{mh.medhistorytype}_form"].instance == mh
                    assert response.context_data[f"{mh.medhistorytype}_form"].instance._state.adding is False
                    assert response.context_data[f"{mh.medhistorytype}_form"].initial == {
                        f"{mh.medhistorytype}-value": True
                    }
                else:
                    assert f"{mh.medhistorytype}_form" not in response.context_data
            for mhtype in GOALURATE_MEDHISTORYS:
                assert f"{mhtype}_form" in response.context_data
                if mhtype not in user.medhistory_set.values_list("medhistorytype", flat=True):
                    assert response.context_data[f"{mhtype}_form"].instance._state.adding is True
                    assert response.context_data[f"{mhtype}_form"].initial == {f"{mhtype}-value": None}
            assert "ckddetail_form" not in response.context_data
            assert "goutdetail_form" not in response.context_data

    def test__get_permission_object(self):
        """Test the get_permission_object() method for the view."""
        request = self.factory.get("/fake-url/")
        request.user = self.anon
        kwargs = {"username": self.anon_psp.username}
        view = self.view()
        # https://stackoverflow.com/questions/33645780/how-to-unit-test-methods-inside-djangos-class-based-views
        view.setup(request, **kwargs)
        view.user = self.anon_psp
        permission_object = view.get_permission_object()
        self.assertEqual(permission_object, self.anon_psp)

    def test__get_user_queryset(self):
        """Test the get_user_queryset() method for the view."""
        request = self.factory.get("/fake-url/")
        kwargs = {"username": self.anon_psp.username}
        view = self.view()
        view.setup(request, **kwargs)
        qs = view.get_user_queryset(view.kwargs["username"])
        self.assertTrue(isinstance(qs, QuerySet))
        qs = qs.get()
        self.assertTrue(isinstance(qs, User))
        self.assertTrue(hasattr(qs, "medhistorys_qs"))

    def test__post(self):
        """Test the post() method for the view."""
        request = self.factory.post("/fake-url/")
        request.user = self.anon
        kwargs = {"username": self.anon_psp.username}
        response = self.view.as_view()(request, **kwargs)
        assert response.status_code == 200

    def test__post_sets_object_user(self):
        """Test that the post() method for the view sets the user on the object."""
        # Create some fake data for a User's FlareAid
        data = create_goalurate_data()
        response = self.client.post(
            reverse("goalurates:pseudopatient-create", kwargs={"username": self.anon_psp.username}), data=data
        )
        tests_print_response_form_errors(response)
        assert response.status_code == 302
        assert GoalUrate.objects.filter(user=self.anon_psp).exists()
        goalurate = GoalUrate.objects.last()
        assert goalurate.user
        assert goalurate.user == self.anon_psp

    def test__post_creates_and_deletes_medhistorys(self):
        """Test that the post() method correctly creates and deletes MedHistorys."""
        for psp in Pseudopatient.objects.select_related("pseudopatientprofile").all():
            medhistorys = list(psp.medhistory_set.all()).copy()
            data = create_goalurate_data()
            if psp.pseudopatientprofile.provider:
                self.client.force_login(psp.pseudopatientprofile.provider)
            response = self.client.post(
                reverse("goalurates:pseudopatient-create", kwargs={"username": psp.username}), data=data
            )
            assert response.status_code == 302
            for mh in [mh for mh in medhistorys if mh.medhistorytype in GOALURATE_MEDHISTORYS]:
                if not data[f"{mh.medhistorytype}-value"]:
                    assert not MedHistory.objects.filter(user=psp, medhistorytype=mh.medhistorytype).exists()
                else:
                    assert MedHistory.objects.filter(user=psp, medhistorytype=mh.medhistorytype).exists()
            for mh in GOALURATE_MEDHISTORYS:
                if not data[f"{mh}-value"]:
                    assert not MedHistory.objects.filter(user=psp, medhistorytype=mh).exists()
                else:
                    assert MedHistory.objects.filter(user=psp, medhistorytype=mh).exists()

    def test__post_creates_goalurates_with_correct_recommendations(self):
        """Test that the post() method correctly creates GoalUrates with the correct recommendations."""
        for psp in Pseudopatient.objects.select_related("pseudopatientprofile").all():
            data = create_goalurate_data()
            if psp.pseudopatientprofile.provider:
                self.client.force_login(psp.pseudopatientprofile.provider)
            response = self.client.post(
                reverse("goalurates:pseudopatient-create", kwargs={"username": psp.username}), data=data
            )
            assert response.status_code == 302
            if psp.medhistory_set.filter(medhistorytype__in=GOALURATE_MEDHISTORYS).exists():
                assert psp.goalurate.goal_urate == GoalUrates.FIVE
            else:
                assert psp.goalurate.goal_urate == GoalUrates.SIX

    def test__post_returns_errors(self):
        """Test that the post() method returns errors if the form is invalid."""
        data = create_goalurate_data()
        # Set the required fields to empty strings to trigger errors (True or False required)
        for mh in GOALURATE_MEDHISTORYS:
            data[f"{mh}-value"] = ""

        response = self.client.post(
            reverse("goalurates:pseudopatient-create", kwargs={"username": self.anon_psp.username}), data=data
        )
        assert response.status_code == 200
        # Assert that the form is returned with errors
        for mh in GOALURATE_MEDHISTORYS:
            assert response.context[f"{mh}_form"].errors
        assert not response.context["form"].errors

    def test__rules(self):
        """Test that django-rules are implemented properly for the view."""
        # Test that a user who isn't logged in can't create a GoalUrate for a Pseudopatient
        # with a provider
        response = self.client.get(
            reverse("goalurates:pseudopatient-create", kwargs={"username": self.prov_psp.username})
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/accounts/login/?next=/goalurates/{self.prov_psp.username}/create/")
        response = self.client.get(
            reverse("goalurates:pseudopatient-create", kwargs={"username": self.admin_psp.username})
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/accounts/login/?next=/goalurates/{self.admin_psp.username}/create/")
        # Test that anyone can create a GoalUrate for a Pseudopatient without a provider
        response = self.client.get(
            reverse("goalurates:pseudopatient-create", kwargs={"username": self.anon_psp.username})
        )
        self.assertEqual(response.status_code, 200)
        self.client.force_login(self.provider)
        response = self.client.get(
            reverse("goalurates:pseudopatient-create", kwargs={"username": self.anon_psp.username})
        )
        self.assertEqual(response.status_code, 200)
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("goalurates:pseudopatient-create", kwargs={"username": self.anon_psp.username})
        )
        self.assertEqual(response.status_code, 200)

        # Test that a Provider can only create a GoalUrate for a Pseudopatient with a provider
        # if that provider is his or her self
        self.client.force_login(self.provider)
        response = self.client.get(
            reverse("goalurates:pseudopatient-create", kwargs={"username": self.prov_psp.username})
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse("goalurates:pseudopatient-create", kwargs={"username": self.admin_psp.username})
        )
        self.assertEqual(response.status_code, 403)

        # Test that an Admin can only create a GoalUrate for a Pseudopatient with a provider
        # if that provider is his or her self
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("goalurates:pseudopatient-create", kwargs={"username": self.admin_psp.username})
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse("goalurates:pseudopatient-create", kwargs={"username": self.prov_psp.username})
        )
        self.assertEqual(response.status_code, 403)


class TestGoalUratePseudopatientDetail(TestCase):
    """Tests for the GoalUratePseudopatientDetail view."""

    def setUp(self):
        self.anon_psp = PseudopatientPlusFactory()
        self.provider = UserFactory()
        self.admin = UserFactory(role=Roles.ADMIN)
        self.prov_psp = PseudopatientPlusFactory(provider=self.provider)
        self.admin_psp = PseudopatientPlusFactory(provider=self.admin)
        self.anon = AnonymousUser()
        self.view = GoalUratePseudopatientDetail
        self.factory = RequestFactory()
        for _ in range(5):
            PseudopatientPlusFactory()
        for psp in Pseudopatient.objects.all():
            GoalUrateUserFactory(user=psp)
        self.empty_psp = PseudopatientPlusFactory()

    def test__assign_goalurate_attrs_from_user(self):
        """Test that the assign_goalurate_attrs_from_user() method for the view
        transfers attributes from the QuerySet, which started with a User,
        to the GoalUrate object."""
        gu = GoalUrate.objects.filter(user__isnull=False).first()
        view = self.view()
        request = self.factory.get("/fake-url/")
        view.setup(request, username=gu.user.username)
        assert not hasattr(gu, "medhistorys_qs")
        view.assign_goalurate_attrs_from_user(goalurate=gu, user=goalurate_user_qs(gu.user.username).get())
        assert hasattr(gu, "medhistorys_qs")

    def test__dispatch(self):
        """Test the dispatch() method for the view. Should redirect to CreateView
        if the user doesn't have a GoalUrate."""
        response = self.client.get(
            reverse("goalurates:pseudopatient-detail", kwargs={"username": self.anon_psp.username})
        )
        self.assertEqual(response.status_code, 200)
        # Test that dispatch redirects to the pseudopatient-create FlareAid view when the user doesn't have a FlareAid
        self.assertRedirects(
            self.client.get(reverse("goalurates:pseudopatient-detail", kwargs={"username": self.empty_psp.username})),
            reverse("goalurates:pseudopatient-create", kwargs={"username": self.empty_psp.username}),
        )

    def test__get_context_data(self):
        """Test the get_context_data() method for the view."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, username=self.anon_psp.username)
        view.object = view.get_object()
        context = view.get_context_data()
        assert "patient" in context
        assert context["patient"] == self.anon_psp
        contents = Content.objects.filter(context=Contexts.GOALURATE, tag=Tags.EXPLANATION, slug__isnull=False)
        for mh in GOALURATE_MEDHISTORYS:
            assert mh.lower() in context
            assert "explanation" in context[mh.lower()]
            assert context[mh.lower()]["explanation"] in contents

    def test__get_object_sets_user(self):
        """Test that the get_object() method sets the user attribute."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, username=self.anon_psp.username)
        view.get_object()
        assert hasattr(view, "user")
        assert view.user == self.anon_psp

    def test__get_object_raises_DoesNotExist(self):
        """Test that the get_object() method raises DoesNotExist when the user
        doesn't have a FlareAid."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, username=self.empty_psp.username)
        with self.assertRaises(ObjectDoesNotExist):
            view.get_object()

    def test__get_permission_object(self):
        """Test that the get_permission_object() method returns the
        view's object, which must have already been set."""
        request = self.factory.get("/fake-url/")
        request.user = self.anon
        view = self.view()
        view.setup(request, username=self.anon_psp.username)
        view.dispatch(request, username=self.anon_psp.username)
        pm_obj = view.get_permission_object()
        assert pm_obj == view.object

    def test__get_queryset(self):
        """Test the get_queryset() method for the view."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, username=self.anon_psp.username)
        with self.assertNumQueries(2):
            qs = view.get_queryset().get()
        assert qs == self.anon_psp
        assert hasattr(qs, "goalurate") and qs.goalurate == self.anon_psp.goalurate
        assert hasattr(qs, "medhistorys_qs")
        psp_mhs = self.anon_psp.medhistory_set.filter(medhistorytype__in=GOALURATE_MEDHISTORYS).all()
        for mh in qs.medhistorys_qs:
            assert mh in psp_mhs

    def test__get_updates_GoalUrate(self):
        """Test that the get() method for the view updates the GoalUrate."""
        # Create a GoalUrate for the User who doesn't have one and such that the
        # goal urate is 6
        gu = GoalUrateUserFactory(user=self.empty_psp, erosions=False, tophi=False, goal_urate=GoalUrates.SIX)
        # Test that this is the case and then create the medhistorys that should make the goal urate
        # 5 when the GoalUrate is updated
        self.assertFalse(self.empty_psp.medhistory_set.filter(medhistorytype__in=GOALURATE_MEDHISTORYS).exists())
        ErosionsFactory(user=self.empty_psp)
        TophiFactory(user=self.empty_psp)
        self.assertTrue(self.empty_psp.medhistory_set.filter(medhistorytype__in=GOALURATE_MEDHISTORYS).exists())
        self.assertEqual(gu.goal_urate, GoalUrates.SIX)
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, username=self.empty_psp.username)
        view.object = view.get_object()
        view.get(request)
        gu.refresh_from_db()
        self.assertEqual(gu.goal_urate, GoalUrates.FIVE)

    def test__get_does_not_update_GoalUrate(self):
        """Same as above, except the url includes the url parameter ?updated=True."""
        # Create a GoalUrate for the User who doesn't have one and such that the
        # goal urate is 6
        gu = GoalUrateUserFactory(user=self.empty_psp, erosions=False, tophi=False, goal_urate=GoalUrates.SIX)
        # Test that this is the case and then create the medhistorys that should make the goal urate
        # 5 when the GoalUrate is updated
        self.assertFalse(self.empty_psp.medhistory_set.filter(medhistorytype__in=GOALURATE_MEDHISTORYS).exists())
        ErosionsFactory(user=self.empty_psp)
        TophiFactory(user=self.empty_psp)
        self.assertTrue(self.empty_psp.medhistory_set.filter(medhistorytype__in=GOALURATE_MEDHISTORYS).exists())
        self.assertEqual(gu.goal_urate, GoalUrates.SIX)
        request = self.factory.get("/fake-url/?updated=True")
        view = self.view()
        view.setup(request, username=self.empty_psp.username)
        view.object = view.get_object()
        view.get(request)
        gu.refresh_from_db()
        self.assertEqual(gu.goal_urate, GoalUrates.SIX)


class TestGoalUratePseudopatientUpdate(TestCase):
    """Tests for the GoalUratePseudopatientUpdate view."""

    def setUp(self):
        self.anon_psp = PseudopatientPlusFactory()
        self.provider = UserFactory()
        self.admin = UserFactory(role=Roles.ADMIN)
        self.prov_psp = PseudopatientPlusFactory(provider=self.provider)
        self.admin_psp = PseudopatientPlusFactory(provider=self.admin)
        self.anon = AnonymousUser()
        self.view = GoalUratePseudopatientUpdate
        self.factory = RequestFactory()
        for _ in range(5):
            PseudopatientPlusFactory()
        for psp in Pseudopatient.objects.all():
            GoalUrateUserFactory(user=psp)
        self.empty_psp = PseudopatientPlusFactory()

    def dummy_get_response(self, request: HttpRequest):
        return None

    def test__ckddetail(self):
        """Tests the ckddetail cached_property."""
        self.assertFalse(self.view().ckddetail)

    def test__goutdetail(self):
        """Tests the goutdetail cached_property."""
        self.assertFalse(self.view().goutdetail)

    def test__dispatch(self):
        """Test that the dispatch method sets the object to the GoalUrate model and
        redirects to the DetailView if a User already has a GoalUrate."""
        # Create a request and set the user to the provider
        request = self.factory.get(
            reverse("goalurates:pseudopatient-update", kwargs={"username": self.anon_psp.username})
        )
        # Set the request's user
        request.user = self.anon
        # Instantiate the view
        view = self.view()
        # Set up the view
        view.setup(request, username=self.anon_psp.username)
        # Add messaging and session middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)
        # Call the dispatch method
        response = view.dispatch(request, username=self.anon_psp.username)
        # Assert that dispatch() set the object attr on the view
        self.assertTrue(hasattr(view, "object"))
        self.assertEqual(view.object, self.anon_psp.goalurate)
        self.assertEqual(response.status_code, 200)

    def test__dispatch_redirects_to_createview(self):
        """Test that the dispatch() method redirects to the CreateView if the user
        doesn't have a GoalUrate."""
        request = self.factory.get(
            reverse("goalurates:pseudopatient-update", kwargs={"username": self.empty_psp.username})
        )
        request.user = self.anon
        view = self.view()
        view.setup(request, username=self.empty_psp.username)
        # Add messaging and session middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)
        response = view.dispatch(request, username=self.empty_psp.username)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, reverse("goalurates:pseudopatient-create", kwargs={"username": self.empty_psp.username})
        )

    def test__get_context_data_medhistorys(self):
        """Test that the context data includes the user's related models."""
        for user in Pseudopatient.objects.all():
            request = self.factory.get("/fake-url/")
            if user.profile.provider:
                request.user = user.profile.provider
            else:
                request.user = self.anon
            # Add messaging and session middleware to the request
            SessionMiddleware(self.dummy_get_response).process_request(request)
            MessageMiddleware(self.dummy_get_response).process_request(request)
            kwargs = {"username": user.username}
            response = self.view.as_view()(request, **kwargs)
            if not hasattr(user, "goalurate"):
                assert response.status_code == 302
            else:
                assert response.status_code == 200
                for mh in user.medhistory_set.all():
                    if mh.medhistorytype in GOALURATE_MEDHISTORYS:
                        assert f"{mh.medhistorytype}_form" in response.context_data
                        assert response.context_data[f"{mh.medhistorytype}_form"].instance == mh
                        assert response.context_data[f"{mh.medhistorytype}_form"].instance._state.adding is False
                        assert response.context_data[f"{mh.medhistorytype}_form"].initial == {
                            f"{mh.medhistorytype}-value": True
                        }
                    else:
                        assert f"{mh.medhistorytype}_form" not in response.context_data
                for mhtype in GOALURATE_MEDHISTORYS:
                    assert f"{mhtype}_form" in response.context_data
                    if mhtype not in user.medhistory_set.values_list("medhistorytype", flat=True):
                        assert response.context_data[f"{mhtype}_form"].instance._state.adding is True
                        assert response.context_data[f"{mhtype}_form"].initial == {f"{mhtype}-value": False}
                assert "ckddetail_form" not in response.context_data
                assert "goutdetail_form" not in response.context_data

    def test__get_object(self):
        """Test the get_object() method, which should set the view's user attr and return
        the user's GoalUrate."""
        # Create a request and set the user
        request = self.factory.get("/fake-url/")
        request.user = self.anon
        # Instantiate the view
        view = self.view()
        # Set up the view
        view.setup(request, username=self.anon_psp.username)
        # Call the get_object() method on the view and set the return value
        obj = view.get_object()
        # Assert that the view's user attr was set
        self.assertTrue(hasattr(view, "user"))
        self.assertEqual(view.user, self.anon_psp)
        # Assert that the returned object is the user's goalurate
        self.assertEqual(obj, self.anon_psp.goalurate)
        # Do the above again except test that get_object returns a DoesNotExist when
        # the user doesn't have a GoalUrate
        view.setup(request, username=self.empty_psp.username)
        with self.assertRaises(ObjectDoesNotExist):
            view.get_object()

    def test__get_permission_object(self):
        """Test the get_permission_object() method for the view."""
        request = self.factory.get("/fake-url/")
        request.user = self.anon
        kwargs = {"username": self.anon_psp.username}
        view = self.view()
        view.setup(request, **kwargs)
        view.object = self.anon_psp.goalurate
        permission_object = view.get_permission_object()
        self.assertEqual(permission_object, self.anon_psp.goalurate)

    def test__get_user_queryset(self):
        """Test the get_user_queryset() method for the view."""

        goalurate = self.anon_psp.goalurate
        request = self.factory.get("/fake-url/")
        kwargs = {"username": self.anon_psp.username}
        view = self.view()
        view.setup(request, **kwargs)
        qs = view.get_user_queryset(view.kwargs["username"])
        self.assertTrue(isinstance(qs, QuerySet))
        with self.assertNumQueries(2):
            qs = qs.get()
            self.assertTrue(isinstance(qs, User))
            self.assertEqual(qs, self.anon_psp)
            self.assertEqual(qs.goalurate, goalurate)
            self.assertTrue(hasattr(qs, "medhistorys_qs"))

    def test__post(self):
        """Test the post() method for the view."""
        request = self.factory.post("/fake-url/")
        request.user = self.anon
        kwargs = {"username": self.anon_psp.username}
        response = self.view.as_view()(request, **kwargs)
        assert response.status_code == 200

    def test__post_updates_medhistorys(self):
        """Test that the post() method correctly creates and deletes MedHistorys."""
        for psp in Pseudopatient.objects.select_related("pseudopatientprofile", "goalurate").all():
            medhistorys = list(psp.medhistory_set.all()).copy()
            data = create_goalurate_data()
            if psp.pseudopatientprofile.provider:
                self.client.force_login(psp.pseudopatientprofile.provider)
            response = self.client.post(
                reverse("goalurates:pseudopatient-update", kwargs={"username": psp.username}), data=data
            )
            assert response.status_code == 302
            if hasattr(psp, "goalurate"):
                for mh in [mh for mh in medhistorys if mh.medhistorytype in GOALURATE_MEDHISTORYS]:
                    if not data[f"{mh.medhistorytype}-value"]:
                        assert not MedHistory.objects.filter(user=psp, medhistorytype=mh.medhistorytype).exists()
                    else:
                        assert MedHistory.objects.filter(user=psp, medhistorytype=mh.medhistorytype).exists()
                for mh in GOALURATE_MEDHISTORYS:
                    if not data[f"{mh}-value"]:
                        assert not MedHistory.objects.filter(user=psp, medhistorytype=mh).exists()
                    else:
                        assert MedHistory.objects.filter(user=psp, medhistorytype=mh).exists()
            else:
                assert response.url == reverse("goalurates:pseudopatient-create", kwargs={"username": psp.username})

    def test__post_updates_goalurates_to_correct_recommendations(self):
        """Test that the post() method correctly creates GoalUrates with the correct recommendations."""
        for psp in Pseudopatient.objects.select_related("pseudopatientprofile", "goalurate").all():
            data = create_goalurate_data()
            if psp.pseudopatientprofile.provider:
                self.client.force_login(psp.pseudopatientprofile.provider)
            response = self.client.post(
                reverse("goalurates:pseudopatient-update", kwargs={"username": psp.username}), data=data
            )
            assert response.status_code == 302
            if hasattr(psp, "goalurate"):
                psp.goalurate.refresh_from_db()
                if psp.medhistory_set.filter(medhistorytype__in=GOALURATE_MEDHISTORYS).exists():
                    assert psp.goalurate.goal_urate == GoalUrates.FIVE
                else:
                    assert psp.goalurate.goal_urate == GoalUrates.SIX
            else:
                assert response.url == reverse("goalurates:pseudopatient-create", kwargs={"username": psp.username})

    def test__post_returns_errors(self):
        """Test that the post() method returns errors if the form is invalid."""
        data = create_goalurate_data()
        # Set the required fields to empty strings to trigger errors (True or False required)
        for mh in GOALURATE_MEDHISTORYS:
            data[f"{mh}-value"] = ""

        response = self.client.post(
            reverse("goalurates:pseudopatient-update", kwargs={"username": self.anon_psp.username}), data=data
        )
        assert response.status_code == 200
        # Assert that the form is returned with errors
        for mh in GOALURATE_MEDHISTORYS:
            assert response.context[f"{mh}_form"].errors
        assert not response.context["form"].errors

    def test__rules(self):
        """Test that django-rules are implemented properly for the view."""
        # Test that a user who isn't logged in can't update a GoalUrate for a Pseudopatient
        # with a provider
        response = self.client.get(
            reverse("goalurates:pseudopatient-update", kwargs={"username": self.prov_psp.username})
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/accounts/login/?next=/goalurates/{self.prov_psp.username}/update/")
        response = self.client.get(
            reverse("goalurates:pseudopatient-update", kwargs={"username": self.admin_psp.username})
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/accounts/login/?next=/goalurates/{self.admin_psp.username}/update/")
        # Test that anyone can update a GoalUrate for a Pseudopatient without a provider
        response = self.client.get(
            reverse("goalurates:pseudopatient-update", kwargs={"username": self.anon_psp.username})
        )
        self.assertEqual(response.status_code, 200)
        self.client.force_login(self.provider)
        response = self.client.get(
            reverse("goalurates:pseudopatient-update", kwargs={"username": self.anon_psp.username})
        )
        self.assertEqual(response.status_code, 200)
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("goalurates:pseudopatient-update", kwargs={"username": self.anon_psp.username})
        )
        self.assertEqual(response.status_code, 200)

        # Test that a Provider can only update a GoalUrate for a Pseudopatient with a provider
        # if that provider is his or her self
        self.client.force_login(self.provider)
        response = self.client.get(
            reverse("goalurates:pseudopatient-update", kwargs={"username": self.prov_psp.username})
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse("goalurates:pseudopatient-update", kwargs={"username": self.admin_psp.username})
        )
        self.assertEqual(response.status_code, 403)

        # Test that an Admin can only update a GoalUrate for a Pseudopatient with a provider
        # if that provider is his or her self
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("goalurates:pseudopatient-update", kwargs={"username": self.admin_psp.username})
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse("goalurates:pseudopatient-update", kwargs={"username": self.prov_psp.username})
        )
        self.assertEqual(response.status_code, 403)
