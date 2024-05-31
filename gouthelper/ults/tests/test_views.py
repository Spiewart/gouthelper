import random  # pylint: disable=E0401  # type: ignore
from decimal import Decimal

import pytest  # pylint: disable=E0401  # type: ignore
from django.contrib.auth.models import AnonymousUser  # pylint: disable=E0401  # type: ignore
from django.contrib.messages.middleware import MessageMiddleware  # pylint: disable=e0401 # type: ignore
from django.contrib.sessions.middleware import SessionMiddleware  # pylint: disable=e0401 # type: ignore
from django.db.models import Q, QuerySet  # pylint: disable=E0401  # type: ignore
from django.http import HttpResponse, HttpResponseRedirect  # pylint: disable=E0401  # type: ignore
from django.test import RequestFactory, TestCase  # pylint: disable=E0401  # type: ignore
from django.urls import reverse  # pylint: disable=E0401  # type: ignore

from ...contents.choices import Tags
from ...contents.models import Content
from ...dateofbirths.helpers import age_calc
from ...dateofbirths.models import DateOfBirth
from ...genders.choices import Genders
from ...genders.models import Gender
from ...labs.models import BaselineCreatinine
from ...medhistorydetails.choices import Stages
from ...medhistorydetails.models import CkdDetail
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import ULT_MEDHISTORYS
from ...medhistorys.models import Ckd, Erosions, Hyperuricemia, MedHistory, Tophi, Uratestones
from ...users.models import Pseudopatient
from ...users.tests.factories import AdminFactory, UserFactory, create_psp
from ...utils.forms import forms_print_response_errors
from ...utils.test_helpers import dummy_get_response
from ..choices import FlareFreqs, FlareNums
from ..models import Ult
from ..selectors import ult_user_qs
from ..views import (
    UltAbout,
    UltCreate,
    UltDetail,
    UltPseudopatientCreate,
    UltPseudopatientDetail,
    UltPseudopatientUpdate,
    UltUpdate,
)
from .factories import create_ult, get_freq_flares, ult_data_factory

pytestmark = pytest.mark.django_db


class TestUltAbout(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltAbout = UltAbout()

    def test__get(self):
        response = self.client.get(reverse("ults:about"))
        self.assertEqual(response.status_code, 200)

    def test__get_context_data(self):
        response = self.client.get(reverse("ults:about"))
        self.assertIn("content", response.context_data)

    def test__content(self):
        self.assertEqual(self.view.content, Content.objects.get(context=Content.Contexts.ULT, slug="about", tag=None))


class TestUltCreate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltCreate = UltCreate()

    def test__get_context_data(self):
        request = self.factory.get("ults/create")
        request.user = AnonymousUser()
        SessionMiddleware(dummy_get_response).process_request(request)
        response = UltCreate.as_view()(request)
        self.assertIn("dateofbirth_form", response.context_data)
        self.assertIn("gender_form", response.context_data)
        self.assertIn(f"{MedHistoryTypes.CKD}_form", response.context_data)
        self.assertIn("ckddetail_form", response.context_data)
        self.assertIn("baselinecreatinine_form", response.context_data)
        self.assertIn(f"{MedHistoryTypes.EROSIONS}_form", response.context_data)
        self.assertIn(f"{MedHistoryTypes.HYPERURICEMIA}_form", response.context_data)
        self.assertIn(f"{MedHistoryTypes.TOPHI}_form", response.context_data)
        self.assertIn(f"{MedHistoryTypes.URATESTONES}_form", response.context_data)

    def test__post_creates_ult_and_related_objects(self):
        ult_data = {
            "num_flares": FlareNums.ONE,
            "dateofbirth-value": 50,
            "gender-value": Genders.FEMALE,
            f"{MedHistoryTypes.CKD}-value": True,
            "baselinecreatinine-value": Decimal("2.0"),
            "dialysis": False,
            "stage": Stages.THREE,
            f"{MedHistoryTypes.EROSIONS}-value": True,
            f"{MedHistoryTypes.HYPERURICEMIA}-value": True,
            f"{MedHistoryTypes.TOPHI}-value": True,
            f"{MedHistoryTypes.URATESTONES}-value": True,
        }
        response = self.client.post(reverse("ults:create"), ult_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Ult.objects.all().exists())
        ult = Ult.related_objects.order_by("created").last()
        self.assertEqual(ult.num_flares, FlareNums.ONE)
        self.assertTrue(hasattr(ult, "dateofbirth"))
        self.assertEqual(ult.dateofbirth, DateOfBirth.objects.order_by("created").last())
        self.assertTrue(hasattr(ult, "gender"))
        self.assertEqual(ult.gender, Gender.objects.order_by("created").last())
        ckd = Ckd.objects.order_by("created").last()
        self.assertIn(ckd, ult.medhistorys_qs)
        baselinecreatinine = BaselineCreatinine.objects.order_by("created").last()
        ckddetail = CkdDetail.objects.order_by("created").last()
        self.assertEqual(ckddetail.medhistory, ckd)
        self.assertEqual(ckddetail.stage, Stages.THREE)
        self.assertEqual(baselinecreatinine.value, Decimal("2.0"))
        self.assertEqual(baselinecreatinine.medhistory, ckd)
        self.assertIn(Erosions.objects.order_by("created").last(), ult.medhistorys_qs)
        self.assertIn(Hyperuricemia.objects.order_by("created").last(), ult.medhistorys_qs)
        self.assertIn(Tophi.objects.order_by("created").last(), ult.medhistorys_qs)
        self.assertIn(Uratestones.objects.order_by("created").last(), ult.medhistorys_qs)

    def test__post_returns_errors(self):
        """Test that the post() method returns a 200 response with errors
        attached to the forms when they are present."""
        ult_data = ult_data_factory()
        ult_data["num_flares"] = FlareNums.ONE
        ult_data["freq_flares"] = FlareFreqs.TWOORMORE
        response = self.client.post(reverse("ults:create"), ult_data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data["form"].errors)
        self.assertIn("freq_flares", response.context_data["form"].errors)


class TestUltDetail(TestCase):
    def setUp(self):
        self.ult = create_ult(num_flares=FlareNums.TWOPLUS, freq_flares=FlareFreqs.TWOORMORE)
        self.factory = RequestFactory()
        self.view: UltDetail = UltDetail
        self.content_qs = Content.objects.filter(
            Q(tag=Content.Tags.EXPLANATION) | Q(tag=Content.Tags.WARNING),
            context=Content.Contexts.ULT,
            slug__isnull=False,
        ).all()
        self.anon_user = AnonymousUser()

    def test__dispatch_redirects_ult_with_user(self):
        ult = create_ult(user=True)
        request = self.factory.get(reverse("ults:detail", kwargs={"pk": ult.pk}))
        request.user = ult.user
        response = self.view.as_view()(request, pk=ult.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("ults:pseudopatient-detail", kwargs={"username": ult.user.username}))

    def test__get_queryset(self):
        qs = self.view(kwargs={"pk": self.ult.pk}).get_queryset()
        self.assertTrue(isinstance(qs, QuerySet))
        ult = qs.get()
        self.assertEqual(ult, self.ult)
        self.assertTrue(hasattr(ult, "medhistorys_qs"))
        self.assertTrue(hasattr(ult, "ckddetail"))
        self.assertTrue(hasattr(ult, "baselinecreatinine"))
        self.assertTrue(hasattr(ult, "dateofbirth"))
        self.assertTrue(hasattr(ult, "gender"))

    def test__get_object_updates(self):
        self.assertEqual(self.ult.indication, self.ult.Indications.NOTINDICATED)
        request = self.factory.get(reverse("ults:detail", kwargs={"pk": self.ult.pk}))
        request.user = self.anon_user
        self.view.as_view()(request, pk=self.ult.pk)
        # This needs to be manually refetched from the db
        self.assertIsNotNone(
            Ult.objects.get().indication,
            Ult.Indications.INDICATED,
        )

    def test__get_object_does_not_update(self):
        self.assertEqual(self.ult.indication, self.ult.Indications.NOTINDICATED)
        request = self.factory.get(reverse("ults:detail", kwargs={"pk": self.ult.pk}) + "?updated=True")
        request.user = self.anon_user
        self.view.as_view()(request, pk=self.ult.pk)
        # This needs to be manually refetched from the db
        self.assertEqual(Ult.objects.get().indication, self.ult.Indications.NOTINDICATED)


class TestUltPseudopatientCreate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltPseudopatientCreate = UltPseudopatientCreate
        self.user = create_psp(plus=True)
        for _ in range(5):
            create_psp(plus=True)
        self.ult_with_user = create_ult(user=create_psp(plus=True))
        self.user_with_ult = self.ult_with_user.user
        self.anon_user = AnonymousUser()

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
        view = self.view()
        view.set_forms()
        self.assertTrue(view.ckddetail)

    def test__dispatch(self):
        """Test the dispatch() method for the view. Should redirect to detailview when
        the user already has a Ult. Should redirect to Pseudopatient Update
        view when the user doesn't have the required 1to1 related models."""
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        kwargs = {"username": self.user.username}
        view = self.view()
        SessionMiddleware(dummy_get_response).process_request(request)

        view.setup(request, **kwargs)
        response = view.dispatch(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(hasattr(view, "user"))
        self.assertEqual(view.user, self.user)

        # Create a new Ult and test that the view redirects to the detailview
        create_ult(user=self.user)
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("ults:pseudopatient-create", kwargs={"username": self.user.username}), follow=True
        )
        self.assertEqual(view.user, self.user)
        self.assertRedirects(response, reverse("ults:pseudopatient-update", kwargs={"username": self.user.username}))
        # Check that the response message is correct
        message = list(response.context.get("messages"))[0]
        self.assertEqual(message.tags, "error")
        self.assertEqual(message.message, f"{self.user} already has a Ult. Please update it instead.")

        # Create empty user and test that the view redirects to the user update view
        empty_user = create_psp(dateofbirth=False, ethnicity=False, gender=False)
        self.client.force_login(empty_user)
        response = self.client.get(
            reverse("ults:pseudopatient-create", kwargs={"username": empty_user.username}), follow=True
        )
        self.assertRedirects(response, reverse("users:pseudopatient-update", kwargs={"username": empty_user.username}))
        message = list(response.context.get("messages"))[0]
        self.assertEqual(message.tags, "error")
        self.assertEqual(
            message.message, "Baseline information is needed to use GoutHelper Decision and Treatment Aids."
        )

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
        self.assertIn("patient", form_kwargs)
        self.assertTrue(form_kwargs["patient"])

    def test__goutdetail(self):
        """Tests the goutdetail cached_property."""
        self.assertFalse(self.view().goutdetail)

    def test__get_context_data_medhistorys(self):
        """Test that the context data includes the user's related MedHistory and MedHistoryDetail models."""
        for user in Pseudopatient.objects.select_related("ult").all():
            if not hasattr(user, "ult"):
                request = self.factory.get("/fake-url/")
                if user.profile.provider:
                    request.user = user.profile.provider
                else:
                    request.user = self.anon_user
                kwargs = {"username": user.username}
                SessionMiddleware(dummy_get_response).process_request(request)
                response = self.view.as_view()(request, **kwargs)
                assert response.status_code == 200
                for mh in user.medhistory_set.all():
                    if mh.medhistorytype in ULT_MEDHISTORYS:
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
                for mhtype in ULT_MEDHISTORYS:
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
        for user in Pseudopatient.objects.select_related("ult").all():
            if not hasattr(user, "ult"):
                request = self.factory.get("/fake-url/")
                if user.profile.provider:
                    request.user = user.profile.provider
                else:
                    request.user = self.anon_user
                kwargs = {"username": user.username}
                SessionMiddleware(dummy_get_response).process_request(request)
                response = self.view.as_view()(request, **kwargs)
                assert response.status_code == 200
                assert "age" in response.context_data
                assert response.context_data["age"] == age_calc(user.dateofbirth.value)
                assert "gender" in response.context_data
                assert response.context_data["gender"] == user.gender.value

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
            with self.assertNumQueries(3):
                kwargs = {"username": pseudopatient.username}
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
                self.assertTrue(hasattr(qs_obj, "gender"))
                if qs_obj.gender:
                    self.assertTrue(isinstance(qs_obj.gender, Gender))
                self.assertTrue(hasattr(qs_obj, "medhistorys_qs"))

    def test__post(self):
        """Test the post() method for the view."""
        for user in Pseudopatient.objects.select_related("ult").all():
            if not hasattr(user, "ult"):
                request = self.factory.post("/fake-url/")
                if user.profile.provider:  # type: ignore
                    request.user = user.profile.provider  # type: ignore
                else:
                    request.user = self.anon_user
                kwargs = {"username": user.username}
                SessionMiddleware(dummy_get_response).process_request(request)
                response = self.view.as_view()(request, **kwargs)
                assert response.status_code == 200

    def test__post_sets_object_user(self):
        """Test that the post() method for the view sets the
        user on the object."""
        for user in Pseudopatient.objects.select_related("ult").all():
            if not hasattr(user, "ult"):
                data = ult_data_factory(user=self.user)
                response = self.client.post(
                    reverse("ults:pseudopatient-create", kwargs={"username": self.user.username}), data=data
                )
                forms_print_response_errors(response)
                assert response.status_code == 302
                assert Ult.objects.filter(user=self.user).exists()
                ult = Ult.objects.get(user=self.user)
                assert ult.user
                assert ult.user == self.user

    def test__post_updates_medhistorys(self):
        for user in Pseudopatient.objects.select_related("ult").all():
            if not hasattr(user, "ult"):
                user_mh_dict = {mh: user.medhistory_set.filter(medhistorytype=mh).exists() for mh in ULT_MEDHISTORYS}
                data = ult_data_factory(user)
                data.update(
                    {
                        **{
                            f"{mh}-value": not user_mh_dict[mh]
                            for mh in ULT_MEDHISTORYS
                            # Need to exclude CKD because of related CkdDetail fields throwing errors
                            if mh != MedHistoryTypes.CKD
                        },
                    }
                )
                response = self.client.post(
                    reverse("ults:pseudopatient-create", kwargs={"username": user.username}), data=data
                )
                forms_print_response_errors(response)
                assert response.status_code == 302
                assert (
                    response.url
                    == f"{reverse('ults:pseudopatient-detail', kwargs={'username': user.username})}?updated=True"
                )
                for mh in [mh for mh in ULT_MEDHISTORYS if mh != MedHistoryTypes.CKD]:
                    self.assertEqual(user.medhistory_set.filter(medhistorytype=mh).exists(), not user_mh_dict[mh])

    def test__post_creates_medhistorydetails(self):
        """Test that the view creates the User's MedHistoryDetails objects."""
        # Create user without ckd
        psp = create_psp(medhistorys=[])
        self.assertFalse(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.CKD).exists())

        data = ult_data_factory(
            user=psp,
            mhs=[MedHistoryTypes.CKD],
            mh_dets={
                MedHistoryTypes.CKD: {
                    "dialysis": False,
                    "baselinecreatinine": Decimal("2.2"),
                }
            },
        )

        response = self.client.post(reverse("ults:pseudopatient-create", kwargs={"username": psp.username}), data=data)
        forms_print_response_errors(response)
        assert response.status_code == 302
        assert (
            response.url == f"{reverse('ults:pseudopatient-detail', kwargs={'username': psp.username})}?updated=True"
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

        data = ult_data_factory(user=psp)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": False,
            }
        )

        response = self.client.post(reverse("ults:pseudopatient-create", kwargs={"username": psp.username}), data=data)
        forms_print_response_errors(response)
        assert response.status_code == 302
        assert (
            response.url == f"{reverse('ults:pseudopatient-detail', kwargs={'username': psp.username})}?updated=True"
        )

        self.assertFalse(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.CKD).exists())
        self.assertFalse(CkdDetail.objects.filter(medhistory=psp.ckd).exists())
        self.assertFalse(BaselineCreatinine.objects.filter(medhistory=psp.ckd).exists())

    def test__post_returns_errors(self):
        """Test that post returns errors for some common scenarios where the
        data is invalid. Typically, these are scenarios that should be prevented by
        the form or javascript."""
        # Test that the view returns errors when the baselinecreatinine and
        # stage are not congruent
        data = ult_data_factory(user=self.user)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": False,
                "baselinecreatinine-value": Decimal("9.9"),
                "stage": Stages.ONE,
            }
        )
        response = self.client.post(
            reverse("ults:pseudopatient-create", kwargs={"username": self.user.username}), data=data
        )
        assert response.status_code == 200

        assert "form" in response.context_data
        assert "ckddetail_form" in response.context_data
        assert "stage" in response.context_data["ckddetail_form"].errors
        assert "baselinecreatinine_form" in response.context_data
        assert "value" in response.context_data["baselinecreatinine_form"].errors

        # Test that the view returns errors when CKD is True and dialysis is left blank
        data = ult_data_factory(user=self.user)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": "",
            }
        )
        response = self.client.post(
            reverse("ults:pseudopatient-create", kwargs={"username": self.user.username}), data=data
        )
        assert response.status_code == 200

    def test__rules(self):
        """Tests for whether the rules appropriately allow or restrict
        access to the view."""
        psp = create_psp()
        provider = UserFactory()
        provider_psp = create_psp(provider=provider)
        admin = AdminFactory()
        admin_psp = create_psp(provider=admin)
        # Test that any User can create an anonymous Pseudopatient's Ult
        response = self.client.get(reverse("ults:pseudopatient-create", kwargs={"username": psp.username}))
        assert response.status_code == 200
        # Test that an anonymous User can't create a Provider's Ult
        response = self.client.get(reverse("ults:pseudopatient-create", kwargs={"username": provider_psp.username}))
        # 302 because PermissionDenied will redirect to the login page
        assert response.status_code == 302
        # Test that an anonymous User can't create an Admin's Ult
        response = self.client.get(reverse("ults:pseudopatient-create", kwargs={"username": admin_psp.username}))
        # Test that a Provider can create his or her own Pseudopatient's Ult
        response = self.client.get(
            reverse("ults:pseudopatient-create", kwargs={"username": psp.username}),
        )
        assert response.status_code == 200
        # Test that a Provider can create an anonymous Pseudopatient's Ult
        response = self.client.get(
            reverse("ults:pseudopatient-create", kwargs={"username": psp.username}),
        )
        assert response.status_code == 200
        self.client.force_login(admin)
        response = self.client.get(
            reverse("ults:pseudopatient-create", kwargs={"username": admin_psp.username}),
        )
        assert response.status_code == 200
        # Test that only a Pseudopatient's Provider can add their Ult if they have a Provider
        response = self.client.get(
            reverse("ults:pseudopatient-create", kwargs={"username": provider_psp.username}),
        )
        assert response.status_code == 403
        self.client.force_login(provider)
        # Test that a Provider can't create another provider's Pseudopatient's Ult
        response = self.client.get(
            reverse("ults:pseudopatient-create", kwargs={"username": admin_psp.username}),
        )
        assert response.status_code == 403
        self.client.force_login(admin)
        # Test that an Admin can create an anonymous Pseudopatient's Ult
        response = self.client.get(
            reverse("ults:pseudopatient-create", kwargs={"username": psp.username}),
        )
        assert response.status_code == 200


class TestUltPseudopatientDetail(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltPseudopatientDetail = UltPseudopatientDetail
        self.content_qs = Content.objects.filter(
            Q(tag=Tags.EXPLANATION) | Q(tag=Tags.WARNING), context=Content.Contexts.ULT, slug__isnull=False
        ).all()
        for _ in range(5):
            create_ult(user=create_psp(plus=True))

    def test__assign_ult_attrs_from_user(self):
        for ult in Ult.objects.filter(user__isnull=False).select_related("user"):
            user = ult_user_qs(username=ult.user.username).get()
            ult = user.ult
            self.assertFalse(getattr(ult, "dateofbirth"))
            self.assertFalse(getattr(ult, "gender"))
            self.assertFalse(hasattr(ult, "medhistorys_qs"))
            self.view.assign_ult_attrs_from_user(ult, ult.user)
            self.assertTrue(getattr(ult, "dateofbirth"))
            self.assertEqual(ult.dateofbirth, ult.user.dateofbirth)
            self.assertTrue(getattr(ult, "gender"))
            self.assertEqual(ult.gender, ult.user.gender)
            self.assertTrue(hasattr(ult, "medhistorys_qs"))
            for mh in ult.user.medhistory_set.filter(medhistorytype__in=ult.aid_medhistorys()):
                self.assertIn(mh, ult.medhistorys_qs)

    def test__dispatch(self):
        for ult in Ult.objects.filter(user__isnull=False).select_related("user"):
            view = self.view()
            kwargs = {"username": ult.user.username}
            request = self.factory.get(reverse("ults:pseudopatient-detail", kwargs=kwargs))
            request.user = ult.user
            view.setup(request, **kwargs)
            response = view.dispatch(request, **kwargs)
            self.assertTrue(isinstance(response, HttpResponse))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(hasattr(view, "object"))
            self.assertEqual(view.object, ult)
            self.assertTrue(hasattr(view, "user"))
            self.assertEqual(view.user, ult.user)

        # Test that the view redirects to the pseudopatient-create view if the user
        # is lacking a Ult
        user_without_ult = create_psp()
        view = self.view()
        kwargs = {"username": user_without_ult.username}
        request = self.factory.get(reverse("ults:pseudopatient-detail", kwargs=kwargs))
        request.user = user_without_ult
        view.setup(request, **kwargs)

        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        response = view.dispatch(request, **kwargs)
        self.assertTrue(isinstance(response, HttpResponseRedirect))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("ults:pseudopatient-create", kwargs=kwargs))

        # Test that the view redirects to the pseudopatient-update view if the user
        # is lacking one of their required OneToOneFields
        user_with_ult = Ult.objects.filter(user__isnull=False).first().user
        user_with_ult.dateofbirth.delete()
        view = self.view()
        kwargs = {"username": user_with_ult.username}
        request = self.factory.get(reverse("ults:pseudopatient-detail", kwargs=kwargs))
        request.user = user_with_ult
        view.setup(request, **kwargs)

        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        response = view.dispatch(request, **kwargs)
        self.assertTrue(isinstance(response, HttpResponseRedirect))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("users:pseudopatient-update", kwargs=kwargs))

    def test__get(self):
        """get() method should update the Ult's decisionaid field."""
        for ult in Ult.objects.filter(user__isnull=False).select_related("user"):
            modified = ult.modified
            response = self.client.get(reverse("ults:pseudopatient-detail", kwargs={"username": ult.user.username}))
            self.assertEqual(response.status_code, 200)
            ult.refresh_from_db()
            self.assertNotEqual(ult.modified, modified)

    def test__get_permission_object(self):
        for ult in Ult.objects.filter(user__isnull=False).select_related("user"):
            view = self.view()
            view.kwargs = {"username": ult.user.username}
            request = self.factory.get(reverse("ults:pseudopatient-detail", kwargs=view.kwargs))
            request.user = ult.user
            view.setup(request, **view.kwargs)
            view.object = view.get_object()
            self.assertEqual(view.get_permission_object(), ult)

    def test__get_queryset(self):
        for ult in Ult.objects.filter(user__isnull=False).select_related("user"):
            with self.assertNumQueries(3):
                qs = self.view(kwargs={"username": ult.user.username}).get_queryset()
                self.assertTrue(isinstance(qs, QuerySet))
                qs_obj = qs.first()
                self.assertTrue(isinstance(qs_obj, Pseudopatient))
                self.assertEqual(qs_obj, ult.user)
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
                self.assertTrue(hasattr(qs_obj, "gender"))
                if qs_obj.gender:
                    self.assertTrue(isinstance(qs_obj.gender, Gender))
                self.assertTrue(hasattr(qs_obj, "medhistorys_qs"))

    def test__get_object(self):
        for user in Pseudopatient.objects.ult_qs().all():
            view = self.view()
            view.kwargs = {"username": user.username}
            request = self.factory.get(reverse("ults:pseudopatient-detail", kwargs=view.kwargs))
            request.user = user
            view.setup(request, **view.kwargs)
            view.object = view.get_object()
            self.assertEqual(view.object, user.ult)

    def test__view_works(self):
        for user in Pseudopatient.objects.ult_qs().all():
            response = self.client.get(reverse("ults:pseudopatient-detail", kwargs={"username": user.username}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context_data["patient"], user)


class TestUltPseudopatientUpdate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltPseudopatientUpdate = UltPseudopatientUpdate
        self.content_qs = Content.objects.filter(
            Q(tag=Tags.EXPLANATION) | Q(tag=Tags.WARNING), context=Content.Contexts.ULT, slug__isnull=False
        ).all()
        self.anon_user = AnonymousUser()
        self.user = create_psp(plus=True)
        create_ult(user=self.user)
        self.user_without_ult = create_psp()
        for _ in range(5):
            create_ult(user=create_psp(plus=True))

    def test__check_user_onetoones(self):
        """Tests that the view checks for the User's related models."""
        empty_user = create_psp(gender=False)
        with self.assertRaises(AttributeError) as exc:
            self.view().check_user_onetoones(empty_user)
        self.assertEqual(
            exc.exception.args[0], "Baseline information is needed to use GoutHelper Decision and Treatment Aids."
        )
        assert self.view().check_user_onetoones(self.user) is None

    def test__ckddetail(self):
        """Tests the ckddetail cached_property."""
        view = self.view()
        view.set_forms()
        self.assertTrue(view.ckddetail)

    def test__dispatch(self):
        """Test the dispatch() method for the view. Should redirect to detailview when
        the user already has a Ult. Should redirect to Pseudopatient Update
        view when the user doesn't have the required 1to1 related models."""
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        kwargs = {"username": self.user.username}
        view = self.view()

        view.setup(request, **kwargs)
        SessionMiddleware(dummy_get_response).process_request(request)
        response = view.dispatch(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(hasattr(view, "user"))
        self.assertEqual(view.user, self.user)

        # Create a user without a Ult and assert that the view redirects to the user's create view
        self.client.force_login(self.user_without_ult)
        response = self.client.get(
            reverse("ults:pseudopatient-update", kwargs={"username": self.user_without_ult.username}),
            follow=True,
        )
        self.assertRedirects(
            response, reverse("ults:pseudopatient-create", kwargs={"username": self.user_without_ult.username})
        )
        # Check that the response message is correct
        message = list(response.context.get("messages"))[0]
        self.assertEqual(message.tags, "error")
        self.assertEqual(message.message, "No Ult matching the query")

        # Create empty user and test that the view redirects to the user update view
        empty_user = create_psp(dateofbirth=False, ethnicity=False, gender=False)
        self.client.force_login(empty_user)
        response = self.client.get(
            reverse("ults:pseudopatient-create", kwargs={"username": empty_user.username}), follow=True
        )
        self.assertRedirects(response, reverse("users:pseudopatient-update", kwargs={"username": empty_user.username}))
        message = list(response.context.get("messages"))[0]
        self.assertEqual(message.tags, "error")
        self.assertEqual(
            message.message, "Baseline information is needed to use GoutHelper Decision and Treatment Aids."
        )

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
        self.assertIn("patient", form_kwargs)
        self.assertTrue(form_kwargs["patient"])

    def test__goutdetail(self):
        """Tests the goutdetail cached_property."""
        self.assertFalse(self.view().goutdetail)

    def test__get_context_data_medhistorys(self):
        """Test that the context data includes the user's related MedHistory and MedHistoryDetail models."""
        for user in Pseudopatient.objects.select_related("ult").all():
            if hasattr(user, "ult"):
                request = self.factory.get("/fake-url/")
                if user.profile.provider:
                    request.user = user.profile.provider
                else:
                    request.user = self.anon_user
                kwargs = {"username": user.username}
                SessionMiddleware(dummy_get_response).process_request(request)
                response = self.view.as_view()(request, **kwargs)
                assert response.status_code == 200
                for mh in user.medhistory_set.all():
                    if mh.medhistorytype in ULT_MEDHISTORYS:
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
                for mhtype in ULT_MEDHISTORYS:
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
        for user in Pseudopatient.objects.select_related("ult").all():
            if hasattr(user, "ult"):
                request = self.factory.get("/fake-url/")
                if user.profile.provider:
                    request.user = user.profile.provider
                else:
                    request.user = self.anon_user
                kwargs = {"username": user.username}
                SessionMiddleware(dummy_get_response).process_request(request)
                response = self.view.as_view()(request, **kwargs)
                assert response.status_code == 200
                assert "age" in response.context_data
                assert response.context_data["age"] == age_calc(user.dateofbirth.value)
                assert "gender" in response.context_data
                assert response.context_data["gender"] == user.gender.value

    def test__get_permission_object(self):
        """Test the get_permission_object() method for the view."""
        for user in Pseudopatient.objects.select_related("ult").all():
            if hasattr(user, "ult"):
                request = self.factory.get("/fake-url/")
                request.user = self.anon_user
                kwargs = {"username": user.username}
                view = self.view()
                view.setup(request, **kwargs)
                view.user = user
                view.object = view.get_object()
                permission_object = view.get_permission_object()
                self.assertEqual(permission_object, user.ult)

    def test__get_user_queryset(self):
        for pseudopatient in Pseudopatient.objects.select_related("ult").all():
            if hasattr(pseudopatient, "ult"):
                with self.assertNumQueries(3):
                    kwargs = {"username": pseudopatient.username}
                    qs = self.view(kwargs=kwargs).get_user_queryset(**kwargs)
                    self.assertTrue(isinstance(qs, QuerySet))
                    qs_obj = qs.first()
                    self.assertTrue(isinstance(qs_obj, Pseudopatient))
                    self.assertEqual(qs_obj, pseudopatient)
                    self.assertTrue(hasattr(qs_obj, "ult"))
                    self.assertEqual(qs_obj.ult, pseudopatient.ult)
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
                    self.assertTrue(hasattr(qs_obj, "gender"))
                    if qs_obj.gender:
                        self.assertTrue(isinstance(qs_obj.gender, Gender))

    def test__post(self):
        """Test the post() method for the view."""
        for user in Pseudopatient.objects.select_related("ult").all():
            if hasattr(user, "ult"):
                request = self.factory.post("/fake-url/")
                if user.profile.provider:  # type: ignore
                    request.user = user.profile.provider  # type: ignore
                else:
                    request.user = self.anon_user
                kwargs = {"username": user.username}
                SessionMiddleware(dummy_get_response).process_request(request)
                response = self.view.as_view()(request, **kwargs)
                assert response.status_code == 200

    def test__post_creates_medhistorydetails(self):
        """Test that the view creates the User's MedHistoryDetails objects."""
        # Create user without ckd
        psp = create_psp(medhistorys=[])
        create_ult(user=psp)

        self.assertFalse(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.CKD).exists())

        data = ult_data_factory(user=psp)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                # Create data for CKD
                "dialysis": False,
                "baselinecreatinine-value": Decimal("2.2"),
                "stage": "",
            }
        )

        response = self.client.post(reverse("ults:pseudopatient-update", kwargs={"username": psp.username}), data=data)
        forms_print_response_errors(response)
        assert response.status_code == 302
        assert (
            response.url == f"{reverse('ults:pseudopatient-detail', kwargs={'username': psp.username})}?updated=True"
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
        create_ult(user=psp)
        self.assertTrue(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.CKD).exists())
        self.assertTrue(
            CkdDetail.objects.filter(medhistory=psp.ckd).exists()
            and BaselineCreatinine.objects.filter(medhistory=psp.ckd).exists()
        )

        data = ult_data_factory(user=psp)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": False,
            }
        )

        response = self.client.post(reverse("ults:pseudopatient-update", kwargs={"username": psp.username}), data=data)
        forms_print_response_errors(response)
        assert response.status_code == 302
        assert (
            response.url == f"{reverse('ults:pseudopatient-detail', kwargs={'username': psp.username})}?updated=True"
        )

        self.assertFalse(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.CKD).exists())
        self.assertFalse(CkdDetail.objects.filter(medhistory=psp.ckd).exists())
        self.assertFalse(BaselineCreatinine.objects.filter(medhistory=psp.ckd).exists())

    def test__post_returns_errors(self):
        """Test that post returns errors for some common scenarios where the
        data is invalid. Typically, these are scenarios that should be prevented by
        the form or javascript."""
        # Test that the view returns errors when the baselinecreatinine and
        # stage are not congruent
        data = ult_data_factory(user=self.user)
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": False,
                "baselinecreatinine-value": Decimal("9.9"),
                "stage": Stages.ONE,
            }
        )
        response = self.client.post(
            reverse("ults:pseudopatient-update", kwargs={"username": self.user.username}), data=data
        )
        assert response.status_code == 200

        assert "form" in response.context_data
        assert "ckddetail_form" in response.context_data
        assert "stage" in response.context_data["ckddetail_form"].errors
        assert "baselinecreatinine_form" in response.context_data
        assert "value" in response.context_data["baselinecreatinine_form"].errors

    def test__rules(self):
        """Tests for whether the rules appropriately allow or restrict
        access to the view."""
        psp = create_psp()
        create_ult(user=psp)
        provider = UserFactory()
        provider_psp = create_psp(provider=provider)
        create_ult(user=provider_psp)
        admin = AdminFactory()
        admin_psp = create_psp(provider=admin)
        create_ult(user=admin_psp)
        # Test that any User can create an anonymous Pseudopatient's Ult
        response = self.client.get(reverse("ults:pseudopatient-update", kwargs={"username": psp.username}))
        assert response.status_code == 200
        # Test that an anonymous User can't create a Provider's Ult
        response = self.client.get(reverse("ults:pseudopatient-update", kwargs={"username": provider_psp.username}))
        # 302 because PermissionDenied will redirect to the login page
        assert response.status_code == 302
        # Test that an anonymous User can't create an Admin's Ult
        response = self.client.get(reverse("ults:pseudopatient-update", kwargs={"username": admin_psp.username}))
        # Test that a Provider can create his or her own Pseudopatient's Ult
        response = self.client.get(
            reverse("ults:pseudopatient-update", kwargs={"username": psp.username}),
        )
        assert response.status_code == 200
        # Test that a Provider can create an anonymous Pseudopatient's Ult
        response = self.client.get(
            reverse("ults:pseudopatient-update", kwargs={"username": psp.username}),
        )
        assert response.status_code == 200
        self.client.force_login(admin)
        response = self.client.get(
            reverse("ults:pseudopatient-update", kwargs={"username": admin_psp.username}),
        )
        assert response.status_code == 200
        # Test that only a Pseudopatient's Provider can add their Ult if they have a Provider
        response = self.client.get(
            reverse("ults:pseudopatient-update", kwargs={"username": provider_psp.username}),
        )
        assert response.status_code == 403
        self.client.force_login(provider)
        # Test that a Provider can't create another provider's Pseudopatient's Ult
        response = self.client.get(
            reverse("ults:pseudopatient-update", kwargs={"username": admin_psp.username}),
        )
        assert response.status_code == 403
        self.client.force_login(admin)
        # Test that an Admin can create an anonymous Pseudopatient's Ult
        response = self.client.get(
            reverse("ults:pseudopatient-update", kwargs={"username": psp.username}),
        )
        assert response.status_code == 200


class TestUltUpdate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltUpdate = UltUpdate()
        self.ult = create_ult(mhs=[])

    def test__post_changes_ult_fields(self):
        """Test that post modifies the num_flares and freq_flares Ult fields."""
        init_num_flares = FlareNums(self.ult.num_flares)
        ult_data = ult_data_factory(ult=self.ult)
        ult_data.update(
            {
                "num_flares": random.choice([num for num in FlareNums.values if num != init_num_flares]),
            }
        )
        new_freq_flares = get_freq_flares(ult_data["num_flares"])
        ult_data.update({"freq_flares": new_freq_flares if new_freq_flares is not None else ""})
        response = self.client.post(reverse("ults:update", kwargs={"pk": self.ult.pk}), ult_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.ult.refresh_from_db()
        self.assertNotEqual(self.ult.num_flares, init_num_flares)
        self.assertEqual(self.ult.num_flares, ult_data["num_flares"])
        self.assertEqual(self.ult.freq_flares, ult_data["freq_flares"] if ult_data["freq_flares"] != "" else None)

    def test__post_with_ckd_ckddetail(self):
        """Test that a POST request creates a Ckd and associated CkdDetail."""
        self.assertFalse(self.ult.ckd)
        self.assertFalse(self.ult.ckddetail)
        ult_data = ult_data_factory(ult=self.ult, mhs=[MedHistoryTypes.CKD])
        response = self.client.post(reverse("ults:update", kwargs={"pk": self.ult.pk}), ult_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.ult.refresh_from_db()
        delattr(self.ult, "medhistorys_qs")
        delattr(self.ult, "ckd")
        delattr(self.ult, "ckddetail")
        self.assertTrue(self.ult.ckd)
        self.assertTrue(self.ult.ckddetail)

    def test__post_creates_baselinecreatinine(self):
        """Test that a POST request creates a BaselineCreatinine."""
        self.assertFalse(self.ult.baselinecreatinine)
        ult_data = ult_data_factory(
            ult=self.ult,
            mhs=[MedHistoryTypes.CKD],
            mh_dets={MedHistoryTypes.CKD: {"baselinecreatinine": Decimal("2.0")}},
        )

        self.assertIn("baselinecreatinine-value", ult_data)
        response = self.client.post(reverse("ults:update", kwargs={"pk": self.ult.pk}), ult_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.ult.refresh_from_db()
        delattr(self.ult, "medhistorys_qs")
        delattr(self.ult, "ckd")
        delattr(self.ult, "baselinecreatinine")
        self.assertTrue(BaselineCreatinine.objects.filter(medhistory=self.ult.ckd).exists())
        self.assertTrue(self.ult.baselinecreatinine)

    def test__post_returns_errors(self):
        """Test that the post() method returns a 200 response with errors
        attached to the forms when they are present."""
        ult_data = ult_data_factory(ult=self.ult)
        ult_data["num_flares"] = FlareNums.ONE
        ult_data["freq_flares"] = FlareFreqs.TWOORMORE
        response = self.client.post(reverse("ults:update", kwargs={"pk": self.ult.pk}), ult_data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data["form"].errors)
        self.assertIn("freq_flares", response.context_data["form"].errors)

        ult_data.update(
            {
                "freq_flares": "",
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": "",
                "stage": Stages.THREE,
            }
        )
        response = self.client.post(reverse("ults:update", kwargs={"pk": self.ult.pk}), ult_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data["ckddetail_form"].errors)
        self.assertIn("dialysis", response.context_data["ckddetail_form"].errors)
