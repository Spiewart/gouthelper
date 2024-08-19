from typing import TYPE_CHECKING, Literal, Union

from django.conf import settings  # type: ignore
from django.core.validators import MaxValueValidator, MinValueValidator  # type: ignore
from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.html import mark_safe  # type: ignore
from django.utils.text import format_lazy  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..medhistorydetails.choices import Stages
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.helpers import medhistory_attr, medhistorys_get_ckd_3_or_higher
from ..medhistorys.lists import ULT_MEDHISTORYS
from ..rules import add_object, change_object, delete_object, view_object
from ..utils.helpers import (
    add_indicator_badge_and_samepage_link,
    link_to_2020_ACR_guidelines,
    wrap_in_samepage_links_anchor,
)
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
                        ultaid__isnull=True,
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
    ultaid = models.OneToOneField(
        "ultaids.UltAid",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    history = HistoricalRecords()

    objects = models.Manager()
    related_objects = UltManager()
    related_models: list[Literal["ultaid"]] = ["ultaid"]
    req_otos: list[None] = []
    decision_aid_service = UltDecisionAid

    def __str__(self):
        return f"Ult: {self.get_indication_display()}"

    @classmethod
    def aid_medhistorys(cls) -> list[MedHistoryTypes]:
        return ULT_MEDHISTORYS

    def ckd_interp(self, samepage_links: bool = True) -> str:
        ckd_interp_str = super().ckd_interp()

        ckd_interp_str += "<br> <br> CKD by itself is not an indication for ULT. However, \
patients who have their first gout flare and have CKD stage III or higher are \
conditionally recommended to start ULT, albeit with a very low certainty of evidence. "
        if self.has_conditional_indication_for_ckd3_or_higher_only:
            subject_the, pos, gender_pos = self.get_str_attrs("subject_the", "pos", "gender_pos")
            ckd_interp_str += f" <strong>Because {subject_the} {pos} CKD stage III or higher, \
ULT is conditionally recommended for {gender_pos}.</strong>"
        elif self.has_multiple_conditional_indications_for_ult:
            Subject_the, pos, gender_pos = self.get_str_attrs("Subject_the", "pos", "gender_pos")
            if self.ckd3:
                ckd_interp_str += f" <strong>{Subject_the} {pos} multiple conditional \
indications for ULT, including {self.ckddetail.explanation if self.ckddetail else 'CKD'}\
.</strong>"
            else:
                ckd_interp_str += f" {Subject_the} {pos} multiple conditional \
indications for ULT ({self.get_conditional_indications_str(samepage_links=samepage_links)}), but not CKD stage III \
or higher in the setting of {gender_pos} first flare."
        elif self.strong_indication:
            Subject_the, pos, gender_subject = self.get_str_attrs("Subject_the", "pos", "gender_subject")
            ckd_interp_str += f" <strong>{Subject_the} {pos} a strong indication \
for ULT ({self.get_strong_indications_strs_with_links(samepage_links=samepage_links)}), making CKD irrelevant for \
the determination of whether {gender_subject} should be on ULT.</strong>"
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

    @property
    def ckd3_detail(self) -> str:
        return add_indicator_badge_and_samepage_link(
            self, "ckd3", self.ckddetail.explanation if self.ckddetail else "CKD"
        )

    @cached_property
    def conditional_indication(self) -> bool:
        return self.indication == Indications.CONDITIONAL

    @cached_property
    def firstflare_conditional_indications(self) -> list[str]:
        return [
            indication
            for indication in ["ckd3", "hyperuricemia", "uratestones"]
            if getattr(self, f"has_conditional_indication_for_{indication}")
        ]

    @cached_property
    def conditional_indications(
        self,
    ) -> list[str]:
        return self.firstflare_conditional_indications + (["multipleflares"] if self.multipleflares else [])

    @staticmethod
    def conditional_indications_str_dict(samepage_links: bool = True) -> dict:
        return {
            "ckd3": (
                wrap_in_samepage_links_anchor(
                    "ckd",
                    "CKD",
                )
                + " stage III or higher"
                if samepage_links
                else "CKD stage III or higher"
            ),
            "hyperuricemia": (
                wrap_in_samepage_links_anchor("hyperuricemia", "hyperuricemia") if samepage_links else "hyperuricemia"
            ),
            "uratestones": (
                wrap_in_samepage_links_anchor("uratestones", "uric acid kidney stones")
                if samepage_links
                else "uric acid kidney stones"
            ),
            "multipleflares": (
                (
                    wrap_in_samepage_links_anchor("multipleflares", "multiple flares")
                    if samepage_links
                    else "multiple flares"
                ),
                " but having one or less flare per year",
            ),
        }

    @staticmethod
    def get_indications_display_strs(
        indications: list[str],
        indications_str_dict: dict[str, str],
    ) -> list[str]:
        return [indications_str_dict[indication] for indication in indications]

    @staticmethod
    def indications_get_strs_with_links(
        indication_strs: list[str],
    ) -> str:
        if len(indication_strs) == 1:
            return indication_strs[0]
        else:
            joined_str = ", ".join(str(item) for item in indication_strs[:-1])
            if len(indication_strs) > 2:
                joined_str += ","
            joined_str += " and a history of " + indication_strs[-1]
            return mark_safe(joined_str)

    @classmethod
    def all_conditional_indications_str(cls) -> str:
        return cls.indications_get_strs_with_links(list(cls.conditional_indications_str_dict().values()))

    def get_conditional_indications_str(self, samepage_links: bool = True) -> str:
        if not self.conditional_indications or self.contraindicated:
            raise ValueError(
                "Conditional indications method should not be called if there are no conditional indications."
            )

        if self.firstflare_conditional_indications:
            conditional_indication_display_strs = self.get_indications_display_strs(
                self.firstflare_conditional_indications,
                self.conditional_indications_str_dict(samepage_links=samepage_links),
            )

            conditional_indications_str = format_lazy(
                """{} plus {}""",
                self.indications_get_strs_with_links(conditional_indication_display_strs),
                (
                    wrap_in_samepage_links_anchor("firstflare", "first gout flare")
                    if samepage_links
                    else "first gout flare"
                ),
            )

            if self.multipleflares:
                conditional_indications_str += f", as well as \
{self.conditional_indications_str_dict(samepage_links=samepage_links)['multipleflares']}"

        else:
            conditional_indications_str = self.conditional_indications_str_dict(samepage_links=samepage_links)[
                "multipleflares"
            ]

        return mark_safe(conditional_indications_str)

    @staticmethod
    def remove_indication_from_list(
        indications: list[str],
        indication_to_remove: str,
    ) -> list[str]:
        return [indication for indication in indications if indication != indication_to_remove]

    @classmethod
    def conditional_indications_str_remove_one_indication(
        cls,
        indications: list[str],
        indication_to_remove: str,
        samepage_links: bool = True,
    ) -> str:
        return cls.indications_str(
            cls.remove_indication_from_list(indications, indication_to_remove),
            cls.conditional_indications_str_dict(samepage_links=samepage_links),
        )

    @classmethod
    def strong_indications_str_remove_one_indication(
        cls,
        indications: list[str],
        indication_to_remove: str,
        samepage_links: bool = True,
    ) -> str:
        return cls.indications_str(
            cls.remove_indication_from_list(indications, indication_to_remove),
            cls.strong_indications_str_dict(samepage_links=samepage_links),
        )

    @cached_property
    def contraindicated(self) -> bool:
        return self.zero_flares_without_indication or self.one_flare_without_any_indication

    def contraindicated_interp(self) -> str:
        Subject_the, subject_the, gender_subject = self.get_str_attrs(
            "Subject_the",
            "subject_the",
            "gender_subject",
        )

        def _get_contraindicated_interp_str() -> str:
            if self.zero_flares_without_indication:
                return f" {Subject_the} has never had a gout flare, which is a contraindication for ULT in the \
absence of <a class='samepage-link' href='#erosions'>erosions</a> or \
<a class='samepage-link' href='#tophi'>tophi</a>."
            elif self.one_flare_without_any_indication:
                return f" {Subject_the} has only had one gout flare, which is a contraindication for ULT in the \
absence of a strong indication for ULT, such as <a class='samepage-link' href='#erosions'>erosions</a> or \
<a class='samepage-link' href='#tophi'>tophi</a>, or a conditional indication for ULT, such as \
{self.all_conditional_indications_str()}."
            else:
                return ""

        return mark_safe(
            f"<strong>ULT is not recommended for {subject_the},</strong> {gender_subject} does not have an indication \
for it.{_get_contraindicated_interp_str()}"
        )

    @property
    def erosions_detail(self) -> str:
        return add_indicator_badge_and_samepage_link(self, "erosions", "Erosions")

    def erosions_interp(self) -> str:
        subject_the, pos, gender_ref = self.get_str_attrs("subject_the", "pos", "gender_ref")
        erosions_interp_str = super().erosions_interp()
        erosions_interp_str += "<br> <br> Like <a class='samepage-link' href='#tophi'>tophi</a>, \
erosions are a sign of advanced gout and more severe disease. While they don't influence choice of \
ULT, they necessitate aggressive gout treatment and are a strong indication for ULT."
        if self.erosions:
            erosions_interp_str += f" <strong>Because {subject_the} {pos} gouty erosions, \
ULT is strongly recommended for {gender_ref}.</strong>"
        return mark_safe(erosions_interp_str)

    @cached_property
    def explanations(self) -> list[tuple[str, str, bool, str]]:
        """Returns a list of tuples containing information to display explanations in the UltDetail template."""
        return [
            ("ckd3", "Chronic Kidney Disease Stage III or Higher", self.ckd3, self.ckd_interp()),
            ("erosions", "Erosions", self.erosions, self.erosions_interp()),
            ("firstflare", "First Flare", self.firstflare, self.firstflare_interp()),
            ("frequentflares", "Frequent Flares", self.frequentflares or False, self.frequentflares_interp()),
            ("hyperuricemia", "Hyperuricemia", self.hyperuricemia, self.hyperuricemia_interp()),
            ("multipleflares", "Multiple Flares", self.multipleflares, self.multipleflares_interp()),
            ("noflares", "No Flares", self.noflares, self.noflares_interp()),
            ("tophi", "Tophi", self.tophi, self.tophi_interp()),
            ("uratestones", "Uric Acid Kidney Stones", self.uratestones, self.uratestones_interp()),
        ]

    @cached_property
    def firstflare(self) -> bool:
        """Method that returns True if a Ult indicates that the patient
        has only had a single gout flare and does not have any secondary
        medical conditions that would conditionally indicate ULT. A single gout flare
        in the absence of any additional conditions is a contraindication to ULT."""
        return self.num_flares == FlareNums.ONE

    @property
    def firstflare_detail(self) -> str:
        return add_indicator_badge_and_samepage_link(self, "firstflare", "First Flare")

    def firstflare_interp(self, samepage_links: bool = True) -> str:
        Subject_the, pos, gender_pos, gender_subject = self.get_str_attrs(
            "Subject_the", "pos", "gender_pos", "gender_subject"
        )

        explanation_str = "Conditional indications for ULT in the setting of an individual's first \
gout flare are: chronic kidney disease (<a class='samepage-link' href='#ckd'>CKD</a>) \
stage III or higher, <a class='samepage-link' href='#uratestones'>uric acid kidney stones</a>, \
or <a class='samepage-link' href='#hyperuricemia'>hyperuricemia</a>"

        def _get_pretext():
            return (
                "only "
                if self.num_flares == self.FlareNums.ONE
                else "not "
                if self.num_flares == self.FlareNums.ZERO
                else ""
            )

        def _get_flares_text():
            return (
                "a single gout flare"
                if self.num_flares == self.FlareNums.ONE
                else "two or more gout flares"
                if self.num_flares == self.FlareNums.TWOPLUS
                else "any gout flares"
            )

        def _get_firstflare_interp(samepage_links: bool = samepage_links) -> str:
            base_str = f"{Subject_the} {pos} {_get_pretext()}had {_get_flares_text()}"
            if self.num_flares == self.FlareNums.TWOPLUS:
                return (
                    base_str
                    + ", so conditional indications in the setting of the first flare \
are not applicable."
                )
            elif self.firstflare_plus:
                if self.strong_indication:
                    return (
                        base_str
                        + f" and {gender_subject} {pos} associated conditions \
({self.get_conditional_indications_str(samepage_links=samepage_links)}) that conditionally indicate ULT, but she also \
has a strong indication for ULT ({self.get_strong_indications_strs_with_links(samepage_links=samepage_links)}), \
making this irrelevant."
                    )
                else:
                    return (
                        base_str
                        + f" but {gender_subject} {pos} associated conditions \
({self.get_conditional_indications_str(samepage_links=samepage_links)}) that conditionally indicate ULT."
                    )
            elif self.firstflare:
                if self.strong_indication:
                    return (
                        base_str
                        + f", does not have any associated conditions conditionally indicating ULT, \
but has a strong indication ({self.get_strong_indications_strs_with_links(samepage_links=samepage_links)}) \
for ULT."
                    )
                elif self.conditional_indication:
                    return (
                        base_str
                        + f", does not have any associated conditions conditionally \
indicating ULT in the setting of {gender_pos} first flare, but has other conditional indications \
for ULT ({self.get_conditional_indications_str(samepage_links=samepage_links)})."
                    )
                else:
                    return (
                        base_str
                        + " and does not have any associated conditions conditionally \
indicating ULT."
                    )
            else:
                if self.strong_indication:
                    return (
                        base_str
                        + f", but does have a strong indication for ULT \
({self.get_strong_indications_strs_with_links(samepage_links=samepage_links)})."
                    )
                else:
                    return base_str + " and thus does not have an indication for ULT."

        return mark_safe(
            f"ULT is almost never indicated in patients with their first gout flare, though there are rare \
exceptions. <strong>{_get_firstflare_interp()}</strong> <br> <br> {explanation_str}"
        )

    @cached_property
    def firstflare_plus(self) -> bool:
        """Method that returns True if a Ult indicates that the patient
        has only had a single gout flare but does have a secondary
        medical conditions that conditionally indicates ULT."""
        return self.num_flares == FlareNums.ONE and (self.ckd3 or self.hyperuricemia or self.uratestones)

    @cached_property
    def frequentflares(self) -> bool:
        """Method that returns True if a Ult indicates the
        patient is having frequent gout flares (2 or more per year)."""
        return self.freq_flares and self.freq_flares == FlareFreqs.TWOORMORE

    @property
    def frequentflares_detail(self) -> str:
        return add_indicator_badge_and_samepage_link(self, "frequentflares", "Frequent Gout Flares")

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
{_get_frequent_flares_str()}ULT.</strong>"
        )

    def get_absolute_url(self):
        if self.user:
            return reverse("ults:pseudopatient-detail", kwargs={"pseudopatient": self.user.pk})
        else:
            return reverse("ults:detail", kwargs={"pk": self.pk})

    @cached_property
    def has_conditional_indication(self) -> bool:
        return self.multipleflares or self.has_conditional_indication_for_firstflare_and_comorbidity

    @cached_property
    def has_conditional_indication_for_firstflare_and_comorbidity(self) -> bool:
        return (
            self.num_flares == self.FlareNums.ONE
            and self.has_conditional_indication_for_ckd3
            and self.has_conditional_indication_for_hyperuricemia
            and self.has_conditional_indication_for_uratestones
        )

    @cached_property
    def has_conditional_indication_for_hyperuricemia(self) -> bool:
        return self.num_flares == self.FlareNums.ONE and self.hyperuricemia

    @cached_property
    def has_conditional_indication_for_hyperuricemia_only(self) -> bool:
        """Returns True if the Ult/Patient has a conditional indication for ULT due to hyperuricemia only."""
        return (
            self.conditional_indication
            and self.hyperuricemia
            and not (self.ckd3 or self.uratestones or self.multipleflares)
        )

    @cached_property
    def has_conditional_indication_for_ckd3(self) -> bool:
        return self.num_flares == self.FlareNums.ONE and self.ckd3

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
            and not (self.has_conditional_indication_for_firstflare_and_comorbidity)
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
    def has_conditional_indication_for_uratestones(self) -> bool:
        return self.num_flares == self.FlareNums.ONE and self.uratestones

    @cached_property
    def has_multiple_conditional_indications_for_ult(self) -> bool:
        """Returns True if the Ult/Patient has multiple conditional indications for ULT."""
        return self.conditional_indication and len(self.conditional_indications) > 1

    @cached_property
    def has_multiple_strong_indications_for_ult(self) -> bool:
        return self.strong_indication and len(self.strong_indications) > 1

    def hyperuricemia_interp(self, samepage_links: bool = True) -> str:
        Subject_the, pos, pos_neg, gender_pos, gender_subject = self.get_str_attrs(
            "Subject_the", "pos", "pos_neg", "gender_pos", "gender_subject"
        )

        def _get_indication_interp_str() -> str:
            return (
                f", and having had {gender_pos} first gout flare in this setting is {gender_pos} \
only conditional indication for ULT"
                if self.has_conditional_indication_for_hyperuricemia_only
                else (
                    (
                        format_lazy(
                            """, which is a conditional indication for ULT in the setting of {} \
first flare. However, {} also {} other conditional indications for ULT in the \
setting of {} first flare, including {}""",
                            gender_pos,
                            gender_subject,
                            pos,
                            gender_pos,
                            self.conditional_indications_str_remove_one_indication(
                                indications=self.conditional_indications,
                                indication_to_remove="hyperuricemia",
                                samepage_links=samepage_links,
                            ),
                        )
                    )
                    if (
                        self.has_multiple_conditional_indications_for_ult
                        and self.has_conditional_indication_for_hyperuricemia
                    )
                    else (
                        f", but has other conditional indications for ULT (\
{self.get_conditional_indications_str(samepage_links=samepage_links)})"
                    )
                    if self.conditional_indication
                    else (
                        (
                            f", but {gender_subject} {pos} a strong indication \
for ULT for other reasons ({self.get_strong_indications_strs_with_links(samepage_links=samepage_links)})"
                        )
                        if self.strong_indication
                        else f", but ULT is not recommended because {gender_subject} has \
never had a gout flare"
                    )
                )
            )

        return mark_safe(
            f"Hyperuricemia, defined as a serum urate level greater than 9 mg/dL, is NOT an indication for \
ULT by itself. In a patient who is having his or her first flare and would not otherwise have an indication \
for ULT, hyperuricemia is a conditional indication for ULT with a very low certainty of evidence. <br> <br> \
<strong> {Subject_the} {pos if self.hyperuricemia else pos_neg} hyperuricemia{_get_indication_interp_str()}\
</strong>."
        )

    @cached_property
    def indicated(self) -> bool:
        """Method that returns a bool indicating whether Ult is indicated."""
        if self.indication == Indications.INDICATED or self.indication == Indications.CONDITIONAL:
            return True
        return False

    def get_indication_interp(self, samepage_links: bool = True) -> str:
        Subject_the, Gender_subject, gender_subject, gender_ref = self.get_str_attrs(
            "Subject_the", "Gender_subject", "gender_subject", "gender_ref"
        )

        def _get_should_statement():
            return (
                "be on " if self.indicated else ("be considered for " if self.conditional_indication else "not be on ")
            )

        def _get_conditional_indication_str(samepage_links: bool = samepage_links) -> str:
            return format_lazy(
                """{} has {} <a href={}>conditional indication{}</a> for ULT: {}.""",
                Gender_subject,
                "multiple" if self.has_multiple_conditional_indications_for_ult else "a",
                reverse("ults:about") + "#conditional",
                "s" if self.has_multiple_conditional_indications_for_ult else "",
                self.get_conditional_indications_str(samepage_links=samepage_links),
            )

        def _get_no_indication_str(samepage_links: bool = samepage_links) -> str:
            if self.noflares:
                return format_lazy(
                    """{} has {}\
, which is a <a href={}>contraindication</a> for ULT.""",
                    gender_subject,
                    (
                        wrap_in_samepage_links_anchor("noflares", "never had a gout flare")
                        if samepage_links
                        else "never had a gout flare"
                    ),
                    reverse("ults:about") + "#notindicated",
                )
            elif self.one_flare_without_any_indication:
                return format_lazy(
                    """{} has only had {}, which is a <a href={}>contraindication</a> for ULT in the absence of other \
conditions that put {} at risk for future flares or other complications related \
to gout or elevated <a href={}>uric acid</a> levels.""",
                    gender_subject,
                    (
                        wrap_in_samepage_links_anchor("firstflare", "one gout flare")
                        if samepage_links
                        else "one gout flare"
                    ),
                    reverse("ults:about") + "#notindicated",
                    gender_ref,
                    reverse("labs:about-urate"),
                )

        def _get_strong_indication_str(samepage_links: bool = samepage_links) -> str:
            return format_lazy(
                """{} has {} <a href={}>strong indication</a>{} for ULT: {}.""",
                Gender_subject,
                "multiple" if self.has_multiple_strong_indications_for_ult else "a",
                reverse("ults:about") + "#strong",
                "s" if self.has_multiple_strong_indications_for_ult else "",
                self.get_strong_indications_strs_with_links(samepage_links=samepage_links),
            )

        def _get_indication_interp_str(samepage_links: bool = samepage_links) -> str:
            if self.strong_indication:
                return _get_strong_indication_str(samepage_links=samepage_links)
            elif self.conditional_indication:
                return _get_conditional_indication_str(samepage_links=samepage_links)
            else:
                return f"{Gender_subject} does not have an indication for ULT because {_get_no_indication_str()}"

        return mark_safe(
            format_lazy(
                """{} should {}<a href={}>ULT</a>. {}""",
                Subject_the,
                _get_should_statement(),
                reverse("treatments:about-ult"),
                _get_indication_interp_str(),
            )
        )

    @classmethod
    def indications_str(
        cls,
        indications: list[str],
        indications_str_dict: dict[str, str],
    ) -> str:
        return cls.indications_get_strs_with_links(
            cls.get_indications_display_strs(
                indications,
                indications_str_dict,
            )
        )

    @cached_property
    def multipleflares(self) -> bool:
        """Method that returns True if a Ult indicates the
        has only one flare per year but has a history of more than 1 gout flare,
        which is a conditional indication for ULT."""
        return self.freq_flares == FlareFreqs.ONEORLESS and self.num_flares == FlareNums.TWOPLUS

    @property
    def multipleflares_detail(self) -> str:
        return add_indicator_badge_and_samepage_link(self, "multipleflares", "Multiple flares")

    def multipleflares_interp(self, samepage_links: bool = True) -> str:
        Subject_the, pos, gender_pos, gender_subject = self.get_str_attrs(
            "Subject_the", "pos", "gender_pos", "gender_subject"
        )

        multiflares_str = f"Individuals who have had multiple gout flares in the past but are currently only having \
one flare per year are conditionally recommended to start ULT based on high moderate certainty of evidence per \
{link_to_2020_ACR_guidelines()}. <strong>{Subject_the} {pos}{' not' if not self.multipleflares else ''} had 1 \
or more gout flares in {gender_pos} lifetime</strong>"

        if self.multipleflares and self.strong_indication:
            multiflares_str += f", however {gender_subject} has other <u>strong indications</u>\
{self.get_strong_indications_strs_with_links(samepage_links=samepage_links)}"
        elif self.multipleflares and self.conditional_indication:
            if self.has_conditional_indication_for_multipleflares_only:
                multiflares_str += f" and as such it is the reason for {gender_pos} conditional \
ULT recommendation"
            else:
                conditional_indications_str = self.conditional_indications_str_remove_one_indication(
                    self.conditional_indications,
                    "multipleflares",
                )
                multiflares_str += f", which is one of the conditional indications {gender_subject} \
{pos} for ULT. {self.get_str_attrs('Gender_subject')} also has {conditional_indications_str}"
        multiflares_str += "."

        return mark_safe(multiflares_str)

    @cached_property
    def noflares(self) -> bool:
        """Method that returns True if a Ult indicates that the patient
        has never had a gout flare, which is a contraindication for ULT."""
        if self.num_flares == FlareNums.ZERO:
            return True
        return False

    @property
    def noflares_detail(self) -> str:
        return add_indicator_badge_and_samepage_link(self, "noflares", "No flares")

    def noflares_interp(self) -> str:
        (Subject_the,) = self.get_str_attrs("Subject_the")
        return mark_safe(
            f"<strong>{Subject_the} has {'never ' if self.noflares else ''}had a gout flare.</strong> \
ULT is contraindicated in individuals who have never had a gout flare, except if they have gouty erosions \
or tophi with no preceding flares, which is quite rare."
        )

    @cached_property
    def one_flare_without_conditional_indication(self) -> bool:
        return self.num_flares == FlareNums.ONE and not (self.ckd3 or self.hyperuricemia or self.uratestones)

    @cached_property
    def one_flare_without_any_indication(self) -> bool:
        return self.one_flare_without_conditional_indication and not self.erosions and not self.tophi

    @cached_property
    def strong_indication(self) -> bool:
        """Method that returns whether or not the Ult
        has a strong recommendation for ULT."""
        if self.indication == Indications.INDICATED:
            return True
        return False

    @cached_property
    def strong_indications(self) -> list[str]:
        """Returns a list of strong indications for ULT."""
        return [indication for indication in self.strong_indications_str_dict().keys() if getattr(self, indication)]

    @staticmethod
    def strong_indications_str_dict(samepage_links: bool = True) -> dict:
        return {
            "erosions": format_lazy(
                """gouty {}""",
                wrap_in_samepage_links_anchor("erosions", "erosions") if samepage_links else "erosions",
            ),
            "frequentflares": format_lazy(
                """{}""",
                (
                    wrap_in_samepage_links_anchor("frequentflares", "frequent flares")
                    if samepage_links
                    else "frequent flares"
                ),
            ),
            "tophi": format_lazy(
                """{}""", wrap_in_samepage_links_anchor("tophi", "tophi") if samepage_links else "tophi"
            ),
        }

    def get_strong_indications_strs_with_links(self, samepage_links: bool = True) -> str:
        if not self.strong_indication and self.strong_indications:
            raise ValueError("Strong indication method should not be called if there is no strong indication.")
        return self.indications_get_strs_with_links(
            self.get_indications_display_strs(
                self.strong_indications,
                self.strong_indications_str_dict(samepage_links=samepage_links),
            )
        )

    def uratestones_interp(self, samepage_links: bool = True) -> str:
        Subject_the, pos, pos_neg, gender_pos, gender_subject = self.get_str_attrs(
            "Subject_the", "pos", "pos_neg", "gender_pos", "gender_subject"
        )

        def _get_indication_interp_str() -> str:
            return (
                f", and having had {gender_pos} first gout flare in this setting is {gender_pos} \
only conditional indication for ULT."
                if self.has_conditional_indication_for_uratestones_only
                else (
                    (
                        f", which is a conditional indication for ULT in the setting of {gender_pos} \
first flare. However, {gender_subject} also {pos} other conditional indications for ULT in the \
setting of {gender_pos} first flare, including \
{self.conditional_indications_str_remove_one_indication(self.conditional_indications, 'uratestones')}"
                    )
                    if (
                        self.has_multiple_conditional_indications_for_ult
                        and self.has_conditional_indication_for_uratestones
                    )
                    else (
                        f", but has other conditional indications for ULT (\
{self.get_conditional_indications_str(samepage_links=samepage_links)})"
                    )
                    if self.conditional_indication
                    else (
                        (
                            f", but {gender_subject} {pos} a strong indication \
for ULT for other reasons ({self.get_strong_indications_strs_with_links(samepage_links=samepage_links)})"
                        )
                        if self.strong_indication
                        else f", but ULT is not recommended because {gender_subject} has \
never had a gout flare"
                    )
                )
            )

        return mark_safe(
            f"History of uric acid kidney stones is NOT an indication for \
ULT by itself. In a patient who is having his or her first flare and would not otherwise have an indication \
for ULT, history of urate stones is a conditional indication for ULT with a very low certainty of evidence. <br> <br> \
<strong> {Subject_the} {pos if self.uratestones else pos_neg} uric acid kidney stones{_get_indication_interp_str()}\
</strong>."
        )

    @cached_property
    def zero_flares_without_indication(self) -> bool:
        return self.num_flares == FlareNums.ZERO and not self.erosions and not self.tophi
