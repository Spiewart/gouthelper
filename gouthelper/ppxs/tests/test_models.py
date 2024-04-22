from datetime import timedelta  # type: ignore
from decimal import Decimal  # type: ignore

import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...labs.models import Urate
from ...labs.tests.factories import UrateFactory
from ...medhistorys.lists import PPX_MEDHISTORYS
from ..models import Ppx
from .factories import create_ppx

pytestmark = pytest.mark.django_db


class TestPpx(TestCase):
    def setUp(self):
        self.ppx = create_ppx(labs=[])
        # Create a few Urates
        self.latest_urate = UrateFactory(value=Decimal("4.5"), date_drawn=timezone.now() - timedelta(days=7))
        self.urates = [
            self.latest_urate,
            UrateFactory(value=Decimal("4.9"), date_drawn=timezone.now() - timedelta(days=140)),
            UrateFactory(value=Decimal("3.4"), date_drawn=timezone.now() - timedelta(days=280)),
            UrateFactory(date_drawn=timezone.now() - timedelta(days=420)),
            UrateFactory(date_drawn=timezone.now() - timedelta(days=960)),
        ]

    def test__aid_medhistorys(self):
        """Test the aid_medhistorys class method."""
        self.assertEqual(self.ppx.aid_medhistorys(), PPX_MEDHISTORYS)

    def test__aid_labs(self):
        """Test the aid_labs class method."""
        self.assertEqual(self.ppx.aid_labs(), [Urate])
        self.assertTrue(isinstance(self.ppx.aid_labs(), list))

    def test__conditional_indication(self):
        """Test the conditional_indication property."""
        self.assertFalse(self.ppx.conditional_indication)
        self.ppx.indication = self.ppx.Indications.CONDITIONAL
        self.ppx.save()
        del self.ppx.conditional_indication
        self.assertTrue(self.ppx.conditional_indication)

    def test__flaring(self):
        """Test the flaring property."""
        goutdetail = self.ppx.goutdetail
        self.assertEqual(self.ppx.flaring, goutdetail.flaring)

        # Modify the goutdetail and test the property again.
        goutdetail.flaring = not goutdetail.flaring
        goutdetail.save()
        del self.ppx.gout
        del self.ppx.flaring
        self.assertEqual(goutdetail.flaring, self.ppx.flaring)

    def test__get_absolute_url(self):
        """Test the get_absolute_url method."""
        self.assertEqual(self.ppx.get_absolute_url(), f"/ppxs/{self.ppx.pk}/")

    def test__at_goal(self):
        """Test the hyperuricemic property."""
        goutdetail = self.ppx.goutdetail
        self.assertEqual(self.ppx.at_goal, goutdetail.at_goal)

        # Modify the goutdetail and test the property again.
        goutdetail.at_goal = not goutdetail.at_goal
        goutdetail.save()
        del self.ppx.gout
        self.assertEqual(goutdetail.at_goal, self.ppx.at_goal)

    def test__indicated(self):
        """Test the indicated property."""
        self.assertFalse(self.ppx.indicated)
        # Need to delete the cached_property to test the property again.
        del self.ppx.indicated
        self.ppx.indication = self.ppx.Indications.CONDITIONAL
        self.ppx.save()
        self.assertTrue(self.ppx.indicated)
        del self.ppx.indicated
        self.ppx.indication = self.ppx.Indications.INDICATED
        self.ppx.save()
        self.assertTrue(self.ppx.indicated)
        del self.ppx.indicated
        self.ppx.indication = self.ppx.Indications.NOTINDICATED
        self.ppx.save()
        self.assertFalse(self.ppx.indicated)

    def test__last_urate_at_goal(self):
        """Test the last_urate_at_goal property."""
        ppx = Ppx.objects.get(pk=self.ppx.pk)

        self.assertFalse(ppx.at_goal)
        del ppx.at_goal

        for urate in self.urates:
            urate.ppx = ppx
            urate.save()

        ppx.refresh_from_db()

        self.assertTrue(ppx.at_goal)

        self.latest_urate.value = Decimal("15.0")
        self.latest_urate.save()

        del ppx.at_goal
        ppx.refresh_from_db()

        self.assertFalse(ppx.at_goal)

    def test__on_ppx(self):
        """Test the on_ppx property."""
        ppx_val = True if self.ppx.on_ppx else False
        self.assertEqual(self.ppx.on_ppx, ppx_val)

        self.ppx.goutdetail.on_ppx = not ppx_val
        self.ppx.goutdetail.save()

        self.ppx.refresh_from_db()
        del self.ppx.goutdetail
        del self.ppx.gout
        del self.ppx.on_ppx
        self.assertEqual(self.ppx.on_ppx, not ppx_val)

    def test__on_ult(self):
        """Test the on_ult property."""
        ult_val = True if self.ppx.on_ult else False
        self.assertEqual(self.ppx.on_ult, ult_val)

        self.ppx.goutdetail.on_ult = not ult_val
        self.ppx.goutdetail.save()

        self.ppx.refresh_from_db()
        del self.ppx.goutdetail
        del self.ppx.gout
        del self.ppx.on_ult
        self.assertEqual(self.ppx.on_ult, not ult_val)

    def test__recent_urate(self):
        """Test the recent_urate property."""
        self.assertFalse(self.ppx.recent_urate)
        del self.ppx.recent_urate
        delattr(self.ppx, "urates_qs")

        for urate in self.urates:
            urate.ppx = self.ppx
            urate.save()

        self.ppx.refresh_from_db()

        self.assertTrue(self.ppx.recent_urate)

    def test__semi_recent_urate(self):
        """Test the semi_recent_urate property."""
        # Get the ppx from the database to avoid the urates_qs being created by the create_ppx method
        ppx = Ppx.objects.get(pk=self.ppx.pk)

        self.assertFalse(ppx.semi_recent_urate)
        del ppx.semi_recent_urate

        UrateFactory(date_drawn=timezone.now() - timedelta(days=190), ppx=ppx)
        ppx.refresh_from_db()
        self.assertFalse(ppx.semi_recent_urate)

        del ppx.semi_recent_urate
        UrateFactory(date_drawn=timezone.now() - timedelta(days=140), ppx=ppx)
        self.ppx.refresh_from_db()
        self.assertTrue(ppx.semi_recent_urate)

    def test__update_aid(self):
        """Test the update_aid method."""
        self.assertEqual(self.ppx.indication, self.ppx.Indications.NOTINDICATED)

        self.ppx.goutdetail.starting_ult = True
        self.ppx.goutdetail.save()

        self.assertTrue(isinstance(self.ppx.update_aid(), Ppx))
        self.ppx.refresh_from_db()
        self.assertEqual(self.ppx.indication, self.ppx.Indications.INDICATED)

    def test__urates_discrepant(self):
        """Test the urates_discrepant property."""
        # Fetch the Ppx from the database to avoid it coming with a urates_qs
        # which is created by the create_ppx method
        ppx = Ppx.objects.get(pk=self.ppx.pk)
        ppx.goutdetail.at_goal = False
        ppx.goutdetail.save()

        self.assertFalse(ppx.urates_discrepant)

        for urate in self.urates:
            urate.ppx = ppx
            urate.save()

        del ppx.urates_discrepant
        del ppx.goutdetail
        del ppx.gout
        ppx.refresh_from_db()

        self.assertFalse(ppx.urates_discrepant)

        ppx.goutdetail.at_goal = True
        ppx.goutdetail.save()
        ppx.goutdetail.refresh_from_db()

        del ppx.urates_discrepant
        del ppx.goutdetail
        del ppx.gout

        self.assertTrue(ppx.urates_discrepant)

    def test__urates_discrepant_str(self):
        """Test the urates_discrepant_str property."""
        ppx = Ppx.objects.get(pk=self.ppx.pk)

        ppx.goutdetail.at_goal = None
        ppx.goutdetail.save()

        self.assertIsNone(ppx.urates_discrepant_str)

        for urate in self.urates:
            urate.ppx = ppx
            urate.save()

        self.assertEqual(
            ppx.urates_discrepant_str,
            "Clarify hyperuricemic status. At least one uric acid was reported but hyperuricemic was not.",
        )

        ppx.goutdetail.at_goal = True
        ppx.goutdetail.save()

        del ppx.goutdetail
        del ppx.gout
        ppx.refresh_from_db()

        self.assertEqual(
            ppx.urates_discrepant_str,
            "Clarify hyperuricemic status. Last Urate was at goal, but hyperuricemic reported True.",
        )
