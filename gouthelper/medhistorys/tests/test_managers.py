from django.db import connection  # type: ignore
from django.test import TestCase
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...medhistorydetails.tests.factories import CkdDetailFactory
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
    def setUp(self):
        self.allopurinolhypersensitivity = Allopurinolhypersensitivity.objects.create()
        self.assertEqual(self.allopurinolhypersensitivity.medhistorytype, MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY)

    def test__get_queryset(self):
        self.assertEqual(Allopurinolhypersensitivity.objects.get_queryset().count(), 1)
        self.assertEqual(Allopurinolhypersensitivity.objects.get_queryset().first(), self.allopurinolhypersensitivity)


class TestAnginaManager(TestCase):
    def setUp(self):
        self.angina = Angina.objects.create()
        self.assertEqual(self.angina.medhistorytype, MedHistoryTypes.ANGINA)

    def test__get_queryset(self):
        self.assertEqual(Angina.objects.get_queryset().count(), 1)
        self.assertEqual(Angina.objects.get_queryset().first(), self.angina)


class TestAnticoagulationManager(TestCase):
    def setUp(self):
        self.anticoagulation = Anticoagulation.objects.create()
        self.assertEqual(self.anticoagulation.medhistorytype, MedHistoryTypes.ANTICOAGULATION)

    def test__get_queryset(self):
        self.assertEqual(Anticoagulation.objects.get_queryset().count(), 1)
        self.assertEqual(Anticoagulation.objects.get_queryset().first(), self.anticoagulation)


class TestBleedManager(TestCase):
    def setUp(self):
        self.bleed = Bleed.objects.create()
        self.assertEqual(self.bleed.medhistorytype, MedHistoryTypes.BLEED)

    def test__get_queryset(self):
        self.assertEqual(Bleed.objects.get_queryset().count(), 1)
        self.assertEqual(Bleed.objects.get_queryset().first(), self.bleed)


class TestCadManager(TestCase):
    def setUp(self):
        self.cad = Cad.objects.create()
        self.assertEqual(self.cad.medhistorytype, MedHistoryTypes.CAD)

    def test__get_queryset(self):
        self.assertEqual(Cad.objects.get_queryset().count(), 1)
        self.assertEqual(Cad.objects.get_queryset().first(), self.cad)


class TestChfManager(TestCase):
    def setUp(self):
        self.chf = Chf.objects.create()
        self.assertEqual(self.chf.medhistorytype, MedHistoryTypes.CHF)

    def test__get_queryset(self):
        self.assertEqual(Chf.objects.get_queryset().count(), 1)
        self.assertEqual(Chf.objects.get_queryset().first(), self.chf)


class TestCkdManagers(TestCase):
    def setUp(self):
        self.ckd = Ckd.objects.create()
        self.assertEqual(self.ckd.medhistorytype, MedHistoryTypes.CKD)
        CkdDetailFactory(medhistory=self.ckd)

    def test__get_queryset(self):
        self.assertEqual(Ckd.objects.get_queryset().count(), 1)
        self.assertEqual(Ckd.objects.get_queryset().first(), self.ckd)

    def test__related_objects(self):
        with CaptureQueriesContext(connection) as queries:
            Ckd.related_objects.get()
        self.assertEqual(len(queries), 1)


class TestColchicineInteractionManager(TestCase):
    def setUp(self):
        self.colchicineinteraction = Colchicineinteraction.objects.create()
        self.assertEqual(self.colchicineinteraction.medhistorytype, MedHistoryTypes.COLCHICINEINTERACTION)

    def test__get_queryset(self):
        self.assertEqual(Colchicineinteraction.objects.get_queryset().count(), 1)
        self.assertEqual(Colchicineinteraction.objects.get_queryset().first(), self.colchicineinteraction)


class TestDiabetesManager(TestCase):
    def setUp(self):
        self.diabetes = Diabetes.objects.create()
        self.assertEqual(self.diabetes.medhistorytype, MedHistoryTypes.DIABETES)

    def test__get_queryset(self):
        self.assertEqual(Diabetes.objects.get_queryset().count(), 1)
        self.assertEqual(Diabetes.objects.get_queryset().first(), self.diabetes)


class TestErosionsManager(TestCase):
    def setUp(self):
        self.erosions = Erosions.objects.create()
        self.assertEqual(self.erosions.medhistorytype, MedHistoryTypes.EROSIONS)

    def test__get_queryset(self):
        self.assertEqual(Erosions.objects.get_queryset().count(), 1)
        self.assertEqual(Erosions.objects.get_queryset().first(), self.erosions)


class TestFebuxostatHypersensitivityManager(TestCase):
    def setUp(self):
        self.febuxostathypersensitivity = Febuxostathypersensitivity.objects.create()
        self.assertEqual(self.febuxostathypersensitivity.medhistorytype, MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY)

    def test__get_queryset(self):
        self.assertEqual(Febuxostathypersensitivity.objects.get_queryset().count(), 1)
        self.assertEqual(Febuxostathypersensitivity.objects.get_queryset().first(), self.febuxostathypersensitivity)


class TestGastricbypassManager(TestCase):
    def setUp(self):
        self.gastricbypass = Gastricbypass.objects.create()
        self.assertEqual(self.gastricbypass.medhistorytype, MedHistoryTypes.GASTRICBYPASS)

    def test__get_queryset(self):
        self.assertEqual(Gastricbypass.objects.get_queryset().count(), 1)
        self.assertEqual(Gastricbypass.objects.get_queryset().first(), self.gastricbypass)


class TestGoutManager(TestCase):
    def setUp(self):
        self.gout = Gout.objects.create()
        self.assertEqual(self.gout.medhistorytype, MedHistoryTypes.GOUT)

    def test__get_queryset(self):
        self.assertEqual(Gout.objects.get_queryset().count(), 1)
        self.assertEqual(Gout.objects.get_queryset().first(), self.gout)


class TestHeartattackManager(TestCase):
    def setUp(self):
        self.heartattack = Heartattack.objects.create()
        self.assertEqual(self.heartattack.medhistorytype, MedHistoryTypes.HEARTATTACK)

    def test__get_queryset(self):
        self.assertEqual(Heartattack.objects.get_queryset().count(), 1)
        self.assertEqual(Heartattack.objects.get_queryset().first(), self.heartattack)


class TestHypertensionManager(TestCase):
    def setUp(self):
        self.hypertension = Hypertension.objects.create()
        self.assertEqual(self.hypertension.medhistorytype, MedHistoryTypes.HYPERTENSION)

    def test__get_queryset(self):
        self.assertEqual(Hypertension.objects.get_queryset().count(), 1)
        self.assertEqual(Hypertension.objects.get_queryset().first(), self.hypertension)


class TestHyperuricemiaManager(TestCase):
    def setUp(self):
        self.hyperuricemia = Hyperuricemia.objects.create()
        self.assertEqual(self.hyperuricemia.medhistorytype, MedHistoryTypes.HYPERURICEMIA)

    def test__get_queryset(self):
        self.assertEqual(Hyperuricemia.objects.get_queryset().count(), 1)
        self.assertEqual(Hyperuricemia.objects.get_queryset().first(), self.hyperuricemia)


class TestIbdManager(TestCase):
    def setUp(self):
        self.ibd = Ibd.objects.create()
        self.assertEqual(self.ibd.medhistorytype, MedHistoryTypes.IBD)

    def test__get_queryset(self):
        self.assertEqual(Ibd.objects.get_queryset().count(), 1)
        self.assertEqual(Ibd.objects.get_queryset().first(), self.ibd)


class TestMenopauseManager(TestCase):
    def setUp(self):
        self.menopause = Menopause.objects.create()
        self.assertEqual(self.menopause.medhistorytype, MedHistoryTypes.MENOPAUSE)

    def test__get_queryset(self):
        self.assertEqual(Menopause.objects.get_queryset().count(), 1)
        self.assertEqual(Menopause.objects.get_queryset().first(), self.menopause)


class TestOrgantransplantManager(TestCase):
    def setUp(self):
        self.organtransplant = Organtransplant.objects.create()
        self.assertEqual(self.organtransplant.medhistorytype, MedHistoryTypes.ORGANTRANSPLANT)

    def test__get_queryset(self):
        self.assertEqual(Organtransplant.objects.get_queryset().count(), 1)
        self.assertEqual(Organtransplant.objects.get_queryset().first(), self.organtransplant)


class TestOsteoporosisManager(TestCase):
    def setUp(self):
        self.osteoporosis = Osteoporosis.objects.create()
        self.assertEqual(self.osteoporosis.medhistorytype, MedHistoryTypes.OSTEOPOROSIS)

    def test__get_queryset(self):
        self.assertEqual(Osteoporosis.objects.get_queryset().count(), 1)
        self.assertEqual(Osteoporosis.objects.get_queryset().first(), self.osteoporosis)


class TestPvdManager(TestCase):
    def setUp(self):
        self.pvd = Pvd.objects.create()
        self.assertEqual(self.pvd.medhistorytype, MedHistoryTypes.PVD)

    def test__get_queryset(self):
        self.assertEqual(Pvd.objects.get_queryset().count(), 1)
        self.assertEqual(Pvd.objects.get_queryset().first(), self.pvd)


class TestStrokeManager(TestCase):
    def setUp(self):
        self.stroke = Stroke.objects.create()
        self.assertEqual(self.stroke.medhistorytype, MedHistoryTypes.STROKE)

    def test__get_queryset(self):
        self.assertEqual(Stroke.objects.get_queryset().count(), 1)
        self.assertEqual(Stroke.objects.get_queryset().first(), self.stroke)


class TestTophiManager(TestCase):
    def setUp(self):
        self.tophi = Tophi.objects.create()
        self.assertEqual(self.tophi.medhistorytype, MedHistoryTypes.TOPHI)

    def test__get_queryset(self):
        self.assertEqual(Tophi.objects.get_queryset().count(), 1)
        self.assertEqual(Tophi.objects.get_queryset().first(), self.tophi)


class TestUratestonesManager(TestCase):
    def setUp(self):
        self.uratestones = Uratestones.objects.create()
        self.assertEqual(self.uratestones.medhistorytype, MedHistoryTypes.URATESTONES)

    def test__get_queryset(self):
        self.assertEqual(Uratestones.objects.get_queryset().count(), 1)
        self.assertEqual(Uratestones.objects.get_queryset().first(), self.uratestones)


class TestXoiinteractionManager(TestCase):
    def setUp(self):
        self.xoiinteraction = Xoiinteraction.objects.create()
        self.assertEqual(self.xoiinteraction.medhistorytype, MedHistoryTypes.XOIINTERACTION)

    def test__get_queryset(self):
        self.assertEqual(Xoiinteraction.objects.get_queryset().count(), 1)
        self.assertEqual(Xoiinteraction.objects.get_queryset().first(), self.xoiinteraction)
