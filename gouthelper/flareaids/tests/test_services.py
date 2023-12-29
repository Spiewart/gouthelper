import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.db.models import QuerySet
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...defaults.models import DefaultFlareTrtSettings, DefaultMedHistory, DefaultTrt
from ...defaults.tests.factories import (
    DefaultColchicineFlareFactory,
    DefaultFlareTrtSettingsFactory,
    DefaultMedHistoryFactory,
)
from ...genders.tests.factories import GenderFactory
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.choices import Stages
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.models import MedHistory
from ...medhistorys.tests.factories import (
    AnginaFactory,
    AnticoagulationFactory,
    BleedFactory,
    ChfFactory,
    CkdFactory,
    ColchicineinteractionFactory,
    DiabetesFactory,
    GastricbypassFactory,
    HeartattackFactory,
)
from ...treatments.choices import FlarePpxChoices, NsaidChoices, Treatments
from ...users.choices import Roles
from ...users.tests.factories import UserFactory
from ...utils.helpers.aid_helpers import aids_dict_to_json
from ..selectors import flareaid_user_qs, flareaid_userless_qs
from ..services import FlareAidDecisionAid
from .factories import FlareAidFactory, FlareAidUserFactory

pytestmark = pytest.mark.django_db


class TestFlareAidMethods(TestCase):
    def setUp(self):
        # Set up userless FlareAidDecisionAid
        self.userless_angina = AnginaFactory()
        self.userless_anticoagulation = AnticoagulationFactory()
        self.userless_bleed = BleedFactory()
        self.userless_chf = ChfFactory()
        self.userless_colchicineinteraction = ColchicineinteractionFactory()
        self.userless_diabetes = DiabetesFactory()
        self.userless_gastricbypass = GastricbypassFactory()
        self.userless_heartattack = HeartattackFactory()
        self.userless_allopurinolallergy = MedAllergyFactory(treatment=Treatments.ALLOPURINOL)
        self.userless_ckd = CkdFactory()
        self.userless_gender = GenderFactory()
        self.userless_ckddetail = CkdDetailFactory(medhistory=self.userless_ckd, stage=Stages.FOUR)
        self.userless_flareaid = FlareAidFactory(gender=self.userless_gender)
        for medhistory in MedHistory.objects.filter().all():
            self.userless_flareaid.medhistorys.add(medhistory)
        self.userless_flareaid.medallergys.add(self.userless_allopurinolallergy)
        self.userless_qs = flareaid_userless_qs(pk=self.userless_flareaid.pk)
        self.userless_decisionaid = FlareAidDecisionAid(qs=self.userless_qs)
        # Set up user FlareAidDecisionAid
        self.user = UserFactory(role=Roles.PSEUDOPATIENT)
        self.user.dateofbirth = DateOfBirthFactory(user=self.user)
        self.user.gender = GenderFactory(user=self.user)
        self.user_angina = AnginaFactory(user=self.user)
        self.user_anticoagulation = AnticoagulationFactory(user=self.user)
        self.user_bleed = BleedFactory(user=self.user)
        self.user_chf = ChfFactory(user=self.user)
        self.user_colchicineinteraction = ColchicineinteractionFactory(user=self.user)
        self.user_diabetes = DiabetesFactory(user=self.user)
        self.user_gastricbypass = GastricbypassFactory(user=self.user)
        self.user_heartattack = HeartattackFactory(user=self.user)
        self.user_allopurinolallergy = MedAllergyFactory(user=self.user, treatment=Treatments.ALLOPURINOL)
        self.user_ckd = CkdFactory(user=self.user)
        self.user_ckddetail = CkdDetailFactory(medhistory=self.user_ckd, stage=Stages.FOUR)
        self.user_flareaid = FlareAidUserFactory(user=self.user)
        self.user_qs = flareaid_user_qs(username=self.user.username)
        self.user_decisionaid = FlareAidDecisionAid(qs=self.user_qs)

    def test__init_without_user(self):
        userless_colchicine_allergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        self.userless_flareaid.medallergys.add(userless_colchicine_allergy)
        with CaptureQueriesContext(connection) as context:
            decisionaid = FlareAidDecisionAid(qs=self.userless_qs)
        self.assertEqual(len(context.captured_queries), 4)  # 3 queries for medhistorys
        self.assertEqual(age_calc(self.userless_flareaid.dateofbirth.value), decisionaid.age)
        self.assertEqual(self.userless_gender, decisionaid.gender)
        self.assertEqual(self.userless_ckd.ckddetail, decisionaid.ckddetail)
        for medhistory in MedHistory.objects.filter(user=None).all():
            self.assertIn(medhistory, decisionaid.medhistorys)
        self.assertEqual(self.userless_flareaid, decisionaid.flareaid)
        self.assertIn(userless_colchicine_allergy, decisionaid.medallergys)
        self.assertNotIn(self.userless_allopurinolallergy, decisionaid.medallergys)
        self.assertIsNone(decisionaid.user)
        self.assertIsNone(decisionaid.sideeffects)
        self.assertTrue(isinstance(decisionaid.defaultflaretrtsettings, DefaultFlareTrtSettings))
        self.assertIsNone(decisionaid.defaultflaretrtsettings.user)  # type: ignore

    def test__init_with_user(self):
        custom_settings = DefaultFlareTrtSettingsFactory(user=self.user)
        user_colchicine_allergy = MedAllergyFactory(user=self.user, treatment=Treatments.COLCHICINE)
        with CaptureQueriesContext(connection) as context:
            decisionaid = FlareAidDecisionAid(qs=self.user_qs)
        self.assertEqual(len(context.captured_queries), 3)
        self.assertEqual(age_calc(self.user.dateofbirth.value), decisionaid.age)
        self.assertEqual(self.user.gender, decisionaid.gender)
        for medhistory in MedHistory.objects.filter(user=self.user).all():
            self.assertIn(medhistory, decisionaid.medhistorys)
            if medhistory.medhistorytype == MedHistoryTypes.CKD:
                self.assertEqual(medhistory.ckddetail, decisionaid.ckddetail)
        self.assertIn(user_colchicine_allergy, decisionaid.medallergys)
        self.assertNotIn(self.user_allopurinolallergy, decisionaid.medallergys)
        self.assertIsNone(decisionaid.sideeffects)
        self.assertEqual(decisionaid.defaultflaretrtsettings, custom_settings)

    def test__init_with_non_QuerySet_object(self):
        user_colchicine_allergy = MedAllergyFactory(user=self.user, treatment=Treatments.COLCHICINE)
        # get() the user_qs to make it a User object
        qs = self.user_qs.get()
        with CaptureQueriesContext(connection) as context:
            decisionaid = FlareAidDecisionAid(qs=qs)
        # 1 because there are no custom settings that can be select_related
        self.assertEqual(len(context.captured_queries), 1)
        self.assertEqual(age_calc(self.user.dateofbirth.value), decisionaid.age)
        self.assertEqual(self.user.gender, decisionaid.gender)
        for medhistory in MedHistory.objects.filter(user=self.user).all():
            self.assertIn(medhistory, decisionaid.medhistorys)
            if medhistory.medhistorytype == MedHistoryTypes.CKD:
                self.assertEqual(medhistory.ckddetail, decisionaid.ckddetail)
        self.assertIn(user_colchicine_allergy, decisionaid.medallergys)
        self.assertNotIn(self.user_allopurinolallergy, decisionaid.medallergys)
        self.assertIsNone(decisionaid.sideeffects)

    def test__init_with_non_FlareAid_User_raises_ValueError(self):
        with self.assertRaises(ValueError):
            FlareAidDecisionAid(qs=self.userless_allopurinolallergy)

    def test__defaulttrts_no_user(self):
        default_trts = self.userless_decisionaid.default_trts
        self.assertEqual(len(default_trts), 9)
        self.assertTrue(isinstance(default_trts, QuerySet))
        for default in list(default_trts):
            self.assertTrue(isinstance(default, DefaultTrt))
            self.assertIsNone(default.user)
        for flare_trt in FlarePpxChoices:
            self.assertTrue(default.treatment for default in list(default_trts) if default.treatment == flare_trt)

    def test__defaulttrts_with_user(self):
        custom_colchicine_default = DefaultColchicineFlareFactory(user=self.user)
        decisionaid = FlareAidDecisionAid(qs=self.user_qs)
        self.assertEqual(len(decisionaid.default_trts), 9)
        self.assertIn(custom_colchicine_default, decisionaid.default_trts)

    def test__defaultmedhistorys_no_user(self):
        default_medhistorys = self.userless_decisionaid.default_medhistorys
        self.assertEqual(len(default_medhistorys), 44)
        medhistorytypes = [medhistory.medhistorytype for medhistory in self.userless_flareaid.medhistorys.all()]
        default_medhistorytypes = [default.medhistorytype for default in default_medhistorys]
        for default in list(default_medhistorys):
            self.assertTrue(isinstance(default, DefaultMedHistory))
            self.assertIsNone(default.user)
            self.assertIn(default.medhistorytype, medhistorytypes)
        for medhistorytype in medhistorytypes:
            # Diabetes will not be in the default_medhistorytypes because it's not a contraindication
            # to steroids. Included to prompt the DetailView to show the user a sub-template about how
            # steroids affect blood sugar.
            if medhistorytype != MedHistoryTypes.DIABETES:
                self.assertIn(medhistorytype, default_medhistorytypes)

    def test__defaultmedhistorys_with_user(self):
        custom_default = DefaultMedHistoryFactory(
            user=self.user,
            medhistorytype=MedHistoryTypes.ANGINA,
            contraindication=DefaultMedHistory.Contraindications.ABSOLUTE,
            treatment=Treatments.COLCHICINE,
            trttype=DefaultMedHistory.TrtTypes.FLARE,
        )
        decisionaid = FlareAidDecisionAid(qs=self.user_qs)
        self.assertEqual(len(decisionaid.default_medhistorys), 45)
        self.assertIn(custom_default, decisionaid.default_medhistorys)

    def test___create_trts_dict(self):
        trts_dict = self.userless_decisionaid._create_trts_dict()
        self.assertTrue(isinstance(trts_dict, dict))
        for trt in FlarePpxChoices:
            self.assertIn(trt, trts_dict)
            self.assertTrue(isinstance(trts_dict[trt], dict))

    def test__decision_aid_dict_created(self):
        decisionaid_dict = self.userless_decisionaid._create_decisionaid_dict()
        self.assertTrue(isinstance(decisionaid_dict, dict))
        for trt in FlarePpxChoices:
            self.assertIn(trt, decisionaid_dict)

    def test___create_decisionaid_dict_aids_process_medhistorys(self):
        flareaid = FlareAidFactory()
        medhistorys = MedHistory.objects.all()
        flareaid.medhistorys.add(*medhistorys)
        decisionaid = FlareAidDecisionAid(qs=flareaid_userless_qs(pk=flareaid.pk))
        decisionaid_dict = decisionaid._create_decisionaid_dict()
        defaults = list(decisionaid.default_medhistorys)
        for default in defaults:
            self.assertTrue(decisionaid_dict[default.treatment]["contra"])

    def test___create_decisionaid_dict_aids_process_medallergys(self):
        flareaid = FlareAidFactory()
        medallergy = MedAllergyFactory(treatment=Treatments.IBUPROFEN)
        flareaid.medallergys.add(medallergy)
        decisionaid = FlareAidDecisionAid(qs=flareaid_userless_qs(pk=flareaid.pk))
        decisionaid_dict = decisionaid._create_decisionaid_dict()
        for medallergy in decisionaid.medallergys:
            self.assertTrue(decisionaid_dict[medallergy.treatment]["contra"])

    def test__create_decisionaid_dict_aids_process_nsaids(self):
        flareaid = FlareAidFactory()
        medallergy = MedAllergyFactory(treatment=Treatments.IBUPROFEN)
        flareaid.medallergys.add(medallergy)
        decisionaid = FlareAidDecisionAid(qs=flareaid_userless_qs(pk=flareaid.pk))
        decisionaid_dict = decisionaid._create_decisionaid_dict()
        for nsaid in NsaidChoices:
            self.assertTrue(decisionaid_dict[nsaid]["contra"])

    def test__create_decisionaid_dict_aids_process_nsaids_not_equivalent(self):
        settings = DefaultFlareTrtSettings.objects.get(user=None)
        settings.nsaids_equivalent = False
        settings.save()
        flareaid = FlareAidFactory()
        medallergy = MedAllergyFactory(treatment=Treatments.IBUPROFEN)
        flareaid.medallergys.add(medallergy)
        decisionaid = FlareAidDecisionAid(qs=flareaid_userless_qs(pk=flareaid.pk))
        decisionaid_dict = decisionaid._create_decisionaid_dict()
        for nsaid in NsaidChoices:
            if nsaid == NsaidChoices.IBUPROFEN:
                self.assertTrue(decisionaid_dict[nsaid]["contra"])
            else:
                self.assertFalse(decisionaid_dict[nsaid]["contra"])

    def test__create_decisionaid_dict_aids_process_steroids(self):
        medallergy = MedAllergyFactory(treatment=Treatments.METHYLPREDNISOLONE)
        flareaid = FlareAidFactory()
        flareaid.medallergys.add(medallergy)
        decisionaid = FlareAidDecisionAid(qs=flareaid_userless_qs(pk=flareaid.pk))
        decisionaid_dict = decisionaid._create_decisionaid_dict()
        self.assertTrue(decisionaid_dict[Treatments.METHYLPREDNISOLONE]["contra"])
        self.assertTrue(decisionaid_dict[Treatments.PREDNISONE]["contra"])

    def test__create_decisionaid_dict_aids_process_steroids_not_equivalent(self):
        settings = DefaultFlareTrtSettings.objects.get(user=None)
        settings.steroids_equivalent = False
        settings.save()
        medallergy = MedAllergyFactory(treatment=Treatments.METHYLPREDNISOLONE)
        flareaid = FlareAidFactory()
        flareaid.medallergys.add(medallergy)
        decisionaid = FlareAidDecisionAid(qs=flareaid_userless_qs(pk=flareaid.pk))
        decisionaid_dict = decisionaid._create_decisionaid_dict()
        self.assertTrue(decisionaid_dict[Treatments.METHYLPREDNISOLONE]["contra"])
        self.assertFalse(decisionaid_dict[Treatments.PREDNISONE]["contra"])

    def test__save_trt_dict_to_decisionaid_saves(self):
        decisionaid_dict = self.userless_decisionaid._create_decisionaid_dict()
        self.userless_decisionaid._save_trt_dict_to_decisionaid(decisionaid_dict)
        self.assertTrue(isinstance(self.userless_flareaid.decisionaid, dict))
        self.assertEqual(aids_dict_to_json(decisionaid_dict), self.userless_decisionaid.flareaid.decisionaid)

    def test__save_trt_dict_to_decisionaid_commit_false_doesnt_save(self):
        decisionaid_dict = self.userless_decisionaid._create_decisionaid_dict()
        self.userless_decisionaid._save_trt_dict_to_decisionaid(decisionaid_dict, commit=False)
        self.assertTrue(isinstance(self.userless_flareaid.decisionaid, dict))
        self.assertFalse(self.userless_flareaid.decisionaid)

    def test__update(self):
        self.assertFalse(self.userless_flareaid.decisionaid)
        self.userless_decisionaid._update()
        self.userless_flareaid.refresh_from_db()
        self.assertTrue(self.userless_flareaid.decisionaid)
