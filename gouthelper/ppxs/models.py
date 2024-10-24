from datetime import timedelta
from typing import TYPE_CHECKING, Literal

from django.conf import settings  # type: ignore
from django.core.validators import MaxValueValidator, MinValueValidator  # type: ignore
from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils import timezone  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.html import mark_safe  # type: ignore
from django.utils.text import format_lazy  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..goalurates.helpers import goalurates_get_object_goal_urate
from ..labs.helpers import labs_urate_within_90_days
from ..labs.models import Urate
from ..medhistorys.lists import PPX_MEDHISTORYS
from ..rules import add_object, change_object, delete_object, view_object
from ..ults.choices import Indications
from ..utils.models import GoutHelperAidModel, GoutHelperModel
from .helpers import ppxs_check_urate_at_goal_discrepant
from .managers import PpxManager
from .services import PpxDecisionAid

if TYPE_CHECKING:
    from ..goalurates.choices import GoalUrates
    from ..medhistorys.choices import MedHistoryTypes


class Ppx(
    RulesModelMixin,
    GoutHelperAidModel,
    GoutHelperModel,
    TimeStampedModel,
    metaclass=RulesModelBase,
):
    """Model to collate information for a patient and determine if he or she has
    an indication for gout flare prophylaxis."""

    Indications = Indications

    class Meta:
        rules_permissions = {
            "add": add_object,
            "change": change_object,
            "delete": delete_object,
            "view": view_object,
        }
        # Make a CheckConstraing for the user and ppxaid fields
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_user_xor_ppxaid",
                check=models.Q(user__isnull=False, ppxaid__isnull=True) | models.Q(user__isnull=True),
            ),
            models.CheckConstraint(
                check=models.Q(indication__gte=0) & models.Q(indication__lte=2),
                name="%(app_label)s_%(class)s_indication_gte_0_lte_2",
            ),
        ]

    indication = models.IntegerField(
        _("Indication"),
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        choices=Indications.choices,
        help_text="Does the patient have an indication for prophylaxis?",
        default=Indications.NOTINDICATED,
    )
    ppxaid = models.OneToOneField(
        "ppxaids.PpxAid",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    history = HistoricalRecords()

    objects = models.Manager()
    related_objects = PpxManager()
    related_models: list[Literal["ppxaid"]] = ["ppxaid"]
    req_otos: list[None] = []
    decision_aid_service = PpxDecisionAid

    @classmethod
    def aid_medhistorys(cls) -> list["MedHistoryTypes"]:
        return PPX_MEDHISTORYS

    @classmethod
    def aid_labs(cls) -> list[str]:
        return [Urate]

    @cached_property
    def at_goal(self) -> bool:
        return self.goutdetail.at_goal

    @cached_property
    def at_goal_long_term(self) -> bool:
        return self.goutdetail.at_goal_long_term

    def at_goal_long_term_interp(self) -> str:
        """Method that returns an explanation of the PPx's at_goal_long_term status."""
        (Subject_the, pos) = self.get_str_attrs("Subject_the", "pos")
        at_goal_str = format_lazy(
            """<strong>{} {} {}been at goal uric acid for six months or longer</strong>. \
For patients who are on flare prophylaxis, prophylaxis is continued until they \
are <a target='_next' href={}>at goal</a> uric acid for 3-6 months, per ACR guidelines. GoutHelper \
defaults to six months.
            """,
            Subject_the,
            pos,
            "" if self.at_goal_long_term else "not ",
            (
                reverse("goalurates:pseudopatient-detail", kwargs={"pseudopatient": self.user.pk})
                if self.user
                else reverse("goalurates:create")
            ),
        )
        return mark_safe(at_goal_str)

    @cached_property
    def at_goal_long_term_urates_discrepant(self) -> bool:
        """Returns True if the GoutDetail at_goal_long_term field and the Ppx/User's urates are discrepant."""
        return (
            self.at_goal_long_term
            and not self.urates_at_goal_long_term
            or not self.at_goal_long_term
            and self.urates_at_goal_long_term
        )

    def at_goal_interp(self) -> str:
        """Method that returns an explanation of the PPx's at_goal status."""
        (Subject_the_pos,) = self.get_str_attrs("Subject_the_pos")
        at_goal_str = format_lazy(
            """<strong>{} uric acid is {}at goal</strong>. \
For patients who are on flare prophylaxis, prophylaxis is continued until they \
are <a target='_next' href={}>at goal</a> uric acid for 3-6 months, per ACR guidelines. GoutHelper \
defaults to six months.
            """,
            Subject_the_pos,
            "" if self.at_goal else "not ",
            (
                reverse("goalurates:pseudopatient-detail", kwargs={"pseudopatient": self.user.pk})
                if self.user
                else reverse("goalurates:create")
            ),
        )
        return mark_safe(at_goal_str)

    @cached_property
    def at_goal_urates_discrepant(self) -> bool:
        """Returns True if the GoutDetail at_goal field and the Ppx/User's urates are discrepant."""
        return self.at_goal and not self.urates_at_goal or not self.at_goal and self.urates_at_goal

    @property
    def clarify_ult_strategy_recommendation(self) -> dict[str, str]:
        """Returns a heading and explanation for a Ppx/Patient that needs clarification on its ULT
        strategy in the context of a Ppx object. This would be the case with a Ppx/Patient who is not
        on or starting ULT but is inquiring about flare prophylaxis, which is misguided."""
        (Subject_the,) = self.get_str_attrs("Subject_the")
        return {
            "Clarify ULT Strategy": mark_safe(
                format_lazy(
                    """{} is neither starting nor on \
urate-lowering therapy (<a target='_next' href={}>ULT</a>). Long-term flare prevention with anti-inflammatories \
is not recommended. Instead, ULT should be utilized.""",
                    Subject_the,
                    (
                        reverse("ults:pseudopatient-detail", kwargs={"pseudopatient": self.user.pk})
                        if self.user
                        else reverse("ults:create")
                    ),
                )
            )
        }

    @cached_property
    def conditional_indication(self) -> bool:
        """Method that returns whether or not the Ult
        has a conditional recommendation for ULT."""
        return self.indication == Indications.CONDITIONAL

    @property
    def consider_other_causes_of_symptoms_recommendation(self) -> dict[str, str]:
        """Returns a dictionary of a heading and explanation describing that a Ppx/Patient should consider other causes
        of the symptoms that prompted the flaring field to be True."""
        Subject_the, tobe, gender_pos = self.get_str_attrs("Subject_the", "tobe", "gender_pos")
        return {
            "Symptoms Not Gout vs Rheumatology Referral": f"{Subject_the} {tobe} having symptoms attributed to gout, \
however {gender_pos} uric acid has been at goal for six months or longer AND has been recently checked. This makes \
gout as a cause of the symptoms unlikely and other diagnoses should be considered."
        }

    @property
    def consider_starting_ppx_recommendation(self):
        """Method that returns a dictionary recommending a conditional indication for flare
        prophylaxis for a Ppx."""

        def get_prefix_str():
            return (
                f", {tobe} flaring, and {tobe} not at goal uric acid"
                if not self.at_goal and self.flaring
                else " and is hyperuricemic"
                if not self.at_goal
                else " and is flaring"
                if self.flaring
                else ""
            )

        Subject_the, tobe, gender_pos, gender_subject = self.get_str_attrs(
            "Subject_the", "tobe", "gender_pos", "gender_subject"
        )

        return {
            "Consider Starting Prophylaxis": mark_safe(
                format_lazy(
                    """{} {} on long-term urate-lowering therapy (ULT){}. \
This suggests that {} needs adjustment to {} ULT and that {} may benefit from flare prophylaxis until {} \
has been at goal uric acid for six months or longer.""",
                    Subject_the,
                    tobe,
                    get_prefix_str(),
                    gender_subject,
                    gender_pos,
                    gender_subject,
                    gender_subject,
                )
            )
        }

    @property
    def continue_prophylaxis_recommendation(self) -> dict[str, str]:
        """Method that returns a dictionary recommending a Ppx continue prophylaxis. Raises
        a ValueError if the Ppx is not at goal or is not on prophylaxis."""
        if self.at_goal_long_term:
            raise ValueError("Calling continue_prophylaxis_recommendation on a Ppx that is at goal.")
        if not self.on_ppx:
            raise ValueError("Calling continue_prophylaxis_recommendation on a Ppx that is not on prophylaxis.")
        else:
            (Subject_the_pos,) = self.get_str_attrs("Subject_the_pos")
            return {
                "Continue Prophylaxis": f"{Subject_the_pos} uric acid \
{'was at goal the last time it was checked, however it ' if not self.at_goal_long_term else ''}has \
not been at goal for six months or longer. \
Continued flare prophylaxis is recommended."
            }

    @cached_property
    def dated_urates(self) -> list[Urate]:
        return list(super().dated_urates)

    @cached_property
    def explanations(self) -> list[tuple[str, str, bool, str]]:
        """Returns a list of tuples containing information to display explanations in the PpxDetail template."""
        return [
            ("at_goal", "At Goal Six Months or Longer", self.at_goal_long_term, self.at_goal_long_term_interp()),
            ("flaring", "Flaring", self.flaring, self.flaring_interp()),
            ("gout", "Gout", self.gout, self.gout_interp()),
            ("hyperuricemic", "Hyperuricemic", not self.at_goal, self.at_goal_interp()),
            ("on_ppx", "On Prophylaxis", self.on_ppx, self.on_ppx_interp()),
            ("on_ult", "On Urate-Lowering Therapy", self.on_ult, self.on_ult_interp()),
            ("starting_ult", "Starting Urate-Lowering Therapy", self.starting_ult, self.starting_ult_interp()),
        ]

    @cached_property
    def flaring(self) -> bool | None:
        """Method that returns Gout MedHistory object's GoutDetail object's flaring
        attribute."""
        return self.goutdetail.flaring if self.goutdetail else None  # pylint: disable=W0125, E1101

    def get_absolute_url(self):
        if self.user:
            return reverse("ppxs:pseudopatient-detail", kwargs={"pseudopatient": self.user.pk})
        else:
            return reverse("ppxs:detail", kwargs={"pk": self.pk})

    @cached_property
    def goal_urate(self) -> "GoalUrates":
        """Fetches the Ppx objects associated GoalUrate.goal_urate if it exists, otherwise
        returns the GoutHelper default GoalUrates.SIX enum object"""
        return goalurates_get_object_goal_urate(self)

    @property
    def hyperuricemic(self) -> bool | None:
        """Method that returns Gout MedHistory object's GoutDetail object indicates hyperuricemia."""
        return self.goutdetail.at_goal is not None and self.goutdetail.at_goal is False  # pylint: disable=W0125, E1101

    @cached_property
    def indicated(self) -> bool:
        """Method that returns a bool indicating whether Ult is indicated."""
        return self.indication == Indications.INDICATED or self.indication == Indications.CONDITIONAL

    def flaring_interp(self) -> str:
        """Returns HTML-formatted str explaining the Ppx flaring attribute."""
        Subject_the, tobe, tobe_neg, subject_the = self.get_str_attrs("Subject_the", "tobe", "tobe_neg", "subject_the")
        if self.flaring is not None:
            prefix_str = f"<strong>{Subject_the} {tobe if self.flaring else tobe_neg} having symptoms attributed \
to gout flares.</strong> "
        else:
            prefix_str = f"<strong>It is not known if {subject_the} is having symptoms attributed to gout flares. \
This should be clarified prior to thinking about flare prophylaxis.</strong>"
        return mark_safe(
            f"{prefix_str} Symptoms are NOT an indication for flare prophylaxis per ACR guidelines. However, \
GoutHelper does use them in cases where a patient has been on urate-lowering therapy (ULT) long-term and \
is hyperuricemic, putting him or her at risk of gout flares. In these cases, if the patient is having gout \
flares, it suggests that he or she would benefit from flare prophylaxis while his or her ULT is being \
adjusted. This is {'' if self.on_ult and not self.starting_ult and self.flaring else 'not '} the case \
for {subject_the}."
        )

    def gout_interp(self) -> str:
        """Returns HTML-formatted str explaining the gout attribute for the Ppx."""
        Subject_the, gender_pos, gender_subject, tobe = self.get_str_attrs(
            "Subject_the", "gender_pos", "gender_subject", "tobe"
        )
        return mark_safe(
            format_lazy(
                """<strong>{} has a history of gout</strong>, and as such prophylaxis could be \
indicated depending on {} other factors, such as whether or not {} {} on urate-lowering \
therapy (<a href={}>ULT</a>) or having gout flares, as well as trends in {} serum uric acid. \
<br> <br> Flare prophylaxis is not indicated for individuals who have never had gout.""",
                Subject_the,
                gender_pos,
                gender_subject,
                tobe,
                reverse("treatments:about-ult"),
                gender_pos,
            )
        )

    @cached_property
    def has_urates(self) -> bool:
        """Returns True if the Ppx or Patient has urates, else False."""
        if self.user:
            return self.user.urates_qs if hasattr(self.user, "urates_qs") else self.user.urate_set.exists()
        else:
            return self.urates_qs if hasattr(self, "urates_qs") else self.urate_set.exists()

    def hyperuricemic_interp(self) -> str:
        """Returns HTML-formatted str explaining the hyperuricemic attribute for the Ppx."""
        Subject_the, subject_the, tobe, tobe_neg = self.get_str_attrs("Subject_the", "subject_the", "tobe", "tobe_neg")
        if self.at_goal is not None:
            prefix_str = f"<strong>{Subject_the} {tobe_neg if self.at_goal else tobe} hyperuricemic.</strong> "
        else:
            prefix_str = f"<strong>It is not known if {subject_the} is hyperuricemic. This should be clarified \
prior to thinking about flare prophylaxis.</strong>"
        return mark_safe(
            f"{prefix_str} Hyperuricemia is NOT an indication for flare prophylaxis. GoutHelper only uses it \
when considering whether an individual on long-term urate-lowering therapy could be at risk for having gout \
flares and thus might benefit from prophylaxis while his or her ULT is adjusted."
        )

    @property
    def inquire_about_flares_recommendation(self) -> dict[str, str]:
        """Returns a dictionary of a heading and explanation for a Ppx/Patient that should inquire about flares."""
        subject_the, gender_subject = self.get_str_attrs("subject_the", "gender_subject")
        return {
            "Inquire about Flares": mark_safe(
                format_lazy(
                    """It is not known if {} is experiencing symptoms that could \
be due to gout flares. Given {} is on long-term urate-lowering therapy \
(<a href={}>ULT</a>), it's prudent to periodically inquire about whether nor \
not {} is experiencing symptoms that could be due to gout and require ULT adjustment.""",
                    subject_the,
                    subject_the,
                    reverse("treatments:about-ult"),
                    gender_subject,
                )
            )
        }

    @cached_property
    def last_urate_within_last_30_days_not_at_goal(self) -> bool:
        """Returns True if the last urate was within the last 30 days and not at goal, False if not."""
        return self.urates_at_goal_within_last_month

    @property
    def not_on_or_starting_ult(self) -> bool:
        return not self.on_ult and not self.starting_ult

    @property
    def not_start_ppx_recommendation(self) -> dict[str, str]:
        """Returns a dictionary of a heading and explanation recommending that a Ppx/Patient not start flare
        prophylaxis."""
        (Subject_the,) = self.get_str_attrs("Subject_the")
        return {"Prophylaxis Not Indicated": f"{Subject_the} does not have an indication for flare prophylaxis."}

    def on_ppx_interp(self) -> str:
        """Returns HTML-formatted str explaining the on_ppx attribute for the Ppx."""
        Subject_the, tobe, tobe_neg = self.get_str_attrs("Subject_the", "tobe", "tobe_neg")
        on_ppx_str = f"<strong>{Subject_the} {tobe if self.on_ppx else tobe_neg} taking flare prophylaxis treatment. \
It is {self.get_indication_display().lower()}</strong>."

        on_ppx_str += " ACR recommends prophylaxis for patients starting urate-lowering therapy for 3-6 months after \
they reach goal uric acid. GoutHelper also recommends prophylaxis for individuals who are on stable long-term doses \
of ULT but who need their ULT dose adjusted due to recurrent gout flares or hyperuricemia."
        return mark_safe(on_ppx_str)

    @cached_property
    def on_ppx(self) -> bool:
        """Method that returns Gout MedHistory object's GoutDetail object's on_ppx
        attribute."""
        return self.goutdetail.on_ppx if self.goutdetail else False  # pylint: disable=W0125, E1101

    @cached_property
    def on_ult(self) -> bool:
        """Method that returns Gout MedHistory object's GoutDetail object's on_ult
        attribute."""
        return self.goutdetail.on_ult if self.goutdetail else False  # pylint: disable=W0125, E1101

    def on_ult_interp(self) -> str:
        """Returns HTML-formatted str explaining the on_ult field for the Ppx's GoutDetail."""
        Subject_the, tobe, tobe_neg, subject_the_pos = self.get_str_attrs(
            "Subject_the", "tobe", "tobe_neg", "subject_the_pos"
        )
        ult_status_str = f"<strong>{Subject_the} {tobe if self.on_ult else tobe_neg} on urate-lowering \
therapy</strong>"
        if self.starting_ult:
            ult_status_str += f" and is still in the initial 'titration' phase where the dose is being adjusted \
to reach {subject_the_pos} goal uric acid. This is the phase when ACR recommends flare prophylaxis and it \
lasts until the patient has been at goal uric acid six months or longer."
        elif self.on_ult:
            ult_status_str += " and has been on a stable long-term dose. The only potential indications \
for prophylaxis during this stage of treatment are for individuals who are having gout flares or who have \
again become hyperuricemic."
        else:
            ult_status_str += ". Gout flare prophylaxis is not indicated for individuals who are not on or \
starting ULT."
        return mark_safe(ult_status_str)

    @cached_property
    def recent_urate(self) -> bool:
        """Method that returns True if the patient has had his or her uric acid checked
        in the last 3 months, False if not."""
        if hasattr(self, "urates_qs"):
            return labs_urate_within_90_days(
                urates=self.dated_urates,
                sorted_by_date=True,
            )
        else:
            return labs_urate_within_90_days(
                urates=self.dated_urates,
                sorted_by_date=True,
            )

    def recommendations(self, samepage_links: bool = True) -> None:
        """Method that interprets the Ppx's information and returns a dictionary of
        recommendations for display in templates."""

        def update_treatment_recommendation(rec_dict: dict):
            if self.should_start_ppx:
                rec_dict.update(self.start_ppx_recommendation)
            elif self.should_continue_ppx:
                rec_dict.update(self.continue_prophylaxis_recommendation)
            elif self.should_consider_starting_ppx:
                rec_dict.update(self.consider_starting_ppx_recommendation)
            elif self.should_stop_ppx:
                rec_dict.update(self.stop_ppx_recommendation)
            elif self.should_not_start_ppx:
                rec_dict.update(self.not_start_ppx_recommendation)
            else:
                raise ValueError("Ppx could not find a treatment recommendation to update.")

        def update_urate_check_recommendation(rec_dict: dict):
            if self.recent_urate:
                rec_dict.update(self.urate_check_recent_urate_recommendation)
            elif self.semi_recent_urate:
                rec_dict.update(self.urate_check_semi_recent_urate_recommendation)
            else:
                rec_dict.update(self.urate_check_no_recent_urate_recommendation)

        rec_dict = {}

        if not self.should_consider_other_causes_of_symptoms:
            update_treatment_recommendation(rec_dict)
        else:
            rec_dict.update(self.consider_other_causes_of_symptoms_recommendation)

        if self.should_check_urate:
            update_urate_check_recommendation(rec_dict)

        if self.should_clarify_ult_strategy:
            rec_dict.update(self.clarify_ult_strategy_recommendation)

        if self.should_inquire_about_flares:
            rec_dict.update(self.inquire_about_flares_recommendation)

        if self.should_update_urates:
            rec_dict.update(self.update_urates_recommendation)

        return rec_dict

    @property
    def should_show_ppxaid(self) -> bool:
        return self.should_start_ppx or self.should_continue_ppx or self.should_consider_starting_ppx

    @cached_property
    def semi_recent_urate(self) -> bool:
        """Method that returns True if the patient has had his or her uric acid checked
        in the last 6 months, False if not."""
        return (
            True
            if next(
                iter(
                    [
                        urate
                        for urate in self.dated_urates
                        if urate.date_drawn and urate.date_drawn > timezone.now() - timedelta(days=180)
                    ]
                ),
                None,
            )
            else False
        )

    @cached_property
    def should_check_urate(self) -> bool:
        """Returns True if a Ppx/Patient should check uric acid."""
        return (
            self.should_check_uric_acid_to_assess_need_for_ppx
            or self.should_consider_other_causes_of_symptoms
            or self.at_goal is None
        )

    @cached_property
    def should_check_uric_acid_to_assess_need_for_ppx(self) -> bool:
        """Returns a boolean indicating whether or not the Ppx/Patient should have a uric acid to evaluate whether \
        ongoing prophylaxis is required."""
        return self.on_ppx and not self.recent_urate

    @cached_property
    def should_clarify_ult_strategy(self) -> bool:
        """Returns bool indicating whether or not a Ppx/Patient needs clarification on ULT strategy. This is for
        Ppx/Patients that are not on or starting ULT."""
        return self.not_on_or_starting_ult

    @cached_property
    def should_consider_other_causes_of_symptoms(self) -> bool:
        """Returns True if a Ppx/Patient should consider other causes of their symptoms or seek expert
        consultation with a rheumatologist."""
        return self.at_goal_long_term and self.recent_urate and self.flaring

    @cached_property
    def should_continue_ppx(self) -> bool:
        """Returns True if a Ppx/Patient should continue prophylaxis."""
        return self.on_ppx and not self.at_goal_long_term and not self.should_stop_ppx

    @cached_property
    def should_continue_ppx_recommendation(self) -> dict[str, str]:
        """Method that returns a dictionary recommending that prophylaxis be continued for a Ppx."""
        (Subject_the,) = self.get_str_attrs("Subject_the")
        return {
            "Continue Prophylaxis": f"{Subject_the} is on flare prophylaxis but has not been at goal uric acid \
for six months or longer and thus is still at risk of flares and will benefit from ongoing prophylaxis against them."
        }

    @cached_property
    def should_consider_starting_ppx(self) -> bool:
        """Returns True if a Ppx/Patient should consider starting prophylaxis."""
        return (
            self.on_ult
            and not self.starting_ult
            and not self.on_ppx
            and (not self.at_goal or self.flaring)
            and not (self.at_goal_long_term and self.recent_urate)
        )

    @property
    def should_consider_starting_ppx_recommendation(self) -> dict[str, str]:
        """Returns a dictionary recommending a Ppx consider starting prophylaxis."""
        Subject_the_pos, subject_the, gender_pos, gender_ref = self.get_str_attrs(
            "Subject_the_pos", "subject_the", "gender_pos", "gender_ref"
        )
        consider_starting_ppx_str = f"{Subject_the_pos} is on long-term urate-lowering therapy (ULT), but"
        if not self.at_goal and self.flaring:
            consider_starting_ppx_str += f" {subject_the} is hyperuricemic and flaring,"
        elif not self.at_goal:
            consider_starting_ppx_str += f" {subject_the} is hyperuricemic,"
        else:
            consider_starting_ppx_str += f" {subject_the} is flaring,"
        consider_starting_ppx_str += f" and has not been at goal uric acid six months or longer with a recently \
checked uric acid. This suggests that {subject_the} needs adjustment to {gender_pos} ULT and that {gender_ref} \
may benefit from flare prophylaxis in the interim."
        return {"Consider Starting Prophylaxis": consider_starting_ppx_str}

    @property
    def should_inquire_about_flares(self) -> bool:
        """Returns True if a Ppx/Patient should inquire about flares. This is in the event that
        the Ppx/Patient are on ULT but are not starting it."""
        return self.flaring is None and self.on_ult and not self.starting_ult

    @cached_property
    def should_not_start_ppx(self) -> bool:
        """Returns True if a Ppx/Patient should NOT start prophylaxis."""
        return (
            not self.should_start_ppx
            and not self.should_consider_starting_ppx
            and not self.should_continue_ppx
            and not self.should_stop_ppx
        )

    @cached_property
    def should_start_ppx(self) -> bool:
        """Returns True if a Ppx/Patient should start prophylaxis."""
        return self.starting_ult and not self.on_ppx

    @property
    def start_ppx_recommendation(self) -> dict[str, str]:
        """Method that returns a dictionary recommending a Ppx start prophylaxis."""
        Subject_the, subject_the = self.get_str_attrs("Subject_the", "subject_the")
        return {
            "Start Prophylaxis": mark_safe(
                format_lazy(
                    """{} is starting urate-lowering therapy (<a href={}>ULT</a>) and ACR guidelines \
recommend starting flare <a href={}>prophylaxis</a> for all patients starting ULT. Prophylaxis should be continued \
until {} has been at goal uric acid ({}) or lower for 6 months.""",
                    Subject_the,
                    reverse("treatments:about-ult"),
                    reverse("treatments:about-ppx"),
                    subject_the,
                    self.goalurate_get_display,
                )
            )
        }

    @cached_property
    def should_stop_ppx(self) -> bool:
        """Returns True if a Ppx/Patient should stop prophylaxis."""
        return self.on_ppx and (
            (self.at_goal_long_term and ((not self.flaring and self.at_goal) or (self.flaring and self.recent_urate)))
            or self.not_on_or_starting_ult
        )

    @cached_property
    def should_update_urates(self) -> bool:
        """Returns True if a Ppx/Patient should update its urates."""
        return self.at_goal_urates_discrepant or self.at_goal_long_term_urates_discrepant

    def starting_ult_interp(self) -> str:
        """Returns HTML-formatted str explaining the starting_ult field for the Ppx."""
        Subject_the, tobe, tobe_neg = self.get_str_attrs("Subject_the", "tobe", "tobe_neg")
        starting_ult_str = f"<strong>{Subject_the} {tobe if self.starting_ult else tobe_neg} \
starting urate-lowering therapy (ULT)</strong>. This {'is' if self.starting_ult else 'would be'} \
the primary indication for flare prophylaxis per ACR guidelines. The risk of gout flares is \
actually higher during the in initiation phase of ULT before the treatments have eliminated \
uric acid stores from a patient's body."
        return mark_safe(starting_ult_str)

    @property
    def stop_ppx_recommendation(self) -> dict[str, str]:
        if self.not_on_or_starting_ult:
            (Subject_the,) = self.get_str_attrs("Subject_the")
            return {
                "Stop Prophylaxis": mark_safe(
                    format_lazy(
                        """{} is on flare <a href={} target='_blank'>prophylaxis</a>\
    but is not on or starting urate-lowering therapy (<a href={} target='_blank'>ULT</a>). This is not recommended. \
    ULT should be utilized for long-term gout management. GoutHelper recommends stopping prophylaxis.""",
                        Subject_the,
                        reverse("treatments:about-ppx"),
                        reverse("treatments:about-ult"),
                    )
                )
            }
        else:
            Subject_the_pos, subject_the, gender_subject = self.get_str_attrs(
                "Subject_the_pos", "subject_the", "gender_subject"
            )
            if self.recent_urate:
                should_stop_ppx_str = f"{Subject_the_pos} uric acid is at goal, has been so for 6 months or longer, \
    and has been recently checked."
            else:
                should_stop_ppx_str = f"{Subject_the_pos} uric acid is at goal, has been so for 6 months or longer, \
and {gender_subject} is not having any symptoms of gout."
            should_stop_ppx_str += f" ACR recommends continuing prophylaxis for six months after achieving and \
sustaining goal uric acid. GoutHelper defaults to 6 months, so {subject_the} doesn't need it any longer."
            return {"Stop Prophylaxis": should_stop_ppx_str}

    def __str__(self):
        return f"Ppx: {self.get_indication_display()}"

    @property
    def update_urates_recommendation(self) -> dict[str, str]:
        """Returns a dict of a recommendation."""
        Subject_the_pos, gender_pos, gender_subject, pos, tobe, tobe_past, pos_neg = self.get_str_attrs(
            "Subject_the_pos",
            "gender_pos",
            "gender_subject",
            "pos",
            "tobe",
            "tobe_past",
            "pos_neg",
        )
        at_goal_str = f"{Subject_the_pos} uric acid is reported as {'' if self.at_goal else 'not '}at \
goal the last time it was checked and that {gender_subject} {pos} {'' if self.at_goal_long_term else 'not '}\
been at goal uric acid for six months or longer, but "
        if self.dated_urates:
            at_goal_str += f"{gender_pos} reported uric acids indicate "
            if self.at_goal_urates_discrepant:
                at_goal_str += f"{gender_subject} {tobe} {'not ' if self.at_goal else ''} \
at goal"
            if self.at_goal_long_term_urates_discrepant:
                if self.at_goal_urates_discrepant:
                    at_goal_str += " and "
                at_goal_str += f"{gender_subject} {pos} {'not ' if self.at_goal_long_term else ''} been at goal uric \
acid for six months or longer"
        else:
            at_goal_str += f"{gender_subject} {pos_neg} have any uric acids reported"
        at_goal_str += f". The uric acids should be updated to reflect {gender_pos} most recent values."
        return {"Update Uric Acids": at_goal_str}

    @property
    def urate_check_recent_urate_recommendation(self) -> dict[str, str]:
        """Returns a dict of a heading and explanation for a Ppx/Patient that needs to have a uric acid check
        despite having had one recently. This is typically for the circumstance that a patient is having symptoms but
        his or her uric acid has been recently checked and has been at goal for 6 months or longer, at which point
        gout would be very unlikely."""
        subject_the, gender_pos, gender_subject, tobe = self.get_str_attrs(
            "subject_the", "gender_pos", "gender_subject", "tobe"
        )
        urate_check_str = f"Even though {subject_the} has had {gender_pos} \
uric acid checked recently and it was at goal, because {gender_subject} {tobe} still having symptoms attributed \
to gout flares, it is worth checking a uric acid because it sometimes drops during flares, confusing patients \
and providers. If the serum uric acid is elevated {gender_subject} will need ULT \
{'adjustment' if self.on_ult else 'initiation'} and will benefit from ongoing prophylaxis against flares."
        return {"Check Uric Acid": urate_check_str}

    @property
    def urate_check_semi_recent_urate_recommendation(self) -> dict[str, str]:
        """Returns a dict of a heading and explanation for a Ppx/Patient that should have a uric acid checked because
        it has been some time (semi-recent = >3 <6 months since they had one and are undergoing gout treatment
        requiring periodic lab monitoring or they are having symptoms of gout."""

        def create_prefix_str(Subject_the: str, tobe) -> str:
            return f"{Subject_the} {' ' + tobe + ' also' if self.flaring else ''}"

        subject_the, gender_pos, gender_subject, tobe, Subject_the = self.get_str_attrs(
            "subject_the",
            "gender_pos",
            "gender_subject",
            "tobe",
            "Subject_the",
        )
        if self.flaring:
            urate_check_rec_str = f"Even though {subject_the} has had {gender_pos} \
uric acid checked semi-recently and it was at goal, because {gender_subject} {tobe} still having symptoms attributed \
to gout flares, {gender_subject} should have {gender_pos} uric acid checked. Serum uric acid can fluctuate due to \
diet and lifestyle changes and it can drop during flares, confusing patients and providers. If the serum uric acid is \
elevated {gender_subject} will need ULT {'adjustment' if self.on_ult else 'initiation'} \
and will benefit from ongoing prophylaxis against flares."
        if self.should_check_uric_acid_to_assess_need_for_ppx:
            next_urate_check_rec_str = f"{create_prefix_str(Subject_the, tobe)} \
on flare prophylaxis and has not had {gender_pos} serum uric acid checked recently. Ongoing monitoring of the uric \
acid is essential for determining whether or not {gender_subject} still needs prophylaxis, which is generally \
continued until the uric acid has been at goal for six months or longer."
            if self.flaring:
                urate_check_rec_str += "<br> <br>" + next_urate_check_rec_str
            else:
                urate_check_rec_str = next_urate_check_rec_str
        return {"Check Uric Acid": mark_safe(urate_check_rec_str)}

    @property
    def urate_check_no_recent_urate_recommendation(self) -> dict[str, str]:
        """Returns a dict of a heading and explanation for a Ppx/Patient that needs a uric acid checked because \
        they have not had their uric acid checked in over 6 months and are on gout treatment requiring lab
        monitoring or having symptoms of gout."""
        (
            Subject_the,
            pos_neg_past,
            Gender_subject,
            gender_pos,
            gender_subject,
            tobe,
        ) = self.get_str_attrs("Subject_the", "pos_neg_past", "Gender_subject", "gender_pos", "gender_subject", "tobe")
        if self.flaring:
            urate_check_rec_str = f"{Subject_the} {pos_neg_past} {gender_pos} \
uric acid checked in the last 6 months and is having symptoms attributed \
to gout flares. {Gender_subject} should have {gender_pos} uric acid checked and if it is elevated \
{gender_subject} will need ULT {'adjustment' if self.on_ult else 'initiation'} and will benefit from \
ongoing prophylaxis against flares."
        if self.should_check_uric_acid_to_assess_need_for_ppx:
            next_urate_check_rec_str = f"{Subject_the} \
{' ' + tobe + ' also' if self.should_consider_other_causes_of_symptoms else ''} \
on flare prophylaxis and has not had {gender_pos} serum uric acid checked recently. Ongoing monitoring of the \
uric acid is essential for determining whether or not {gender_subject} still needs prophylaxis, which is \
generally continued until the uric acid has been at goal for six months or longer."
            if self.flaring:
                urate_check_rec_str += "<br> <br>" + next_urate_check_rec_str
            else:
                urate_check_rec_str = next_urate_check_rec_str
        elif self.at_goal is None:
            urate_check_rec_str = self.urate_status_unknown_detail
        return {"Check Uric Acid": mark_safe(urate_check_rec_str)}

    @cached_property
    def urates_discrepant(self) -> bool:
        """Method that implements the ppxs_check_urate_hyperuricemic_discrepant helper
        method to determine if the labs (Urates) and the goutdetail hyperuricemic field
        are discrepant.

        returns:
            bool: True if the labs (Urates) and the goutdetail hyperuricemic field are
            discrepant (i.e. hyperuricemic is True but the last urate was at goal),
            False if not.
        """
        if self.goutdetail and self.dated_urates:  # pylint: disable=W0125
            return ppxs_check_urate_at_goal_discrepant(
                urate=self.dated_urates[0],
                goutdetail=self.goutdetail,  # type: ignore
                goal_urate=self.goal_urate,
            )
        return False
