from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...goalurates.choices import GoalUrates
from ...labs.tests.factories import UrateFactory
from ...ppxs.models import Ppx
from ...ppxs.tests.factories import create_ppx
from ...ults.choices import Indications
from ..selectors import ppx_userless_qs
from ..services import PpxDecisionAid

pytestmark = pytest.mark.django_db


class TestPpxDecisionAidMethods(TestCase):
    """Suite of tests to test the various methods of the class method PpxDecisionAid."""

    def add_urates_to_ppx(self):
        for urate in self.urates:
            urate.ppx = self.ppx
            urate.save()

    def setUp(self):
        # Create a Ppx object without User and set the on_ult attr of its goutdetail to False
        self.ppx = create_ppx()
        self.ppx.goutdetail.on_ult = False
        self.ppx.goutdetail.save()
        # Create some userless Urate objects
        self.urate1 = UrateFactory(date_drawn=timezone.now())
        self.urate2 = UrateFactory(date_drawn=timezone.now() - timedelta(days=180))
        self.urate3 = UrateFactory(date_drawn=timezone.now() - timedelta(days=365))
        self.urates = [self.urate1, self.urate2, self.urate3]

    def test__init__assigns_attrs(self):
        """This also indirectly tests _assign_medhistorys() via the self.gout"""
        # Test that __init__ assigns None attrs
        aid = PpxDecisionAid(ppx_userless_qs(pk=self.ppx.pk))
        self.assertEqual(aid.ppx, self.ppx)
        self.assertEqual(aid.gout, self.ppx.gout)
        self.assertEqual(aid.goutdetail, self.ppx.goutdetail)
        self.assertEqual(aid.medhistorys, [self.ppx.gout])
        if aid.urates:
            for urate in aid.urates:
                self.assertTrue(hasattr(urate, "date"))
                self.assertIn(urate, self.ppx.urate_set.all())
        else:
            self.assertEqual(aid.urates, [])

        self.add_urates_to_ppx()

        # Test that related models correctly assigned
        aid = PpxDecisionAid(ppx_userless_qs(pk=self.ppx.pk))
        self.assertEqual(aid.ppx, self.ppx)
        self.assertEqual(aid.gout, self.ppx.gout)
        self.assertEqual(aid.goutdetail, self.ppx.goutdetail)
        self.assertEqual(aid.medhistorys, [self.ppx.gout])
        self.assertIn(self.urate1, aid.urates)
        self.assertIn(self.urate2, aid.urates)
        self.assertIn(self.urate3, aid.urates)

        # Check that each Urate has a date attr
        for urate in aid.urates:
            self.assertTrue(hasattr(urate, "date"))

    def test__check_for_gout_and_detail(self):
        """Test that _check_for_gout_and_detail raises TypeError if
        the ppx does not have a Gout object or a GoutDetail object."""
        self.ppx.goutdetail.delete()
        with self.assertRaises(TypeError) as error:
            PpxDecisionAid(ppx_userless_qs(pk=self.ppx.pk))
        self.assertEqual(str(error.exception), "No GoutDetail associated with Ppx.gout.")

        self.ppx.gout.delete()
        with self.assertRaises(TypeError) as error:
            PpxDecisionAid(ppx_userless_qs(pk=self.ppx.pk))
        self.assertEqual(str(error.exception), "No Gout MedHistory in Ppx.medhistorys.")

    def test__goal_urate(self):
        """Test that the goal_urate property returns the correct value."""
        aid = PpxDecisionAid(ppx_userless_qs(pk=self.ppx.pk))
        self.assertEqual(aid.goalurate, GoalUrates.SIX)

    def test__flaring(self):
        """Test that all the flaring property outcomes return the correct value."""
        aid = PpxDecisionAid(ppx_userless_qs(pk=self.ppx.pk))
        self.assertEqual(aid.flaring, self.ppx.flaring)

        self.ppx.goutdetail.flaring = True
        self.ppx.goutdetail.save()
        del self.ppx.flaring  # Delete the cached property

        aid = PpxDecisionAid(ppx_userless_qs(pk=self.ppx.pk))
        self.assertTrue(aid.flaring)

    def test__hyperuricemic(self):
        """Test that all the hyperuricemic property outcomes return the correct value."""
        aid = PpxDecisionAid(ppx_userless_qs(pk=self.ppx.pk))
        self.ppx.urate_set.all().delete()
        self.assertEqual(aid.hyperuricemic, self.ppx.hyperuricemic)

        self.ppx.goutdetail.hyperuricemic = True
        self.ppx.goutdetail.save()
        del self.ppx.gout
        del self.ppx.goutdetail

        aid = PpxDecisionAid(ppx_userless_qs(pk=self.ppx.pk))
        self.assertTrue(aid.hyperuricemic)

    def test__init_not_at_goal(self):
        """Test that the constructor sets the GoutDetail object's
        at_goal attr to False when the Urates indicate that the patient
        is hyperuricemic, meaning the most recent Urate was above the goal."""
        self.ppx.goutdetail.hyperuricemic = None
        self.ppx.goutdetail.save()
        self.assertIsNone(self.ppx.goutdetail.hyperuricemic)

        UrateFactory(date_drawn=timezone.now(), value=Decimal("8.9"), ppx=self.ppx)
        UrateFactory(date_drawn=timezone.now() - timedelta(days=180), value=Decimal("9.1"), ppx=self.ppx)

        aid = PpxDecisionAid(ppx_userless_qs(pk=self.ppx.pk))

        self.assertFalse(aid.at_goal)

    def test__init_at_goal_but_not_six_months(self):
        """Test that the constructor sets the GoutDetail object's
        at_goal attr to True when the Urates indicate that the patient
        is hyperuricemic, meaning the most recent Urate was above the goal."""
        self.ppx.goutdetail.hyperuricemic = None
        self.ppx.goutdetail.save()
        self.assertIsNone(self.ppx.goutdetail.hyperuricemic)
        self.ppx.urate_set.all().delete()

        UrateFactory(date_drawn=timezone.now(), value=Decimal("5.9"), ppx=self.ppx)
        UrateFactory(date_drawn=timezone.now() - timedelta(days=181), value=Decimal("5.9"), ppx=self.ppx)

        self.ppx.refresh_from_db()
        aid = PpxDecisionAid(ppx_userless_qs(pk=self.ppx.pk))
        self.assertTrue(aid.at_goal)

    def test__init_at_goal_changes_hyperuricemic_False(self):
        """Test that the constructor sets the GoutDetail object's
        hyperuricemic field to False when the Urates indicate that the patient
        is hyperuricemic but then at goal."""
        # Set the Ppx's GoutDetail object's hyperuricemic attr to True
        self.ppx.goutdetail.hyperuricemic = True
        self.ppx.goutdetail.save()
        self.ppx.urate_set.all().delete()

        # Assert that the Ppx's GoutDetail object's hyperuricemic attr is True
        self.assertTrue(self.ppx.goutdetail.hyperuricemic)
        # Create 2 Urate objects that are at goal six months apart
        UrateFactory(date_drawn=timezone.now(), value=Decimal("5.9"), ppx=self.ppx)
        UrateFactory(date_drawn=timezone.now() - timedelta(days=181), value=Decimal("5.9"), ppx=self.ppx)

        self.ppx.refresh_from_db()
        aid = PpxDecisionAid(ppx_userless_qs(pk=self.ppx.pk))
        self.assertFalse(aid.goutdetail.hyperuricemic)
        ppx = Ppx.objects.get()
        self.assertFalse(ppx.goutdetail.hyperuricemic)

    def test__init_not_at_goal_changes_hyperuricemic_True(self):
        """Test that the constructor method sets the GoutDetail object's
        hyperuricemic field to True when the patient is at goal but the
        Urates indicate he or she is hyperuricemic."""
        # Set the Ppx's GoutDetail object's hyperuricemic attr to False
        self.ppx.goutdetail.hyperuricemic = False
        self.ppx.goutdetail.save()

        # Assert that the Ppx's GoutDetail object's hyperuricemic attr is False
        self.assertFalse(self.ppx.goutdetail.hyperuricemic)

        # Create a Urate object that is hyperuricemic
        UrateFactory(date_drawn=timezone.now(), value=Decimal("9.1"), ppx=self.ppx)

        aid = PpxDecisionAid(ppx_userless_qs(pk=self.ppx.pk))
        self.assertTrue(aid.goutdetail.hyperuricemic)

        ppx = Ppx.objects.get(pk=self.ppx.pk)

        self.assertTrue(ppx.goutdetail.hyperuricemic)

    def test__get_indication_not_on_ult(self):
        """Test that _get_indication returns NOTINDICATED when the patient is
        not on ULT."""
        self.ppx.starting_ult = False
        self.ppx.save()
        self.ppx.goutdetail.on_ult = False
        self.ppx.goutdetail.save()
        # Assert that the Ppx's indication attr is None
        aid = PpxDecisionAid(ppx_userless_qs(pk=self.ppx.pk))
        self.assertEqual(aid._get_indication(), Indications.NOTINDICATED)

    def test__get_indication_starting_ult(self):
        """Test that _get_indication returns INDICATED when the Ppx's starting_ult
        field is True."""
        # Assert that the Ppx's indication attr is None
        self.ppx.starting_ult = True
        self.ppx.save()
        aid = PpxDecisionAid(ppx_userless_qs(pk=self.ppx.pk))
        self.assertEqual(aid._get_indication(), Indications.INDICATED)

    def test__get_indication_on_not_starting_ult_no_hyperuricemic_or_flaring(self):
        """Test that get_indication returns NOTINDICATED when the patient is on but not
        starting ULT and is not hyperuricemic or flaring."""
        self.ppx.starting_ult = False
        self.ppx.save()
        self.ppx.urate_set.all().delete()

        self.ppx.goutdetail.hyperuricemic = False
        self.ppx.goutdetail.flaring = False
        self.ppx.goutdetail.on_ult = True
        self.ppx.goutdetail.save()
        aid = PpxDecisionAid(ppx_userless_qs(pk=self.ppx.pk))
        self.assertEqual(aid._get_indication(), Indications.NOTINDICATED)

    def test__get_indication_on_not_starting_ult_hyperuricemic_not_flaring(self):
        """Test taht get_indication returns CONDITIONAL when the patient is on but not
        starting ULT and is hyperuricemic but not flaring."""
        self.ppx.starting_ult = False
        self.ppx.save()

        self.ppx.goutdetail.hyperuricemic = True
        self.ppx.goutdetail.flaring = False
        self.ppx.goutdetail.on_ult = True
        self.ppx.goutdetail.save()

        aid = PpxDecisionAid(ppx_userless_qs(pk=self.ppx.pk))
        self.assertEqual(aid._get_indication(), Indications.CONDITIONAL)

    def test__get_indication_on_not_starting_ult_flaring_not_hyperuricemic(self):
        """Test that get_indication returns CONDITIONAL when the patient is on but not
        starting ULT and is flaring but not hyperuricemic."""
        self.ppx.starting_ult = False
        self.ppx.save()

        self.ppx.goutdetail.hyperuricemic = False
        self.ppx.goutdetail.flaring = True
        self.ppx.goutdetail.on_ult = True
        self.ppx.goutdetail.save()

        aid = PpxDecisionAid(ppx_userless_qs(pk=self.ppx.pk))
        self.assertEqual(aid._get_indication(), Indications.CONDITIONAL)

    def test__get_indication_on_not_starting_ult_flaring_and_hyperuricemic(self):
        """Test that get_indication returns CONDITIONAL when the patient is on but not
        starting ULT and is flaring and hyperuricemic."""
        self.ppx.starting_ult = False
        self.ppx.save()

        self.ppx.goutdetail.hyperuricemic = True
        self.ppx.goutdetail.flaring = True
        self.ppx.goutdetail.on_ult = True
        self.ppx.goutdetail.save()

        aid = PpxDecisionAid(ppx_userless_qs(pk=self.ppx.pk))
        self.assertEqual(aid._get_indication(), Indications.CONDITIONAL)

    def test__get_indication_on_not_starting_ult_high_urate_hyperuricemic_flaring_none(self):
        """Test that get_indication returns CONDITIONAL when the patient is on but not
        starting ULT and the most recent Urate is high, the hyperuricemic is None, and
        flaring is None."""
        self.ppx.starting_ult = False
        self.ppx.save()

        self.ppx.goutdetail.hyperuricemic = None
        self.ppx.goutdetail.flaring = None
        self.ppx.goutdetail.on_ult = True
        self.ppx.goutdetail.save()

        UrateFactory(date_drawn=timezone.now(), value=Decimal("9.1"), ppx=self.ppx)

        aid = PpxDecisionAid(ppx_userless_qs(pk=self.ppx.pk))
        self.assertEqual(aid._get_indication(), Indications.CONDITIONAL)

    def test__update(self):
        """Test that the update method correctly updates the Ppx object's
        indication field."""
        # Assert that the Ppx's Indication attr is NOTINDICATED
        self.assertEqual(self.ppx.indication, Indications.NOTINDICATED)

        self.ppx.starting_ult = False
        self.ppx.save()
        self.ppx.goutdetail.on_ult = True
        self.ppx.goutdetail.flaring = True
        self.ppx.goutdetail.save()

        # Create a Urate object that is hyperuricemic
        UrateFactory(date_drawn=timezone.now(), value=Decimal("9.1"), ppx=self.ppx)

        aid = PpxDecisionAid(ppx_userless_qs(pk=self.ppx.pk))
        aid._update()  # pylint: disable=protected-access

        self.assertEqual(aid.ppx.indication, Indications.CONDITIONAL)
        self.ppx.refresh_from_db()
        self.assertEqual(self.ppx.indication, Indications.CONDITIONAL)
