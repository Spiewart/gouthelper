from typing import TYPE_CHECKING, Any  # pylint: disable=E0401, E0015, E0013 # type: ignore

from django.apps import apps  # pylint: disable=e0401 # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # pylint: disable=e0401 # type: ignore
from django.core.exceptions import ValidationError  # type: ignore
from django.utils.functional import cached_property  # pylint: disable=e0401 # type: ignore
from django.views.generic import CreateView, TemplateView, UpdateView  # pylint: disable=e0401 # type: ignore
from rules.contrib.views import (  # pylint: disable=e0401 # type: ignore
    AutoPermissionRequiredMixin,
    PermissionRequiredMixin,
)

from ..contents.choices import Contexts
from ..goalurates.choices import GoalUrates
from ..labs.forms import PpxUrateFormSet, UrateFormHelper
from ..labs.helpers import (
    labs_formset_get_most_recent_form,
    labs_formset_has_one_or_more_valid_labs,
    labs_formset_order_by_date_drawn_remove_deleted_and_blank_forms,
    labs_urate_form_at_goal_within_last_month,
    labs_urate_formset_at_goal_for_six_months,
    labs_urates_annotate_order_by_flare_date_or_date_drawn,
)
from ..labs.models import Urate
from ..labs.selectors import dated_urates
from ..ppxaids.models import PpxAid
from ..users.models import Pseudopatient
from ..utils.views import (
    GoutHelperDetailMixin,
    GoutHelperPseudopatientDetailMixin,
    LabFormSetsMixin,
    MedHistoryFormMixin,
)
from .dicts import LAB_FORMSETS, MEDHISTORY_DETAIL_FORMS, MEDHISTORY_FORMS
from .forms import PpxForm
from .models import Ppx

if TYPE_CHECKING:
    from uuid import UUID

    from django.contrib.auth import get_user_model  # pylint: disable=e0401 # type: ignore
    from django.db.models import QuerySet  # pylint: disable=e0401 # type: ignore

    User = get_user_model()


class PpxAbout(TemplateView):
    """About page for Ppx decision aid."""

    template_name = "ppxs/about.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"content": self.content})
        return context

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="about", context=Contexts.PPX, tag=None)


class PpxEditBase(LabFormSetsMixin, MedHistoryFormMixin):
    class Meta:
        abstract = True

    form_class = PpxForm
    model = Ppx

    LAB_FORMSETS = LAB_FORMSETS
    MEDHISTORY_FORMS = MEDHISTORY_FORMS
    MEDHISTORY_DETAIL_FORMS = MEDHISTORY_DETAIL_FORMS

    def post_compare_urates_and_at_goal(self, goal_urate: GoalUrates = GoalUrates.SIX) -> None:
        """Compares POST data for urates, at_goal field, and at_goal_long_term.
        If the urates indicate that the patient is at goal and/or
        at goal long term, sets error message on the form and errors_bool to True
        if the provided values contradict the urates."""

        goutdetail_form = self.medhistory_detail_forms["goutdetail"]
        at_goal = goutdetail_form.cleaned_data.get("at_goal", None)
        at_goal_long_term = goutdetail_form.cleaned_data.get("at_goal_long_term", None)
        urate_formset = self.lab_formsets["urate"][0]
        if labs_formset_has_one_or_more_valid_labs(formset=urate_formset):
            ordered_urate_formset = labs_formset_order_by_date_drawn_remove_deleted_and_blank_forms(
                formset=urate_formset
            )
            most_recent_urate_form = labs_formset_get_most_recent_form(ordered_urate_formset)
            at_goal_within_last_month = labs_urate_form_at_goal_within_last_month(
                urate_form=most_recent_urate_form, goal_urate=goal_urate
            )
            at_goal_six_months = labs_urate_formset_at_goal_for_six_months(
                ordered_urate_formset=ordered_urate_formset, goal_urate=goal_urate
            )
            if not at_goal and at_goal is not None and at_goal_within_last_month:
                (subject_the, gender_subject, gender_pos) = (
                    self.str_attrs.get("subject_the"),
                    self.str_attrs.get("gender_subject"),
                    self.str_attrs.get("gender_pos"),
                )
                urate_error = ValidationError(
                    message=f"The uric acid levels indicate that {subject_the} was at goal in the last \
month. If {gender_subject} has had {gender_pos} uric acid checked since, please enter it. Otherwise, clarify at \
goal status."
                )
                goutdetail_form.add_error("at_goal", urate_error)
                if not self.errors_bool:
                    self.errors_bool = True
            elif at_goal and not at_goal_within_last_month:
                (subject_the, gender_subject, gender_pos) = (
                    self.str_attrs.get("subject_the"),
                    self.str_attrs.get("gender_subject"),
                    self.str_attrs.get("gender_pos"),
                )
                urate_error = ValidationError(
                    message=f"The uric acid levels indicate that {subject_the} was not at goal in the last \
month. If {gender_subject} has had {gender_pos} uric acid checked since, please enter it. Otherwise, clarify \
at goal status."
                )
                goutdetail_form.add_error("at_goal", urate_error)
                if not self.errors_bool:
                    self.errors_bool = True
            if at_goal_long_term and not at_goal_six_months:
                (subject_the, gender_pos) = (
                    self.str_attrs.get("subject_the"),
                    self.str_attrs.get("gender_pos"),
                )
                urate_error = ValidationError(
                    message=f"The uric acid levels indicate that {subject_the} is not at goal long term. \
Please check {gender_pos} uric acid levels and long term goal urate status."  # noqa
                )
                goutdetail_form.add_error("at_goal_long_term", urate_error)
                if not self.errors_bool:
                    self.errors_bool = True
            elif at_goal and not at_goal_long_term and at_goal_six_months:
                (subject_the, gender_pos) = (
                    self.str_attrs.get("subject_the"),
                    self.str_attrs.get("gender_pos"),
                )
                urate_error = ValidationError(
                    message=f"The uric acid levels indicate that {subject_the} is at goal long term. \
Please check {gender_pos} uric acid levels and long term goal urate status."
                )
                goutdetail_form.add_error("at_goal_long_term", urate_error)
                if not self.errors_bool:
                    self.errors_bool = True


class PpxCreate(PpxEditBase, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """
    Create a new Ppx instance.
    """

    permission_required = "ppxs.can_add_ppx"
    success_message = "Ppx successfully created."

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"ppxaid": self.ppxaid})
        return context

    def get_permission_object(self):
        if self.ppxaid and self.ppxaid.user:
            raise PermissionError("Trying to create a Ppx for a PpxAid with a user with an anonymous view.")
        return None

    @cached_property
    def urate_formset_qs(self):
        return dated_urates(Urate.objects.none())

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        goal_urate_kwarg = (
            {"goal_urate": self.form.instance.goalurate.goal_urate} if hasattr(self.form.instance, "goalurate") else {}
        )
        self.post_compare_urates_and_at_goal(**goal_urate_kwarg)
        if self.errors or self.errors_bool:
            if self.errors_bool and not self.errors:
                return super().render_errors()
            else:
                return self.errors
        else:
            labs_urates_annotate_order_by_flare_date_or_date_drawn(self.form.instance.urates_qs)
            return self.form_valid()

    @cached_property
    def ppxaid(self) -> PpxAid | None:
        ppxaid_kwarg = self.kwargs.get("ppxaid", None)
        return PpxAid.related_objects.get(pk=ppxaid_kwarg) if ppxaid_kwarg else None

    @cached_property
    def related_object(self) -> PpxAid:
        return self.ppxaid


class PpxDetail(GoutHelperDetailMixin):
    model = Ppx
    object: Ppx


class PpxPatientBase(PpxEditBase):
    class Meta:
        abstract = True

    def get_user_queryset(self, pseudopatient: "UUID") -> "QuerySet[Any]":
        """Used to set the user attribute on the view, with associated related models
        select_related and prefetch_related."""
        return Pseudopatient.objects.ppx_qs().filter(pk=pseudopatient)

    @cached_property
    def urate_formset_qs(self):
        return dated_urates(Urate.objects.select_related("flare").filter(user=self.user))  # pylint: disable=E1101


class PpxPseudopatientCreate(PpxPatientBase, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """View for creating a Ppx for a patient."""

    permission_required = "ppxs.can_add_ppx"
    success_message = "%(user)s's Ppx successfully created."

    def get_permission_object(self):
        return self.user

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, user=self.user)

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        self.post_compare_urates_and_at_goal(goal_urate=self.user.goal_urate)
        if self.errors or self.errors_bool:
            if self.errors_bool and not self.errors:
                return super().render_errors()
            else:
                return self.errors
        else:
            labs_urates_annotate_order_by_flare_date_or_date_drawn(self.user.urates_qs)
            return self.form_valid()


class PpxPseudopatientDetail(GoutHelperPseudopatientDetailMixin):
    model = Ppx
    object: Ppx


class PpxPseudopatientUpdate(PpxPatientBase, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin):
    success_message = "%(user)ss's Ppx successfully updated."

    def get_permission_object(self):
        return self.object

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, user=self.user)

    def post(self, request, *args, **kwargs):
        """Overwritten to finish the post() method and avoid conflicts with the MRO.
        For Ppx, no additional processing is needed."""
        super().post(request, *args, **kwargs)
        self.post_compare_urates_and_at_goal(goal_urate=self.user.goal_urate)
        if self.errors or self.errors_bool:
            if self.errors_bool and not self.errors:
                return super().render_errors()
            else:
                return self.errors
        else:
            labs_urates_annotate_order_by_flare_date_or_date_drawn(self.user.urates_qs)
            return self.form_valid()


class PpxUpdate(PpxEditBase, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin):
    """Updates a Ppx"""

    labs = {"urate": (PpxUrateFormSet, UrateFormHelper)}

    @cached_property
    def urate_formset_qs(self):
        return dated_urates(Urate.objects.filter(ppx=self.object))

    def get_permission_object(self):
        return self.object

    def get_queryset(self):
        return Ppx.related_objects.filter(pk=self.kwargs["pk"])

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        goal_urate_kwarg = (
            {"goal_urate": self.form.instance.goalurate.goal_urate} if hasattr(self.form.instance, "goalurate") else {}
        )
        self.post_compare_urates_and_at_goal(**goal_urate_kwarg)
        if self.errors or self.errors_bool:
            if self.errors_bool and not self.errors:
                return super().render_errors()
            else:
                return self.errors
        labs_urates_annotate_order_by_flare_date_or_date_drawn(self.form.instance.urates_qs)
        return self.form_valid()
