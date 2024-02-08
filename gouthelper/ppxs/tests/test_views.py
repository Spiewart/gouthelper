from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils import timezone  # type: ignore

from ...goalurates.choices import GoalUrates
from ...labs.helpers import labs_urates_hyperuricemic
from ...labs.tests.factories import UrateFactory
from ...medhistorydetails.models import GoutDetail
from ...medhistorydetails.tests.factories import GoutDetailFactory
from ...medhistorys.models import Gout
from ...medhistorys.tests.factories import GoutFactory
from ...utils.helpers.test_helpers import count_data_deleted, tests_print_response_form_errors
from ..models import Ppx
from ..selectors import ppx_userless_qs
from ..views import PpxCreate, PpxUpdate
from .factories import create_ppx, ppx_data_factory

pytestmark = pytest.mark.django_db


class TestPpxCreate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: PpxCreate = PpxCreate()

    def test__post_creates_ppx(self):
        """Tests that a POST request creates a Ppx object."""
        # Count the number of existing Ppx, Gout, and GoutDetail objects
        ppx_count = Ppx.objects.count()
        gout_count = Gout.objects.count()
        goutdetail_count = GoutDetail.objects.count()

        # Create fake post() data and POST it
        ppx_data = ppx_data_factory()
        response = self.client.post(reverse("ppxs:create"), ppx_data)
        # NOTE: Will print errors for all forms in the context_data.
        tests_print_response_form_errors(response)
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
        self.assertEqual(goutdetail.flaring, ppx_data["flaring"])
        hyperuricemic = labs_urates_hyperuricemic(ppx.urates_qs, goutdetail, GoalUrates.SIX, commit=False)
        self.assertEqual(goutdetail.hyperuricemic, hyperuricemic if hyperuricemic else ppx_data["hyperuricemic"])
        if not hyperuricemic:
            self.assertEqual(goutdetail.hyperuricemic, ppx_data["hyperuricemic"])
        if getattr(ppx, "urates_qs", None):
            for urate in ppx.urates_qs:
                # Assert that the urate value and date_drawn are present in the ppx_data
                self.assertIn(urate.value, ppx_data.values())

    def test__post_creates_urate(self):
        """Test that post() method creates a single Urate object"""
        # Create some fake data that indicates new urates are to be created
        data = ppx_data_factory(urates=[Decimal("9.1"), Decimal("4.5")])

        # POST the data
        response = self.client.post(reverse("ppxs:create"), data)
        # NOTE: Will print errors for all forms in the context_data.
        tests_print_response_form_errors(response)
        self.assertEqual(response.status_code, 302)

        # Get the new ppx and its urates
        ppx = ppx_userless_qs(pk=Ppx.objects.order_by("created").last().pk).get()
        urates = ppx.urates_qs

        assert urates

        assert next(iter([urate for urate in urates if urate.value == Decimal("9.1")]), None)
        assert next(iter([urate for urate in urates if urate.value == Decimal("4.5")]), None)

        for urate in urates:
            assert urate.date_drawn
            assert urate.ppx == ppx


class TestPpxUpdate(TestCase):
    """Tests for the PpxUpdateView"""

    def setUp(self):
        self.factory = RequestFactory()
        self.view: PpxUpdate = PpxUpdate()
        # Create a Ppx object
        self.gout = GoutFactory()
        self.goutdetail = GoutDetailFactory(medhistory=self.gout, on_ult=False)
        self.urate1 = UrateFactory(date_drawn=timezone.now(), value=Decimal("5.9"))
        self.urate2 = UrateFactory(date_drawn=timezone.now() - timedelta(days=180), value=Decimal("7.9"))
        self.urate3 = UrateFactory(date_drawn=timezone.now() - timedelta(days=360), value=Decimal("9.9"))
        self.ppx = create_ppx(
            labs=[self.urate1, self.urate2, self.urate3],
        )

    def test__post_updates_ppx(self):
        """Tests that a POST request updates a Ppx object."""
        # Create some fake post() data based off the existing Ppx object
        data = ppx_data_factory(ppx=self.ppx, urates=[])

        # Make a couple data fields the opposite
        data.update(
            {
                "on_ult": not self.goutdetail.on_ult,
                "flaring": not self.goutdetail.flaring,
            }
        )
        # POST the data
        response = self.client.post(reverse("ppxs:update", kwargs={"pk": self.ppx.pk}), data)
        tests_print_response_form_errors(response)

        self.assertEqual(response.status_code, 302)

        # Assert that the changes were made
        ppx = ppx_userless_qs(pk=self.ppx.pk).get()
        self.assertNotEqual(ppx.goutdetail.on_ult, self.goutdetail.on_ult)
        self.assertNotEqual(ppx.goutdetail.flaring, self.goutdetail.flaring)

    def test__post_adds_urate(self):
        """Test that post() adds a Urate to the 3 that already exist for the Ppx."""
        # Create fake data with data for an extra urate
        data = ppx_data_factory(ppx=self.ppx, urates=[Decimal("11.5")])
        # Count the number of urates that are going to be deleted
        urates_deleted = count_data_deleted(data)

        # Count the total number of urates for the Ppx
        urates_count = self.ppx.urate_set.count()

        # POST the data
        response = self.client.post(reverse("ppxs:update", kwargs={"pk": self.ppx.pk}), data)
        tests_print_response_form_errors(response)
        self.assertEqual(response.status_code, 302)

        ppx = Ppx.objects.order_by("created").last()
        urates = ppx.urate_set.order_by("-date_drawn").all()

        self.assertEqual(urates.count(), urates_count - urates_deleted + 1)
        self.assertIn(Decimal("11.5"), [urate.value for urate in urates])

    def test__post_removes_multiple_urates(self):
        """Test that post() removes 3 existing Urates for the Ppx."""
        # Create fake data with data for 3 urates to be deleted
        data = ppx_data_factory(ppx=self.ppx, urates=[])
        exi_i = 0
        for _ in self.ppx.urate_set.all():
            data.update({f"urate-{exi_i}-DELETE": "on"})
            exi_i += 1

        # Post the data
        response = self.client.post(reverse("ppxs:update", kwargs={"pk": self.ppx.pk}), data)
        tests_print_response_form_errors(response)
        self.assertEqual(response.status_code, 302)

        # Test that the urates were deleted
        self.assertEqual(self.ppx.urate_set.count(), 0)

    def test__post_removes_multiple_but_not_all_urates(self):
        """Test that post() removes 3 existing Urates for the Ppx."""
        # Create fake data with data for 3 urates to be deleted and a new one to be added
        data = ppx_data_factory(ppx=self.ppx, urates=[Decimal("18.9")])
        exi_i = 0
        for _ in self.ppx.urate_set.all():
            data.update({f"urate-{exi_i}-DELETE": "on"})
            exi_i += 1

        # Post the data
        response = self.client.post(reverse("ppxs:update", kwargs={"pk": self.ppx.pk}), data)
        tests_print_response_form_errors(response)
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
                "urate-0-date_drawn": "",
            }
        )
        if data.get("urate-0-DELETE"):
            data.pop("urate-0-DELETE")

        # Test that a partially filled out Urate form returns a 200 status code
        response = self.client.post(reverse("ppxs:update", kwargs={"pk": self.ppx.pk}), data)
        tests_print_response_form_errors(response)
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
        data = ppx_data_factory(ppx=self.ppx, urates=[])

        # Set GoutDetail fields as attrs on the test to test against later
        data.update(
            {
                "on_ult": not self.goutdetail.on_ult,
                "flaring": not self.goutdetail.flaring,
                "hyperuricemic": not self.goutdetail.hyperuricemic,
            }
        )

        # POST the data
        response = self.client.post(reverse("ppxs:update", kwargs={"pk": self.ppx.pk}), data)
        tests_print_response_form_errors(response)
        self.assertEqual(response.status_code, 302)

        # Test that the GoutDetail object attrs are correct
        goutdetail = GoutDetail.objects.order_by("created").last()
        self.assertEqual(goutdetail.on_ult, data["on_ult"])
        self.assertEqual(goutdetail.flaring, data["flaring"])
        self.assertEqual(goutdetail.hyperuricemic, data["hyperuricemic"])
