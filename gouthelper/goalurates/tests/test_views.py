import pytest  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from django.contrib.auth.models import AnonymousUser  # type: ignore
from django.contrib.sessions.middleware import SessionMiddleware
from django.db.models import QuerySet  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore

from ...contents.choices import Contexts, Tags
from ...contents.models import Content
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.forms import ErosionsForm, TophiForm
from ...medhistorys.lists import GOALURATE_MEDHISTORYS
from ...medhistorys.models import Erosions, Tophi
from ...ppxs.tests.factories import create_ppx
from ...ultaids.models import UltAid
from ...ultaids.tests.factories import create_ultaid
from ...ults.models import Ult
from ...ults.tests.factories import create_ult
from ...utils.forms import forms_print_response_errors
from ...utils.test_helpers import dummy_get_response
from ..choices import GoalUrates
from ..models import GoalUrate
from ..views import GoalUrateAbout, GoalUrateCreate, GoalUrateDetail, GoalUrateUpdate
from .factories import create_goalurate

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
        self.request.user = AnonymousUser()
        SessionMiddleware(dummy_get_response).process_request(self.request)
        self.response = self.view.as_view()(self.request)
        self.ultaid = create_ultaid()

    def test__view_attrs(self):
        self.assertEqual(self.view.model, GoalUrate)
        self.assertEqual(self.view.form_class, GoalUrateCreate.form_class)
        self.assertIn(MedHistoryTypes.EROSIONS, self.view.MEDHISTORY_FORMS)
        self.assertEqual(self.view.MEDHISTORY_FORMS[MedHistoryTypes.EROSIONS], ErosionsForm)
        self.assertIn(MedHistoryTypes.TOPHI, self.view.MEDHISTORY_FORMS)
        self.assertEqual(self.view.MEDHISTORY_FORMS[MedHistoryTypes.TOPHI], TophiForm)

    def test__get_context_data(self):
        for medhistory in GOALURATE_MEDHISTORYS:
            self.assertIn(f"{medhistory}_form", self.response.context_data)  # type: ignore
            self.assertIsInstance(
                self.response.context_data[f"{medhistory}_form"],
                self.view.MEDHISTORY_FORMS[medhistory],  # type: ignore
            )
            self.assertIsInstance(
                self.response.context_data[f"{medhistory}_form"].instance,  # type: ignore
                self.view.MEDHISTORY_FORMS[medhistory]._meta.model,
            )
        # Test that the ultaid is None
        self.assertFalse(self.response.context_data.get("ultaid"))

    def test__get_context_data_with_ultaid(self):
        request = self.factory.get(reverse("goalurates:ultaid-create", kwargs={"ultaid": self.ultaid.id}))
        request.htmx = False
        request.user = AnonymousUser()
        SessionMiddleware(dummy_get_response).process_request(request)
        response = self.view.as_view()(request, ultaid=self.ultaid.id)
        self.assertEqual(response.context_data.get("ultaid"), self.ultaid)

    def test__get_form_kwargs(self):
        view = self.view()
        view.setup(self.request)
        view.set_forms()
        view.object = view.get_object()
        kwargs = view.get_form_kwargs()
        self.assertFalse(kwargs.get("htmx"))

    def test__get_form_kwargs_htmx(self):
        self.request.htmx = True
        view = self.view()
        view.setup(self.request)
        view.set_forms()
        view.object = view.get_object()
        kwargs = view.get_form_kwargs()
        self.assertTrue(kwargs.get("htmx"))

    def test__get_template_name(self):
        self.assertEqual(self.response.template_name, ["goalurates/goalurate_form.html"])

    def test__get_template_name_htmx(self):
        request = self.factory.get(reverse("goalurates:create"))
        request.htmx = True
        request.user = AnonymousUser()
        SessionMiddleware(dummy_get_response).process_request(request)
        response = self.view.as_view()(request)
        self.assertEqual(response.template_name, ["goalurates/partials/goalurate_form.html"])

    def test__post_no_medhistorys(self):
        data = {
            f"{MedHistoryTypes.EROSIONS}-value": False,
            f"{MedHistoryTypes.TOPHI}-value": False,
        }
        response = self.client.post(reverse("goalurates:create"), data=data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        goalurate = GoalUrate.objects.first()
        self.assertEqual(response.url, reverse("goalurates:detail", kwargs={"pk": goalurate.id}) + "?updated=True")
        self.assertEqual(goalurate.ultaid, None)
        self.assertFalse(goalurate.medhistory_set.all())

    def test__post_creates_medhistorys(self):
        data = {
            f"{MedHistoryTypes.EROSIONS}-value": True,
            f"{MedHistoryTypes.TOPHI}-value": True,
        }
        response = self.client.post(reverse("goalurates:create"), data=data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        goalurate = GoalUrate.objects.first()
        erosions = Erosions.objects.first()
        tophi = Tophi.objects.first()
        self.assertIn(erosions.pk, goalurate.medhistory_set.values_list("pk", flat=True))
        self.assertIn(tophi.pk, goalurate.medhistory_set.values_list("pk", flat=True))

    def test__post_creates_goalurate_with_ultaid(self):
        data = {
            f"{MedHistoryTypes.EROSIONS}-value": True,
            f"{MedHistoryTypes.TOPHI}-value": True,
        }
        response = self.client.post(reverse("goalurates:ultaid-create", kwargs={"ultaid": self.ultaid.id}), data=data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        goalurate = GoalUrate.objects.order_by("created").last()
        self.assertTrue(goalurate.ultaid)
        self.assertEqual(goalurate.ultaid, self.ultaid)

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

    def test__post_creates_goalurate_with_ppx(self):
        """Test that the post() method with a ppx url parameter creates a GoalUrate
        with the correct Ppx."""
        ppx = create_ppx()
        data = {
            f"{MedHistoryTypes.EROSIONS}-value": True,
            f"{MedHistoryTypes.TOPHI}-value": True,
        }
        response = self.client.post(reverse("goalurates:ppx-create", kwargs={"ppx": ppx.id}), data=data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(GoalUrate.objects.filter(ppx__id=ppx.pk).exists())
        goalurate = GoalUrate.objects.filter(ppx=ppx).get()
        self.assertEqual(ppx.goalurate, goalurate)

    def test__updates_ult_related_by_ultaid(self):
        ult = create_ult(mhs=[])
        self.assertFalse(ult.medhistory_set.all())
        ultaid = create_ultaid(mhs=[])
        ult.ultaid = ultaid
        ult.save()
        self.assertFalse(ultaid.medhistory_set.all())
        self.assertEqual(UltAid.objects.filter(ult=ult).get(), ultaid)
        self.assertEqual(Ult.objects.filter(ultaid=ultaid).get(), ult)
        data = {
            f"{MedHistoryTypes.EROSIONS}-value": True,
            f"{MedHistoryTypes.TOPHI}-value": False,
        }
        response = self.client.post(reverse("goalurates:ultaid-create", kwargs={"ultaid": ultaid.id}), data=data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ult.medhistory_set.filter(medhistorytype=MedHistoryTypes.EROSIONS).exists())
        self.assertFalse(ult.medhistory_set.filter(medhistorytype=MedHistoryTypes.TOPHI).exists())


class TestGoalUrateDetail(TestCase):
    def setUp(self):
        self.goalurate = create_goalurate()
        self.view: GoalUrateDetail = GoalUrateDetail
        self.request = RequestFactory().get(reverse("goalurates:detail", kwargs={"pk": self.goalurate.id}))
        self.request.user = AnonymousUser()
        self.response = self.view.as_view()(self.request, pk=self.goalurate.id)
        self.content_qs = Content.objects.filter(context=Contexts.GOALURATE, tag=Tags.EXPLANATION, slug__isnull=False)
        self.factory = RequestFactory()

    def test__get_queryset(self):
        qs = self.view(kwargs={"pk": self.goalurate.pk}).get_queryset()
        self.assertTrue(isinstance(qs, QuerySet))
        self.assertEqual(qs.first(), self.goalurate)
        self.assertTrue(hasattr(qs.first(), "medhistorys_qs"))


class TestGoalUrateUpdate(TestCase):
    def setUp(self):
        self.goalurate = create_goalurate(mhs=[*GOALURATE_MEDHISTORYS])
        self.view: GoalUrateUpdate = GoalUrateUpdate
        self.request = RequestFactory().get(reverse("goalurates:update", kwargs={"pk": self.goalurate.id}))
        self.request.htmx = False
        self.request.user = AnonymousUser()
        SessionMiddleware(dummy_get_response).process_request(self.request)
        self.response = self.view.as_view()(self.request, pk=self.goalurate.id)
        self.ultaid = create_ultaid()
        self.factory = RequestFactory()

    def test__get_context_data(self):
        gu_medhistorys = self.goalurate.medhistory_set.all()
        for medhistory in GOALURATE_MEDHISTORYS:
            self.assertIn(f"{medhistory}_form", self.response.context_data)  # type: ignore
            self.assertIsInstance(
                self.response.context_data[f"{medhistory}_form"],
                self.view.MEDHISTORY_FORMS[medhistory],  # type: ignore
            )
            gu_mh = next(iter([mh for mh in gu_medhistorys if mh.medhistorytype == medhistory]), None)
            if gu_mh:
                self.assertEqual(
                    self.response.context_data[f"{medhistory}_form"].instance,  # type: ignore
                    gu_mh,
                )
            else:
                self.assertIsNone(self.response.context_data[f"{medhistory}_form"].instance)

    def test__get_form_kwargs(self):
        view = self.view()
        view.setup(self.request, pk=self.goalurate.id)
        view.set_forms()
        view.object = view.get_object()
        kwargs = view.get_form_kwargs()
        self.assertFalse(kwargs.get("htmx"))

    def test__get_form_kwargs_htmx(self):
        self.request.htmx = True
        view = self.view()
        view.setup(self.request, pk=self.goalurate.id)
        view.set_forms()
        view.object = view.get_object()
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
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        goalurate = GoalUrate.objects.first()
        self.assertEqual(response.url, reverse("goalurates:detail", kwargs={"pk": goalurate.id}) + "?updated=True")
        self.assertIsNone(goalurate.ultaid)
        self.assertFalse(goalurate.medhistory_set.all())
        self.assertFalse(goalurate.tophi)
        self.assertFalse(goalurate.erosions)
        self.assertEqual(goalurate.goalurate, GoalUrates.SIX)

    def test__post_adds_medhistorys(self):
        goalurate = create_goalurate()
        self.assertEqual(goalurate.goalurate, GoalUrates.SIX)
        data = {
            f"{MedHistoryTypes.EROSIONS}-value": True,
            f"{MedHistoryTypes.TOPHI}-value": True,
        }
        response = self.client.post(reverse("goalurates:update", kwargs={"pk": goalurate.id}), data=data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(goalurate.medhistory_set.all())
        self.assertTrue(goalurate.medhistory_set.get(medhistorytype=MedHistoryTypes.EROSIONS))
        self.assertTrue(goalurate.medhistory_set.get(medhistorytype=MedHistoryTypes.TOPHI))
        goalurate.refresh_from_db()
        self.assertEqual(goalurate.goalurate, GoalUrates.FIVE)

    def test__updates_ult_related_by_ultaid(self):
        ult = create_ult(mhs=[])
        self.assertFalse(ult.medhistory_set.all())
        ultaid = create_ultaid(mhs=[])
        ult.ultaid = ultaid
        ult.save()
        self.assertFalse(ultaid.medhistory_set.all())
        self.assertEqual(UltAid.objects.filter(ult=ult).get(), ultaid)
        self.assertEqual(Ult.objects.filter(ultaid=ultaid).get(), ult)
        goalurate = create_goalurate(ultaid=ultaid, mhs=[])
        self.assertFalse(goalurate.medhistory_set.all())
        self.assertEqual(goalurate.ultaid, ultaid)
        data = {
            f"{MedHistoryTypes.EROSIONS}-value": True,
            f"{MedHistoryTypes.TOPHI}-value": False,
        }
        response = self.client.post(reverse("goalurates:update", kwargs={"pk": goalurate.id}), data=data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ult.medhistory_set.filter(medhistorytype=MedHistoryTypes.EROSIONS).exists())
        self.assertFalse(ult.medhistory_set.filter(medhistorytype=MedHistoryTypes.TOPHI).exists())
        data = {
            f"{MedHistoryTypes.EROSIONS}-value": False,
            f"{MedHistoryTypes.TOPHI}-value": True,
        }
        response = self.client.post(reverse("goalurates:update", kwargs={"pk": goalurate.id}), data=data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ult.medhistory_set.filter(medhistorytype=MedHistoryTypes.EROSIONS).exists())
        self.assertTrue(ult.medhistory_set.filter(medhistorytype=MedHistoryTypes.TOPHI).exists())
