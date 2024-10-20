from datetime import timedelta
from decimal import Decimal

import pytest  # pylint: disable=e0401 # type: ignore
from django.contrib.auth.models import AnonymousUser  # pylint: disable=e0401 # type: ignore
from django.contrib.messages.middleware import MessageMiddleware  # pylint: disable=e0401 # type: ignore
from django.contrib.sessions.middleware import SessionMiddleware  # pylint: disable=e0401 # type: ignore
from django.db.models import Q, QuerySet  # pylint: disable=e0401 # type: ignore
from django.http import HttpResponse, HttpResponseRedirect  # pylint: disable=e0401 # type: ignore
from django.test import RequestFactory, TestCase  # pylint: disable=e0401 # type: ignore
from django.urls import reverse  # pylint: disable=e0401 # type: ignore
from django.utils import timezone  # pylint: disable=e0401 # type: ignore

from ...contents.choices import Tags
from ...contents.models import Content
from ...dateofbirths.helpers import age_calc
from ...dateofbirths.models import DateOfBirth
from ...defaults.models import UltAidSettings
from ...ethnicitys.choices import Ethnicitys
from ...ethnicitys.models import Ethnicity
from ...ethnicitys.tests.factories import EthnicityFactory
from ...genders.choices import Genders
from ...genders.models import Gender
from ...goalurates.models import GoalUrate
from ...goalurates.tests.factories import GoalUrateFactory
from ...labs.models import BaselineCreatinine, Hlab5801
from ...labs.tests.factories import Hlab5801Factory
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.choices import Stages
from ...medhistorydetails.models import CkdDetail
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import ULTAID_MEDHISTORYS
from ...medhistorys.models import MedHistory, Xoiinteraction
from ...treatments.choices import Treatments, UltChoices
from ...ults.tests.factories import create_ult
from ...users.models import Pseudopatient
from ...users.tests.factories import AdminFactory, UserFactory, create_psp
from ...utils.forms import forms_print_response_errors
from ...utils.test_helpers import dummy_get_response
from ..models import UltAid
from ..views import (
    UltAidAbout,
    UltAidCreate,
    UltAidDetail,
    UltAidPseudopatientCreate,
    UltAidPseudopatientDetail,
    UltAidPseudopatientUpdate,
    UltAidUpdate,
)
from .factories import create_ultaid, ultaid_data_factory

pytestmark = pytest.mark.django_db


class TestUltAidAbout(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltAidAbout = UltAidAbout()

    def test__get(self):
        response = self.client.get(reverse("ultaids:about"))
        self.assertEqual(response.status_code, 200)

    def test__get_context_data(self):
        response = self.client.get(reverse("ultaids:about"))
        self.assertIn("content", response.context_data)

    def test__content(self):
        self.assertEqual(
            self.view.content, Content.objects.get(context=Content.Contexts.ULTAID, slug="about", tag=None)
        )


class TestUltAidCreate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltAidCreate = UltAidCreate()

    def test__get_with_ult_resolves(self):
        ult = create_ult()
        response = self.client.get(reverse("ultaids:ult-create", kwargs={"ult": ult.pk}))
        self.assertEqual(response.status_code, 200)

    def test__post_adds_hlab5801_True(self):
        """Tests that a POST request adds a Hlab5801 instance as an attribute
        to the created UltAid."""
        # Create some fake data and add hlab5801-value to it
        ultaid_data = ultaid_data_factory()
        ultaid_data.update({"hlab5801-value": True})

        # Post the data to the view and make sure it responds correctly
        response = self.client.post(reverse("ultaids:create"), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        # Test that the UltAid and Hlab5801 objects were created
        ultaid = UltAid.objects.order_by("created").last()
        hlab5801 = Hlab5801.objects.order_by("created").last()
        self.assertEqual(ultaid.hlab5801, hlab5801)
        self.assertTrue(hlab5801.value)

    def test__post_adds_hlab5801_False(self):
        """Tests that a POST request adds a Hlab5801 instance as an attribute
        to the created UltAid."""
        # Create some fake data and add hlab5801-value to it
        ultaid_data = ultaid_data_factory()
        ultaid_data.update({"hlab5801-value": False})

        # Post the data to the view and make sure it responds correctly
        response = self.client.post(reverse("ultaids:create"), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        # Test that the UltAid and Hlab5801 objects were created
        ultaid = UltAid.objects.order_by("created").last()
        hlab5801 = Hlab5801.objects.order_by("created").last()
        self.assertEqual(ultaid.hlab5801, hlab5801)
        self.assertFalse(hlab5801.value)

    def test__post_doesnt_add_hlab5801(self):
        """Tests that a POST request adds a Hlab5801 instance as an attribute
        to the created UltAid."""
        # Create some fake data without hlab5801-value
        ultaid_data = ultaid_data_factory()
        ultaid_data.update({"hlab5801-value": ""})

        # Post the data to the view and make sure it responds correctly
        response = self.client.post(reverse("ultaids:create"), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        # Test that the UltAid and Hlab5801 objects were created
        ultaid = UltAid.objects.order_by("created").last()
        self.assertIsNone(ultaid.hlab5801)

    def test__post_adds_xoiinteraction_contraindicates_xois(self):
        """Tests that a POST request adds a Hlab5801 instance as an attribute
        to the created UltAid."""
        ultaid_data = {
            "dateofbirth-value": age_calc(timezone.now() - timedelta(days=365 * 50)),
            "gender-value": Genders.FEMALE,
            "ethnicity-value": Ethnicitys.CAUCASIANAMERICAN,
            "hlab5801-value": "",
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.HEPATITIS}-value": True,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"{MedHistoryTypes.URATESTONES}-value": False,
            f"{MedHistoryTypes.XOIINTERACTION}-value": True,
        }
        response = self.client.post(reverse("ultaids:create"), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(UltAid.objects.exists())
        ultaid = UltAid.objects.get()
        self.assertTrue(Xoiinteraction.objects.exists())
        xoiinteraction = Xoiinteraction.objects.order_by("created").last()
        self.assertIn(xoiinteraction, ultaid.medhistory_set.all())
        self.assertNotIn(Treatments.ALLOPURINOL, ultaid.options)
        self.assertNotIn(Treatments.FEBUXOSTAT, ultaid.options)
        self.assertEqual(Treatments.PROBENECID, ultaid.recommendation[0])

    def test__post_with_ult_dateofbirth_gender_ckd(self):
        ult = create_ult(
            mhs=[MedHistoryTypes.CKD],
            gender=Genders.MALE,
            dateofbirth=timezone.now() - timedelta(days=365 * 40),
            baselinecreatinine=Decimal("2.0"),
        )
        self.assertTrue(ult.medhistory_set.filter(medhistorytype=MedHistoryTypes.CKD).exists())
        self.assertTrue(ult.dateofbirth)
        self.assertTrue(ult.gender)
        ultaid_data = {
            "dateofbirth-value": ult.dateofbirth.value,
            "gender-value": ult.gender.value,
            "ethnicity-value": Ethnicitys.CAUCASIANAMERICAN,
            "hlab5801-value": "",
            f"{MedHistoryTypes.CKD}-value": True,
            "dialysis": ult.ckddetail.dialysis,
            "baselinecreatinine": ult.baselinecreatinine.value,
            "stage": ult.ckddetail.stage,
            f"{MedHistoryTypes.HEPATITIS}-value": True,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"{MedHistoryTypes.URATESTONES}-value": False,
            f"{MedHistoryTypes.XOIINTERACTION}-value": True,
        }
        response = self.client.post(reverse("ultaids:ult-create", kwargs={"ult": ult.pk}), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

    def test__get_with_ult_adds_ult_medhistorys_to_context_as_true(self):
        ult = create_ult(mhs=[MedHistoryTypes.CKD, MedHistoryTypes.URATESTONES])
        self.assertTrue(ult.medhistory_set.filter(medhistorytype=MedHistoryTypes.CKD).exists())
        self.assertTrue(ult.medhistory_set.filter(medhistorytype=MedHistoryTypes.URATESTONES).exists())
        response = self.client.get(reverse("ultaids:ult-create", kwargs={"ult": ult.pk}))
        self.assertTrue(response.context_data[f"{MedHistoryTypes.CKD}_form"].fields[f"{MedHistoryTypes.CKD}-value"])
        self.assertTrue(
            response.context_data[f"{MedHistoryTypes.URATESTONES}_form"].fields[f"{MedHistoryTypes.URATESTONES}-value"]
        )

    def test__get_with_ult_adds_age_gender_from_ult_to_context(self):
        ult = create_ult(
            mhs=[MedHistoryTypes.CKD],
            gender=Genders.MALE,
            dateofbirth=timezone.now() - timedelta(days=365 * 40),
            baselinecreatinine=Decimal("2.0"),
        )
        self.assertTrue(ult.medhistory_set.filter(medhistorytype=MedHistoryTypes.CKD).exists())
        self.assertTrue(ult.dateofbirth)
        self.assertTrue(ult.gender)
        response = self.client.get(reverse("ultaids:ult-create", kwargs={"ult": ult.pk}))
        self.assertIn("age", response.context_data)
        self.assertEqual(response.context_data["age"], ult.age)
        self.assertIn("gender", response.context_data)
        self.assertEqual(response.context_data["gender"], ult.gender.value)


class TestUltAidDetail(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltAidDetail = UltAidDetail
        self.content_qs = Content.objects.filter(
            Q(tag=Tags.EXPLANATION) | Q(tag=Tags.WARNING), context=Content.Contexts.ULTAID, slug__isnull=False
        ).all()
        # Need to set ethnicity to Caucasian to avoid HLA-B*5801 contraindication with high risk ethnicity
        self.ultaid = create_ultaid(
            mas=[], mhs=[], ethnicity=EthnicityFactory(value=Ethnicitys.CAUCASIANAMERICAN), hlab5801=False
        )

    def test__get_context_data(self):
        response = self.client.get(reverse("ultaids:detail", kwargs={"pk": self.ultaid.pk}))
        context = response.context_data
        for content in self.content_qs:
            self.assertIn(content.slug, context)
            self.assertEqual(context[content.slug], {content.tag: content})

    def test__get_queryset(self):
        # Create a GoalUrate to and add it to the ultaid object to test the qs
        GoalUrateFactory(ultaid=self.ultaid)
        qs = self.view(kwargs={"pk": self.ultaid.pk}).get_queryset()
        self.assertTrue(isinstance(qs, QuerySet))
        qs_obj = qs.first()
        self.assertEqual(qs_obj, self.ultaid)
        self.assertTrue(hasattr(qs_obj, "medhistorys_qs"))
        self.assertTrue(hasattr(qs_obj, "medallergys_qs"))
        self.assertTrue(hasattr(qs_obj, "ckddetail"))
        self.assertTrue(hasattr(qs_obj, "baselinecreatinine"))
        self.assertTrue(hasattr(qs_obj, "dateofbirth"))
        self.assertTrue(hasattr(qs_obj, "gender"))
        self.assertTrue(hasattr(qs_obj, "ethnicity"))
        self.assertTrue(hasattr(qs_obj, "hlab5801"))
        self.assertTrue(hasattr(qs_obj, "goalurate"))

    def test__get_object_updates(self):
        self.assertTrue(self.ultaid.recommendation[0] == Treatments.ALLOPURINOL)
        MedAllergyFactory(treatment=Treatments.ALLOPURINOL, ultaid=self.ultaid)
        response = self.client.get(reverse("ultaids:detail", kwargs={"pk": self.ultaid.pk}))
        self.assertEqual(response.status_code, 200)
        ultaid = UltAid.objects.get(pk=self.ultaid.pk)
        # This needs to be manually refetched from the db
        self.assertFalse(ultaid.recommendation[0] == Treatments.ALLOPURINOL)


class TestUltAidPseudopatientCreate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltAidPseudopatientCreate = UltAidPseudopatientCreate
        self.user = create_psp(plus=True)
        for _ in range(5):
            create_psp(plus=True)
        self.ultaid_with_user = create_ultaid(user=create_psp(plus=True))
        self.user_with_ultaid = self.ultaid_with_user.user
        self.anon_user = AnonymousUser()

    def test__check_user_onetoones(self):
        """Tests that the view checks for the User's related models."""
        empty_user = create_psp(ethnicity=False)
        view = self.view()
        view.user = empty_user
        self.assertFalse(view.user_has_required_otos)

    def test__ckddetail(self):
        """Tests the ckddetail cached_property."""
        view = self.view()
        view.set_forms()
        self.assertTrue(view.ckddetail)

    def test__dispatch(self):
        """Test the dispatch() method for the view. Should redirect to detailview when
        the user already has a UltAid. Should redirect to Pseudopatient Update
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

        # Create a new UltAid and test that the view redirects to the detailview
        create_ultaid(user=self.user)
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": self.user.pk}), follow=True
        )
        self.assertEqual(view.user, self.user)
        self.assertRedirects(response, reverse("ultaids:pseudopatient-update", kwargs={"pseudopatient": self.user.pk}))
        # Check that the response message is correct
        message = list(response.context.get("messages"))[0]
        self.assertEqual(message.tags, "error")
        self.assertEqual(message.message, f"{self.user} already has a UltAid. Please update it instead.")

        # Create empty user and test that the view redirects to the user update view
        empty_user = create_psp(dateofbirth=False, ethnicity=False, gender=False)
        self.client.force_login(empty_user)
        response = self.client.get(
            reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": empty_user.pk}), follow=True
        )
        self.assertRedirects(response, reverse("users:pseudopatient-update", kwargs={"pseudopatient": empty_user.pk}))
        message = list(response.context.get("messages"))[0]
        self.assertEqual(message.tags, "error")
        self.assertEqual(message.message, f"{empty_user} is missing required information.")

    def test__get_form_kwargs(self):
        # Create a fake request
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        view = self.view(request=request)

        # Set the user on the view, as this would be done by dispatch()
        view.user = self.user
        view.setup(request, username=self.user.username)
        view.set_forms()
        view.object = view.get_object()

        # Call the get_form_kwargs() method and assert that the correct kwargs are returned
        form_kwargs = view.get_form_kwargs()
        self.assertIn("medallergys", form_kwargs)
        self.assertEqual(form_kwargs["medallergys"], view.MEDALLERGY_FORMS.keys())
        self.assertIn("patient", form_kwargs)
        self.assertTrue(form_kwargs["patient"])

    def test__goutdetail(self):
        """Tests the goutdetail cached_property."""
        self.assertFalse(self.view().goutdetail)

    def test__get_context_data_medallergys(self):
        """Test that the context data includes the user's
        related models."""
        for user in Pseudopatient.objects.select_related("ultaid").all():
            if not hasattr(user, "ultaid"):
                request = self.factory.get("/fake-url/")
                if user.profile.provider:
                    request.user = user.profile.provider
                else:
                    request.user = self.anon_user
                SessionMiddleware(dummy_get_response).process_request(request)
                kwargs = {"pseudopatient": user.pk}
                response = self.view.as_view()(request, **kwargs)
                assert response.status_code == 200
                for ma in user.medallergy_set.filter(Q(treatment__in=UltChoices.values)).all():
                    assert f"medallergy_{ma.treatment}_form" in response.context_data
                    assert response.context_data[f"medallergy_{ma.treatment}_form"].instance == ma
                    assert (
                        response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                            f"medallergy_{ma.treatment}_form"
                        ].instance._state.adding
                        is False
                    )
                    assert response.context_data[f"medallergy_{ma.treatment}_form"].initial == {
                        f"medallergy_{ma.treatment}": True,
                        f"{ma.treatment}_matype": None,
                    }
                for treatment in UltChoices.values:
                    assert f"medallergy_{treatment}_form" in response.context_data
                    if treatment not in user.medallergy_set.values_list("treatment", flat=True):
                        assert (
                            response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                                f"medallergy_{treatment}_form"
                            ].instance._state.adding
                            is True
                        )
                        assert response.context_data[f"medallergy_{treatment}_form"].initial == {
                            f"medallergy_{treatment}": None,
                            f"{treatment}_matype": None,
                        }

    def test__get_context_data_medhistorys(self):
        """Test that the context data includes the user's related MedHistory and MedHistoryDetail models."""
        for user in Pseudopatient.objects.select_related("ultaid").all():
            if not hasattr(user, "ultaid"):
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
                    if mh.medhistorytype in ULTAID_MEDHISTORYS:
                        assert f"{mh.medhistorytype}_form" in response.context_data
                        assert response.context_data[f"{mh.medhistorytype}_form"].instance == mh
                        assert (
                            response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                                f"{mh.medhistorytype}_form"
                            ].instance._state.adding
                            is False
                        )
                        assert response.context_data[f"{mh.medhistorytype}_form"].initial == {
                            f"{mh.medhistorytype}-value": True
                        }
                    else:
                        assert f"{mh.medhistorytype}_form" not in response.context_data
                for mhtype in ULTAID_MEDHISTORYS:
                    assert f"{mhtype}_form" in response.context_data
                    if mhtype not in user.medhistory_set.values_list("medhistorytype", flat=True):
                        assert (
                            response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                                f"{mhtype}_form"
                            ].instance._state.adding
                            is True
                        )
                        assert response.context_data[f"{mhtype}_form"].initial == {f"{mhtype}-value": None}
                assert "ckddetail_form" in response.context_data
                if user.ckd:
                    if getattr(user.ckd, "ckddetail", None):
                        assert response.context_data["ckddetail_form"].instance == user.ckd.ckddetail
                        assert (
                            response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                                "ckddetail_form"
                            ].instance._state.adding
                            is False
                        )
                    else:
                        assert (
                            response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                                "ckddetail_form"
                            ].instance._state.adding
                            is True
                        )
                    if getattr(user.ckd, "baselinecreatinine", None):
                        assert response.context_data["baselinecreatinine_form"].instance == user.ckd.baselinecreatinine
                        assert (
                            response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                                "baselinecreatinine_form"
                            ].instance._state.adding
                            is False
                        )
                    else:
                        assert (
                            response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                                "baselinecreatinine_form"
                            ].instance._state.adding
                            is True
                        )
                else:
                    assert (
                        response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                            "ckddetail_form"
                        ].instance._state.adding
                        is True
                    )
                    assert (
                        response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                            "baselinecreatinine_form"
                        ].instance._state.adding
                        is True
                    )

    def test__get_context_data_onetoones(self):
        """Test that the context data includes the user's related models."""
        for user in Pseudopatient.objects.select_related("ultaid").all():
            if not hasattr(user, "ultaid"):
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
                assert "ethnicity" in response.context_data
                assert response.context_data["ethnicity"] == user.ethnicity.value
                assert "gender" in response.context_data
                assert response.context_data["gender"] == user.gender.value
                assert "hlab5801_form" in response.context_data
                if hasattr(user, "hlab5801"):
                    assert response.context_data["hlab5801_form"].instance == user.hlab5801
                    assert response.context_data["hlab5801_form"].initial == {"value": user.hlab5801.value}

    def test__get_permission_object(self):
        """Test the get_permission_object() method for the view."""
        for user in Pseudopatient.objects.all():
            request = self.factory.get("/fake-url/")
            request.user = self.anon_user
            kwargs = {"username": user.username}
            view = self.view()
            view.setup(request, **kwargs)
            view.user = user
            permission_object = view.get_permission_object()
            self.assertEqual(permission_object, user)

    def test__get_user_queryset(self):
        for pseudopatient in Pseudopatient.objects.all():
            with self.assertNumQueries(4):
                kwargs = {"pseudopatient": pseudopatient.pk}
                qs = self.view(kwargs=kwargs).get_user_queryset(**kwargs)
                self.assertTrue(isinstance(qs, QuerySet))
                qs_obj = qs.first()
                self.assertTrue(isinstance(qs_obj, Pseudopatient))
                self.assertEqual(qs_obj, pseudopatient)
                self.assertTrue(hasattr(qs_obj, "baselinecreatinine"))
                self.assertTrue(hasattr(qs_obj, "ckddetail"))
                if qs_obj.ckddetail:
                    self.assertTrue(getattr(qs_obj, "ckd"))
                    self.assertTrue(isinstance(qs_obj.ckddetail, CkdDetail))
                self.assertTrue(hasattr(qs_obj, "baselinecreatinine"))
                if qs_obj.baselinecreatinine:
                    self.assertTrue(isinstance(qs_obj.baselinecreatinine, BaselineCreatinine))
                    self.assertTrue(getattr(qs_obj, "dateofbirth"))
                    self.assertTrue(getattr(qs_obj, "gender"))
                    self.assertTrue(getattr(qs_obj, "ckddetail"))
                self.assertTrue(hasattr(qs_obj, "dateofbirth"))
                if qs_obj.dateofbirth:
                    self.assertTrue(isinstance(qs_obj.dateofbirth, DateOfBirth))
                if hasattr(qs_obj, "ultaidsettings"):
                    self.assertTrue(isinstance(qs_obj.ultaidsettings, UltAidSettings))
                else:
                    self.assertFalse(hasattr(qs_obj, "ultaidsettings"))
                self.assertTrue(hasattr(qs_obj, "ethnicity"))
                self.assertTrue(isinstance(qs_obj.ethnicity, Ethnicity))
                self.assertTrue(hasattr(qs_obj, "gender"))
                if qs_obj.gender:
                    self.assertTrue(isinstance(qs_obj.gender, Gender))
                if hasattr(qs_obj, "goalurate"):
                    self.assertTrue(isinstance(qs_obj.goalurate, GoalUrate))
                if hasattr(qs_obj, "hlab5801"):
                    self.assertTrue(isinstance(qs_obj.hlab5801, Hlab5801))
                self.assertTrue(hasattr(qs_obj, "medallergys_qs"))
                self.assertTrue(hasattr(qs_obj, "medhistorys_qs"))

    def test__post(self):
        """Test the post() method for the view."""
        for user in Pseudopatient.objects.select_related("ultaid").all():
            if not hasattr(user, "ultaid"):
                request = self.factory.post("/fake-url/")
                if user.profile.provider:  # type: ignore
                    request.user = user.profile.provider  # type: ignore
                else:
                    request.user = self.anon_user
                SessionMiddleware(dummy_get_response).process_request(request)
                kwargs = {"username": user.username}
                response = self.view.as_view()(request, **kwargs)
                assert response.status_code == 200

    def test__post_sets_object_user(self):
        """Test that the post() method for the view sets the
        user on the object."""
        for user in Pseudopatient.objects.select_related("ultaid").all():
            if not hasattr(user, "ultaid"):
                data = ultaid_data_factory(user=self.user)
                response = self.client.post(
                    reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": self.user.pk}), data=data
                )
                forms_print_response_errors(response)
                assert response.status_code == 302
                assert UltAid.objects.filter(user=self.user).exists()
                ultaid = UltAid.objects.get(user=self.user)
                assert ultaid.user
                assert ultaid.user == self.user

    def test__post_updates_medhistorys(self):
        for user in Pseudopatient.objects.select_related("ultaid").all():
            if not hasattr(user, "ultaid"):
                user_mh_dict = {
                    mh: user.medhistory_set.filter(medhistorytype=mh).exists() for mh in ULTAID_MEDHISTORYS
                }
                data = ultaid_data_factory(user)
                data.update(
                    {
                        **{
                            f"{mh}-value": not user_mh_dict[mh]
                            for mh in ULTAID_MEDHISTORYS
                            # Need to exclude CKD because of related CkdDetail fields throwing errors
                            if mh != MedHistoryTypes.CKD
                        },
                    }
                )
                response = self.client.post(
                    reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": user.pk}), data=data
                )
                forms_print_response_errors(response)
                assert response.status_code == 302
                assert (
                    response.url
                    == f"{reverse('ultaids:pseudopatient-detail', kwargs={'pseudopatient': user.pk})}?updated=True"
                )
                for mh in [mh for mh in ULTAID_MEDHISTORYS if mh != MedHistoryTypes.CKD]:
                    self.assertEqual(user.medhistory_set.filter(medhistorytype=mh).exists(), not user_mh_dict[mh])

    def test__post_updates_medallergys(self):
        for user in Pseudopatient.objects.select_related("ultaid").all():
            if not hasattr(user, "ultaid"):
                user_ma_dict = {ma: user.medallergy_set.filter(treatment=ma).exists() for ma in UltChoices.values}
                data = ultaid_data_factory(user)
                data.update(
                    {
                        **{f"medallergy_{ma}": not user_ma_dict[ma] for ma in UltChoices.values},
                    }
                )
                response = self.client.post(
                    reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": user.pk}), data=data
                )
                forms_print_response_errors(response)
                assert response.status_code == 302
                assert (
                    response.url
                    == f"{reverse('ultaids:pseudopatient-detail', kwargs={'pseudopatient': user.pk})}?updated=True"
                )
                for ma in UltChoices.values:
                    self.assertEqual(user.medallergy_set.filter(treatment=ma).exists(), not user_ma_dict[ma])

    def test__post_creates_medhistorydetails(self):
        """Test that the view creates the User's MedHistoryDetails objects."""
        # Create user without ckd
        psp = create_psp(medhistorys=[])
        self.assertFalse(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.CKD).exists())

        data = ultaid_data_factory(user=psp)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                # Create data for CKD
                "dialysis": False,
                "baselinecreatinine-value": Decimal("2.2"),
            }
        )

        response = self.client.post(
            reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": psp.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302
        assert (
            response.url == f"{reverse('ultaids:pseudopatient-detail', kwargs={'pseudopatient': psp.pk})}?updated=True"
        )

        self.assertTrue(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.CKD).exists())
        ckd = MedHistory.objects.get(user=psp, medhistorytype=MedHistoryTypes.CKD)
        self.assertTrue(CkdDetail.objects.filter(medhistory=ckd).exists())
        self.assertTrue(BaselineCreatinine.objects.filter(medhistory=ckd).exists())

    def test__post_deletes_medhistorydetail(self):
        psp = create_psp(
            medhistorys=[MedHistoryTypes.CKD],
            mh_dets={MedHistoryTypes.CKD: {"dialysis": False, "baselinecreatinine": Decimal("2.2")}},
        )
        self.assertTrue(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.CKD).exists())
        self.assertTrue(
            CkdDetail.objects.filter(medhistory=psp.ckd).exists()
            and BaselineCreatinine.objects.filter(medhistory=psp.ckd).exists()
        )

        data = ultaid_data_factory(user=psp)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": False,
            }
        )

        response = self.client.post(
            reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": psp.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302
        assert (
            response.url == f"{reverse('ultaids:pseudopatient-detail', kwargs={'pseudopatient': psp.pk})}?updated=True"
        )

        self.assertFalse(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.CKD).exists())
        self.assertFalse(CkdDetail.objects.filter(medhistory=psp.ckd).exists())
        self.assertFalse(BaselineCreatinine.objects.filter(medhistory=psp.ckd).exists())

    def test__post_removes_hlab5801(self):
        """Test that a POST request removes a Hlab5801 instance as an attribute
        to the updated UltAid and deletes the Hlab5801 instance."""
        Hlab5801Factory(user=self.user, value=True)
        ultaid_data = ultaid_data_factory(user=self.user, otos={"hlab5801": ""})
        response = self.client.post(
            reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": self.user.pk}), ultaid_data
        )
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Hlab5801.objects.filter(user=self.user).exists())

    def test__post_adds_False_hlab5801(self):
        """Test that a POST request creates and adds a Hlab5801 instance, with
        a value=False, as an attribute to the updated 'UltAid's user."""
        ultaid_data = ultaid_data_factory(user=self.user, otos={"hlab5801": False})
        response = self.client.post(
            reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": self.user.pk}), ultaid_data
        )
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Hlab5801.objects.filter(user=self.user).exists())
        self.assertFalse(Hlab5801.objects.get(user=self.user).value)

    def test__post_adds_True_hlab5801(self):
        """Test that a POST request creates and adds a Hlab5801 instance, with
        a value=True, as an attribute to the updated UltAid's user."""
        ultaid_data = ultaid_data_factory(user=self.user, otos={"hlab5801": True})
        response = self.client.post(
            reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": self.user.pk}), ultaid_data
        )
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Hlab5801.objects.filter(user=self.user).exists())
        self.assertTrue(Hlab5801.objects.get(user=self.user).value)

    def test__post_updates_hlab5801_True_to_False(self):
        """Test that a POST request updates a Hlab5801 object / UltAid attribute
        from True to False."""
        Hlab5801Factory(user=self.user, value=True)
        ultaid_data = ultaid_data_factory(user=self.user, otos={"hlab5801": False})
        response = self.client.post(
            reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": self.user.pk}), ultaid_data
        )
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Hlab5801.objects.filter(user=self.user).exists())
        self.assertFalse(Hlab5801.objects.get(user=self.user).value)

    def test__post_updates_hlab5801_False_to_True(self):
        """Test that a POST request updates a Hlab5801 object / UltAid attribute
        from False to True."""
        Hlab5801Factory(user=self.user, value=False)
        ultaid_data = ultaid_data_factory(user=self.user, otos={"hlab5801": True})
        response = self.client.post(
            reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": self.user.pk}), ultaid_data
        )
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Hlab5801.objects.filter(user=self.user).exists())
        self.assertTrue(Hlab5801.objects.get(user=self.user).value)

    def test__post_returns_errors(self):
        """Test that post returns errors for some common scenarios where the
        data is invalid. Typically, these are scenarios that should be prevented by
        the form or javascript."""
        # Test that the view returns errors when the baselinecreatinine and
        # stage are not congruent
        data = ultaid_data_factory(user=self.user)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": False,
                "baselinecreatinine-value": Decimal("9.9"),
                "stage": Stages.ONE,
            }
        )
        response = self.client.post(
            reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": self.user.pk}), data=data
        )
        assert response.status_code == 200

        assert "form" in response.context_data
        assert "ckddetail_form" in response.context_data
        assert "stage" in response.context_data["ckddetail_form"].errors
        assert "baselinecreatinine_form" in response.context_data
        assert "value" in response.context_data["baselinecreatinine_form"].errors

        # Test that the view DOES NOT return errors when CKD is True and dialysis is left blank
        # For the UltAid CkdDetail is optional
        data = ultaid_data_factory(user=self.user)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
            }
        )
        response = self.client.post(
            reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": self.user.pk}), data=data
        )
        assert response.status_code == 302

    def test__rules(self):
        """Tests for whether the rules appropriately allow or restrict
        access to the view."""
        psp = create_psp()
        provider = UserFactory()
        provider_psp = create_psp(provider=provider)
        admin = AdminFactory()
        admin_psp = create_psp(provider=admin)
        # Test that any User can create an anonymous Pseudopatient's UltAid
        response = self.client.get(reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": psp.pk}))
        assert response.status_code == 200
        # Test that an anonymous User can't create a Provider's UltAid
        response = self.client.get(reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": provider_psp.pk}))
        # 302 because PermissionDenied will redirect to the login page
        assert response.status_code == 302
        # Test that an anonymous User can't create an Admin's UltAid
        response = self.client.get(reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": admin_psp.pk}))
        # Test that a Provider can create his or her own Pseudopatient's UltAid
        response = self.client.get(
            reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": psp.pk}),
        )
        assert response.status_code == 200
        # Test that a Provider can create an anonymous Pseudopatient's UltAid
        response = self.client.get(
            reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": psp.pk}),
        )
        assert response.status_code == 200
        self.client.force_login(admin)
        response = self.client.get(
            reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": admin_psp.pk}),
        )
        assert response.status_code == 200
        # Test that only a Pseudopatient's Provider can add their UltAid if they have a Provider
        response = self.client.get(
            reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": provider_psp.pk}),
        )
        assert response.status_code == 403
        self.client.force_login(provider)
        # Test that a Provider can't create another provider's Pseudopatient's UltAid
        response = self.client.get(
            reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": admin_psp.pk}),
        )
        assert response.status_code == 403
        self.client.force_login(admin)
        # Test that an Admin can create an anonymous Pseudopatient's UltAid
        response = self.client.get(
            reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": psp.pk}),
        )
        assert response.status_code == 200


class TestUltAidPseudopatientDetail(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltAidPseudopatientDetail = UltAidPseudopatientDetail
        self.content_qs = Content.objects.filter(
            Q(tag=Tags.EXPLANATION) | Q(tag=Tags.WARNING), context=Content.Contexts.ULTAID, slug__isnull=False
        ).all()
        for _ in range(5):
            create_ultaid(user=create_psp(plus=True))

    def test__dispatch(self):
        for ultaid in UltAid.objects.filter(user__isnull=False).select_related("user"):
            view = self.view()
            kwargs = {"pseudopatient": ultaid.user.pk}
            request = self.factory.get(reverse("ultaids:pseudopatient-detail", kwargs=kwargs))
            request.user = ultaid.user
            view.setup(request, **kwargs)
            response = view.dispatch(request, **kwargs)
            self.assertTrue(isinstance(response, HttpResponse))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(hasattr(view, "object"))
            self.assertEqual(view.object, ultaid)
            self.assertTrue(hasattr(view, "user"))
            self.assertEqual(view.user, ultaid.user)

        # Test that the view redirects to the pseudopatient-create view if the user
        # is lacking a UltAid
        user_without_ultaid = create_psp()
        view = self.view()
        kwargs = {"pseudopatient": user_without_ultaid.pk}
        request = self.factory.get(reverse("ultaids:pseudopatient-detail", kwargs=kwargs))
        request.user = user_without_ultaid
        view.setup(request, **kwargs)

        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        response = view.dispatch(request, **kwargs)
        self.assertTrue(isinstance(response, HttpResponseRedirect))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("ultaids:pseudopatient-create", kwargs=kwargs))

        # Test that the view redirects to the pseudopatient-update view if the user
        # is lacking one of their required OneToOneFields
        user_with_ultaid = UltAid.objects.filter(user__isnull=False).first().user
        user_with_ultaid.ethnicity.delete()

        view = self.view()
        kwargs = {"pseudopatient": user_with_ultaid.pk}
        request = self.factory.get(reverse("ultaids:pseudopatient-detail", kwargs=kwargs))
        request.user = user_with_ultaid
        view.setup(request, **kwargs)

        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        response = view.dispatch(request, **kwargs)
        self.assertTrue(isinstance(response, HttpResponseRedirect))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("users:pseudopatient-update", kwargs=kwargs))

    def test__get(self):
        """get() method should update the UltAid's decisionaid field."""
        for ultaid in UltAid.objects.filter(user__isnull=False).select_related("user"):
            self.assertFalse(ultaid.decisionaid)
            response = self.client.get(
                reverse("ultaids:pseudopatient-detail", kwargs={"pseudopatient": ultaid.user.pk})
            )
            self.assertEqual(response.status_code, 200)
            ultaid.refresh_from_db()
            self.assertTrue(ultaid.decisionaid)
            self.assertTrue(isinstance(ultaid.decisionaid, str))

    def test__get_context_data(self):
        for ultaid in UltAid.objects.filter(user__isnull=False).select_related("user"):
            response = self.client.get(
                reverse("ultaids:pseudopatient-detail", kwargs={"pseudopatient": ultaid.user.pk})
            )
            context = response.context_data
            for content in self.content_qs:
                self.assertIn(content.slug, context)
                self.assertEqual(context[content.slug], {content.tag: content})
            self.assertIn("patient", context)
            self.assertEqual(context["patient"], ultaid.user)

    def test__get_permission_object(self):
        for ultaid in UltAid.objects.filter(user__isnull=False).select_related("user"):
            view = self.view()
            view.kwargs = {"pseudopatient": ultaid.user.pk}
            request = self.factory.get(reverse("ultaids:pseudopatient-detail", kwargs=view.kwargs))
            request.user = ultaid.user
            view.setup(request, **view.kwargs)
            view.object = view.get_object()
            self.assertEqual(view.get_permission_object(), ultaid)

    def test__get_queryset(self):
        for ultaid in UltAid.objects.filter(user__isnull=False).select_related("user"):
            with self.assertNumQueries(4):
                qs = self.view(kwargs={"pseudopatient": ultaid.user.pk}).get_queryset()
                self.assertTrue(isinstance(qs, QuerySet))
                qs_obj = qs.first()
                self.assertTrue(isinstance(qs_obj, Pseudopatient))
                self.assertEqual(qs_obj, ultaid.user)
                self.assertTrue(hasattr(qs_obj, "baselinecreatinine"))
                self.assertTrue(hasattr(qs_obj, "ckddetail"))
                if qs_obj.ckddetail:
                    self.assertTrue(getattr(qs_obj, "ckd"))
                    self.assertTrue(isinstance(qs_obj.ckddetail, CkdDetail))
                self.assertTrue(hasattr(qs_obj, "baselinecreatinine"))
                if qs_obj.baselinecreatinine:
                    self.assertTrue(isinstance(qs_obj.baselinecreatinine, BaselineCreatinine))
                    self.assertTrue(getattr(qs_obj, "dateofbirth"))
                    self.assertTrue(getattr(qs_obj, "gender"))
                    self.assertTrue(getattr(qs_obj, "ckddetail"))
                self.assertTrue(hasattr(qs_obj, "dateofbirth"))
                if qs_obj.dateofbirth:
                    self.assertTrue(isinstance(qs_obj.dateofbirth, DateOfBirth))
                if hasattr(qs_obj, "ultaidsettings"):
                    self.assertTrue(isinstance(qs_obj.ultaidsettings, UltAidSettings))
                else:
                    self.assertFalse(hasattr(qs_obj, "ultaidsettings"))
                self.assertTrue(hasattr(qs_obj, "ethnicity"))
                self.assertTrue(isinstance(qs_obj.ethnicity, Ethnicity))
                self.assertTrue(hasattr(qs_obj, "gender"))
                if qs_obj.gender:
                    self.assertTrue(isinstance(qs_obj.gender, Gender))
                if hasattr(qs_obj, "goalurate"):
                    self.assertTrue(isinstance(qs_obj.goalurate, GoalUrate))
                if hasattr(qs_obj, "hlab5801"):
                    self.assertTrue(isinstance(qs_obj.hlab5801, Hlab5801))
                self.assertTrue(hasattr(qs_obj, "medallergys_qs"))
                self.assertTrue(hasattr(qs_obj, "medhistorys_qs"))

    def test__get_object(self):
        for user in Pseudopatient.objects.ultaid_qs().all():
            view = self.view()
            view.kwargs = {"pseudopatient": user.pk}
            request = self.factory.get(reverse("ultaids:pseudopatient-detail", kwargs=view.kwargs))
            request.user = user
            view.setup(request, **view.kwargs)
            view.object = view.get_object()
            self.assertEqual(view.object, user.ultaid)

    def test__view_works(self):
        for user in Pseudopatient.objects.ultaid_qs().all():
            response = self.client.get(reverse("ultaids:pseudopatient-detail", kwargs={"pseudopatient": user.pk}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context_data["patient"], user)


class TestUltAidPseudopatientUpdate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltAidPseudopatientUpdate = UltAidPseudopatientUpdate
        self.content_qs = Content.objects.filter(
            Q(tag=Tags.EXPLANATION) | Q(tag=Tags.WARNING), context=Content.Contexts.ULTAID, slug__isnull=False
        ).all()
        self.anon_user = AnonymousUser()
        self.user = create_psp(plus=True)
        create_ultaid(user=self.user)
        self.user_without_ultaid = create_psp()
        for _ in range(5):
            create_ultaid(user=create_psp(plus=True))

    def test__check_user_onetoones(self):
        """Tests that the view checks for the User's related models."""
        empty_user = create_psp(ethnicity=False)
        view = self.view()
        view.user = empty_user
        self.assertFalse(view.user_has_required_otos)

    def test__ckddetail(self):
        """Tests the ckddetail cached_property."""
        view = self.view()
        view.set_forms()
        self.assertTrue(view.ckddetail)

    def test__dispatch(self):
        """Test the dispatch() method for the view. Should redirect to detailview when
        the user already has a UltAid. Should redirect to Pseudopatient Update
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

        # Create a user without a UltAid and assert that the view redirects to the user's create view
        self.client.force_login(self.user_without_ultaid)
        response = self.client.get(
            reverse("ultaids:pseudopatient-update", kwargs={"pseudopatient": self.user_without_ultaid.pk}),
            follow=True,
        )
        self.assertRedirects(
            response, reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": self.user_without_ultaid.pk})
        )
        # Check that the response message is correct
        message = list(response.context.get("messages"))[0]
        self.assertEqual(message.tags, "error")
        self.assertEqual(message.message, "No UltAid matching the query")

        # Create empty user and test that the view redirects to the user update view
        empty_user = create_psp(dateofbirth=False, ethnicity=False, gender=False)
        self.client.force_login(empty_user)
        response = self.client.get(
            reverse("ultaids:pseudopatient-create", kwargs={"pseudopatient": empty_user.pk}), follow=True
        )
        self.assertRedirects(response, reverse("users:pseudopatient-update", kwargs={"pseudopatient": empty_user.pk}))
        message = list(response.context.get("messages"))[0]
        self.assertEqual(message.tags, "error")
        self.assertEqual(message.message, f"{empty_user} is missing required information.")

    def test__get_form_kwargs(self):
        # Create a fake request
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        view = self.view(request=request)

        # Set the user on the view, as this would be done by dispatch()
        view.user = self.user
        view.setup(request, username=self.user.username)
        view.set_forms()
        view.object = view.get_object()

        # Call the get_form_kwargs() method and assert that the correct kwargs are returned
        form_kwargs = view.get_form_kwargs()
        self.assertIn("medallergys", form_kwargs)
        self.assertEqual(form_kwargs["medallergys"], view.MEDALLERGY_FORMS.keys())
        self.assertIn("patient", form_kwargs)
        self.assertTrue(form_kwargs["patient"])

    def test__goutdetail(self):
        """Tests the goutdetail cached_property."""
        self.assertFalse(self.view().goutdetail)

    def test__get_context_data_medallergys(self):
        """Test that the context data includes the user's
        related models."""
        for user in Pseudopatient.objects.select_related("ultaid").all():
            if hasattr(user, "ultaid"):
                request = self.factory.get("/fake-url/")
                if user.profile.provider:
                    request.user = user.profile.provider
                else:
                    request.user = self.anon_user
                SessionMiddleware(dummy_get_response).process_request(request)
                kwargs = {"pseudopatient": user.pk}
                response = self.view.as_view()(request, **kwargs)
                assert response.status_code == 200
                for ma in user.medallergy_set.filter(Q(treatment__in=UltChoices.values)).all():
                    assert f"medallergy_{ma.treatment}_form" in response.context_data
                    assert response.context_data[f"medallergy_{ma.treatment}_form"].instance == ma
                    assert (
                        response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                            f"medallergy_{ma.treatment}_form"
                        ].instance._state.adding
                        is False
                    )
                    assert response.context_data[f"medallergy_{ma.treatment}_form"].initial == {
                        f"medallergy_{ma.treatment}": True,
                        f"{ma.treatment}_matype": None,
                    }
                for treatment in UltChoices.values:
                    assert f"medallergy_{treatment}_form" in response.context_data
                    if treatment not in user.medallergy_set.values_list("treatment", flat=True):
                        assert (
                            response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                                f"medallergy_{treatment}_form"
                            ].instance._state.adding
                            is True
                        )
                        assert response.context_data[f"medallergy_{treatment}_form"].initial == {
                            f"medallergy_{treatment}": None,
                            f"{treatment}_matype": None,
                        }

    def test__get_context_data_medhistorys(self):
        """Test that the context data includes the user's related MedHistory and MedHistoryDetail models."""
        for user in Pseudopatient.objects.select_related("ultaid").all():
            if hasattr(user, "ultaid"):
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
                    if mh.medhistorytype in ULTAID_MEDHISTORYS:
                        assert f"{mh.medhistorytype}_form" in response.context_data
                        assert response.context_data[f"{mh.medhistorytype}_form"].instance == mh
                        assert (
                            response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                                f"{mh.medhistorytype}_form"
                            ].instance._state.adding
                            is False
                        )
                        assert response.context_data[f"{mh.medhistorytype}_form"].initial == {
                            f"{mh.medhistorytype}-value": True
                        }
                    else:
                        assert f"{mh.medhistorytype}_form" not in response.context_data
                for mhtype in ULTAID_MEDHISTORYS:
                    assert f"{mhtype}_form" in response.context_data
                    if mhtype not in user.medhistory_set.values_list("medhistorytype", flat=True):
                        assert (
                            response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                                f"{mhtype}_form"
                            ].instance._state.adding
                            is True
                        )
                        assert response.context_data[f"{mhtype}_form"].initial == {f"{mhtype}-value": False}
                assert "ckddetail_form" in response.context_data
                if user.ckd:
                    if getattr(user.ckd, "ckddetail", None):
                        assert response.context_data["ckddetail_form"].instance == user.ckd.ckddetail
                        assert (
                            response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                                "ckddetail_form"
                            ].instance._state.adding
                            is False
                        )
                    else:
                        assert (
                            response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                                "ckddetail_form"
                            ].instance._state.adding
                            is True
                        )
                    if getattr(user.ckd, "baselinecreatinine", None):
                        assert response.context_data["baselinecreatinine_form"].instance == user.ckd.baselinecreatinine
                        assert (
                            response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                                "baselinecreatinine_form"
                            ].instance._state.adding
                            is False
                        )
                    else:
                        assert (
                            response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                                "baselinecreatinine_form"
                            ].instance._state.adding
                            is True
                        )
                else:
                    assert (
                        response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                            "ckddetail_form"
                        ].instance._state.adding
                        is True
                    )
                    assert (
                        response.context_data[  # pylint: disable=w0212, line-too-long # noqa: E501
                            "baselinecreatinine_form"
                        ].instance._state.adding
                        is True
                    )

    def test__get_context_data_onetoones(self):
        """Test that the context data includes the user's related models."""
        for user in Pseudopatient.objects.select_related("ultaid").all():
            if hasattr(user, "ultaid"):
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
                assert "ethnicity" in response.context_data
                assert response.context_data["ethnicity"] == user.ethnicity.value
                assert "gender" in response.context_data
                assert response.context_data["gender"] == user.gender.value
                assert "hlab5801_form" in response.context_data
                if hasattr(user, "hlab5801"):
                    assert response.context_data["hlab5801_form"].instance == user.hlab5801
                    assert response.context_data["hlab5801_form"].initial == {"value": user.hlab5801.value}

    def test__get_permission_object(self):
        """Test the get_permission_object() method for the view."""
        for user in Pseudopatient.objects.select_related("ultaid").all():
            if hasattr(user, "ultaid"):
                request = self.factory.get("/fake-url/")
                request.user = self.anon_user
                kwargs = {"username": user.username}
                view = self.view()
                view.setup(request, **kwargs)
                view.user = user
                view.object = view.get_object()
                permission_object = view.get_permission_object()
                self.assertEqual(permission_object, user.ultaid)

    def test__get_user_queryset(self):
        for pseudopatient in Pseudopatient.objects.select_related("ultaid").all():
            if hasattr(pseudopatient, "ultaid"):
                with self.assertNumQueries(4):
                    kwargs = {"pseudopatient": pseudopatient.pk}
                    qs = self.view(kwargs=kwargs).get_user_queryset(**kwargs)
                    self.assertTrue(isinstance(qs, QuerySet))
                    qs_obj = qs.first()
                    self.assertTrue(isinstance(qs_obj, Pseudopatient))
                    self.assertEqual(qs_obj, pseudopatient)
                    self.assertTrue(hasattr(qs_obj, "ultaid"))
                    self.assertEqual(qs_obj.ultaid, pseudopatient.ultaid)
                    self.assertTrue(hasattr(qs_obj, "baselinecreatinine"))
                    self.assertTrue(hasattr(qs_obj, "ckddetail"))
                    if qs_obj.ckddetail:
                        self.assertTrue(getattr(qs_obj, "ckd"))
                        self.assertTrue(isinstance(qs_obj.ckddetail, CkdDetail))
                    self.assertTrue(hasattr(qs_obj, "baselinecreatinine"))
                    if qs_obj.baselinecreatinine:
                        self.assertTrue(isinstance(qs_obj.baselinecreatinine, BaselineCreatinine))
                        self.assertTrue(getattr(qs_obj, "dateofbirth"))
                        self.assertTrue(getattr(qs_obj, "gender"))
                        self.assertTrue(getattr(qs_obj, "ckddetail"))
                    self.assertTrue(hasattr(qs_obj, "dateofbirth"))
                    if qs_obj.dateofbirth:
                        self.assertTrue(isinstance(qs_obj.dateofbirth, DateOfBirth))
                    if hasattr(qs_obj, "ultaidsettings"):
                        self.assertTrue(isinstance(qs_obj.ultaidsettings, UltAidSettings))
                    else:
                        self.assertFalse(hasattr(qs_obj, "ultaidsettings"))
                    self.assertTrue(hasattr(qs_obj, "ethnicity"))
                    self.assertTrue(isinstance(qs_obj.ethnicity, Ethnicity))
                    self.assertTrue(hasattr(qs_obj, "gender"))
                    if qs_obj.gender:
                        self.assertTrue(isinstance(qs_obj.gender, Gender))
                    if hasattr(qs_obj, "goalurate"):
                        self.assertTrue(isinstance(qs_obj.goalurate, GoalUrate))
                    if hasattr(qs_obj, "hlab5801"):
                        self.assertTrue(isinstance(qs_obj.hlab5801, Hlab5801))
                    self.assertTrue(hasattr(qs_obj, "medallergys_qs"))
                    self.assertTrue(hasattr(qs_obj, "medhistorys_qs"))

    def test__post(self):
        """Test the post() method for the view."""
        for user in Pseudopatient.objects.select_related("ultaid").all():
            if hasattr(user, "ultaid"):
                request = self.factory.post("/fake-url/")
                if user.profile.provider:  # type: ignore
                    request.user = user.profile.provider  # type: ignore
                else:
                    request.user = self.anon_user
                SessionMiddleware(dummy_get_response).process_request(request)
                kwargs = {"pseudopatient": user.pk}
                response = self.view.as_view()(request, **kwargs)
                assert response.status_code == 200

    def test__post_creates_medhistorydetails(self):
        """Test that the view creates the User's MedHistoryDetails objects."""
        # Create user without ckd
        psp = create_psp(medhistorys=[])
        create_ultaid(user=psp)

        self.assertFalse(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.CKD).exists())

        data = ultaid_data_factory(user=psp)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                # Create data for CKD
                "dialysis": False,
                "baselinecreatinine-value": Decimal("2.2"),
            }
        )

        response = self.client.post(
            reverse("ultaids:pseudopatient-update", kwargs={"pseudopatient": psp.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302
        assert (
            response.url == f"{reverse('ultaids:pseudopatient-detail', kwargs={'pseudopatient': psp.pk})}?updated=True"
        )

        self.assertTrue(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.CKD).exists())
        ckd = MedHistory.objects.get(user=psp, medhistorytype=MedHistoryTypes.CKD)
        self.assertTrue(CkdDetail.objects.filter(medhistory=ckd).exists())
        self.assertTrue(BaselineCreatinine.objects.filter(medhistory=ckd).exists())

    def test__post_deletes_medhistorydetail(self):
        psp = create_psp(
            medhistorys=[MedHistoryTypes.CKD],
            mh_dets={MedHistoryTypes.CKD: {"dialysis": False, "baselinecreatinine": Decimal("2.2")}},
        )
        create_ultaid(user=psp)
        self.assertTrue(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.CKD).exists())
        self.assertTrue(
            CkdDetail.objects.filter(medhistory=psp.ckd).exists()
            and BaselineCreatinine.objects.filter(medhistory=psp.ckd).exists()
        )

        data = ultaid_data_factory(user=psp)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": False,
            }
        )

        response = self.client.post(
            reverse("ultaids:pseudopatient-update", kwargs={"pseudopatient": psp.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302
        assert (
            response.url == f"{reverse('ultaids:pseudopatient-detail', kwargs={'pseudopatient': psp.pk})}?updated=True"
        )

        self.assertFalse(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.CKD).exists())
        self.assertFalse(CkdDetail.objects.filter(medhistory=psp.ckd).exists())
        self.assertFalse(BaselineCreatinine.objects.filter(medhistory=psp.ckd).exists())

    def test__post_removes_hlab5801(self):
        """Test that a POST request removes a Hlab5801 instance as an attribute
        to the updated UltAid and deletes the Hlab5801 instance."""
        if not hasattr(self.user, "hlab5801"):
            Hlab5801Factory(user=self.user, value=True)
        ultaid_data = ultaid_data_factory(user=self.user, otos={"hlab5801": ""})
        response = self.client.post(
            reverse("ultaids:pseudopatient-update", kwargs={"pseudopatient": self.user.pk}), ultaid_data
        )
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Hlab5801.objects.filter(user=self.user).exists())

    def test__post_adds_False_hlab5801(self):
        """Test that a POST request creates and adds a Hlab5801 instance, with
        a value=False, as an attribute to the updated 'UltAid's user."""
        user_without_hlab5801 = create_psp()
        create_ultaid(user=user_without_hlab5801, hlab5801=None)
        self.assertFalse(Hlab5801.objects.filter(user=user_without_hlab5801).exists())

        ultaid_data = ultaid_data_factory(user=user_without_hlab5801, otos={"hlab5801": False})

        response = self.client.post(
            reverse("ultaids:pseudopatient-update", kwargs={"pseudopatient": user_without_hlab5801.pk}), ultaid_data
        )
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        self.assertTrue(Hlab5801.objects.filter(user=user_without_hlab5801).exists())
        self.assertFalse(Hlab5801.objects.get(user=user_without_hlab5801).value)

    def test__post_adds_True_hlab5801(self):
        """Test that a POST request creates and adds a Hlab5801 instance, with
        a value=True, as an attribute to the updated UltAid's user."""
        user_without_hlab5801 = create_psp()
        create_ultaid(user=user_without_hlab5801, hlab5801=None)
        self.assertFalse(Hlab5801.objects.filter(user=user_without_hlab5801).exists())

        ultaid_data = ultaid_data_factory(user=user_without_hlab5801, otos={"hlab5801": True})
        response = self.client.post(
            reverse("ultaids:pseudopatient-update", kwargs={"pseudopatient": user_without_hlab5801.pk}),
            ultaid_data,
        )
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Hlab5801.objects.filter(user=user_without_hlab5801).exists())
        self.assertTrue(Hlab5801.objects.get(user=user_without_hlab5801).value)

    def test__post_updates_hlab5801_True_to_False(self):
        """Test that a POST request updates a Hlab5801 object / UltAid attribute
        from True to False."""
        if not hasattr(self.user, "hlab5801"):
            Hlab5801Factory(user=self.user, value=True)
        elif self.user.hlab5801.value:
            self.user.hlab5801.value = False
            self.user.hlab5801.save()
        ultaid_data = ultaid_data_factory(user=self.user, otos={"hlab5801": False})
        response = self.client.post(
            reverse("ultaids:pseudopatient-update", kwargs={"pseudopatient": self.user.pk}), ultaid_data
        )
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Hlab5801.objects.filter(user=self.user).exists())
        self.assertFalse(Hlab5801.objects.get(user=self.user).value)

    def test__post_updates_hlab5801_False_to_True(self):
        """Test that a POST request updates a Hlab5801 object / UltAid attribute
        from False to True."""
        if not hasattr(self.user, "hlab5801"):
            Hlab5801Factory(user=self.user, value=False)
        elif not self.user.hlab5801.value:
            self.user.hlab5801.value = False
            self.user.hlab5801.save()
        ultaid_data = ultaid_data_factory(user=self.user, otos={"hlab5801": True})
        response = self.client.post(
            reverse("ultaids:pseudopatient-update", kwargs={"pseudopatient": self.user.pk}), ultaid_data
        )
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Hlab5801.objects.filter(user=self.user).exists())
        self.assertTrue(Hlab5801.objects.get(user=self.user).value)

    def test__post_returns_errors(self):
        """Test that post returns errors for some common scenarios where the
        data is invalid. Typically, these are scenarios that should be prevented by
        the form or javascript."""
        # Test that the view returns errors when the baselinecreatinine and
        # stage are not congruent
        data = ultaid_data_factory(user=self.user)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": False,
                "baselinecreatinine-value": Decimal("9.9"),
                "stage": Stages.ONE,
            }
        )
        response = self.client.post(
            reverse("ultaids:pseudopatient-update", kwargs={"pseudopatient": self.user.pk}), data=data
        )
        assert response.status_code == 200

        assert "form" in response.context_data
        assert "ckddetail_form" in response.context_data
        assert "stage" in response.context_data["ckddetail_form"].errors
        assert "baselinecreatinine_form" in response.context_data
        assert "value" in response.context_data["baselinecreatinine_form"].errors

        # Test that the view DOES NOT return errors when CKD is True and dialysis is left blank
        # For the UltAid CkdDetail is optional
        data = ultaid_data_factory(user=self.user)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
            }
        )
        response = self.client.post(
            reverse("ultaids:pseudopatient-update", kwargs={"pseudopatient": self.user.pk}), data=data
        )
        assert response.status_code == 302

    def test__rules(self):
        """Tests for whether the rules appropriately allow or restrict
        access to the view."""
        psp = create_psp()
        create_ultaid(user=psp)
        provider = UserFactory()
        provider_psp = create_psp(provider=provider)
        create_ultaid(user=provider_psp)
        admin = AdminFactory()
        admin_psp = create_psp(provider=admin)
        create_ultaid(user=admin_psp)
        # Test that any User can create an anonymous Pseudopatient's UltAid
        response = self.client.get(reverse("ultaids:pseudopatient-update", kwargs={"pseudopatient": psp.pk}))
        assert response.status_code == 200
        # Test that an anonymous User can't create a Provider's UltAid
        response = self.client.get(reverse("ultaids:pseudopatient-update", kwargs={"pseudopatient": provider_psp.pk}))
        # 302 because PermissionDenied will redirect to the login page
        assert response.status_code == 302
        # Test that an anonymous User can't create an Admin's UltAid
        response = self.client.get(reverse("ultaids:pseudopatient-update", kwargs={"pseudopatient": admin_psp.pk}))
        # Test that a Provider can create his or her own Pseudopatient's UltAid
        response = self.client.get(
            reverse("ultaids:pseudopatient-update", kwargs={"pseudopatient": psp.pk}),
        )
        assert response.status_code == 200
        # Test that a Provider can create an anonymous Pseudopatient's UltAid
        response = self.client.get(
            reverse("ultaids:pseudopatient-update", kwargs={"pseudopatient": psp.pk}),
        )
        assert response.status_code == 200
        self.client.force_login(admin)
        response = self.client.get(
            reverse("ultaids:pseudopatient-update", kwargs={"pseudopatient": admin_psp.pk}),
        )
        assert response.status_code == 200
        # Test that only a Pseudopatient's Provider can add their UltAid if they have a Provider
        response = self.client.get(
            reverse("ultaids:pseudopatient-update", kwargs={"pseudopatient": provider_psp.pk}),
        )
        assert response.status_code == 403
        self.client.force_login(provider)
        # Test that a Provider can't create another provider's Pseudopatient's UltAid
        response = self.client.get(
            reverse("ultaids:pseudopatient-update", kwargs={"pseudopatient": admin_psp.pk}),
        )
        assert response.status_code == 403
        self.client.force_login(admin)
        # Test that an Admin can create an anonymous Pseudopatient's UltAid
        response = self.client.get(
            reverse("ultaids:pseudopatient-update", kwargs={"pseudopatient": psp.pk}),
        )
        assert response.status_code == 200


class TestUltAidUpdate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltAidUpdate = UltAidUpdate()

    def test__post_removes_hlab5801(self):
        """Test that a POST request removes a Hlab5801 instance as an attribute
        to the updated UltAid and deletes the Hlab5801 instance."""
        ultaid = create_ultaid(hlab5801=True)
        self.assertTrue(Hlab5801.objects.all())
        self.assertEqual(UltAid.objects.get().hlab5801, Hlab5801.objects.get())
        ultaid_data = ultaid_data_factory(ultaid=ultaid, otos={"hlab5801": ""})
        response = self.client.post(reverse("ultaids:update", kwargs={"pk": ultaid.pk}), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Hlab5801.objects.all())
        ultaid.refresh_from_db()
        self.assertIsNone(ultaid.hlab5801)

    def test__post_adds_False_hlab5801(self):
        """Test that a POST request creates and adds a Hlab5801 instance, with
        a value=False, as an attribute to the updated UltAid."""
        ultaid = create_ultaid(hlab5801=None)
        self.assertFalse(Hlab5801.objects.all())
        self.assertIsNone(UltAid.objects.get().hlab5801)
        ultaid_data = ultaid_data_factory(ultaid=ultaid, otos={"hlab5801": False})
        response = self.client.post(reverse("ultaids:update", kwargs={"pk": ultaid.pk}), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        ultaid.refresh_from_db()
        self.assertTrue(Hlab5801.objects.all())
        hlab5801 = Hlab5801.objects.get()
        self.assertEqual(ultaid.hlab5801, hlab5801)
        self.assertFalse(hlab5801.value)

    def test__post_adds_True_hlab5801(self):
        """Test that a POST request creates and adds a Hlab5801 instance, with
        a value=True, as an attribute to the updated UltAid."""
        ultaid = create_ultaid(hlab5801=None)
        self.assertFalse(Hlab5801.objects.all())
        self.assertIsNone(UltAid.objects.get().hlab5801)
        ultaid_data = ultaid_data_factory(ultaid=ultaid, otos={"hlab5801": True})
        response = self.client.post(reverse("ultaids:update", kwargs={"pk": ultaid.pk}), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        ultaid.refresh_from_db()
        self.assertTrue(Hlab5801.objects.all())
        hlab5801 = Hlab5801.objects.get()
        self.assertEqual(ultaid.hlab5801, hlab5801)
        self.assertTrue(hlab5801.value)

    def test__post_removes_updates_hlab5801_True_to_False(self):
        """Test that a POST request updates a Hlab5801 object / UltAid attribute
        from True to False."""
        ultaid = create_ultaid(hlab5801=True)
        self.assertTrue(Hlab5801.objects.all())
        self.assertEqual(UltAid.objects.get().hlab5801, Hlab5801.objects.get())
        ultaid_data = ultaid_data_factory(ultaid=ultaid, otos={"hlab5801": False})
        response = self.client.post(reverse("ultaids:update", kwargs={"pk": ultaid.pk}), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        self.assertTrue(Hlab5801.objects.all())
        hlab5801 = Hlab5801.objects.get()
        ultaid.refresh_from_db()
        self.assertEqual(ultaid.hlab5801, hlab5801)
        self.assertFalse(hlab5801.value)

    def test__post_removes_updates_hlab5801_False_to_True(self):
        """Test that a POST request updates a Hlab5801 object / UltAid attribute
        from False to True."""
        ultaid = create_ultaid(hlab5801=False)
        self.assertTrue(Hlab5801.objects.all())
        self.assertEqual(UltAid.objects.get().hlab5801, Hlab5801.objects.get())
        ultaid_data = ultaid_data_factory(ultaid=ultaid, otos={"hlab5801": True})

        response = self.client.post(reverse("ultaids:update", kwargs={"pk": ultaid.pk}), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        self.assertTrue(Hlab5801.objects.all())
        hlab5801 = Hlab5801.objects.get()
        ultaid.refresh_from_db()
        self.assertEqual(ultaid.hlab5801, hlab5801)
        self.assertTrue(hlab5801.value)

    def test__post_ckd_without_detail_saves(self):
        """Test that a POST request can create or update a CKD instance without
        an associated CkdDetail instance. This is unique to certain models, like
        UltAid, that doesn't require CkdDetail for processing."""
        ultaid = create_ultaid(mhs=[])
        self.assertFalse(ultaid.ckd)
        self.assertFalse(ultaid.ckddetail)
        ultaid_data = ultaid_data_factory(ultaid=ultaid, mhs=[MedHistoryTypes.CKD])
        response = self.client.post(reverse("ultaids:update", kwargs={"pk": ultaid.pk}), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        ultaid = UltAid.objects.get(pk=ultaid.pk)
        self.assertTrue(ultaid.ckd)
        self.assertFalse(ultaid.ckddetail)
