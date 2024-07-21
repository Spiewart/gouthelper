from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...akis.choices import Statuses
from ...defaults.models import FlareAidSettings
from ...flares.selectors import flares_user_qs
from ...flares.tests.factories import CustomFlareFactory, create_flare
from ...labs.tests.factories import CreatinineFactory
from ...medhistorys.lists import FLAREAID_MEDHISTORYS
from ...medhistorys.tests.factories import ColchicineinteractionFactory, HeartattackFactory
from ...treatments.choices import ColchicineDoses, FlarePpxChoices, Treatments
from ..models import FlareAid
from .factories import CustomFlareAidFactory, create_flareaid

pytestmark = pytest.mark.django_db


class TestFlareAid(TestCase):
    def setUp(self):
        self.flareaid = create_flareaid()
        self.settings = FlareAidSettings.objects.get(user=None)
        self.user_flareaid = create_flareaid(user=True)
        self.empty_flareaid = create_flareaid(mhs=[], mas=[])
        self.empty_flareaid_mh_kwargs = {mhtype.lower(): None for mhtype in FLAREAID_MEDHISTORYS}

    def test___str__(self):
        self.assertEqual(str(self.flareaid), f"FlareAid: {self.flareaid.created.date()}")
        self.assertEqual(str(self.user_flareaid), f"{str(self.user_flareaid.user)}'s FlareAid")

    def test__aid_dict(self):
        self.assertFalse(self.flareaid.decisionaid)
        self.assertIsInstance(self.flareaid.aid_dict, dict)
        for flare_trt in FlarePpxChoices.values:
            self.assertIn(flare_trt, self.flareaid.aid_dict.keys())
            self.assertIsInstance(self.flareaid.aid_dict[flare_trt], dict)
        self.assertTrue(self.flareaid.decisionaid)

    def test__aid_medhistorys(self):
        self.assertEqual(self.flareaid.aid_medhistorys(), FLAREAID_MEDHISTORYS)

    def test__aid_treatments(self):
        """Test that the aid_treatments class method returns a list of the values
        of the FlarePpxChoices enum."""
        ats = FlareAid.aid_treatments()
        self.assertIsInstance(ats, list)
        self.assertEqual(ats, FlarePpxChoices.values)

    def test__defaulttrtsettings(self):
        self.assertIsInstance(self.flareaid.defaulttrtsettings, FlareAidSettings)
        self.assertEqual(self.flareaid.defaulttrtsettings, FlareAidSettings.objects.get(user=None))

    def test__get_absolute_url(self):
        self.assertEqual(self.flareaid.get_absolute_url(), f"/flareaids/{self.flareaid.id}/")

    def test__options(self):
        self.assertIsInstance(self.empty_flareaid.options, dict)
        for flare_trt in FlarePpxChoices.values:
            self.assertIn(flare_trt, self.empty_flareaid.options.keys())
            self.assertIsInstance(self.empty_flareaid.options[flare_trt], dict)

    def test__recommendation_no_user(self):
        self.assertIsInstance(self.empty_flareaid.recommendation, tuple)
        self.assertEqual(self.empty_flareaid.recommendation[0], self.settings.flaretrt1)
        HeartattackFactory(flareaid=self.empty_flareaid)
        self.empty_flareaid = self.empty_flareaid.update_aid()
        self.assertEqual(self.empty_flareaid.recommendation[0], Treatments.COLCHICINE)
        ColchicineinteractionFactory(flareaid=self.empty_flareaid)
        self.empty_flareaid = self.empty_flareaid.update_aid()
        self.assertEqual(self.empty_flareaid.recommendation[0], Treatments.PREDNISONE)

    def test__update(self):
        self.assertFalse(self.flareaid.decisionaid)
        self.flareaid.update_aid()
        self.flareaid.refresh_from_db()
        self.assertTrue(self.flareaid.decisionaid)

    def test__related_flare(self):
        flareaid = create_flareaid()
        flare = create_flare(flareaid=flareaid)
        self.assertEqual(flareaid.related_flare, flare)

    def test__related_flare_with_user(self):
        user_flareaid = create_flareaid(user=True)
        user_flare = create_flare(user=user_flareaid.user)
        user = flares_user_qs(username=user_flareaid.user.username, flare_pk=user_flare.pk).get()
        flareaid = user.flareaid
        flare = user.flare_qs[0]
        self.assertEqual(flareaid.related_flare, flare)

    def test__get_flare_options_without_aki(self):
        flareaid = create_flareaid(mhs=[], mas=[])
        flare = create_flare(flareaid=flareaid, mhs=[], aki=None)
        self.assertFalse(flare.aki)
        options = flareaid.get_flare_options(flare=flare)
        self.assertEqual(options, flareaid.options)
        self.assertIn(Treatments.NAPROXEN, options.keys())
        self.assertIn(Treatments.COLCHICINE, options.keys())

    def test__get_flare_options_with_aki_ongoing(self):
        flareaid = create_flareaid(mhs=[], mas=[])
        flare = create_flare(flareaid=flareaid, mhs=[], aki={"status": Statuses.ONGOING}, labs=None)
        self.assertTrue(flare.aki)
        options = flareaid.get_flare_options(flare=flare)
        self.assertNotIn(Treatments.NAPROXEN, options.keys())
        self.assertNotIn(Treatments.COLCHICINE, options.keys())

    def test__get_flare_options_with_aki_resolved(self):
        flareaid = create_flareaid(mhs=[], mas=[])
        flare = create_flare(flareaid=flareaid, mhs=[], aki={"status": Statuses.RESOLVED}, labs=None)
        self.assertTrue(flare.aki)
        options = flareaid.get_flare_options(flare=flare)
        self.assertEqual(options, flareaid.options)
        self.assertIn(Treatments.NAPROXEN, options.keys())
        self.assertIn(Treatments.COLCHICINE, options.keys())

    def test__get_flare_options_with_aki_improving_no_creatinines(self):
        flareaid = create_flareaid(mhs=[], mas=[])
        flare = create_flare(flareaid=flareaid, mhs=[], aki={"status": Statuses.IMPROVING}, labs=None)
        self.assertTrue(flare.aki)
        options = flareaid.get_flare_options(flare=flare)
        self.assertNotIn(Treatments.NAPROXEN, options.keys())
        self.assertNotIn(Treatments.COLCHICINE, options.keys())

    def test__get_flare_options_with_aki_improving_not_at_baselinecreatinine(self):
        flareaid = CustomFlareAidFactory(
            baselinecreatinine=Decimal("2.0"),
            **self.empty_flareaid_mh_kwargs,
        ).create_object()
        flare = CustomFlareFactory(
            aki=Statuses.IMPROVING,
            creatinines=[CreatinineFactory(value="3.0", date_drawn=timezone.now() - timedelta(days=4))],
            flareaid=flareaid,
        ).create_object()
        options = flareaid.get_flare_options(flare=flare)
        self.assertNotIn(Treatments.NAPROXEN, options.keys())
        self.assertNotIn(Treatments.COLCHICINE, options.keys())

    def test__get_flare_options_colchicine_dose_adjusted_for_most_recent_creatinine_stage(self) -> None:
        flareaid = CustomFlareAidFactory(
            dateofbirth=timezone.now() - timedelta(days=365 * 50),
            colchicine_allergy=False,
            **self.empty_flareaid_mh_kwargs,
        ).create_object()
        flare = CustomFlareFactory(
            aki=Statuses.IMPROVING,
            creatinines=[
                CreatinineFactory(value="3.0", date_drawn=timezone.now() - timedelta(days=4)),
                CreatinineFactory(value="1.4", date_drawn=timezone.now() - timedelta(days=1)),
            ],
            flareaid=flareaid,
        ).create_object()
        options = flareaid.get_flare_options(flare=flare)
        self.assertIn(Treatments.COLCHICINE, options.keys())
        colchicine_dosing_dict = options[Treatments.COLCHICINE]
        self.assertEqual(colchicine_dosing_dict["dose"], ColchicineDoses.POINTTHREE)
        self.assertEqual(colchicine_dosing_dict["dose2"], ColchicineDoses.POINTSIX)
        self.assertEqual(colchicine_dosing_dict["dose3"], ColchicineDoses.POINTTHREE)

    def test__get_flare_options_colchicine_dose_adjusted_for_most_recent_creatinine_baselinecreatinine(self) -> None:
        flareaid = CustomFlareAidFactory(
            dateofbirth=timezone.now() - timedelta(days=365 * 40),
            baselinecreatinine=Decimal("1.7"),
            colchicine_allergy=False,
            **self.empty_flareaid_mh_kwargs,
        ).create_object()
        flare = CustomFlareFactory(
            aki=Statuses.IMPROVING,
            creatinines=[
                CreatinineFactory(value="3.0", date_drawn=timezone.now() - timedelta(days=4)),
                CreatinineFactory(value="2.0", date_drawn=timezone.now() - timedelta(days=1)),
            ],
            flareaid=flareaid,
        ).create_object()
        options = flareaid.get_flare_options(flare=flare)
        self.assertIn(Treatments.COLCHICINE, options.keys())
        colchicine_dosing_dict = options[Treatments.COLCHICINE]
        self.assertEqual(colchicine_dosing_dict["dose"], ColchicineDoses.POINTTHREE)
        self.assertEqual(colchicine_dosing_dict["dose2"], ColchicineDoses.POINTSIX)
        self.assertEqual(colchicine_dosing_dict["dose3"], ColchicineDoses.POINTTHREE)
