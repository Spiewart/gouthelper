from datetime import timedelta
from typing import TYPE_CHECKING, Union

from django.conf import settings  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.html import mark_safe  # type: ignore
from django.utils.text import format_lazy  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from multiselectfield import MultiSelectField  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..choices import BOOL_CHOICES
from ..genders.choices import Genders
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.lists import FLARE_MEDHISTORYS
from ..rules import add_object, change_object, delete_object, view_object
from ..users.models import Pseudopatient
from ..utils.helpers import calculate_duration, first_letter_lowercase, now_date, shorten_date_for_str
from ..utils.models import GoutHelperAidModel, GoutHelperModel
from .choices import LessLikelys, Likelihoods, LimitedJointChoices, Prevalences
from .helpers import (
    flares_abnormal_duration,
    flares_calculate_prevalence_points,
    flares_common_joints,
    flares_diagnostic_rule_urate_high,
    flares_get_less_likelys,
    flares_uncommon_joints,
)
from .managers import FlareManager
from .services import FlareDecisionAid

if TYPE_CHECKING:
    User = get_user_model()


class Flare(
    RulesModelMixin,
    GoutHelperAidModel,
    GoutHelperModel,
    TimeStampedModel,
    metaclass=RulesModelBase,
):
    """
    Model for describing a gout flare and calculating probability it was from gout.
    """

    class Meta:
        rules_permissions = {
            "add": add_object,
            "change": change_object,
            "delete": delete_object,
            "view": view_object,
        }
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_valid",
                check=(
                    models.Q(
                        user__isnull=False,
                        dateofbirth__isnull=True,
                        gender__isnull=True,
                        flareaid__isnull=True,
                    )
                    | models.Q(
                        user__isnull=True,
                        dateofbirth__isnull=False,
                        gender__isnull=False,
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
    LessLikelys = LessLikelys
    LimitedJointChoices = LimitedJointChoices
    Likelihoods = Likelihoods
    Prevalences = Prevalences

    aki = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name=_("Acute Kidney Injury"),
        help_text=_("Did the patient have acute kidney injury during this flare?"),
        default=None,
        null=True,
        blank=True,
    )
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
    # Age is required, but can be null if user is not null
    dateofbirth = models.OneToOneField(
        "dateofbirths.DateOfBirth",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    date_started = models.DateField(
        _("Date Flare Started"),
        help_text=_("What day did this flare start?"),
        default=now_date,
    )
    diagnosed = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name=_("Provider Diagnosis"),
        help_text=_("Did a medical provider think these symptoms were from gout?"),
        blank=True,
        null=True,
    )
    flareaid = models.OneToOneField(
        "flareaids.FlareAid",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    # Gender is required, but can be null if user is not null
    gender = models.OneToOneField(
        "genders.Gender",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    history = HistoricalRecords()

    objects = models.Manager()
    related_objects = FlareManager()

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
                and self.age >= 18  # pylint: disable=w0143
                or self.gender.value == Genders.FEMALE
                and (self.post_menopausal or self.ckd)
            )
        return False

    @cached_property
    def ckd_interp(self) -> str:
        ckd_str = super().ckd_interp

        (Subject_the, subject_the, tobe) = self.get_str_attrs("Subject_the", "subject_the", "tobe")

        ckd_str += " Uric acid is also excreted by the kidneys, \
and impaired kidney function causes bodily retention of uric acid, hence the risk of gout. <br> <br>\
CKD is not included in the Diagnostic Rule, so it doesn't play any role in our calculation of the gout prevalence \
in a population similar to the Flare reported. However, GoutHelper includes CKD as a variable in Flare estimations of \
likelihood only to interpret pre-menopausal women who almost never experience gout in the absence of chronic kidney \
disease."
        if self.premenopausal_with_ckd:
            ckd_str += f" {Subject_the} {tobe} a pre-menopausal woman with CKD, which GoutHelper interprets as an \
at-risk demographic for gout. Demographics that are not at risk are interpreted as less likely to have gout, \
which doesn't apply to {subject_the}."
        elif self.post_menopausal:
            ckd_str += f" {Subject_the} {tobe} a post-menopausal woman, which GoutHelper interprets as an \
at-risk demographic for gout with or without CKD. Demographics that are not at risk are interpreted as \
less likely to have gout, which doesn't apply to {subject_the}."
        elif self.user.gender.value == Genders.FEMALE if self.user else self.gender.value == Genders.FEMALE:
            ckd_str += f" {Subject_the} {tobe} a pre-menopausal woman without CKD, which GoutHelper interprets as a \
demographic that is not at risk for gout and as such is less likely to have gout."
        else:
            ckd_str += f" {Subject_the} {tobe} an adult male, which GoutHelper interprets as an at-risk demographic \
for gout, regardless of whether or not he has CKD. Demographics that are not at risk are interpreted as less likely \
to have gout, which doesn't apply to {subject_the}."
        return mark_safe(ckd_str)

    @cached_property
    def common_joints(self) -> list[LimitedJointChoices]:
        """Method that returns a list of the joints of a Flare that are
        in COMMON_GOUT_JOINTS."""
        return flares_common_joints(joints=self.joints)

    @property
    def common_joints_str(self) -> str:
        """Method that returns a str of the joints of a Flare that are
        in COMMON_GOUT_JOINTS."""

        return self.stringify_joints([getattr(LimitedJointChoices, joint) for joint in self.common_joints])

    @cached_property
    def contradiction(self) -> dict[str, str]:
        """Method that returns a dictionary of contradictions for the Flare to use in templates."""
        # If the user has a positive crystal analysis but the likelihood is unlikely, that can be a sign
        # that there is some confusion or disagreement in the form fields.
        Subject_the, pos_past = self.get_str_attrs("Subject_the", "pos_past")
        if self.crystal_analysis and self.likelihood != self.Likelihoods.LIKELY:
            return mark_safe(
                f"<strong>Something seems off</strong>. {Subject_the} {pos_past} a joint aspiration \
and the synovial fluid contained monosodium urate which is the gold standard for diagnosing gout. \
The likelihood of gout should be high."
            )
        # If the user was diagnosed with gout but the likelihood is unlikely, it will be noted.
        elif self.diagnosed and self.likelihood == self.Likelihoods.UNLIKELY:
            return mark_safe(
                f"<strong>Something seems off</strong>. {Subject_the} was diagnosed with gout, \
but the likelihood of gout is unlikely."
            )
        # If the user is diagnosed as not having gout without a crystal analysis, but gout is likely,
        # it should be noted.
        elif (
            self.diagnosed is not None
            and self.diagnosed is False
            and self.likelihood == self.Likelihoods.LIKELY
            and self.crystal_analysis is None
        ):
            return mark_safe(
                f"<strong>Something seems off</strong>. {Subject_the} was diagnosed as \
not having gout, but the likelihood of gout is high."
            )

    @cached_property
    def crystal_analysis_interp(self) -> str:
        (Subject_the, subject_the, subject_the_pos, pos_past, pos_neg_past) = self.get_str_attrs(
            "Subject_the",
            "subject_the",
            "subject_the_pos",
            "pos_past",
            "pos_neg_past",
        )

        crystal_analysis_str = "Crystal analysis is a definitive diagnostic test for gout. It is performed \
by using a needle to drain fluid out of a symptomatic joint and then examining the fluid under a microscope. \
If monosodium urate crystals are present, the diagnosis of gout is confirmed. <br> <br>"

        if self.crystal_analysis:
            crystal_analysis_str += f"<strong>{Subject_the} {pos_past} a joint aspiration and the synovial fluid \
contained monosodium urate crystals</strong>, consistent with gout."
            if self.diagnosed:
                crystal_analysis_str += f" The provider's diagnosis is correct, and {subject_the} has gout. \
GoutHelper set the Flare likelihood to likely because the providers' opinion was supported by a synovial fluid \
analysis that contained monosodium urate."
            elif self.diagnosed is not None and self.diagnosed is False:
                crystal_analysis_str += " <strong>The provider disagreed with the synovial fluid \
analysis in that he or she did not think that the symptoms were due to gout</strong>, but the synovial \
fluid analysis contained monosodium urate crystals, highly suggestive of gout. GoutHelper didn't \
modify the Flare likelihood due to the disagreement, and instead relies on the other information provided \
to determine the likelihood of gout."
            else:
                crystal_analysis_str += f" <strong>The provider was uncertain whether to attribute {subject_the_pos} \
symptoms to gout or not</strong>. However, the presence of monosodium urate crystals in the synovial fluid is highly \
suggestive of gout. GoutHelper didn't modify the Flare likelihood because of the disagreement, and instead relies on \
the other information provided to determine the likelihood of gout."
        elif self.crystal_analysis is not None:
            crystal_analysis_str += f"<strong>{Subject_the} {pos_past} a joint aspiration and the synovial fluid \
did not contain monosodium urate crystals</strong>, which is inconsistent with gout."
            if self.diagnosed is not None:
                if self.diagnosed is False:
                    crystal_analysis_str += f" The provider's diagnosis is correct, and {subject_the} does \
not have gout. GoutHelper set the Flare likelihood to unlikely because the providers' opinion was supported \
by a synovial fluid analysis that did not contain monosodium urate."
                if self.diagnosed is True:
                    crystal_analysis_str += f" <strong>The provider disagreed with the synovial fluid analysis in \
that he or she diagnosed {subject_the} with gout</strong>, but the synovial fluid analysis did not contain \
monosodium urate crystals, so GoutHelper decreased the likelihood of gout."
        else:
            crystal_analysis_str += f"<strong>{Subject_the} {pos_neg_past} a joint aspiration</strong>, \
so the presence or absence of monosodium urate crystals in the synovial fluid is unknown."
        return mark_safe(crystal_analysis_str)

    @cached_property
    def crystal_proven_gout_explanation(self) -> str:
        subject_the_pos = self.get_str_attrs("subject_the_pos")
        return mark_safe(
            format_lazy(
                """A provider diagnosed {} as gout, and monosodium <a target='_next" \
href={}>urate</a> crystals were observed in {} synovial fluid, consistent with a high likelihood of gout, \
though this is a non-empiric determination made by GoutHelper and not based in Diagnostic Rule evidence.""",
                self,
                reverse("labs:about-urate"),
                subject_the_pos,
            )
        )

    @property
    def crystal_analysis_negative_str(self):
        """Method that returns a str of the crystal analysis negative result."""
        Subject_the, pos_past = self.get_str_attrs("Subject_the", "pos_past")
        return f"{Subject_the} {pos_past} a joint aspiration and the synovial fluid did not contain \
monosodium urate crystals."

    @property
    def crystal_analysis_positive_str(self):
        """Method that returns a str of the crystal analysis positive result."""
        Subject_the, pos_past = self.get_str_attrs("Subject_the", "pos_past")
        return f"{Subject_the} {pos_past} a joint aspiration and the synovial fluid contained \
monosodium urate crystals."

    @cached_property
    def crystal_unproven(self) -> bool:
        """Method that determines if a Flare was diagnosed as not due to gout and proven
        with a crystal analysis of aspirated synovial fluid."""
        return (
            self.diagnosed is not None
            and not self.diagnosed
            and self.crystal_analysis is not None
            and not self.crystal_analysis
        )

    @cached_property
    def crystal_unproven_explanation(self) -> str:
        (subject_the,) = self.get_str_attrs("subject_the")
        return mark_safe(
            format_lazy(
                """{} was <a class='samepage-link' href='#diagnosed'>diagnosed</a> \
with something other than gout and had a joint aspiration with a negative <a class='samepage-link' \
href='#crystal_analysis'>crystal analysis</a>.""",
                subject_the,
            )
        )

    @cached_property
    def cvdiseases_interp(self) -> str:
        subject_the, subject_the_pos, pos_neg, gender_pos, gender_subject = self.get_str_attrs(
            "subject_the", "subject_the_pos", "pos_neg", "gender_pos", "gender_subject"
        )

        main_str = "Gout and cardiovascular disease are risk factors for one another. As part of the Diagnostic Rule, \
cardiovascular disease increases the likelihood that an individual's symptoms are from gout. <br> <br>"

        if self.cvdiseases:
            main_str += f"Because of <strong>{subject_the}'s cardiovascular disease(s) ({self.cvdiseases_str.lower()})\
</strong>, {subject_the_pos} Diagnostic Rule score is 1.5 points higher, making it more likely that {gender_pos} \
symptoms are due to gout."
        else:
            main_str += f"Because <strong>{subject_the} {pos_neg} cardiovascular disease</strong>, {gender_subject} \
doesn't get any extra points for {gender_pos} Diagnostic Rule score."
        return mark_safe(main_str)

    @cached_property
    def demographic_risk(self) -> bool:
        """Method that returns True if the patient referenced by a Flare
        is at risk for gout demographically and False if not."""
        if self.user.gender.value == Genders.MALE if self.user else self.gender.value == Genders.MALE:
            return self.age >= 18
        return self.post_menopausal or self.premenopausal_with_ckd

    @cached_property
    def demographic_risk_interp(self) -> str:
        (Subject_the,) = self.get_str_attrs("Subject_the")
        if (
            self.user.gender.value == Genders.MALE
            if self.user
            else self.gender.value == Genders.MALE and self.age >= 18
        ):
            demo_desc = "an adult male"
        elif self.post_menopausal:
            demo_desc = "a post-menopausal female"
        elif self.premenopausal_with_ckd:
            demo_desc = "a pre-menopausal female with chronic kidney disease"
        else:
            demo_desc = "adult pre-menopausal female without chronic kidney disease"
        if self.demographic_risk:
            demo_str = f"<strong>{Subject_the} is {demo_desc}, which is a demographic considered at \
risk for gout</strong>."
            if (
                self.user.gender.value == Genders.MALE
                if self.user
                else self.gender.value == Genders.MALE and self.age >= 18
            ):
                demo_str += " This increases the Diagnostic Rule score by 2 points."
            demo_str += " GoutHelper only reduces the likelihood of a Flare being gout if the demographic is not at \
risk."
            return mark_safe(demo_str)
        else:
            return mark_safe(
                f"<strong>{Subject_the} is {demo_desc}, a demographic that is not typically considered at risk for \
gout</strong>, so GoutHelper adjusted the Flare likelihood to be lower."
            )

    @property
    def description(self):
        flare_str = "Monoarticular" if self.monoarticular else "Polyarticular"
        flare_str += f", {self.date_started.strftime('%m/%d/%Y')} - "
        flare_str += f"{self.date_ended.strftime('%m/%d/%Y')}" if self.date_ended else "present"
        return flare_str

    @cached_property
    def diagnosed_interp(self) -> str:
        """Method that returns a str interpretation of the diagnosed field."""
        subject_the_pos, subject_the, gender_pos = self.get_str_attrs("subject_the_pos", "subject_the", "gender_pos")
        if self.diagnosed is None:
            if self.crystal_analysis is not None or self.urate:
                diagnosed_str = f"<strong>The provider was not certain whether {subject_the_pos} symptoms</strong> \
were due to gout. This has no effect on the likelihood of gout."
            else:
                diagnosed_str = f"<strong>A provider did not evaluate {subject_the_pos} symptoms</strong>. \
    This has no effect on the likelihood of gout."
        elif self.diagnosed is True:
            diagnosed_str = f"<strong>A provider diagnosed {subject_the_pos} symptoms as due to gout</strong>."
            if self.crystal_analysis:
                diagnosed_str += " <strong>The presence of monosodium urate crystals in the synovial fluid \
confirms the diagnosis</strong>. GoutHelper interprets the likelihood of gout as high in this context."
            elif self.crystal_analysis is None:
                diagnosed_str += " <strong>No joint aspiration was performed, so the diagnosis of gout is not \
confirmed</strong>. GoutHelper doesn't adjust the likelihood of gout in this context."
            else:
                diagnosed_str += " <strong>The absence of monosodium urate crystals in the synovial fluid \
did not confirm the diagnosis</strong>. GoutHelper doesn't adjust the likelihood of gout in this context. \
There are two possibilities to explain this scenario: 1) the patient has gout, but the crystals were not \
detected in the synovial fluid, or 2) the patient does not have gout and the provider's diagnosis is incorrect."
        else:
            diagnosed_str = f"<strong>A provider felt that {subject_the_pos} symptoms were not from gout</strong>."
            if self.crystal_analysis:
                diagnosed_str += f" <strong>However, the presence of monosodium urate crystals in the synovial fluid \
is highly suspicious for gout</strong>. Either the provider is incorrect or {subject_the} has gout and something \
else going on in {gender_pos} joints."
            elif self.crystal_analysis is None:
                diagnosed_str += " <strong>No joint aspiration was performed</strong>."
            else:
                diagnosed_str += " <strong>The absence of monosodium urate crystals in the synovial fluid \
is inconsistent with gout</strong>. GoutHelper set the Flare likelihood to unlikely because the provider thoroughly \
ruled out gout."
        return mark_safe(diagnosed_str)

    @property
    def duration(self) -> timedelta:
        return calculate_duration(date_started=self.date_started, date_ended=self.date_ended)

    @cached_property
    def duration_interp(self) -> str:
        """Method that returns a str interpretation of the duration field."""

        (Subject_the_pos,) = self.get_str_attrs("Subject_the_pos")
        duration_str = f"<strong>{Subject_the_pos} flare {'lasted' if self.date_ended else 'has been ongoing for'} \
{self.duration.days} day{'s' if self.duration.days > 1 or self.duration.days == 0 else ''}</strong>. "
        if self.abnormal_duration == LessLikelys.TOOLONG:
            duration_str += "This duration is atypically long for a gout flare, and as such GoutHelper \
reduced the likelihood that these symptoms were due to gout. "
        elif self.abnormal_duration == LessLikelys.TOOSHORT:
            duration_str += self.tooshort_explanation
        else:
            if not self.date_ended:
                if self.duration.days < 2:
                    duration_str += "This is less than 2 days, so if it resolved \
now it would be too short to be consistent with gout. Because the symptoms have not resolved, \
GoutHelper did not adjust the likelihood that these symptoms were due to gout. "
                elif self.duration.days > 10:
                    duration_str += "This is 10 or more days and if it lasts longer than \
2 weeks it would be considered atypically long for gout and other diagnoses should be considered."
                else:
                    duration_str += "The duration of this flare thus far is typical for gout, \
and as such GoutHelper did not adjust the likelihood that these symptoms were due to gout."
            else:
                duration_str += "The duration of this flare is typical for gout, \
and as such GoutHelper did not adjust the likelihood that these symptoms were due to gout. "
        return mark_safe(duration_str)

    @cached_property
    def explanations(self) -> list[tuple[str, str, bool, str]]:
        """Method that returns a dictionary of tuples explanations for the Flare to use in templates."""
        return [
            ("ckd", "Chronic Kidney Disease", self.ckd, self.ckd_interp),
            ("crystal_analysis", "Crystal Analysis", self.crystal_analysis, self.crystal_analysis_interp),
            ("cvdiseases", "Cardiovascular Diseases", True if self.cvdiseases else False, self.cvdiseases_interp),
            ("demographics", "Demographic Risk", self.demographic_risk, self.demographic_risk_interp),
            ("diagnosed", "Clinician Diagnosis", self.diagnosed, self.diagnosed_interp),
            ("duration", "Duration", self.abnormal_duration, self.duration_interp),
            ("redness", "Erythema", self.redness, self.redness_interp),
            ("gout", "Gout Diagnosis", self.gout, self.gout_interp),
            ("hyperuricemia", "Hyperuricemia", self.hyperuricemia, self.hyperuricemia_interp),
            ("joints", "Joints", self.joints, self.joints_interp),
            ("onset", "Onset", self.onset, self.onset_interp),
        ]

    @cached_property
    def female_explanation(self) -> str:
        """Method that explains the pre-menopausal female LessLikelys."""
        (subject_the,) = self.get_str_attrs("subject_the")
        return f"Pre-menopausal females typically do not get gout unless they have chronic kidney disease, \
which is not the case with {subject_the}. Consequently, GoutHelper reduced the likelihood that {subject_the} \
symptoms were due to gout."

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
        if self.user:
            return reverse("flares:pseudopatient-detail", kwargs={"username": self.user.username, "pk": self.pk})
        else:
            return reverse("flares:detail", kwargs={"pk": self.pk})

    def gout_interp(self):
        """Method that returns a str interpretation of the gout cached_property."""
        (Subject_the,) = self.get_str_attrs("Subject_the")
        if self.gout:
            return mark_safe(
                f"<strong>{Subject_the} has a medical history of gout, which is a significant risk \
factor for having more gout</strong>. This increases the Diagnostic Rule score by 2 points."
            )
        else:
            return mark_safe(
                f"<strong>{Subject_the} does not have a medical history of gout</strong>. \
This does not affect the Diagnostic Rule score."
            )

    @cached_property
    def hyperuricemia(self) -> bool:
        """Method that returns True if a Flare has a Urate that is
        in the hyperuricemic range (>= 6 mg/dL) and False if not."""
        return flares_diagnostic_rule_urate_high(self.urate)

    @cached_property
    def hyperuricemia_interp(self) -> str:
        """Method that returns a str interpretation of the hyperuricemia field."""
        (Subject_the_pos,) = self.get_str_attrs("Subject_the_pos")
        if self.urate:
            hyperuricemia_str = format_lazy(
                """<strong>{} serum <a target='_next' href={}>uric acid</a> level was {} during the flare, """,
                Subject_the_pos,
                reverse("labs:about-urate"),
                self.urate,
            )
            if self.hyperuricemia:
                hyperuricemia_str += "which is hyperuricemic (>= 5.88 mg/dL)</strong> per the Diagnostic Rule. \
This increases the Diagnostic Rule score by 3.5 points."
            else:
                hyperuricemia_str += "which is not hyperuricemic (>= 5.88 mg/dL)</strong> per the Diagnostic Rule. \
This does not affect the Diagnostic Rule score."
        else:
            hyperuricemia_str = f"<strong>{Subject_the_pos} serum uric acid level was not measured during the \
flare</strong>. This does not affect the Diagnostic Rule score."
        return mark_safe(hyperuricemia_str)

    @property
    def joints_explanation(self) -> str:
        """Method that provides a str explanation for the joints field."""
        subject_the_pos, Subject_the_pos = self.get_str_attrs("subject_the_pos", "Subject_the_pos")
        if self.LessLikelys.JOINTS in self.less_likelys:
            return f"The joints involved in {subject_the_pos} flare are atypical for gout. \
GoutHelper reduced the likelihood that these symptoms were due to gout."
        else:
            if not self.uncommon_joints:
                joints_str = f"Some of the joints involved in {subject_the_pos} flare are typical for gout \
({self.common_joints}) and others are not ({self.uncommon_joints_str})."
            else:
                joints_str = f"The joints involved in {subject_the_pos} flare ({self.common_joints_str}) \
are typical for gout."
            joints_str += "GoutHelper only reduces a Flare's likelihood if ALL of the affected joints are \
atypical for gout."
            if self.firstmtp:
                joints_str += f" {Subject_the_pos} flare involved {self.firstmtp_str}, which is the most \
common location for gout flares. Involvement of the 1st MTP joint(s) adds 2.5 points \
To the Diagnostic Rule score."
            return joints_str

    @property
    def joints_interp(self):
        """Method that returns a str interpretation of the joints field."""
        (Subject_the_pos,) = self.get_str_attrs("Subject_the_pos")
        joints = self.joints_str()
        joints_str = f"<strong>{Subject_the_pos} Flare involved: the {joints}, "
        if self.firstmtp:
            joints_str += "and included the base of the big toe</strong>. The base of the big toe, \
otherwise known as the first metatarsophalangeal (1st MTP) joint, is the most common location for gout flares. \
Involvement of the 1st MTP joint(s) adds 2.5 points to the Diagnostic Rule score."
        else:
            joints_str += "but did not involve the base of the big toe</strong>. The base of the big toe, \
otherwise known as the first metatarsophalangeal (1st MTP) joints, is the most common location for gout flares. \
Lack of involvement of the 1st MTP joint(s) does not rule out gout, but doesn't add any points to the Diagnostic Rule \
score."
        return mark_safe(joints_str)

    def joints_str(self):
        """
        Function that returns a str of the joints affected by the flare
        returns: [str]: [str describing the joints(s) of the flare]
        """
        joints = self.get_joints_list()
        if joints and len(joints) > 1:
            if len(joints) == 2:
                return f"{joints[0].lower()} and {joints[1].lower()}"
            else:
                return (
                    ", ".join([joint.lower() for joint in joints[: len(joints) - 1]]) + ", and " + joints[-1].lower()
                )
        else:
            return ", ".join([joint.lower() for joint in joints])

    @cached_property
    def less_likelys(self) -> list[LessLikelys]:
        """Method that returns a list of the LessLikelys for a Flare."""
        return flares_get_less_likelys(
            age=self.age,
            date_ended=self.date_ended,
            duration=self.duration,
            gender=self.user.gender if self.user else self.gender,
            joints=self.joints,
            menopause=self.menopause,
            crystal_analysis=self.crystal_analysis,
            ckd=self.ckd,
        )

    @property
    def less_likelys_explanations(self) -> list[str]:
        """Method that returns a list of the LessLikelys explanations for a Flare."""
        return [
            (self.LessLikelys(less_likely).label, self.less_likely_get_explanation(less_likely))
            for less_likely in self.less_likelys
        ]

    def less_likely_get_explanation(self, less_likely: LessLikelys) -> str:
        """Method that takes a less likely and gets a str to link to the correct explanation."""
        if less_likely == self.LessLikelys.FEMALE:
            return "demographics"
        elif less_likely == self.LessLikelys.JOINTS:
            return "joints"
        elif less_likely == self.LessLikelys.NEGCRYSTALS:
            return "crystal_analysis"
        elif less_likely == self.LessLikelys.TOOLONG:
            return "duration"
        elif less_likely == self.LessLikelys.TOOSHORT:
            return "duration"
        elif less_likely == self.LessLikelys.TOOYOUNG:
            return "age"
        else:
            raise ValueError("Unsupported LessLikelys")

    @property
    def less_likelys_str(self) -> str:
        """Method that returns a str of the LessLikelys for a Flare."""
        return ", ".join([less_likely.label.lower() for less_likely in self.less_likelys])

    def likelihood_base_explanation(self) -> str:
        subject_the_pos, subject_the = self.get_str_attrs("subject_the_pos", "subject_the")
        likelihood_exp_str = format_lazy(
            """<strong>The likelihood of gout for {} Flare is \
{}</strong> based on a {} <a class='samepage-link' href='#prevalence'>Diagnostic Rule</a> score""",
            subject_the_pos,
            self.Likelihoods(self.likelihood).label.lower(),
            self.Prevalences(self.prevalence).name.lower(),
            subject_the,
        )
        return mark_safe(likelihood_exp_str)

    def likelihood_likely_explanation(self) -> str:
        """Method that interprets an LIKELY likelihood for a Flare."""
        likelihood_exp_str = self.likelihood_base_explanation()
        if self.prevalence == self.Prevalences.HIGH:
            likelihood_exp_str += " that was not adjusted for any <em>less likely</em> factors."
            if self.diagnosed and self.crystal_analysis:
                crystal_proven_str = self.crystal_proven_gout_explanation
                crystal_proven_str = first_letter_lowercase(crystal_proven_str)
                likelihood_exp_str += " Also, " + crystal_proven_str
        elif self.prevalence == self.Prevalences.MEDIUM:
            likelihood_exp_str += " that was lowered due to: {self.less_likelys_str}."
        elif self.prevalence == self.Prevalences.LOW:
            pass
        else:
            raise ValueError("Trying to explain a Flare likelihood without a prevalence")
        return mark_safe(likelihood_exp_str)

    def likelihood_equivocal_explanation(self) -> str:
        """Method that interprets an EQUIVOCAL likelihood for a Flare."""
        likelihood_exp_str = self.likelihood_base_explanation()
        if self.prevalence == self.Prevalences.HIGH:
            likelihood_exp_str += " that was lowered due to <em>less likely</em> factors:"
        elif self.prevalence == self.Prevalences.MEDIUM or self.prevalence == self.Prevalences.LOW:
            likelihood_exp_str += "."
        else:
            raise ValueError("Trying to explain a Flare likelihood without a prevalence")
        return mark_safe(likelihood_exp_str)

    def likelihood_get_explanation(self, likelihood: Likelihoods) -> str:
        """Method that takes a likelihood and returns the appropriate explanation."""
        if likelihood == Likelihoods.LIKELY:
            return self.likelihood_likely_explanation()
        elif likelihood == Likelihoods.EQUIVOCAL:
            return self.likelihood_equivocal_explanation()
        elif likelihood == Likelihoods.UNLIKELY:
            return self.likelihood_unlikely_explanation()
        else:
            raise ValueError("Trying to explain a Flare likelihood without a likelihood")

    def likelihood_unlikely_explanation(self) -> str:
        """Method that interprets an UNLIKELY likelihood for a Flare."""
        likelihood_exp_str = self.likelihood_base_explanation()
        if self.prevalence == self.Prevalences.HIGH:
            if self.crystal_unproven:
                likelihood_exp_str += " whose likelihood was lowered because " + self.crystal_unproven_explanation
                if self.less_likelys:
                    likelihood_exp_str += " Additionally, had the likelihood not already been unlikely, it would have \
been lowered due to:"
                else:
                    likelihood_exp_str += "."
            else:
                raise ValueError(
                    "Trying to explain a Flare with an unlikely likelihood and a high prevalence \
without a negative diagnosis and supporting crystal analysis"
                )
        elif self.prevalence == self.Prevalences.MEDIUM:
            if self.crystal_unproven:
                likelihood_exp_str += " whose likelihood was lowered because " + self.crystal_unproven_explanation
            if self.less_likelys:
                if self.crystal_unproven:
                    likelihood_exp_str += " Additionally, had the likelihood not already been unlikely, it would have \
been lowered due to:"
                else:
                    likelihood_exp_str += " that was lowered due to:"
            else:
                raise ValueError(
                    "Trying to explain a Flare with an unlikely likelihood and a medium prevalence \
without any less likely factors"
                )
        elif self.prevalence == self.Prevalences.LOW:
            if self.crystal_unproven:
                likelihood_exp_str += " whose likelihood was lowered because " + self.crystal_unproven_explanation
            if self.less_likelys:
                if self.crystal_unproven:
                    likelihood_exp_str += " Additionally, had the likelihood not already been unlikely, it would have \
been lowered due to:"
                else:
                    likelihood_exp_str += " that was lowered due to:"
        else:
            raise ValueError("Trying to explain a Flare likelihood without a prevalence")
        return mark_safe(likelihood_exp_str)

    @property
    def likelihood_explanation(self):
        """Method that returns a str explanation of the likelihood field."""
        if self.likelihood:
            return self.likelihood_get_explanation(likelihood=self.likelihood)
        # The Flare has not yet been processed and the likelihood field is None
        else:
            return f"The likelihood of gout for {self} has not been calculated yet."

    @property
    def likelihood_interp(self):
        if self.likelihood == Likelihoods.UNLIKELY:
            return "Gout isn't likely"
        elif self.likelihood == Likelihoods.EQUIVOCAL:
            return "Gout can't be ruled in or out"
        elif self.likelihood == Likelihoods.LIKELY:
            return "Gout is very likely"
        else:
            return "Flare hasn't been processed yet..."

    @property
    def likelihood_recommendation(self):
        if self.likelihood == Likelihoods.UNLIKELY:
            return "Consider alternative causes of the symptoms."
        elif self.likelihood == Likelihoods.EQUIVOCAL:
            rec_str = "Medical evaluation is needed."
            if not self.urate:
                rec_str += f" Check {self.get_str_attrs('subject_the_pos')[0]} serum uric acid."
            return rec_str
        elif self.likelihood == Likelihoods.LIKELY:
            return "Treat the gout!"
        else:
            return "Flare hasn't been processed yet..."

    @property
    def monoarticular(self):
        return not self.polyarticular

    @property
    def negcrystals_explanation(self) -> str:
        """Method that explains the NEGCRYSTALS LessLikelys."""
        (subject_the_pos,) = self.get_str_attrs("subject_the_pos")
        return f"Joint aspiration was performed but synovial fluid analysis did not show monosodium urate crystals \
, which argues against the diagnosis of gout. As a result, GoutHelper reduced the likelihood that {subject_the_pos} \
symptoms were due to gout."

    @cached_property
    def onset_interp(self) -> str:
        """Method that returns a str interpretation of the onset field."""
        (Subject_the,) = self.get_str_attrs("Subject_the")
        if self.onset:
            return mark_safe(
                f"<strong>{Subject_the} symptoms started and reached maximum intensity within 1 day</strong>. \
This rapid onset is typical of gout flares and adds 0.5 points to the Diagnostic Rule score."
            )
        else:
            return mark_safe(
                f"<strong>{Subject_the} symptoms did not start and reach maximum intensity within 1 day</strong>, \
as is typical for gout flares. This does not add any points to the Diagnostic Rule score."
            )

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
        return self.menopause or (self.age and self.age >= 60)  # pylint: disable=w0143

    @cached_property
    def premenopausal_with_ckd(self) -> bool:
        """Method that determines if the Flare belongs to a pre-menopausal woman with CKD."""
        return (
            (self.user.gender.value == Genders.FEMALE if self.user else self.gender.value == Genders.FEMALE)
            and not self.post_menopausal
            and self.ckd
        )

    @property
    def prevalence_explanation(self) -> str:
        (subject_the_pos,) = self.get_str_attrs("subject_the_pos")
        if self.prevalence == self.Prevalences.LOW:
            return (
                f"A low prevalence is associated with very low odds that {subject_the_pos} symptoms are due to gout."
            )
        elif self.prevalence == self.Prevalences.MEDIUM:
            return "Flares that fall into the medium prevalence range benefit most from additional \
investigations, such as a joint aspiration."
        elif self.prevalence == self.Prevalences.HIGH:
            return "Flares whose characteristics place them in a high prevalence group are highly likely to be due to \
gout and should probably just be treated as such."
        else:
            raise ValueError("This flare has not been processed and does not yet have a prevalence.")

    @cached_property
    def prevalence_points(self) -> float:
        """Method that returns the Diagnostic Rule points for prevalence for a Flare."""
        return flares_calculate_prevalence_points(
            gender=self.gender if self.gender else self.user.gender,
            onset=self.onset,
            redness=self.redness,
            joints=self.joints,
            medhistorys=self.medhistorys_qs if hasattr(self, "medhistorys_qs") else list(self.medhistory_set.all()),
            urate=self.urate,
        )

    @cached_property
    def redness_interp(self) -> str:
        """Method that returns a str interpretation of the redness field."""

        (Subject_the_pos,) = self.get_str_attrs("Subject_the_pos")
        if self.redness:
            redness_str = f"<strong>{Subject_the_pos} symptomatic joint(s) are red (erythematous)</strong>. \
This is suggestive of inflammation in the joint(s) and is consistent with gout. Erythema (redness) adds \
1 point to the Diagnostic Rule score."
        else:
            redness_str = f"<strong>{Subject_the_pos} symptomatic joint(s) are not red (erythematous)</strong>. \
The absence of erythema (redness) does not add any points to the Diagnostic Rule score."
        return mark_safe(redness_str)

    def __str__(self):
        return f" Flare ({shorten_date_for_str(self.date_started)} - \
{shorten_date_for_str(self.date_ended) if self.date_ended else 'present'})"

    @classmethod
    def stringify_joints(cls, joints: list[LimitedJointChoices]) -> str:
        """Method that returns a str of the joints of a Flare."""
        if joints and len(joints) > 1:
            if len(joints) == 2:
                return f"{joints[0].label.lower()} and {joints[1].label.lower()}"
            else:
                return (
                    ", ".join([joint.label.lower() for joint in joints[: len(joints) - 1]])
                    + ", and "
                    + joints[-1].label.lower()
                )
        else:
            return ", ".join([joint.label.lower() for joint in joints])

    @cached_property
    def toolong_explanation(self) -> str:
        """Method that explains the TOOLONG LessLikelys."""
        Subject_the_pos, pos_past, pos = self.get_str_attrs("Subject_the_pos", "pos_past", "pos")
        return f"{Subject_the_pos} gout symptoms {'lasted' if self.date_ended else 'have lasted'} for \
longer than is consistent with gout, so GoutHelper reduced the likelihood that \
{pos_past if self.date_ended else pos} symptoms {'were' if self.date_ended else 'are'} due to gout."

    @cached_property
    def tooshort_explanation(self) -> str:
        """Method that explains the TOOSHORT LessLikelys."""
        Subject_the_pos, gender_pos, gender_subject = self.get_str_attrs(
            "Subject_the_pos", "gender_pos", "gender_subject"
        )
        return f"{Subject_the_pos} gout symptoms resolved too quickly to be consistent with gout, \
so GoutHelper reduced the likelihood that {gender_pos} symptoms were due to gout. If {gender_subject} \
started treatment early (immediately at flare onset), it may have resolved the symptoms quickly."

    @cached_property
    def tooyoung_explanation(self) -> str:
        """Method that explains the TOOYOUNG LessLikelys."""
        Subject_the, subject_the_pos = self.get_str_attrs("Subject_the", "subject_the_pos")
        return f"{Subject_the} is too young to have gout, which is why GoutHelper reduced the likelihood that \
{subject_the_pos} symptoms were due to gout."

    @cached_property
    def uncommon_joints(self) -> list[LimitedJointChoices]:
        """Method that returns a list of the joints of a Flare that are
        NOT in COMMON_GOUT_JOINTS."""
        return flares_uncommon_joints(joints=self.joints)

    @property
    def uncommon_joints_str(self) -> str:
        """Method that returns a str of the joints of a Flare that are
        NOT in COMMON_GOUT_JOINTS."""
        return self.stringify_joints([getattr(LimitedJointChoices, joint) for joint in self.uncommon_joints])

    def update_aid(self, qs: Union["Flare", "User", None] = None) -> "Flare":
        """Updates Flare prevalence and likelihood fields.

        args:
            qs: Flare object with attached qs to use for updating prevalence and likelihood

        returns: [Flare]: [Flare object]"""
        if qs is None:
            if self.user:
                qs = Pseudopatient.objects.flares_qs(flare_pk=self.pk).get()
            else:
                qs = Flare.related_objects.get(pk=self.pk)
        decisionaid = FlareDecisionAid(qs=qs)
        return decisionaid._update()  # pylint: disable=W0212
