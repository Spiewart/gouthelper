from django.apps import apps  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from django.db import models  # type: ignore
from django.db.models.functions import Now  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..medhistorys.lists import (
    FLARE_MEDHISTORYS,
    FLAREAID_MEDHISTORYS,
    GOALURATE_MEDHISTORYS,
    PPX_MEDHISTORYS,
    PPXAID_MEDHISTORYS,
    ULT_MEDHISTORYS,
    ULTAID_MEDHISTORYS,
)
from ..utils.models import DecisionAidRelation, GoutHelperModel, TreatmentAidRelation
from .choices import MedHistoryTypes
from .helpers import medhistorys_get_default_medhistorytype
from .managers import (
    AllopurinolhypersensitivityManager,
    AnginaManager,
    AnticoagulationManager,
    BleedManager,
    CadManager,
    ChfManager,
    CkdManager,
    CkdRelationsManager,
    ColchicineinteractionManager,
    DiabetesManager,
    ErosionsManager,
    FebuxostathypersensitivityManager,
    GastricbypassManager,
    GoutManager,
    GoutRelationsManager,
    HeartattackManager,
    HypertensionManager,
    HyperuricemiaManager,
    IbdManager,
    MenopauseManager,
    OrgantransplantManager,
    OsteoporosisManager,
    PudManager,
    PvdManager,
    StrokeManager,
    TophiManager,
    UratestonesManager,
    XoiinteractionManager,
)

User = get_user_model()


class MedHistory(
    RulesModelMixin,
    GoutHelperModel,
    DecisionAidRelation,
    TreatmentAidRelation,
    TimeStampedModel,
    metaclass=RulesModelBase,
):
    """GoutHelper MedHistory model to store medical, family, social history data
    for Patients. value field is a Boolean that is required and defaults to False.
    """

    class Meta:
        constraints = [
            # If there's a User, there can be no associated Aid objects
            # Likewise, if there's an Aid object, there can be no User
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_user_aid_exclusive",
                check=(
                    models.Q(
                        user__isnull=False,
                        flare__isnull=True,
                        flareaid__isnull=True,
                        goalurate__isnull=True,
                        ppxaid__isnull=True,
                        ppx__isnull=True,
                        ultaid__isnull=True,
                        ult__isnull=True,
                    )
                    | models.Q(
                        user__isnull=True,
                    )
                    | models.Q(
                        user__isnull=True,
                        flare__isnull=True,
                        flareaid__isnull=True,
                        goalurate__isnull=True,
                        ppxaid__isnull=True,
                        ppx__isnull=True,
                        ultaid__isnull=True,
                        ult__isnull=True,
                    )
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_set_date_valid",
                check=(
                    models.Q(set_date__isnull=False) & models.Q(set_date__lte=Now()) | models.Q(set_date__isnull=True)
                ),
            ),
            # Check that medhistorytype is in MedHistoryTypes.choices
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_medhistorytype_valid",
                check=models.Q(medhistorytype__in=MedHistoryTypes.values),
            ),
            # A User can only have one of each type of MedHistory
            models.UniqueConstraint(
                fields=["user", "medhistorytype"],
                name="%(app_label)s_%(class)s_unique_user",
            ),
            # Each type of Aid inherited from DecisionAidRelation and TreatmentAidRelation can only have
            # MedHistory objects with medhistorytypes that are in their respective lists
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_flare_mhtype",
                check=(
                    models.Q(
                        flare__isnull=False,
                        medhistorytype__in=FLARE_MEDHISTORYS,
                    )
                    | models.Q(
                        flare__isnull=True,
                    )
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_flareaid_mhtype",
                check=(
                    models.Q(
                        flareaid__isnull=False,
                        medhistorytype__in=FLAREAID_MEDHISTORYS,
                    )
                    | models.Q(
                        flareaid__isnull=True,
                    )
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_goalurate_mhtype",
                check=(
                    models.Q(
                        goalurate__isnull=False,
                        medhistorytype__in=GOALURATE_MEDHISTORYS,
                    )
                    | models.Q(
                        goalurate__isnull=True,
                    )
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_ppx_mhtype",
                check=(
                    models.Q(
                        ppx__isnull=False,
                        medhistorytype__in=PPX_MEDHISTORYS,
                    )
                    | models.Q(
                        ppx__isnull=True,
                    )
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_ppxaid_mhtype",
                check=(
                    models.Q(
                        ppxaid__isnull=False,
                        medhistorytype__in=PPXAID_MEDHISTORYS,
                    )
                    | models.Q(
                        ppxaid__isnull=True,
                    )
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_ult_mhtype",
                check=(
                    models.Q(
                        ult__isnull=False,
                        medhistorytype__in=ULT_MEDHISTORYS,
                    )
                    | models.Q(
                        ult__isnull=True,
                    )
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_ultaid_mhtype",
                check=(
                    models.Q(
                        ultaid__isnull=False,
                        medhistorytype__in=ULTAID_MEDHISTORYS,
                    )
                    | models.Q(
                        ultaid__isnull=True,
                    )
                ),
            ),
            # Each type of Aid inherited from DecisionAidRelation and TreatmentAidRelation can only have
            # one of each type of MedHistory
            models.UniqueConstraint(
                fields=["flare", "medhistorytype"],
                name="%(app_label)s_%(class)s_unique_flare",
            ),
            models.UniqueConstraint(
                fields=["flareaid", "medhistorytype"],
                name="%(app_label)s_%(class)s_unique_flareaid",
            ),
            models.UniqueConstraint(
                fields=["goalurate", "medhistorytype"],
                name="%(app_label)s_%(class)s_unique_goalurate",
            ),
            models.UniqueConstraint(
                fields=["ppxaid", "medhistorytype"],
                name="%(app_label)s_%(class)s_unique_ppxaid",
            ),
            models.UniqueConstraint(
                fields=["ppx", "medhistorytype"],
                name="%(app_label)s_%(class)s_unique_ppx",
            ),
            models.UniqueConstraint(
                fields=["ultaid", "medhistorytype"],
                name="%(app_label)s_%(class)s_unique_ultaid",
            ),
            models.UniqueConstraint(
                fields=["ult", "medhistorytype"],
                name="%(app_label)s_%(class)s_unique_ult",
            ),
        ]

    MedHistoryTypes = MedHistoryTypes

    medhistorytype = models.CharField(
        _("MedHistory Type"),
        max_length=50,
        choices=MedHistoryTypes.choices,
        editable=False,
    )
    set_date = models.DateTimeField(
        _("Date MedHistory Created or Modified"),
        help_text="What date this MedHistory was last created or modified?",
        default=None,
        null=True,
        blank=True,
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    history = HistoricalRecords()
    objects = models.Manager()

    def __str__(self):
        return f"{self.MedHistoryTypes(self.medhistorytype).label}"

    def delete(
        self,
        *args,
        **kwargs,
    ):
        """Overwritten to change class before and after calling super().save()
        so Django-Simple-History works."""
        # Change class to MedHistory, call super().delete(), then change class back
        # to proxy model class in order for Django-Simple-History to work properly
        self.__class__ = MedHistory
        super().delete(*args, **kwargs)
        self.__class__ = apps.get_model(f"medhistorys.{self.medhistorytype}")

    def save(
        self,
        *args,
        **kwargs,
    ):
        """Overwritten to:
        1. Add medhistorytype on initial save.
        2. Change class before and after calling super().save()
        so Django-Simple-History works.
        """
        # Add medhistorytype on initial save
        if self._state.adding is True:
            if not self.medhistorytype:
                self.medhistorytype = medhistorys_get_default_medhistorytype(self)
        # Change class to MedHistory, call super().save(), then change class back
        # to proxy model class in order for Django-Simple-History to work properly
        self.__class__ = MedHistory
        super().save(*args, **kwargs)
        self.__class__ = apps.get_model(f"medhistorys.{self.medhistorytype}")


class Allopurinolhypersensitivity(MedHistory):
    """Patient has had a hypersensitivity reaction to allopurinol."""

    class Meta:
        proxy = True

    objects = AllopurinolhypersensitivityManager()


class Angina(MedHistory):
    """Model for history of cardiac chest pain."""

    class Meta:
        proxy = True

    objects = AnginaManager()


class Anticoagulation(MedHistory):
    """Model for Patient's anticoagulation use. HistoryDetail related object
    AnticoagulationDetail to describe which anticoagulants."""

    class Meta:
        proxy = True

    objects = AnticoagulationManager()


class Bleed(MedHistory):
    """Model for Patient's history of bleeding events."""

    class Meta:
        proxy = True

    objects = BleedManager()


class Cad(MedHistory):
    """Proxy model for Cad MedHistory objects."""

    class Meta:
        proxy = True

    objects = CadManager()


class Chf(MedHistory):
    """Describes whether Patient has a history of congestive heart failure."""

    class Meta:
        proxy = True

    objects = ChfManager()


class Ckd(MedHistory):
    """Whether Patient has a history of chronic kidney disease.
    Details are stored in HistoryDetail related object CkdDetail."""

    class Meta:
        proxy = True

    objects = CkdManager()
    related_objects = CkdRelationsManager()


class Colchicineinteraction(MedHistory):
    """Model for Patient being on a medication that interacts with colchicine.
    Details about which medication are stored in HistoryDetail related object
    ColchicineinteractionDetail."""

    class Meta:
        proxy = True

    objects = ColchicineinteractionManager()


class Diabetes(MedHistory):
    """Whether or not a Patient is diabetic."""

    class Meta:
        proxy = True

    objects = DiabetesManager()


class Erosions(MedHistory):
    """Whether or not a Patient has gouty erosions."""

    class Meta:
        proxy = True

    objects = ErosionsManager()


class Febuxostathypersensitivity(MedHistory):
    """Whether or not a Patient has had a hypersensitivity reaction to febuxostat."""

    class Meta:
        proxy = True

    objects = FebuxostathypersensitivityManager()


class Gastricbypass(MedHistory):
    """Whether or not a Patient has had gastric bypass surgery."""

    class Meta:
        proxy = True

    objects = GastricbypassManager()


class Gout(MedHistory):
    """Whether or not a Patient has gout. GoutDetail related object to describe
    whether or not a Patient is actively flaring or hyperuricemic (past 6 months)."""

    class Meta:
        proxy = True

    objects = GoutManager()
    related_objects = GoutRelationsManager()


class Heartattack(MedHistory):
    """Whether or not a Patient has had a heart attack."""

    class Meta:
        proxy = True

    objects = HeartattackManager()


class Hypertension(MedHistory):
    """Stores whether or not a Patient has a history of hypertension."""

    class Meta:
        proxy = True

    objects = HypertensionManager()


class Hyperuricemia(MedHistory):
    """MedHistory class to indicate whether a Patient has EVER had hyperuricemia
    defined as a serum uric acid > 9 mg/dL.

    This is based off the 2020 ACR guidelines where CKD stage >=3 and serum uric acid
    > 9 mg/dL is a low-evidence, conditional recommendation for ULT.

    FitzGerald JD, Dalbeth N, Mikuls T, Brignardello-Petersen R, Guyatt G, Abeles AM, Gelber AC,
    Harrold LR, Khanna D, King C, Levy G, Libbey C, Mount D, Pillinger MH, Rosenthal A, Singh JA,
    Sims JE, Smith BJ, Wenger NS, Bae SS, Danve A, Khanna PP, Kim SC, Lenert A, Poon S, Qasim A,
    Sehra ST, Sharma TSK, Toprover M, Turgunbaev M, Zeng L, Zhang MA, Turner AS, Neogi T.
    2020 American College of Rheumatology Guideline for the Management of Gout. Arthritis Care Res (Hoboken).
    2020 Jun;72(6):744-760. doi: 10.1002/acr.24180. Epub 2020 May 11. Erratum in: Arthritis Care Res (Hoboken).
    2020 Aug;72(8):1187. Erratum in: Arthritis Care Res (Hoboken). 2021 Mar;73(3):458. PMID: 32391934.
    """

    class Meta:
        proxy = True

    objects = HyperuricemiaManager()


class Ibd(MedHistory):
    """Records history of a Patient's inflammatory bowel disease."""

    class Meta:
        proxy = True

    objects = IbdManager()


class Menopause(MedHistory):
    """Records medical history of menopause. Mostly for figuring out if a
    woman who is having symptoms could be having a gout flare."""

    class Meta:
        proxy = True

    objects = MenopauseManager()


class Organtransplant(MedHistory):
    """Records medical history of an organ transplant. Related
    object OrgantransplantDetail stores details of the transplant."""

    class Meta:
        proxy = True

    objects = OrgantransplantManager()


class Osteoporosis(MedHistory):
    """Records medical history of osteoporosis."""

    class Meta:
        proxy = True

    objects = OsteoporosisManager()


class Pud(MedHistory):
    """Records medical history of peptic ulcer disease."""

    class Meta:
        proxy = True

    objects = PudManager()


class Pvd(MedHistory):
    """Records medical history of peripheral vascular disease."""

    class Meta:
        proxy = True

    objects = PvdManager()


class Stroke(MedHistory):
    """Patient's history of stroke."""

    class Meta:
        proxy = True

    objects = StrokeManager()


class Tophi(MedHistory):
    """Patient's history of gouty tophi."""

    class Meta:
        proxy = True

    objects = TophiManager()


class Uratestones(MedHistory):
    """Patient's history of urate kidney stones."""

    class Meta:
        proxy = True

    objects = UratestonesManager()


class Xoiinteraction(MedHistory):
    class Meta:
        proxy = True

    objects = XoiinteractionManager()
