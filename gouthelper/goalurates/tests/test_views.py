import pytest  # type: ignore
from django.db.models import QuerySet  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore

from ...contents.choices import Contexts, Tags
from ...contents.models import Content
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.forms import ErosionsForm, TophiForm
from ...medhistorys.lists import GOALURATE_MEDHISTORYS
from ...medhistorys.models import Erosions, Tophi
from ...medhistorys.tests.factories import ErosionsFactory, TophiFactory
from ...ultaids.tests.factories import UltAidFactory
from ...utils.helpers.test_helpers import tests_print_form_errors
from ..choices import GoalUrates
from ..models import GoalUrate
from ..views import GoalUrateAbout, GoalUrateCreate, GoalUrateDetail, GoalUrateUpdate
from .factories import GoalUrateFactory

pytestmark = pytest.mark.django_db


@pytest.mark.usefixtures("contents_setup")
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
        tests_print_form_errors(response)
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
        tests_print_form_errors(response)
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
        tests_print_form_errors(response)
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


@pytest.mark.usefixtures("contents_setup")
class TestGoalUrateDetail(TestCase):
    def setUp(self):
        self.goalurate = GoalUrateFactory()
        self.view: GoalUrateDetail = GoalUrateDetail
        self.request = RequestFactory().get(reverse("goalurates:detail", kwargs={"pk": self.goalurate.id}))
        self.response = self.view.as_view()(self.request, pk=self.goalurate.id)
        self.content_qs = Content.objects.filter(context=Contexts.GOALURATE, tag=Tags.EXPLANATION, slug__isnull=False)

    def test__contents(self):
        view_instance = self.view()
        self.assertTrue(isinstance(view_instance.contents, QuerySet))
        for content in view_instance.contents:
            self.assertIn(content, self.content_qs)
        for content in self.content_qs:
            self.assertIn(content, view_instance.contents)

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
        self.goalurate = GoalUrateFactory()
        self.erosions = ErosionsFactory()
        self.tophi = TophiFactory()
        self.goalurate.medhistorys.add(self.erosions, self.tophi)
        self.view: GoalUrateUpdate = GoalUrateUpdate
        self.request = RequestFactory().get(reverse("goalurates:update", kwargs={"pk": self.goalurate.id}))
        self.request.htmx = False
        self.response = self.view.as_view()(self.request, pk=self.goalurate.id)
        self.ultaid = UltAidFactory()

    def test__get_context_data(self):
        for medhistory in GOALURATE_MEDHISTORYS:
            self.assertIn(f"{medhistory}_form", self.response.context_data)  # type: ignore
            self.assertIsInstance(
                self.response.context_data[f"{medhistory}_form"],
                self.view.medhistorys[medhistory]["form"],  # type: ignore
            )
            self.assertEqual(
                self.response.context_data[f"{medhistory}_form"].instance,  # type: ignore
                getattr(self, medhistory.value.lower()),
            )

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
        tests_print_form_errors(response)
        self.assertEqual(response.status_code, 302)
        goal_urate = GoalUrate.objects.first()
        self.assertEqual(response.url, reverse("goalurates:detail", kwargs={"pk": goal_urate.id}) + "?updated=True")
        self.assertEqual(goal_urate.ultaid, None)
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
        tests_print_form_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(goalurate.medhistorys.all())
        self.assertTrue(goalurate.medhistorys.get(medhistorytype=MedHistoryTypes.EROSIONS))
        self.assertTrue(goalurate.medhistorys.get(medhistorytype=MedHistoryTypes.TOPHI))
        goalurate.refresh_from_db()
        self.assertEqual(goalurate.goal_urate, GoalUrates.FIVE)
