from datetime import timedelta
from decimal import Decimal
from typing import Union

from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from multiselectfield import MultiSelectField  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..choices import BOOL_CHOICES
from ..genders.choices import Genders
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.lists import FLARE_MEDHISTORYS
from ..utils.helpers.helpers import calculate_duration, now_date
from ..utils.models import DecisionAidModel, GoutHelperModel, MedHistoryAidModel
from .choices import Likelihoods, LimitedJointChoices, Prevalences
from .helpers import (
    flares_abnormal_duration,
    flares_calculate_prevalence_points,
    flares_common_joints,
    flares_get_likelihood_str,
    flares_uncommon_joints,
)
from .services import FlareDecisionAid


class Flare(
    RulesModelMixin,
    DecisionAidModel,
    GoutHelperModel,
    MedHistoryAidModel,
    TimeStampedModel,
    metaclass=RulesModelBase,
):
    """
    Model for describing a gout flare and calculating probability it was from gout.
    """

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_diagnosed_valid",
                check=(
                    models.Q(
                        diagnosed=True,
                    )
                    | models.Q(
                        diagnosed=False,
                        crystal_analysis__isnull=True,
                    )
                ),
            ),
            models.CheckConstraint(
                check=models.Q(date_started__lte=models.functions.Now()),
                name="%(app_label)s_%(class)s_date_started_not_in_future",
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_start_end_date_valid",
                check=(models.Q(date_ended__gte=models.F("date_started"))),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_likelihood_valid",
                check=(models.Q(likelihood__in=Likelihoods.values)),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_prevalence_valid",
                check=(models.Q(prevalence__in=Prevalences.values)),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_joints_valid",
                check=(
                    models.Q(joints__contains=LimitedJointChoices.MTP1R)
                    | models.Q(joints__contains=LimitedJointChoices.MTP1L)
                    | models.Q(joints__contains=LimitedJointChoices.RFOOT)
                    | models.Q(joints__contains=LimitedJointChoices.LFOOT)
                    | models.Q(joints__contains=LimitedJointChoices.ANKLER)
                    | models.Q(joints__contains=LimitedJointChoices.ANKLEL)
                    | models.Q(joints__contains=LimitedJointChoices.KNEER)
                    | models.Q(joints__contains=LimitedJointChoices.KNEEL)
                    | models.Q(joints__contains=LimitedJointChoices.HIPR)
                    | models.Q(joints__contains=LimitedJointChoices.HIPL)
                    | models.Q(joints__contains=LimitedJointChoices.RHAND)
                    | models.Q(joints__contains=LimitedJointChoices.LHAND)
                    | models.Q(joints__contains=LimitedJointChoices.WRISTR)
                    | models.Q(joints__contains=LimitedJointChoices.WRISTL)
                    | models.Q(joints__contains=LimitedJointChoices.ELBOWR)
                    | models.Q(joints__contains=LimitedJointChoices.ELBOWL)
                    | models.Q(joints__contains=LimitedJointChoices.SHOULDERR)
                    | models.Q(joints__contains=LimitedJointChoices.SHOULDERL)
                ),
            ),
        ]
        ordering = ["created"]

    FLARE_MEDHISTORYS = FLARE_MEDHISTORYS
    LimitedJointChoices = LimitedJointChoices
    Likelihoods = Likelihoods
    Prevalences = Prevalences

    crystal_analysis = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name=_("Crystal Analysis"),
        help_text=_(
            "Did a clinician drain the joint and observe \
monosodium urate crystals on polarized microscopy?"
        ),
        default=None,
        null=True,
        blank=True,
    )
    date_ended = models.DateField(
        _("Date Flare Resolved"),
        help_text=_("What day did this flare resolve? Leave blank if it's ongoing."),
        blank=True,
        null=True,
        default=None,
    )
    dateofbirth = models.OneToOneField(
        "dateofbirths.DateOfBirth",
        on_delete=models.CASCADE,
    )
    date_started = models.DateField(
        _("Date Flare Started"),
        help_text=_("What day did this flare start?"),
        default=now_date,
    )
    gender = models.OneToOneField(
        "genders.Gender",
        on_delete=models.CASCADE,
    )
    joints = MultiSelectField(
        choices=LimitedJointChoices.choices,
        verbose_name=_("Location(s) of Flare"),
        help_text=_("What joint(s) did the flare occur in?"),
        # need to put max_length otherwise migrations will raise IndexError on self.validators
        max_length=600,
    )
    onset = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name=_("Rapid Onset (1 day)"),
        help_text=_("Did your symptoms start and reach maximum intensity within 1 day?"),
        default=False,
    )
    redness = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name=_("Redness"),
        help_text=_("Is(are) the joint(s) red (erythematous)?"),
        default=False,
    )
    likelihood = models.CharField(
        _("Likelihood"),
        max_length=20,
        choices=Likelihoods.choices,
        default=None,
        null=True,
        blank=True,
    )
    prevalence = models.CharField(
        _("Prevalence"),
        max_length=10,
        choices=Prevalences.choices,
        default=None,
        null=True,
        blank=True,
    )
    urate = models.OneToOneField(
        "labs.Urate",
        on_delete=models.SET_NULL,
        help_text=_("Was a urate level measured during this flare?"),
        blank=True,
        null=True,
        verbose_name=_("Flare Urate"),
    )
    diagnosed = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name=_("Clinician Diagnosed"),
        help_text=_("Did a clinician diagnose these symptoms as a gout flare?"),
        default=False,
    )

    history = HistoricalRecords()
    objects = models.Manager()

    @cached_property
    def abnormal_duration(self) -> bool:
        """Method that returns True if a Flare is abnormally long or short
        for a typical gout flare."""
        return flares_abnormal_duration(duration=self.duration, date_ended=self.date_ended)

    @classmethod
    def aid_medhistorys(cls) -> list[MedHistoryTypes]:
        return FLARE_MEDHISTORYS

    @cached_property
    def at_risk_for_gout(self) -> bool:
        """Method that returns True if the patient referenced by a Flare
        is at risk for gout demographically and False if not."""
        if self.gender:
            return (
                self.gender.value == Genders.MALE
                and self.age
                and self.age >= 18
                or self.gender.value == Genders.FEMALE
                and (self.post_menopausal or self.ckd)
            )
        return False

    @cached_property
    def common_joints(self) -> list[LimitedJointChoices]:
        """Method that returns a list of the joints of a Flare that are
        in COMMON_GOUT_JOINTS."""
        return flares_common_joints(joints=self.joints)

    @property
    def common_joints_str(self) -> str:
        """Method that returns a str of the joints of a Flare that are
        in COMMON_GOUT_JOINTS."""
        enum_list = [getattr(LimitedJointChoices, joint) for joint in self.common_joints]
        # https://stackoverflow.com/questions/10880813/typeerror-sequence-item-0-expected-string-int-found
        return ", ".join([str(joint.label).lower() for joint in enum_list])

    @property
    def duration(self) -> timedelta:
        return calculate_duration(date_started=self.date_started, date_ended=self.date_ended)

    @cached_property
    def firstmtp(self) -> bool:
        """Method that returns True if LimitedJointChoices.MTP1L or
        LimitedJointChoices.MTP1R is in the joints of a Flare and False if not."""
        return LimitedJointChoices.MTP1L in self.joints or LimitedJointChoices.MTP1R in self.joints

    @property
    def firstmtp_str(self) -> str:
        """Method that returns a str of the first metatarsophalangeal joint
        of a Flare."""
        mtp_str = ""
        if LimitedJointChoices.MTP1L in self.joints:
            mtp_str += "left"
        if LimitedJointChoices.MTP1R in self.joints:
            if mtp_str:
                mtp_str += " and "
            mtp_str += "right"
        mtp_str += " first metatarsophalangeal joint"
        return mtp_str

    def get_absolute_url(self):
        return reverse("flares:detail", kwargs={"pk": self.pk})

    @cached_property
    def hyperuricemia(self) -> bool:
        """Method that returns True if a Flare has a Urate that is
        in the hyperuricemic range (>= 6 mg/dL) and False if not."""
        if self.urate:
            return self.urate.value > Decimal("5.88")
        return False

    def joints_str(self):
        """
        Function that returns a str of the joints affected by the flare
        returns: [str]: [str describing the joints(s) of the flare]
        """
        if len(self.joints) == 1:
            return f"{', '.join(joint.lower() for joint in self.get_joints_list())}"
        else:
            return f"{', '.join(joint.lower() for joint in self.get_joints_list())}"

    @property
    def likelihood_str(self):
        return flares_get_likelihood_str(flare=self)

    @property
    def monoarticular(self):
        return not self.polyarticular

    @property
    def polyarticular(self):
        if len(self.joints) > 1:
            return True
        return False

    @cached_property
    def post_menopausal(self) -> bool:
        """Method that determines if the patient references by a Flare
        is post-menopausal. Returns True if so, False if not."""
        # Check for age and menopause in medhistorys
        # Return True if age >= 50 or menopause
        return self.age and self.age >= 60 or self.menopause

    @cached_property
    def prevalence_points(self) -> float:
        """Method that returns the Diagnostic Rule points for prevalence for a Flare."""
        return flares_calculate_prevalence_points(
            gender=self.gender,
            onset=self.onset,
            redness=self.redness,
            joints=self.joints,
            medhistorys=self.medhistorys_qs if self.medhistorys_qs else list(self.medhistorys.all()),
            urate=self.urate,
        )

    def __str__(self):
        flare_str = "Monoarticular" if self.monoarticular else "Polyarticular"
        flare_str += f", {self.date_started} - "
        flare_str += f"{self.date_ended}" if self.date_ended else "present"
        return flare_str

    @cached_property
    def uncommon_joints(self) -> list[LimitedJointChoices]:
        """Method that returns a list of the joints of a Flare that are
        NOT in COMMON_GOUT_JOINTS."""
        return flares_uncommon_joints(joints=self.joints)

    @property
    def uncommon_joints_str(self) -> str:
        """Method that returns a str of the joints of a Flare that are
        NOT in COMMON_GOUT_JOINTS."""
        enum_list = [getattr(LimitedJointChoices, joint) for joint in self.uncommon_joints]
        # https://stackoverflow.com/questions/10880813/typeerror-sequence-item-0-expected-string-int-found
        return ", ".join([str(joint.label).lower() for joint in enum_list])

    def update(self, decisionaid: FlareDecisionAid | None = None, qs: Union["Flare", None] = None) -> "Flare":
        """Updates Flare prevalence and likelihood fields.

        args:
            decisionaid: FlareDecisionAid object to use for updating prevalence and likelihood
            qs: Flare object with attached qs to use for updating prevalence and likelihood

        returns: [Flare]: [Flare object]"""
        if decisionaid is None:
            decisionaid = FlareDecisionAid(pk=self.pk, qs=qs)
        return decisionaid._update()
