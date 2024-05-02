from typing import TYPE_CHECKING, Union

from django.conf import settings  # type: ignore
from django.core.validators import MaxValueValidator, MinValueValidator  # type: ignore
from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.html import mark_safe  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..medhistorydetails.choices import Stages
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.helpers import medhistory_attr, medhistorys_get_ckd_3_or_higher
from ..medhistorys.lists import ULT_MEDHISTORYS
from ..rules import add_object, change_object, delete_object, view_object
from ..users.models import Pseudopatient
from ..utils.models import GoutHelperAidModel, GoutHelperModel
from .choices import FlareFreqs, FlareNums, Indications
from .managers import UltManager
from .services import UltDecisionAid

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    from ..medhistorys.models import Ckd

    User = get_user_model()


class Ult(
    RulesModelMixin,
    GoutHelperAidModel,
    GoutHelperModel,
    TimeStampedModel,
    metaclass=RulesModelBase,
):
    class Meta:
        rules_permissions = {
            "add": add_object,
            "change": change_object,
            "delete": delete_object,
            "view": view_object,
        }
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_num_flares_valid",
                check=(models.Q(num_flares__in=FlareNums.values)),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_freq_flares_valid",
                check=(models.Q(freq_flares__in=FlareFreqs.values)),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_indication_valid",
                check=(models.Q(indication__in=Indications.values)),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_freq_num_flares_valid",
                check=(
                    (models.Q(num_flares=FlareNums.TWOPLUS) & models.Q(freq_flares__isnull=False))
                    | (models.Q(num_flares=FlareNums.ONE) & models.Q(freq_flares__isnull=True))
                    | (models.Q(num_flares=FlareNums.ZERO) & models.Q(freq_flares__isnull=True))
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_valid",
                check=(
                    models.Q(
                        user__isnull=False,
                        dateofbirth__isnull=True,
                        gender__isnull=True,
                    )
                    | models.Q(
                        user__isnull=True,
                        # dateofbirth and gender can be null because not all Ults will have a CkdDetail
                    )
                ),
            ),
        ]

    FlareFreqs = FlareFreqs
    FlareNums = FlareNums
    Indications = Indications
    Stages = Stages

    dateofbirth = models.OneToOneField(
        "dateofbirths.DateOfBirth",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    freq_flares = models.IntegerField(
        _("Flares per Year"),
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        choices=FlareFreqs.choices,
        help_text="How many gout flares to you have per year?",
        blank=True,
        null=True,
    )
    gender = models.OneToOneField(
        "genders.Gender",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    indication = models.IntegerField(
        _("Indication"),
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        choices=Indications.choices,
        help_text="Does the patient have an indication for ULT?",
        default=Indications.NOTINDICATED,
    )
    num_flares = models.IntegerField(
        _("Total Number of Flares"),
        choices=FlareNums.choices,
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        help_text="How many gout flares have you had?",
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    history = HistoricalRecords()

    objects = models.Manager()
    related_objects = UltManager()

    def __str__(self):
        return f"Ult: {self.get_indication_display()}"

    @classmethod
    def aid_medhistorys(cls) -> list[MedHistoryTypes]:
        return ULT_MEDHISTORYS

    @property
    def ckd_interp(self) -> str:
        ckd_interp_str = super().ckd_interp

        ckd_interp_str += "<br> <br> CKD by itself is not an indication for ULT. However, \
patients who have their first gout flare and have CKD stage III or higher are \
conditionally recommended to start ULT, albeit with a very low certainty of evidence. "
        if self.has_conditional_indication_for_ckd3_or_higher_only:
            subject_the, pos, gender_pos = self.get_str_attrs("subject_the", "pos", "gender_pos")
            ckd_interp_str += f" <strong>Because {subject_the} {pos} CKD stage III or higher, \
ULT is conditionally recommended for {gender_pos}.</strong>"
        elif self.has_multiple_conditional_indications_for_ult:
            Subject_the, pos = self.get_str_attrs("Subject_the", "pos")
            ckd_interp_str += f" <strong>{Subject_the} {pos} multiple conditional \
indications ({self.conditional_indications_str}) for ULT.</strong>"
        elif self.strong_indication:
            Subject_the, pos, gender_subject = self.get_str_attrs("Subject_the", "pos", "gender_subject")
            ckd_interp_str += f" <strong>{Subject_the} {pos} a strong indication \
for ULT ({self.strong_indications_str}), making CKD irrelevant for the determination of whether or not \
{gender_subject} should be on ULT.</strong>"
        return mark_safe(ckd_interp_str)

    @cached_property
    def ckd3(self) -> Union["Ckd", None]:
        """Returns True if Ult or its user has CKD stage III or higher."""
        return medhistory_attr(
            medhistory=MedHistoryTypes.CKD,
            obj=self,
            select_related=["ckddetail", "baselinecreatinine"],
            mh_get=medhistorys_get_ckd_3_or_higher,
        )

    @cached_property
    def conditional_indication(self) -> bool:
        return self.indication == Indications.CONDITIONAL

    @cached_property
    def contraindicated(self) -> bool:
        return (
            self.num_flares == FlareNums.ONE
            and not (self.ckd3 or self.erosions or self.hyperuricemia or self.tophi or self.uratestones)
            or (self.num_flares == FlareNums.ZERO and not (self.erosions or self.tophi))
        )

    @property
    def erosions_interp(self) -> str:
        subject_the, pos, gender_subject, gender_pos = self.get_str_attrs(
            "subject_the", "pos", "gender_subject", "gender_pos"
        )
        erosions_interp_str = super().erosions_interp
        erosions_interp_str += "<br> <br> Like <a class='samepage-link' href='#tophi'>tophi</a>, \
erosions are a sign of advanced gout and more severe disease. While they don't influence choice of \
ULT, they necessitate aggressive gout treatment and are a strong indication for ULT."
        if self.erosions:
            erosions_interp_str += f" <strong>Because {subject_the} {pos} gouty erosions, \
ULT is strongly recommended for {gender_pos}.</strong>"
        return mark_safe(erosions_interp_str)

    @cached_property
    def explanations(self) -> list[tuple[str, str, bool, str]]:
        """Returns a list of tuples containing information to display explanations in the UltDetail template."""
        return [
            ("ckd", "Chronic Kidney Disease", self.ckd, self.ckd_interp),  # TODO: Add to Ult
            ("erosions", "Erosions", self.erosions, self.erosions_interp),  # TODO: Add to Ult
            ("firstflare", "First Flare", self.firstflare, self.firstflare_interp),
            ("frequentflares", "Frequent Flares", self.frequentflares, self.frequentflares_interp),
            ("hyperuricemia", "Hyperuricemia", self.hyperuricemia, self.hyperuricemia_interp),
            ("multipleflares", "Multiple Flares", self.multipleflares, self.multipleflares_interp),
            ("noflares", "No Flares", self.noflares, self.noflares_interp),
            ("tophi", "Tophi", self.tophi, self.tophi_interp),  # TODO: Add to Ult
            ("uratestones", "Uric Acid Kidney Stones", self.uratestones, self.uratestones_interp),  # TODO: Add to Ult
        ]

    @cached_property
    def firstflare(self) -> bool:
        """Method that returns True if a Ult indicates that the patient
        has only had a single gout flare and does not have any secondary
        medical conditions that would conditionally indicate ULT. A single gout flare
        in the absence of any additional conditions is a contraindication to ULT."""
        return (
            self.num_flares == FlareNums.ONE
            and not (self.ckd3)
            and not self.hyperuricemia
            and not self.uratestones
            and not self.erosions
            and not self.tophi
        )

    @property
    def firstflare_interp(self) -> str:
        Subject_the, pos, subject_the = self.get_str_attrs("Subject_the", "pos", "subject_the")
        firstflare_plus_str = f"Individuals who have their first flare AND who have chronic kidney disease \
(<a class='samepage-link' href='#ckd'>CKD</a>) stage III or higher, <a class='samepage-link' href='#uratestones'>\
uric acid kidney stones</a>, or <a class='samepage-link' href='#hyperuricemia'>hyperuricemia</a> \
{'such as ' + subject_the + ', ' if self.firstflare_plus  and not self.erosions and not self.tophi else ''}have a \
conditional indication for ULT. Patients who have evidence of <a class='samepage-link' \
href='#tophi'>tophaceous gout</a> or gouty <a class='samepage-link' href='#erosions'>erosions</a> \
{'such as ' + subject_the + ', ' if self.erosions or self.tophi else ''}have a strong indication for ULT."
        return mark_safe(
            f"<strong>{Subject_the} {pos} {'only ' if self.firstflare_plus else ''}had a single gout flare.</strong> \
ULT is almost never indicated in patients with their first gout flare, though there are rare exceptions. \
{firstflare_plus_str}"
        )

    @cached_property
    def firstflare_plus(self) -> bool:
        """Method that returns True if a Ult indicates that the patient
        has only had a single gout flare but does have a secondary
        medical conditions that conditionally indicates ULT."""
        return self.num_flares == FlareNums.ONE and self.ckd3 or self.hyperuricemia or self.uratestones

    @cached_property
    def frequentflares(self) -> bool:
        """Method that returns True if a Ult indicates the
        patient is having frequent gout flares (2 or more per year)."""
        return self.freq_flares and self.freq_flares == FlareFreqs.TWOORMORE

    @property
    def frequentflares_interp(self) -> str:
        Subject_the, pos, pos_neg = self.get_str_attrs("Subject_the", "pos", "pos_neg")

        def _get_frequent_flares_str():
            return (
                "and should be on "
                if self.frequentflares
                else (
                    "but still should be on "
                    if self.strong_indication
                    else (
                        "but still should be considered for "
                        if self.conditional_indication
                        else "and " + pos_neg + " an indication for "
                    )
                )
            )

        return mark_safe(
            f"Individuals who have frequent gout flares, defined as 2 or more per year, have a strong \
indication for ULT. <strong>{Subject_the} {pos if self.frequentflares else pos_neg} frequent flares  \
{_get_frequent_flares_str()}ULT therapy.</strong>"
        )

    def get_absolute_url(self):
        if self.user:
            return reverse("ults:pseudopatient-detail", kwargs={"username": self.user.username})
        else:
            return reverse("ults:detail", kwargs={"pk": self.pk})

    def conditional_indication_interp(self, conditional_indication: str) -> str:
        pos, gender_pos, gender_subject = self.get_str_attrs(
            "Subject_the", "pos", "pos_neg", "gender_pos", "gender_subject"
        )
        return (
            f" and {conditional_indication} is {gender_pos} only conditional indication for ULT"
            if getattr(self, f"has_conditional_indication_for_{conditional_indication}_only")
            else (
                f" and {gender_subject} {pos} multiple conditional indications \
({self.conditional_indications_str}) for ULT"
                if self.has_multiple_conditional_indications_for_ult
                else (
                    f" but {gender_subject} {pos} a strong indication for ULT for other reasons"
                    if self.strong_indication
                    else ""
                )
            )
        )

    @cached_property
    def conditional_indications_list_of_strs(self) -> list[str]:
        """Returns a list of conditional indications for ULT."""
        conditional_indication_list_of_strs = []
        if self.ckd3:
            conditional_indication_list_of_strs.append("chronic kidney disease")
        if self.hyperuricemia:
            conditional_indication_list_of_strs.append("hyperuricemia")
        if self.uratestones:
            conditional_indication_list_of_strs.append("uric acid kidney stones")
        if self.multipleflares:
            conditional_indication_list_of_strs.append(
                "multiple flares but having one or less \
flare per year"
            )
        return conditional_indication_list_of_strs

    @cached_property
    def conditional_indications_str(self) -> str:
        """Returns a string of conditional indications for ULT."""
        return ", ".join(self.conditional_indications_list_of_strs)

    @cached_property
    def has_conditional_indication_for_hyperuricemia_only(self) -> bool:
        """Returns True if the Ult/Patient has a conditional indication for ULT due to hyperuricemia only."""
        return (
            self.conditional_indication
            and self.hyperuricemia
            and not (self.ckd3 or self.uratestones or self.multipleflares)
        )

    @cached_property
    def has_conditional_indication_for_ckd3_or_higher_only(self) -> bool:
        """Returns True if the Ult/Patient has a conditional indication for ULT due to CKD stage III or higher only."""
        return (
            self.conditional_indication
            and self.ckd3
            and not (self.hyperuricemia or self.uratestones or self.multipleflares)
        )

    @cached_property
    def has_conditional_indication_for_multipleflares_only(self) -> bool:
        """Returns True if the Ult/Patient has a conditional indication for ULT due to multiple flares only."""
        return (
            self.conditional_indication
            and self.multipleflares
            and not (self.ckd3 or self.hyperuricemia or self.uratestones)
        )

    @cached_property
    def has_conditional_indication_for_uratestones_only(self) -> bool:
        """Returns True if the Ult/Patient has a conditional indication for ULT due to uric acid kidney stones only."""
        return (
            self.conditional_indication
            and self.uratestones
            and not (self.ckd3 or self.hyperuricemia or self.multipleflares)
        )

    @cached_property
    def has_multiple_conditional_indications_for_ult(self) -> bool:
        """Returns True if the Ult/Patient has multiple conditional indications for ULT."""
        return (
            self.conditional_indication
            and len(
                [
                    indication_bool
                    for indication_bool in [self.ckd3, self.hyperuricemia, self.uratestones, self.multipleflares]
                    if indication_bool
                ]
            )
            > 1
        )

    @property
    def hyperuricemia_interp(self) -> str:
        Subject_the, pos, pos_neg, gender_pos, gender_subject = self.get_str_attrs(
            "Subject_the", "pos", "pos_neg", "gender_pos", "gender_subject"
        )

        def _get_indication_interp_str() -> str:
            return (
                f", and this is {gender_pos} only conditional indication for ULT"
                if self.has_conditional_indication_for_hyperuricemia_only
                else (
                    (
                        f", and {gender_subject} {pos} multiple conditional indications \
({self.conditional_indications_str}) for ULT"
                    )
                    if self.has_multiple_conditional_indications_for_ult
                    else (
                        (
                            f", but {gender_subject} {pos} a strong indication \
for ULT for other reasons ({self.strong_indications_str})"
                        )
                        if self.strong_indication
                        else ""
                    )
                )
            )

        return mark_safe(
            f"Hyperuricemia, defined as a serum urate level greater than 9 mg/dL, is NOT an indication for \
ULT by itself. In a patient who is having his or her first flare and would not otherwise have an indication \
for ULT, hyperuricemia is a conditional indication for ULT with a very low certainty of evidence. <strong> \
{Subject_the} {pos if self.hyperuricemia else pos_neg} hyperuricemia</strong>{_get_indication_interp_str()}."
        )

    @cached_property
    def indicated(self) -> bool:
        """Method that returns a bool indicating whether Ult is indicated."""
        if self.indication == Indications.INDICATED or self.indication == Indications.CONDITIONAL:
            return True
        return False

    @cached_property
    def multipleflares(self) -> bool:
        """Method that returns True if a Ult indicates the
        has only one flare per year but has a history of more than 1 gout flare,
        which is a conditional indication for ULT."""
        return self.freq_flares and self.freq_flares == FlareFreqs.ONEORLESS and self.num_flares == FlareNums.TWOPLUS

    @property
    def multipleflares_interp(self) -> str:
        Subject_the, pos, subject_the = self.get_str_attrs("Subject_the", "pos", "subject_the")
        return mark_safe(
            "Individuals who have had multiple gout flares in the past but are currently only having one \
flare per year are conditionally recommended to start ULT based on high moderate certainty of evidence per \
the 2012 ACR guidelines."
        )

    @cached_property
    def noflares(self) -> bool:
        """Method that returns True if a Ult indicates that the patient
        has never had a gout flare, which is a contraindication for ULT."""
        if self.num_flares == FlareNums.ZERO:
            return True
        return False

    @property
    def noflares_interp(self) -> str:
        (Subject_the,) = self.get_str_attrs("Subject_the")
        return mark_safe(
            f"{Subject_the} has {'no ' if self.noflares else ''}previous gout flares.</strong> \
Individuals who have never had a gout flare do not have an indication for ULT."
        )

    @cached_property
    def strong_indication(self) -> bool:
        """Method that returns whether or not the Ult
        has a strong recommendation for ULT."""
        if self.indication == Indications.INDICATED:
            return True
        return False

    @cached_property
    def strong_indications_list_of_strs(self) -> list[str]:
        """Returns a list of strong indications for ULT."""
        strong_indication_list_of_strs = []
        if self.frequentflares:
            strong_indication_list_of_strs.append("frequent flares")
        if self.erosions:
            strong_indication_list_of_strs.append("erosions")
        if self.tophi:
            strong_indication_list_of_strs.append("tophi")
        return strong_indication_list_of_strs

    @cached_property
    def strong_indications_str(self) -> str:
        """Returns a string of strong indications for ULT."""
        return ", ".join(self.strong_indications_list_of_strs)

    def update_aid(self, qs: Union["Ult", "User", None] = None) -> "Ult":
        """Updates Ult indication field.

        Args:
            qs (Ult, User, optional): Ult or User object. Defaults to None.
            Should have related medhistorys prefetched as medhistorys_qs.

        Returns:
            Ult: Ult object."""
        if qs is None:
            if self.user:
                qs = Pseudopatient.objects.ultaid_qs().filter(username=self.user.username)
            else:
                qs = Ult.related_objects.filter(pk=self.pk)
        decisionaid = UltDecisionAid(qs=qs)
        return decisionaid._update()  # pylint: disable=W0212 # type: ignore
