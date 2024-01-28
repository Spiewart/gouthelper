from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils import timezone  # type: ignore

from ...labs.models import Urate
from ...labs.tests.factories import UrateFactory
from ...medhistorydetails.models import GoutDetail
from ...medhistorydetails.tests.factories import GoutDetailFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.models import Gout
from ...medhistorys.tests.factories import GoutFactory
from ...utils.helpers.test_helpers import tests_print_response_form_errors
from ..models import Ppx
from ..views import PpxCreate, PpxUpdate
from .factories import PpxFactory

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
        ppx_data = {
            f"{MedHistoryTypes.GOUT}-value": True,
            "on_ult": False,
            "starting_ult": True,
            "on_ppx": False,
            "labs-TOTAL_FORMS": 0,
            "labs-INITIAL_FORMS": 0,
        }
        response = self.client.post(reverse("ppxs:create"), ppx_data)
        # NOTE: Will print errors for all forms in the context_data.
        tests_print_response_form_errors(response)
        self.assertEqual(response.status_code, 302)

        # Assert that the number of Ppx, Gout, and GoutDetail objects has increased by 1
        self.assertEqual(Ppx.objects.count(), ppx_count + 1)
        self.assertEqual(Gout.objects.count(), gout_count + 1)
        self.assertEqual(GoutDetail.objects.count(), goutdetail_count + 1)

        # Test that the created Gout and GoutDetail objects have the correct fields
        gout = Gout.objects.order_by("created").last()
        goutdetail = GoutDetail.objects.order_by("created").last()
        # Assert that the GoutDetail object attrs are correct
        self.assertEqual(goutdetail.medhistory, gout)
        self.assertFalse(goutdetail.on_ult)
        self.assertIsNone(goutdetail.flaring)
        self.assertIsNone(goutdetail.hyperuricemic)

    def test__post_sets_goutdetail_fields(self):
        """Test that post() correctly sets the goutdetail fields."""
        ppx_data = {
            f"{MedHistoryTypes.GOUT}-value": True,
            "flaring": True,
            "hyperuricemic": True,
            "on_ppx": False,
            "starting_ult": True,
            "on_ult": True,
            "labs-TOTAL_FORMS": 0,
            "labs-INITIAL_FORMS": 0,
        }
        response = self.client.post(reverse("ppxs:create"), ppx_data)
        # NOTE: Will print errors for all forms in the context_data.
        tests_print_response_form_errors(response)
        self.assertEqual(response.status_code, 302)
        goutdetail = GoutDetail.objects.order_by("created").last()
        # Assert that the GoutDetail object attrs are correct
        self.assertTrue(goutdetail.on_ult)
        self.assertTrue(goutdetail.flaring)
        self.assertTrue(goutdetail.hyperuricemic)

    def test__post_creates_urate(self):
        """Test that post() method creates a single Urate object"""
        ppx_data = {
            f"{MedHistoryTypes.GOUT}-value": True,
            "on_ppx": False,
            "starting_ult": True,
            "on_ult": False,
            "labs-0-value": Decimal("9.1"),
            "labs-0-date_drawn": timezone.now() - timedelta(days=18),
            "labs-TOTAL_FORMS": 1,
            "labs-INITIAL_FORMS": 0,
        }
        response = self.client.post(reverse("ppxs:create"), ppx_data)
        # NOTE: Will print errors for all forms in the context_data.
        tests_print_response_form_errors(response)
        urates = Urate.objects.all()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urates.count(), 1)
        urate = urates.get()
        self.assertEqual(urate.value, Decimal("9.1"))
        self.assertEqual(urate.date_drawn, ppx_data["labs-0-date_drawn"])
        # Test that the urate has a relationship with the ppx
        ppx = Ppx.objects.get()
        self.assertEqual(ppx.labs.get(), urate)

    def test__post_creates_multiple_urates(self):
        """Test that post() method creates several Urate objects, with a User
        error creating an extra blank form that's not filled out."""
        ppx_data = {
            f"{MedHistoryTypes.GOUT}-value": True,
            "on_ppx": False,
            "starting_ult": True,
            "on_ult": False,
            "labs-0-value": Decimal("9.1"),
            "labs-0-date_drawn": timezone.now() - timedelta(days=18),
            "labs-1-value": "",
            "labs-2-value": Decimal("10.1"),
            "labs-2-date_drawn": timezone.now() - timedelta(days=180),
            "labs-TOTAL_FORMS": 3,
            "labs-INITIAL_FORMS": 0,
        }
        response = self.client.post(reverse("ppxs:create"), ppx_data)
        # NOTE: Will print errors for all forms in the context_data.
        tests_print_response_form_errors(response)
        urates = Urate.objects.order_by("-date_drawn").all()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urates.count(), 2)
        urate1 = urates[0]
        urate2 = urates[1]
        self.assertEqual(urate1.value, Decimal("9.1"))
        self.assertEqual(urate1.date_drawn, ppx_data["labs-0-date_drawn"])
        # Test that the urate has a relationship with the ppx
        ppx = Ppx.objects.get()
        self.assertIn(urate1, ppx.labs.all())
        self.assertEqual(urate2.value, Decimal("10.1"))
        self.assertEqual(urate2.date_drawn, ppx_data["labs-2-date_drawn"])
        # Test that the urate has a relationship with the ppx
        self.assertIn(urate2, ppx.labs.all())


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
        self.ppx = PpxFactory(
            medhistorys=[self.gout],
            goutdetail=self.goutdetail,
            labs=[self.urate1, self.urate2, self.urate3],
        )

    def test__post_updates_ppx(self):
        """Tests that a POST request updates a Ppx object."""
        ppx_data = {
            f"{MedHistoryTypes.GOUT}-value": True,
            "on_ppx": False,
            "starting_ult": True,
            "on_ult": self.goutdetail.on_ult if self.goutdetail.on_ult else False,
            "flaring": self.goutdetail.flaring if self.goutdetail.flaring else False,
            "hyperuricemic": self.goutdetail.hyperuricemic if self.goutdetail.hyperuricemic else False,
            "labs-TOTAL_FORMS": 3,
            "labs-INITIAL_FORMS": 3,
            "labs-0-value": self.urate1.value,
            "labs-0-date_drawn": self.urate1.date_drawn,
            "labs-0-id": self.urate1.pk,
            "labs-1-value": self.urate2.value,
            "labs-1-date_drawn": self.urate2.date_drawn,
            "labs-1-id": self.urate2.pk,
            "labs-2-value": self.urate3.value,
            "labs-2-date_drawn": self.urate3.date_drawn,
            "labs-2-id": self.urate3.pk,
        }
        response = self.client.post(reverse("ppxs:update", kwargs={"pk": self.ppx.pk}), ppx_data)
        # NOTE: Will print errors for all forms in the context_data.
        tests_print_response_form_errors(response)
        self.assertEqual(response.status_code, 302)

    def test__post_adds_urate(self):
        """Test that post() adds a Urate to the 3 that already exist for the Ppx."""
        ppx_data = {
            f"{MedHistoryTypes.GOUT}-value": True,
            "on_ppx": False,
            "starting_ult": True,
            "on_ult": self.goutdetail.on_ult if self.goutdetail.on_ult else False,
            "flaring": self.goutdetail.flaring if self.goutdetail.flaring else False,
            "hyperuricemic": self.goutdetail.hyperuricemic if self.goutdetail.hyperuricemic else False,
            "labs-TOTAL_FORMS": 5,
            "labs-INITIAL_FORMS": 3,
            "labs-0-value": self.urate1.value,
            "labs-0-date_drawn": self.urate1.date_drawn,
            "labs-0-id": self.urate1.pk,
            "labs-1-value": self.urate2.value,
            "labs-1-date_drawn": self.urate2.date_drawn,
            "labs-1-id": self.urate2.pk,
            "labs-2-value": self.urate3.value,
            "labs-2-date_drawn": self.urate3.date_drawn,
            "labs-2-id": self.urate3.pk,
            "labs-3-value": "",
            "labs-3-date_drawn": "",
            "labs-3-id": "",
            "labs-4-value": Decimal("11.5"),
            "labs-4-date_drawn": timezone.now() - timedelta(days=729),
        }
        response = self.client.post(reverse("ppxs:update", kwargs={"pk": self.ppx.pk}), ppx_data)
        # NOTE: Will print errors for all forms in the context_data.
        tests_print_response_form_errors(response)
        self.assertEqual(response.status_code, 302)
        ppx = Ppx.objects.get()
        urates = ppx.labs.order_by("-date_drawn").all()
        self.assertEqual(urates.count(), 4)
        self.assertEqual(urates.last().value, ppx_data["labs-4-value"])
        self.assertEqual(urates.last().date_drawn, ppx_data["labs-4-date_drawn"])

    def test__post_removes_multiple_urates(self):
        """Test that post() removes 3 existing Urates for the Ppx."""
        ppx_data = {
            f"{MedHistoryTypes.GOUT}-value": True,
            "on_ppx": False,
            "starting_ult": True,
            "on_ult": self.goutdetail.on_ult if self.goutdetail.on_ult else False,
            "flaring": self.goutdetail.flaring if self.goutdetail.flaring else False,
            "hyperuricemic": self.goutdetail.hyperuricemic if self.goutdetail.hyperuricemic else False,
            "labs-TOTAL_FORMS": 4,
            "labs-INITIAL_FORMS": 3,
            "labs-0-value": self.urate1.value,
            "labs-0-date_drawn": self.urate1.date_drawn,
            "labs-0-id": self.urate1.pk,
            "labs-0-DELETE": True,
            "labs-1-value": self.urate2.value,
            "labs-1-date_drawn": self.urate2.date_drawn,
            "labs-1-id": self.urate2.pk,
            "labs-1-DELETE": True,
            "labs-2-value": self.urate3.value,
            "labs-2-date_drawn": self.urate3.date_drawn,
            "labs-2-id": self.urate3.pk,
            "labs-2-DELETE": True,
            "labs-3-value": "",
            "labs-3-date_drawn": "",
            "labs-3-id": "",
        }
        response = self.client.post(reverse("ppxs:update", kwargs={"pk": self.ppx.pk}), ppx_data)
        # NOTE: Will print errors for all forms in the context_data.
        tests_print_response_form_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.ppx.labs.count(), 0)

    def test__post_removes_multiple_but_not_all_urates(self):
        """Test that post() removes 3 existing Urates for the Ppx."""
        # create 4th urate and add to ppx
        urate4 = UrateFactory(date_drawn=timezone.now() - timedelta(days=540), value=Decimal("18.9"))
        self.ppx.add_labs([urate4])
        ppx_data = {
            f"{MedHistoryTypes.GOUT}-value": True,
            "on_ppx": False,
            "starting_ult": True,
            "on_ult": self.goutdetail.on_ult if self.goutdetail.on_ult else False,
            "flaring": self.goutdetail.flaring if self.goutdetail.flaring else False,
            "hyperuricemic": self.goutdetail.hyperuricemic if self.goutdetail.hyperuricemic else False,
            "labs-TOTAL_FORMS": 4,
            "labs-INITIAL_FORMS": 4,
            "labs-0-value": self.urate1.value,
            "labs-0-date_drawn": self.urate1.date_drawn,
            "labs-0-id": self.urate1.pk,
            "labs-0-DELETE": True,
            "labs-1-value": self.urate2.value,
            "labs-1-date_drawn": self.urate2.date_drawn,
            "labs-1-id": self.urate2.pk,
            "labs-1-DELETE": True,
            "labs-2-value": self.urate3.value,
            "labs-2-date_drawn": self.urate3.date_drawn,
            "labs-2-id": self.urate3.pk,
            "labs-3-value": urate4.value,
            "labs-3-date_drawn": urate4.date_drawn,
            "labs-3-id": urate4.pk,
            "labs-3-DELETE": True,
        }
        response = self.client.post(reverse("ppxs:update", kwargs={"pk": self.ppx.pk}), ppx_data)
        # NOTE: Will print errors for all forms in the context_data.
        tests_print_response_form_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.ppx.labs.count(), 1)
        self.assertIn(self.urate3, self.ppx.labs.all())

    def test__post_partial_urate_form_raises_ValidationError(self):
        """Test that a partially filled out Urate form raises a ValidationError."""
        ppx_data = {
            f"{MedHistoryTypes.GOUT}-value": True,
            "on_ppx": False,
            "starting_ult": True,
            "on_ult": self.goutdetail.on_ult if self.goutdetail.on_ult else False,
            "flaring": self.goutdetail.flaring if self.goutdetail.flaring else False,
            "hyperuricemic": self.goutdetail.hyperuricemic if self.goutdetail.hyperuricemic else False,
            "labs-TOTAL_FORMS": 5,
            "labs-INITIAL_FORMS": 3,
            "labs-0-value": self.urate1.value,
            "labs-0-date_drawn": self.urate1.date_drawn,
            "labs-0-id": self.urate1.pk,
            "labs-1-value": self.urate2.value,
            "labs-1-date_drawn": self.urate2.date_drawn,
            "labs-1-id": self.urate2.pk,
            "labs-2-value": self.urate3.value,
            "labs-2-date_drawn": self.urate3.date_drawn,
            "labs-2-id": self.urate3.pk,
            "labs-3-value": Decimal("13.5"),
            "labs-3-date_drawn": "",
            "labs-3-id": "",
            "labs-4-value": Decimal("11.5"),
            "labs-4-date_drawn": timezone.now() - timedelta(days=729),
        }
        tests_print_response_form_errors(
            self.client.post(reverse("ppxs:update", kwargs={"pk": self.ppx.pk}), ppx_data)
        )
        # Test that a partially filled out Urate form returns a 200 status code
        response = self.client.post(reverse("ppxs:update", kwargs={"pk": self.ppx.pk}), ppx_data)
        self.assertEqual(response.status_code, 200)
        # Test that the response contains the erroneous UrateForm with errors
        self.assertTrue("lab_formset" in response.context_data)
        self.assertTrue(response.context_data["lab_formset"].errors)
        # Test that the response has the correct error message
        error_list = response.context_data["lab_formset"].errors
        self.assertTrue(any(error_list))
        for error_dict in error_list:
            if error_dict:
                self.assertIn("date_drawn", error_dict)
                self.assertEqual(error_dict["date_drawn"], ["We need to know when this was drawn."])

    def test__post_updates_goutdetail(self):
        """Tests that a POST request updates a Ppx object's related GoutDetail."""
        # Set GoutDetail fields as attrs on the test to test against later
        on_ult = self.goutdetail.on_ult.copy() if self.goutdetail.on_ult else False
        flaring = self.goutdetail.flaring.copy() if self.goutdetail.flaring else False
        hyperuricemic = self.goutdetail.hyperuricemic.copy() if self.goutdetail.hyperuricemic else False
        ppx_data = {
            f"{MedHistoryTypes.GOUT}-value": True,
            "on_ppx": False,
            "starting_ult": True,
            "on_ult": True if not self.goutdetail.on_ult else False,
            # Need to set these to empty strings to get the form to validate
            "flaring": "" if not self.goutdetail.flaring else True,
            "hyperuricemic": "" if not self.goutdetail.hyperuricemic else True,
            "labs-TOTAL_FORMS": 3,
            "labs-INITIAL_FORMS": 3,
            "labs-0-value": self.urate1.value,
            "labs-0-date_drawn": self.urate1.date_drawn,
            "labs-0-id": self.urate1.pk,
            "labs-1-value": self.urate2.value,
            "labs-1-date_drawn": self.urate2.date_drawn,
            "labs-1-id": self.urate2.pk,
            "labs-2-value": self.urate3.value,
            "labs-2-date_drawn": self.urate3.date_drawn,
            "labs-2-id": self.urate3.pk,
        }
        response = self.client.post(reverse("ppxs:update", kwargs={"pk": self.ppx.pk}), ppx_data)
        # NOTE: Will print errors for all forms in the context_data.
        tests_print_response_form_errors(response)
        self.assertEqual(response.status_code, 302)
        # Test that the GoutDetail object attrs are correct
        goutdetail = GoutDetail.objects.order_by("created").last()
        self.assertNotEqual(goutdetail.on_ult, on_ult)
        self.assertNotEqual(goutdetail.flaring, flaring)
        self.assertNotEqual(goutdetail.hyperuricemic, hyperuricemic)
