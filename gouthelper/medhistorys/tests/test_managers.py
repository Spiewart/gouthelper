from django.db import connection  # type: ignore
from django.test import TestCase
from django.test.utils import CaptureQueriesContext  # type: ignore

from ..choices import MedHistoryTypes
from ..models import (
    Allopurinolhypersensitivity,
    Angina,
    Anticoagulation,
    Bleed,
    Cad,
    Chf,
    Ckd,
    Colchicineinteraction,
    Diabetes,
    Erosions,
    Febuxostathypersensitivity,
    Gastricbypass,
    Gout,
    Heartattack,
    Hypertension,
    Hyperuricemia,
    Ibd,
    Menopause,
    Organtransplant,
    Osteoporosis,
    Pvd,
    Stroke,
    Tophi,
    Uratestones,
    Xoiinteraction,
)


class TestAllopurinolHypersensitivityManager(TestCase):
    def test__manager(self):
        self.allopurinolhypersensitivity = Allopurinolhypersensitivity.objects.create()
        self.assertEqual(self.allopurinolhypersensitivity.medhistorytype, MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY)
        for mh in Allopurinolhypersensitivity.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY)


class TestAnginaManager(TestCase):
    def test_manager(self):
        self.angina = Angina.objects.create()
        self.assertEqual(self.angina.medhistorytype, MedHistoryTypes.ANGINA)
        for mh in Angina.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.ANGINA)


class TestAnticoagulationManager(TestCase):
    def test__manager(self):
        self.anticoagulation = Anticoagulation.objects.create()
        self.assertEqual(self.anticoagulation.medhistorytype, MedHistoryTypes.ANTICOAGULATION)
        for mh in Anticoagulation.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.ANTICOAGULATION)


class TestBleedManager(TestCase):
    def test__manager(self):
        self.bleed = Bleed.objects.create()
        self.assertEqual(self.bleed.medhistorytype, MedHistoryTypes.BLEED)
        for mh in Bleed.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.BLEED)


class TestCadManager(TestCase):
    def test__manager(self):
        self.cad = Cad.objects.create()
        self.assertEqual(self.cad.medhistorytype, MedHistoryTypes.CAD)
        for mh in Cad.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.CAD)


class TestChfManager(TestCase):
    def test__manager(self):
        self.chf = Chf.objects.create()
        self.assertEqual(self.chf.medhistorytype, MedHistoryTypes.CHF)
        for mh in Chf.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.CHF)


class TestCkdManagers(TestCase):
    def setUp(self):
        self.ckd = Ckd.objects.create()

    def test__manager(self):
        self.assertEqual(self.ckd.medhistorytype, MedHistoryTypes.CKD)
        for mh in Ckd.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.CKD)

    def test__related_objects(self):
        with CaptureQueriesContext(connection) as queries:
            Ckd.related_objects.last()
        self.assertEqual(len(queries), 1)


class TestColchicineInteractionManager(TestCase):
    def test__manager(self):
        self.colchicineinteraction = Colchicineinteraction.objects.create()
        self.assertEqual(self.colchicineinteraction.medhistorytype, MedHistoryTypes.COLCHICINEINTERACTION)
        for mh in Colchicineinteraction.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.COLCHICINEINTERACTION)


class TestDiabetesManager(TestCase):
    def test__manager(self):
        self.diabetes = Diabetes.objects.create()
        self.assertEqual(self.diabetes.medhistorytype, MedHistoryTypes.DIABETES)
        for mh in Diabetes.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.DIABETES)


class TestErosionsManager(TestCase):
    def test__manager(self):
        self.erosions = Erosions.objects.create()
        self.assertEqual(self.erosions.medhistorytype, MedHistoryTypes.EROSIONS)
        for mh in Erosions.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.EROSIONS)


class TestFebuxostatHypersensitivityManager(TestCase):
    def test__manager(self):
        self.febuxostathypersensitivity = Febuxostathypersensitivity.objects.create()
        self.assertEqual(self.febuxostathypersensitivity.medhistorytype, MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY)
        for mh in Febuxostathypersensitivity.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY)


class TestGastricbypassManager(TestCase):
    def test__manager(self):
        self.gastricbypass = Gastricbypass.objects.create()
        self.assertEqual(self.gastricbypass.medhistorytype, MedHistoryTypes.GASTRICBYPASS)
        for mh in Gastricbypass.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.GASTRICBYPASS)


class TestGoutManager(TestCase):
    def test__manager(self):
        self.gout = Gout.objects.create()
        self.assertEqual(self.gout.medhistorytype, MedHistoryTypes.GOUT)
        for mh in Gout.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.GOUT)


class TestHeartattackManager(TestCase):
    def test__manager(self):
        self.heartattack = Heartattack.objects.create()
        self.assertEqual(self.heartattack.medhistorytype, MedHistoryTypes.HEARTATTACK)
        for mh in Heartattack.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.HEARTATTACK)


class TestHypertensionManager(TestCase):
    def test__manager(self):
        self.hypertension = Hypertension.objects.create()
        self.assertEqual(self.hypertension.medhistorytype, MedHistoryTypes.HYPERTENSION)
        for mh in Hypertension.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.HYPERTENSION)


class TestHyperuricemiaManager(TestCase):
    def test__manager(self):
        self.hyperuricemia = Hyperuricemia.objects.create()
        self.assertEqual(self.hyperuricemia.medhistorytype, MedHistoryTypes.HYPERURICEMIA)
        for mh in Hyperuricemia.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.HYPERURICEMIA)


class TestIbdManager(TestCase):
    def test__manager(self):
        self.ibd = Ibd.objects.create()
        self.assertEqual(self.ibd.medhistorytype, MedHistoryTypes.IBD)
        for mh in Ibd.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.IBD)


class TestMenopauseManager(TestCase):
    def test__manager(self):
        self.menopause = Menopause.objects.create()
        self.assertEqual(self.menopause.medhistorytype, MedHistoryTypes.MENOPAUSE)
        for mh in Menopause.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.MENOPAUSE)


class TestOrgantransplantManager(TestCase):
    def test__manager(self):
        self.organtransplant = Organtransplant.objects.create()
        self.assertEqual(self.organtransplant.medhistorytype, MedHistoryTypes.ORGANTRANSPLANT)
        for mh in Organtransplant.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.ORGANTRANSPLANT)


class TestOsteoporosisManager(TestCase):
    def test__manager(self):
        self.osteoporosis = Osteoporosis.objects.create()
        self.assertEqual(self.osteoporosis.medhistorytype, MedHistoryTypes.OSTEOPOROSIS)
        for mh in Osteoporosis.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.OSTEOPOROSIS)


class TestPvdManager(TestCase):
    def test__manager(self):
        self.pvd = Pvd.objects.create()
        self.assertEqual(self.pvd.medhistorytype, MedHistoryTypes.PVD)
        for mh in Pvd.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.PVD)


class TestStrokeManager(TestCase):
    def test__manager(self):
        self.stroke = Stroke.objects.create()
        self.assertEqual(self.stroke.medhistorytype, MedHistoryTypes.STROKE)
        for mh in Stroke.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.STROKE)


class TestTophiManager(TestCase):
    def test__manager(self):
        self.tophi = Tophi.objects.create()
        self.assertEqual(self.tophi.medhistorytype, MedHistoryTypes.TOPHI)
        for mh in Tophi.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.TOPHI)


class TestUratestonesManager(TestCase):
    def test__manager(self):
        self.uratestones = Uratestones.objects.create()
        self.assertEqual(self.uratestones.medhistorytype, MedHistoryTypes.URATESTONES)
        for mh in Uratestones.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.URATESTONES)


class TestXoiinteractionManager(TestCase):
    def test__manager(self):
        self.xoiinteraction = Xoiinteraction.objects.create()
        self.assertEqual(self.xoiinteraction.medhistorytype, MedHistoryTypes.XOIINTERACTION)
        for mh in Xoiinteraction.objects.get_queryset().all():
            self.assertEqual(mh.medhistorytype, MedHistoryTypes.XOIINTERACTION)
