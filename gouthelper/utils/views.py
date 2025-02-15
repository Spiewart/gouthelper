import uuid
from typing import TYPE_CHECKING, Any, Literal, Union

from django.contrib import messages  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from django.core.exceptions import ValidationError  # type: ignore
from django.db import transaction  # type: ignore
from django.db.models import Model  # type: ignore
from django.forms import ModelForm  # type: ignore
from django.http import HttpResponseRedirect  # type: ignore
from django.urls import reverse
from django.utils.functional import cached_property  # type: ignore
from django.views.generic import CreateView, DetailView
from rules.contrib.views import AutoPermissionRequiredMixin

from ..dateofbirths.helpers import age_calc
from ..genders.choices import Genders
from ..labs.models import BaselineCreatinine
from ..medallergys.models import MedAllergy
from ..medhistorydetails.models import CkdDetail, GoutDetail
from ..medhistorydetails.services import CkdDetailFormProcessor
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.helpers import medhistorys_get_default_medhistorytype
from ..medhistorys.models import Gout
from ..profiles.helpers import get_provider_alias
from ..profiles.models import PseudopatientProfile
from ..users.choices import Roles
from ..users.models import Patient
from .exceptions import Continue, EmptyRelatedModel
from .helpers import (
    attr_is_in_model_fields,
    get_model_foreignkey_fields,
    get_model_onetoone_field_names,
    get_model_onetoone_fields,
    get_or_create_qs_attr,
    get_str_attrs_dict,
    list_of_objects_related_objects,
)

if TYPE_CHECKING:
    from datetime import date

    from crispy_forms.helper import FormHelper
    from django.db.models import OneToOneField, QuerySet
    from django.forms import BaseModelFormSet
    from django.http import HttpRequest, HttpResponse

    from ..akis.models import Aki
    from ..dateofbirths.forms import DateOfBirthForm
    from ..genders.forms import GenderForm
    from ..genders.models import Gender
    from ..labs.models import Lab
    from ..medhistorydetails.forms import CkdDetailForm, GoutDetailForm
    from ..medhistorys.models import MedHistory
    from ..treatments.choices import Treatments
    from .types import Aids


User = get_user_model()


class PatientSessionMixin:
    """Mixin to add a session to a view."""

    request: "HttpRequest"

    def get_context_data(self, **kwargs):
        """Overwritten to add the patient to the session."""
        context = super().get_context_data(**kwargs)
        self.update_session_patient()
        return context

    def add_patient_to_session(self, patient: Patient) -> None:
        self.request.session.update({"patient": str(patient), "pk": str(patient.pk)})
        if not self.request.session.get("recent_patients", None):
            self.request.session["recent_patients"] = []
        if str(patient.pk) not in [recent_patient[1] for recent_patient in self.request.session["recent_patients"]]:
            self.request.session["recent_patients"].append(tuple([str(patient), str(patient.pk)]))
        elif str(patient.pk) != self.request.session["recent_patients"][0][1]:
            self.request.session["recent_patients"].remove(
                next(
                    iter(
                        [
                            recent_patient
                            for recent_patient in self.request.session["recent_patients"]
                            if recent_patient[1] == str(patient.pk)
                        ]
                    )
                )
            )
            self.request.session["recent_patients"].insert(0, tuple([str(patient), str(patient.pk)]))

    def remove_patient_from_session(
        self,
        patient: Patient,
        delete: bool = False,
    ) -> None:
        self.request.session.pop("patient", None)
        self.request.session.pop("pk", None)
        if (
            delete
            and self.request.session.get("recent_patients", None)
            and str(patient.pk) in [recent_patient[1] for recent_patient in self.request.session["recent_patients"]]
        ):
            self.request.session["recent_patients"].remove(
                next(
                    iter(
                        [
                            recent_patient
                            for recent_patient in self.request.session["recent_patients"]
                            if recent_patient[1] == str(patient.pk)
                        ]
                    )
                )
            )

    def update_session_patient(self) -> None:
        patient = getattr(self, "user", None)
        if patient:
            self.add_patient_to_session(patient)
        else:
            self.remove_patient_from_session(patient)


class GoutHelperDetailMixin(AutoPermissionRequiredMixin, DetailView, PatientSessionMixin):
    class Meta:
        abstract = True

    object: "Aids"
    patient: Patient | None

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not request.GET.get("updated", None):
            self.object.update_aid(qs=self.object)
            self.object.update_related_objects(qs=self.object)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Does NOT call get_object(), which is called in dispatch().
        Required to set the patient and evaluate permissions."""

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["patient"] = self.patient
        # context.update({"str_attrs": get_str_attrs(self.object, self.object.user, self.request.user)})

        return context

    def get_object(self) -> "Aids":
        self.object = super().get_object()
        self.patient = self.object.patient
        return self.object

    def get_permission_object(self):
        return self.object.patient

    def get_queryset(self, **kwargs) -> "QuerySet[Any]":
        return self.object.related_objects.filter(pk=self.kwargs["pk"])


class GoutHelperEditMixin:
    @cached_property
    def ckddetail(self) -> bool:
        """Method that returns True if CKD is in the medhistory_details dict."""
        return hasattr(self, "medhistory_detail_forms") and "ckddetail" in self.medhistory_detail_forms.keys()

    def form_invalid(self, form):
        response = super().form_invalid(form)
        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        if next_url:
            return HttpResponseRedirect(f"{self.request.path}?next={next_url}")
        return response

    def form_valid(self, **kwargs) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Method to be called if all forms are valid."""
        self.form_valid_init()
        self.from_valid_update_fks()
        self.form_valid_end(**kwargs)
        return self.form_valid_return(**kwargs)

    def form_valid_init(self) -> None:
        if self.form_valid_form_should_save():
            self.object = self.form.save(commit=False)
            self.save_object = True
            if self.form.instance.patient is None:
                self.form.instance.patient = self.patient
        else:
            self.object = self.form.instance
            self.save_object = False

    def form_valid_form_should_save(self) -> bool:
        return (
            self.form.has_changed
            or self.oto_forms
            # TODO: put these into another property that can be overwritten on child views
            # TODO: that have one to one relations that may need editing
            and (self.oto_2_save or self.oto_2_rem)
            and self.form.instance.patient is None
        )

    def from_valid_update_fks(self) -> None:
        """Method to update foreign key relationships in child views."""
        if self.save_object:
            self.object.full_clean()
            self.object.save()

    def form_valid_end(self, **kwargs) -> Union["HttpResponseRedirect", "HttpResponse"]:
        self.object.update_aid(qs=self.object)

    def form_valid_return(self, **kwargs) -> Union["HttpResponseRedirect", "HttpResponse"]:
        messages.success(self.request, self.get_success_message(self.form.cleaned_data))
        if self.request.htmx:
            return kwargs.get("htmx")
        return HttpResponseRedirect(self.get_success_url())

    def get(self, request, *args, **kwargs):
        """Overwritten to not call get_object()."""
        self.set_forms()
        return self.render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        if "patient" not in kwargs and self.patient:
            kwargs["patient"] = self.patient
        kwargs.update({"str_attrs": self.str_attrs})
        return super().get_context_data(**kwargs)

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs.update({**self.subform_kwargs})
        return kwargs

    def get_patient_qs(self, pk: str) -> "QuerySet[Patient]":
        """Returns a QuerySet of Patient objects. Meant to be overwritten by child
        classes to select_related or prefetch_related objects that can be checked for
        by the view for redirection to an update, rather than a create, view."""

        return Patient.objects.filter(pk=pk)

    def get_permission_object(self):
        """The view's permission_object is the patient, which is either an attribute
        of the view's object or derived from the view's patient kwarg."""
        return self.patient

    def get_success_url(self):
        """Overwritten to take optional next parameter from url, which is used to direct
        the user to a subsection of the page that was updated (i.e. FlareAid from Flare DetailView)"""
        next_url = self.request.POST.get("next", None)
        if next_url:
            next_url += f"?updated=True&related_object_id=#{self.object_attr}-card"
            return next_url
        else:
            return super().get_success_url() + "?updated=True"

    @cached_property
    def goutdetail(self) -> bool:
        """Method that returns True if GOUT is in the medhistorys dict."""
        return hasattr(self, "medhistory_detail_forms") and "goutdetail" in self.medhistory_detail_forms.keys()

    @cached_property
    def object_attr(self) -> str:
        return self.object.__class__.__name__.lower()

    def post(self, request, *args, **kwargs):
        self.post_init()
        if self.post_forms_valid():
            self.post_process_forms()
            self.post_errors()
        else:
            self.errors_bool = False
            self.errors = self.render_errors()

    def post_init(self) -> None:
        self.set_forms()
        form_class = self.get_form_class()
        self.form = form_class(
            **self.get_form_kwargs(),
        )

    def post_forms_valid(self) -> bool:
        """Overwritten in child classes to validate additional forms and formsets."""
        return self.form.is_valid()

    def post_process_forms(self) -> None:
        """Parent method for child classes to inherit. super() will be called in the child class."""
        self.errors_bool = False
        self.form.save(commit=False)

    def post_errors(self) -> Union["HttpResponse", None]:
        self.errors = self.render_errors() if self.errors_bool else None

    @cached_property
    def patient(self) -> User | None:
        """Method that returns the User object from the username kwarg
        and sets the user attr on the view."""
        if self.object.patient and not self.object._state.adding:
            return self.object.patient
        patient_pk = self.kwargs.get("patient")
        if patient_pk:
            return self.get_patient_qs(pk=patient_pk).get()
        return None

    def render_errors(self) -> "HttpResponse":
        """Renders forms with errors in multiple locations in post()."""
        context = self.get_errors_context()
        return self.render_to_response(
            self.get_context_data(
                form=self.form,
                **context,
            )
        )

    def get_errors_context(self) -> dict[str, Any]:
        """To be overwritten by child classes to add additional forms to the errors context."""
        return self.get_context_data(form=self.form)

    def set_forms(self) -> None:
        """Method that sets attributes for forms and formsets."""
        self.set_lab_formsets()
        self.set_medallergy_forms()
        self.set_medhistory_forms()
        self.set_medhistory_detail_forms()
        self.set_oto_forms()

    def set_lab_formsets(self) -> None:
        self.lab_formsets = (
            {lab_formset[0]._meta.model.__class__.__name__.lower(): lab_formset for lab_formset in self.LAB_FORMSETS}
            if hasattr(self, "LAB_FORMSETS")
            else {}
        )

    def set_medallergy_forms(self) -> None:
        self.medallergy_forms = (
            {f"medallergy_{treatment}_form": ma_form for treatment, ma_form in self.MEDALLERGY_FORMS.items()}
            if hasattr(self, "MEDALLERGY_FORMS")
            else {}
        )

    def set_medhistory_forms(self) -> None:
        self.medhistory_forms = (
            {f"{mhtype}_form": mh_form for mhtype, mh_form in self.MEDHISTORY_FORMS.items()}
            if hasattr(self, "MEDHISTORY_FORMS")
            else {}
        )

    def set_medhistory_detail_forms(self) -> None:
        self.medhistory_detail_forms = (
            {f"{mhdet}": mh_det_form for mhdet, mh_det_form in self.MEDHISTORY_DETAIL_FORMS.items()}
            if hasattr(self, "MEDHISTORY_DETAIL_FORMS")
            else {}
        )

    def set_oto_forms(self) -> None:
        self.oto_forms = (
            {f"{oto}_form": oto_form for oto, oto_form in self.OTO_FORMS.items()} if hasattr(self, "OTO_FORMS") else {}
        )

    @cached_property
    def str_attrs(self) -> dict[str, str]:
        """Returns a dict of string attributes to make forms context-sensitive."""
        return get_str_attrs_dict(self.patient, self.request.user)

    @property
    def subform_kwargs(self) -> dict[str, Any]:
        return {
            "patient": self.patient,
            "request_user": self.request.user,
            "str_attrs": self.str_attrs,
        }

    @staticmethod
    def validate_form_list(form_list: list[ModelForm]) -> bool:
        """Method to validate a list of forms.

        Args:
            form_list: A list of ModelForms to validate.

        Returns:
            True if all forms are valid, False otherwise."""
        forms_valid = True
        for form in form_list:
            if not form.is_valid():
                forms_valid = False
        return forms_valid

    @staticmethod
    def validate_formset_list(formset_list: list["BaseModelFormSet"]) -> bool:
        """Method to validate a list of formsets.

            formset_list: A list of BaseModelFormSets to validate.

        Returns:
            True if all formsets are valid, False otherwise."""
        formsets_valid = True
        for formset in formset_list:
            if not formset.is_valid():
                formsets_valid = False
        return formsets_valid


class LabFormSetsMixin(GoutHelperEditMixin):
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Overwritten to add the lab formsets to the context."""

        context = super().get_context_data(**kwargs)

        for lab, lab_tup in self.lab_formsets.items():
            self.update_lab_formset_context(
                context=context,
                lab=lab,
                lab_formset=lab_tup[0],
                lab_formset_helper=lab_tup[1],
            )

        return context

    def get_errors_context(self) -> dict[str, Any]:
        """Overwritten to add the lab formsets to the errors context."""
        context = super().get_errors_context()
        context.update(
            {
                **(
                    {
                        # https://stackoverflow.com/questions/23983908/multiple-key-value-pairs-in-dict-comprehension
                        k: v
                        for pair in self.lab_formsets.items()
                        for k, v in zip((f"{pair[0]}_formset", f"{pair[0]}_formset_helper"), pair[1])
                    }
                )
            }
        )
        return context

    def update_lab_formset_context(
        self,
        context: dict[str, Any],
        lab: str,
        lab_formset: "BaseModelFormSet",
        lab_formset_helper: "FormHelper",
    ) -> None:
        """ "Method that checks if a lab formset is in the context and adds it if it is not.
        Adds kwargs to the formset to inform the labs' queryset, as the lab may belong to one of
        the view's models OneToOne fields and not the model itself. Also adds the formset helper
        to the context if it is not already there."""

        if f"{lab}_formset" not in context:
            queryset_kwargs = self.get_lab_formset_queryset_kwargs(lab_formset)

            context[f"{lab}_formset"] = self.get_lab_formset_kwargs(lab, queryset_kwargs)

        if f"{lab}_formset_helper" not in context:
            context[f"{lab}_formset_helper"] = lab_formset_helper

    def get_lab_formset_queryset_kwargs(
        self,
        lab_formset: "BaseModelFormSet",
    ) -> dict[str, Any] | None:
        """Method that gets kwargs for a lab formset instance. Returns None if no extra kwargs are needed."""

        # If the lab is a ForeignKey of the view's model
        # return kwargs to filter the queryset for the model and the view's object
        # only if the view's object is not being added
        if self.lab_is_fk(lab_formset.model):
            return {self.object_attr: self.object} if not self.object._state.adding else {}
        else:
            # Otherwise, if the lab is a ForeignKey of one of the view's model's OneToOne related models
            # return kwargs to filter the queryset for the related model and the instance on the view's object
            rel_oto = self.lab_is_oto_fk(lab_model=lab_formset.model)
            if rel_oto:
                oto_attr = rel_oto.name.lower()
                rel_oto = getattr(self.object, oto_attr, None) if not self.object._state.adding else None
                return {oto_attr: rel_oto} if rel_oto else {}
            # Otherwise, the lab must be a ForeignKey of the User model
            # return kwargs to filter the queryset for the patient
            else:
                return {"patient": self.patient} if self.patient else {}

    def lab_is_fk(self, lab_model: Model) -> bool:
        """Method that checks if a lab model is a foreign key of the view's model."""
        return lab_model in get_model_foreignkey_fields(self.model)

    def lab_is_oto_fk(self, lab_model: Model) -> Union["OneToOneField", None]:
        """Method that checks if a lab model is a foreign key of one of the view's model's
        one-to-one related models. Returns the one-to-one field if it is."""
        return next(
            iter(
                fk
                for fk in [get_model_foreignkey_fields(field.model) for field in get_model_onetoone_fields(self.model)]
                if fk.model == lab_model
            ),
            None,
        )

    def from_valid_update_fks(self) -> None:
        super().from_valid_update_fks()
        self.form_valid_save_and_delete_labs()

    def form_valid_save_and_delete_labs(self) -> None:
        if self.labs_2_save:
            # Modify and remove labs from the object
            for lab in self.labs_2_save:
                if self.patient:
                    if lab.patient is None:
                        lab.patient = self.patient
                if self.lab_is_fk(lab.__class__):
                    if getattr(lab, self.object_attr, None) is None:
                        setattr(lab, self.object_attr, self.object)
                else:
                    rel_oto = self.lab_is_oto_fk(lab.__class__)
                    oto_attr = rel_oto.name.lower() if rel_oto else None
                    if oto_attr and getattr(lab, oto_attr, None) is None:
                        setattr(lab, oto_attr, getattr(self.object, oto_attr))
                lab.save()
        if self.labs_2_rem:
            for lab in self.labs_2_rem:
                lab.delete()

    def post_init(self) -> None:
        super().post_init()
        self.post_populate_lab_formsets()

    def post_populate_lab_formsets(self) -> None:
        """Method to populate a dict of lab forms with POST data in the post() method."""
        for lab, lab_tup in self.lab_formsets.items():
            queryset_kwargs = self.get_lab_formset_queryset_kwargs(lab_tup[0])
            self.lab_formsets.update(
                {
                    lab: (
                        self.get_lab_formset_kwargs(lab, queryset_kwargs),
                        lab_tup[1],
                    )
                }
            )

    def post_forms_valid(self) -> bool:
        other_forms_valid = super().post_forms_valid()
        lab_formsets_valid = self.validate_formset_list(
            formset_list=[lab_tup[0] for lab_tup in self.lab_formsets.values()]
        )
        return other_forms_valid and lab_formsets_valid

    def post_process_forms(self) -> None:
        super().post_process_forms()
        self.post_process_lab_formsets()

    def post_process_lab_formsets(self) -> None:
        """Method to process the forms in a Lab formset for the post() method.
        Requires a list of existing labs (can be empty) to iterate over and compare to the forms in the
        formset to identify labs that need to be removed or updated."""

        def _lab_needs_relation_set(lab: "Lab") -> bool:
            if self.lab_is_fk(lab.__class__):
                return getattr(lab, self.object_attr, None) is None
            else:
                if self.lab_is_oto_fk(lab.__class__):
                    oto_attr = self.lab_is_oto_fk(lab.__class__).name.lower()
                    return getattr(lab, oto_attr, None) is None
                else:
                    return lab.patient is None

        def _lab_qs_object(lab: "Lab") -> Union["Aids", "Aki", Patient, None]:
            if self.lab_is_fk(lab.__class__):
                return self.object
            else:
                if self.lab_is_oto_fk(lab.__class__):
                    oto_attr = self.lab_is_oto_fk(lab.__class__).name.lower()
                    return getattr(self.object, oto_attr, None)
                else:
                    return self.patient

        # Set attrs for labs to save and remove
        self.labs_2_save: list["Lab"] = []
        self.labs_2_rem: list["Lab"] = []

        if self.lab_formsets:
            for lab_name, lab_tup in self.lab_formsets.items():
                qs_object = _lab_qs_object(lab_tup[0].model())
                qs_attr = (
                    get_or_create_qs_attr(
                        qs_object,
                        lab_name,
                    )
                    if qs_object
                    else None
                )
                # Check for and iterate over the existing queryset of labs to catch objects that
                # are not changed in the formset but NEED to be saved for the view (i.e. to add relations)
                if qs_attr:
                    cleaned_data = lab_tup[0].cleaned_data
                    for lab in qs_attr:
                        for lab_form in cleaned_data:
                            lab_id = lab_form.get("id", None)
                            if lab_id:
                                if lab_id == lab:
                                    if not lab_form["DELETE"]:
                                        if _lab_needs_relation_set(lab):
                                            self.labs_2_save.append(lab)
                                        break
                            else:
                                pass
                        else:
                            self.labs_2_rem.append(lab)
                for form in lab_tup[0]:
                    if form.instance_should_persist and (
                        (form.instance and form.has_changed())
                        or form.instance is None
                        or _lab_needs_relation_set(form.instance)
                    ):
                        self.labs_2_save.append(form.instance)

    def get_lab_formset_kwargs(
        self,
        lab: str,
        queryset_kwargs: dict[str, Any] | None,
    ) -> "BaseModelFormSet":
        formset_kwargs = {
            "queryset": (
                getattr(self, f"{lab}_formset_qs").filter(**queryset_kwargs)
                if queryset_kwargs
                else getattr(self, f"{lab}_formset_qs").none()
            ),
            "prefix": lab,
            "form_kwargs": self.subform_kwargs,
        }
        if self.request.method == "POST":
            formset_kwargs.update({"data": self.request.POST})
        return self.lab_formsets[lab][0](
            **formset_kwargs,
        )


class MedAllergyFormMixin(GoutHelperEditMixin):
    def get_context_data(self, **kwargs):
        """Ovewritten to add the medallergy forms to the context."""

        context = super().get_context_data(**kwargs)

        for treatment, medallergy_form in self.medallergy_forms.items():
            self.update_ma_form_context(context, treatment, medallergy_form)

        return context

    def get_errors_context(self) -> dict[str, Any]:
        """Overwritten to add the medallergy forms to the errors context."""
        context = super().get_errors_context()
        context.update({**self.medallergy_forms})
        return context

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        # Pass the medallergy treatments to the form kwargs so the form will render the MedAllergyForms
        if self.medallergy_forms:
            kwargs["medallergys"] = self.medallergy_forms.keys()
        return kwargs

    def update_ma_form_context(
        self,
        context: dict[str, Any],
        treatment: str,
        ma_form: ModelForm | type[ModelForm],
    ) -> None:
        form_str = f"medallergy_{treatment}_form"
        if form_str not in context:
            context[form_str] = (
                ma_form
                if isinstance(ma_form, ModelForm)
                else ma_form(
                    **self.get_ma_form_kwargs(
                        treatment=treatment,
                        ma_obj=self.get_ma_obj(treatment),
                    )
                )
            )

    def get_ma_obj(self, treatment: "Treatments") -> Union["MedAllergy", None]:
        return getattr(self.patient, f"{treatment.lower()}_medallergy", None) if self.patient else None

    @staticmethod
    def get_ma_form_initial(
        ma_obj: Union["MedAllergy", None],
    ) -> dict[str, Any]:
        return {
            f"medallergy_{ma_obj.treatment}": ma_obj.value if ma_obj else None,
            f"{ma_obj.treatment}_matype": ma_obj.matype if ma_obj else None,
        }

    def get_ma_form_kwargs(self, treatment: "Treatments", ma_obj: Union["MedAllergy", None]) -> dict[str, Any]:
        kwargs = {
            "treatment": treatment,
            "instance": ma_obj,
            "initial": self.get_ma_form_initial(ma_obj),
            **self.subform_kwargs,
        }
        if self.request.method == "POST":
            kwargs.update({"data": self.request.POST})
        return kwargs

    def post_init(self) -> None:
        super().post_init()
        self.post_populate_ma_forms()

    def post_populate_ma_forms(self) -> None:
        """Method to populate the forms for the MedAllergys for the post() method."""
        for treatment, medallergy_form in self.medallergy_forms.items():
            self.medallergy_forms.update(
                {
                    treatment: medallergy_form(
                        **self.get_ma_form_kwargs(
                            treatment=treatment,
                            ma_obj=self.get_ma_obj(treatment),
                        )
                    )
                }
            )

    def post_forms_valid(self) -> bool:
        other_forms_valid = super().post_forms_valid()
        ma_forms_valid = self.validate_form_list(form_list=self.medallergy_forms.values())
        return other_forms_valid and ma_forms_valid

    def post_process_forms(self) -> None:
        super().post_process_forms()
        self.post_process_ma_forms()

    def post_process_ma_forms(self) -> None:
        """Method to process the forms for the MedAllergys for the post() method."""

        self.ma_2_save: list["MedAllergy"] = []
        self.ma_2_rem: list["MedAllergy"] = []

        for treatment, medallergy_form in self.medallergy_forms.items():
            if f"medallergy_{treatment}" in medallergy_form.cleaned_data:
                ma_obj = getattr(self.patient, f"{treatment.lower()}_medallergy", None) if self.patient else None
                medallergy = medallergy_form.cleaned_data["treatment"]
                if ma_obj and not medallergy:
                    self.ma_2_rem.append(ma_obj)
                elif medallergy:
                    matype = medallergy_form.cleaned_data.get(f"{treatment}_matype", None)
                    if not ma_obj:
                        ma = medallergy_form.save(commit=False)
                        # MedAllergy fields need to be specified for the type of allergy
                        ma.treatment = medallergy
                        ma.matype = matype
                        self.ma_2_save.append(ma)
                    # MedAllergy type could potentially change during an update (i.e. to/from hypersensitivity)
                    elif matype and ma_obj.matype != matype:
                        ma_obj.matype = matype
                        self.ma_2_save.append(ma_obj)

    def from_valid_update_fks(self) -> None:
        super().from_valid_update_fks()
        self.form_valid_save_medallergys()
        self.form_valid_delete_medallergys()

    def form_valid_save_medallergys(self) -> None:
        for ma in self.ma_2_save:
            if ma.patient is None:
                ma.patient = self.patient
            ma.full_clean()
            ma.save()

    def form_valid_delete_medallergys(self) -> None:
        for ma in self.ma_2_rem:
            ma.delete()


class MedHistoryFormMixin(GoutHelperEditMixin):
    def get_context_data(self, **kwargs):
        """Overwritten to add MedHistory and MedHistoryDetail forms to the context."""

        context = super().get_context_data(**kwargs)

        # Need to check for MedHistory forms because some views will have just MedHistory Details
        if self.medhistory_forms:
            for mhtype, mh_form in self.medhistory_forms.items():
                self.update_mh_form_context(context=context, mhtype=mhtype, mh_form=mh_form)

        # Need to check for MedHistoryDetail forms because some views will have just MedHistorys
        if self.medhistory_detail_forms:
            for mhdet, mhdet_form in self.medhistory_detail_forms.items():
                self.update_mhdet_form_context(context=context, mhdet=mhdet, mhdet_form=mhdet_form)

        return context

    def update_mh_form_context(
        self,
        context: dict[str, Any],
        mhtype: str,
        mh_form: ModelForm | type[ModelForm],
    ) -> None:
        """Method to update the context with a MedHistory form and its related
        MedHistoryDetail form as needed."""

        form_str = f"{mhtype}_form"
        # Add the MedHistory form to the context if it is not already there
        if form_str not in context:
            context[form_str] = (
                mh_form
                # If the form is already an instance, it is being re-rendered with errors
                if isinstance(mh_form, ModelForm)
                else mh_form(**self.get_mh_form_kwargs(mhtype=mhtype, context=context))
            )

    def get_mh_form_kwargs(
        self,
        mhtype: MedHistoryTypes,
    ) -> dict[str, Any]:
        """Returns a dict of kwargs for the MedHistory form.
        Also updates context with the MedHistoryDetail form if needed."""

        mh_obj = getattr(self.patient, mhtype, None) if self.patient else None
        mh_kwargs = {}
        if self.request.method == "POST":
            mh_kwargs.update({"data": self.request.POST})
        # Check for the MedHistoryType's related MedHistoryDetail
        mh_det = f"{mhtype.lower()}detail"
        # Check if the MedHistoryType has a detail attr set on the view
        mh_det_attr = getattr(self, mh_det, False)
        # If so, there is a MedHistoryDetail form to render
        if mh_det_attr:
            mh_kwargs.update(
                {
                    mh_det: mh_det_attr,
                    # The sub_form kwarg indicates to the MedHistoryForm that there is an
                    # embedded MedHistoryDetail form to render
                    "sub_form": True,
                }
            )
        return {
            "instance": mh_obj,
            "initial": {f"{mhtype}-value": mh_obj.value} if mh_obj else None,
            **self.subform_kwargs,
            **mh_kwargs,
        }

    def update_mhdet_form_context(
        self,
        context: dict[str, Any],
        mhdet: str,
        mhdet_form: ModelForm | type[ModelForm],
    ) -> None:
        """Method to update the context with a MedHistoryDetail form."""

        form_str = f"{mhdet}_form"
        if form_str not in context:
            context[form_str] = (
                mhdet_form
                if isinstance(mhdet_form, ModelForm)
                else mhdet_form(**self.get_mhdet_form_kwargs(mhdet=mhdet))
            )

    def get_mhdet_form_kwargs(
        self,
        mhdet: Literal["baselinecreatinine", "ckddetail", "goutdetail"],
    ) -> dict[str, Any]:
        instance = getattr(self.patient, mhdet, None) if self.patient else None
        kwargs = {
            "instance": instance,
            **self.subform_kwargs,
        }
        if self.request.method == "POST":
            kwargs.update({"data": self.request.POST})
        return kwargs

    def get_errors_context(self) -> dict[str, Any]:
        """Overwritten to add the MedHistory and MedHistoryDetail forms to the errors context."""
        context = super().get_errors_context()
        if self.medhistory_forms:
            context.update({**self.medhistory_forms})
        if self.medhistory_detail_forms:
            context.update({**self.medhistory_detail_forms})
        return context

    def post_init(self) -> None:
        super().post_init()
        if self.medhistory_forms:
            self.post_populate_mh_forms()
        if self.medhistory_detail_forms:
            self.post_populate_mhdet_forms()

    def post_populate_mh_forms(self) -> None:
        """Populates forms for MedHistory and MedHistoryDetail objects in post() method."""

        for mhtype, mh_form in self.medhistory_forms.items():
            self.medhistory_forms.update(
                {
                    mhtype: mh_form(
                        **self.get_mh_form_kwargs(mhtype=mhtype),
                    )
                }
            )

    def post_populate_mhdet_forms(self) -> None:
        """Populates forms for MedHistoryDetail objects in post() method."""

        for mhdet, mhdet_form in self.medhistory_detail_forms.items():
            self.medhistory_detail_forms.update(
                {
                    mhdet: mhdet_form(
                        **self.get_mhdet_form_kwargs(mhdet=mhdet),
                    )
                }
            )

    def post_forms_valid(self) -> bool:
        other_forms_valid = super().post_forms_valid()
        mh_forms_valid = self.validate_form_list(self.medhistory_forms) if self.medhistory_forms else True
        mh_det_forms_valid = (
            self.validate_form_list(form_list=self.medhistory_detail_forms.values())
            if self.medhistory_detail_forms
            else True
        )
        return other_forms_valid and mh_forms_valid and mh_det_forms_valid

    def post_process_forms(self) -> None:
        super().post_process_forms()
        self.post_process_mh_forms()
        self.post_process_mhdet_forms()

    def post_process_mh_forms(
        self,
    ) -> tuple[
        list["MedHistory"],
        list["MedHistory"],
        list["CkdDetailForm", BaselineCreatinine, "GoutDetailForm"],
        list[CkdDetail, BaselineCreatinine, GoutDetail],
    ]:
        """Method that processes the MedHistory forms in the post() method."""

        self.mhs_2_save: list["MedHistory"] = []
        self.mhs_2_remove: list["MedHistory"] = []

        # Create medhistory_qs attribute on the form instance if it doesn't exist
        # TODO: several deprecated methods commented out for linter to allow commit
        # get_or_create_qs_attr(post_qs_target, "medhistory")
        for mhtype, mh_form in self.medhistory_forms.items():
            mh_obj = self.get_mh_obj(mhtype)
            if self.get_mh_cleaned_value(mhtype, mh_form.cleaned_data):
                if mh_obj:
                    if (
                        self.related_objects
                        and self.medhistory_needs_object_attr_update_for_any_related_object(mh_obj)
                        or self.medhistory_needs_object_attr_update(mh_obj, self.object, self.object_attr)
                        or self.user
                        and not mh_obj.user
                    ):
                        self.add_mh_to_qs(mh=mh_obj, qs=self.mhs_2_save)
                else:
                    mh_obj = mh_form.save(commit=False)
                    self.add_mh_to_qs(mh=mh_obj, qs=self.mhs_2_save)
                # self.add_mh_to_qs(mh=mh_obj, qs=post_qs_target.medhistorys_qs)
                if self.related_object:
                    self.add_mh_to_qs(mh=mh_obj, qs=self.related_object.medhistorys_qs)
                self.post_process_medhistory_detail(mhtype, mh_obj)
            elif mh_obj:
                self.mhs_2_remove.append(mh_obj)
                # self.post_remove_mh_from_medhistorys_qs(post_qs_target, mh_obj)

    def post_process_mhdet_forms(self) -> None:
        """Method that processes the MedHistoryDetail forms in the post() method."""

        self.mhdets_2_save: list["CkdDetailForm" | BaselineCreatinine | "GoutDetailForm"] = []
        self.mhdets_2_remove: list[CkdDetail | BaselineCreatinine | GoutDetail] = []

        for mhdet_form in self.medhistory_detail_forms.values():
            if mhdet_form.has_changed or not mhdet_form.instance:
                self.post_process_medhistory_detail(mhdet_form.instance.mhtype, mhdet_form.instance)

    def post_process_medhistory_detail(self, mhtype: MedHistoryTypes, medhistory: Union["MedHistory", None]) -> None:
        if mhtype == MedHistoryTypes.GOUT and self.goutdetail:
            self.goutdetail_mh_post_process(
                gout=medhistory,
            )
        elif mhtype == MedHistoryTypes.CKD and self.ckddetail:
            self.ckddetail_mh_post_process(
                ckd=medhistory,
            )

    def post_process_menopause(self) -> None:
        gender = self.post_get_gender_value()
        if gender == Genders.FEMALE:
            ckd = self.medhistory_forms.get(MedHistoryTypes.CKD).value
            age = self.post_get_age_value()
            if not age and not ckd:
                dateofbirth_error = ValidationError(
                    "GoutHelper needs to know the date of birth for females without CKD."
                )
                self.medhistory_forms[f"{MedHistoryTypes.MENOPAUSE}"].add_error(
                    f"{MedHistoryTypes.MENOPAUSE}-value", dateofbirth_error
                )
                self.oto_forms["dateofbirth"].add_error("value", dateofbirth_error)
                self.errors_bool = True
                return
            age = age
            if age >= 40 and age < 60:
                menopause_value = self.medhistory_forms[f"{MedHistoryTypes.MENOPAUSE}"].cleaned_data.get(
                    f"{MedHistoryTypes.MENOPAUSE}-value", None
                )
                if menopause_value is None or menopause_value == "":
                    menopause_error = ValidationError(
                        message="For females between ages 40 and 60, we need to know the patient's \
menopause status to evaluate their flare."
                    )
                    self.medhistory_forms[f"{MedHistoryTypes.MENOPAUSE}"].add_error(
                        f"{MedHistoryTypes.MENOPAUSE}-value", menopause_error
                    )
                    self.errors_bool = True

    @staticmethod
    def get_mh_cleaned_value(
        mytype: MedHistoryTypes,
        cleaned_data: dict[str, Any],
    ) -> bool:
        """Method that searches a cleaned_data dict for a value key and returns
        True if found, False otherwise."""
        value = cleaned_data.get(f"{mytype}-value", False)
        return False if value == "" else value

    def ckddetail_mh_post_process(
        self,
        ckd: "MedHistory",
    ) -> None:
        """Method to process the CkdDetailForm and BaselineCreatinineForm
        as part of the post() method."""
        dateofbirth_form = self.get_dateofbirth_form()
        gender_form = self.get_gender_form()
        ckddet_form, bc_form, errors = CkdDetailFormProcessor(
            ckd=ckd,
            ckddetail_form=self.medhistory_detail_forms["ckddetail"],
            baselinecreatinine_form=self.medhistory_detail_forms["baselinecreatinine"],
            dateofbirth=dateofbirth_form if dateofbirth_form else self.get_dateofbirth_value(),
            gender=gender_form if gender_form is not None else self.get_gender_value(),
        ).process()
        if bc_form:
            self.baselinecreatinine_form_post_process()
        if ckddet_form:
            self.ckddetail_form_post_process()
        if errors and not self.errors_bool:
            self.errors_bool = errors

    def baselinecreatinine_form_post_process(self) -> None:
        baselinecreatinine_form = self.medhistory_detail_forms["baselinecreatinine"]
        if hasattr(baselinecreatinine_form.instance, "to_save"):
            self.mhdets_2_save.append(baselinecreatinine_form)
        elif hasattr(baselinecreatinine_form.instance, "to_delete"):
            self.mhdets_2_remove.append(baselinecreatinine_form)

    def ckddetail_form_post_process(self) -> None:
        ckddetail_form = self.medhistory_detail_forms["ckddetail"]
        if hasattr(ckddetail_form.instance, "to_save"):
            self.mhdets_2_save.append(ckddetail_form)
        elif hasattr(ckddetail_form.instance, "to_delete"):
            self.mhdets_2_remove.append(ckddetail_form)

    def goutdetail_mh_post_process(
        self,
        gout: Union["MedHistory", None],
    ) -> None:
        """Method that processes the GoutDetailForm as part of the post() method."""

        gd_form = self.medhistory_detail_forms["goutdetail"]
        gd_mh = getattr(gd_form.instance, "medhistory", None)
        if gd_form.has_changed or not gd_mh:
            self.mhdets_2_save.append(gd_form.save(commit=False))
            # Check if the form instance has a medhistory attr
            if not gd_mh and gout:
                # If not, set it to the medhistory instance
                gd_form.instance.medhistory = gout

    def post_remove_mh_from_medhistorys_qs(
        self,
        post_qs_target: Union["Aids", User],
        mh_obj: "MedHistory",
    ) -> None:
        if post_qs_target == self.query_object:
            post_qs_target.medhistorys_qs.remove(mh_obj)
        else:
            self.query_object.medhistorys_qs.remove(mh_obj)

    def from_valid_update_fks(self) -> None:
        super().from_valid_update_fks()
        self.form_valid_save_medhistorys()
        self.form_valid_save_medhistory_details()
        self.form_valid_delete_medhistorys()
        self.form_valid_delete_medhistory_details()

    def form_valid_update_mh_det_mh(self, mh: "MedHistory", commit: bool = True) -> None:
        """Checks if the MedHistory object has a MedHistoryDetail that needs to be saved and adjusts the set_date to
        timezone.now(), also checks if a MedHistoryDetail object that is going to be saved has a MedHistory object
        that needs to be updated and saved."""

        def need_to_save_mh(mh: "MedHistory") -> bool:
            return (self.mhs_2_save and mh not in self.mhs_2_save or not self.mhs_2_save) and (
                self.mhs_2_remove and mh not in self.mhs_2_remove or not self.mhs_2_remove
            )

        if need_to_save_mh(mh):
            mh.update_set_date_and_save(commit=commit)

    def form_valid_save_medhistorys(self) -> None:
        if self.mhs_2_save:
            if self.user:
                for mh in self.mhs_2_save:
                    if mh.user is None:
                        mh.user = self.user
                    mh.update_set_date_and_save()
            else:
                for mh in self.mhs_2_save:
                    if getattr(mh, self.object_attr, None) is None:
                        setattr(mh, self.object_attr, self.object)
                    self.form_valid_update_medhistory_related_objects(mh)
                    mh.update_set_date_and_save()

    def form_valid_update_medhistory_related_objects(self, mh: "MedHistory") -> None:
        for related_object in self.related_objects:
            related_object_attr = related_object.__class__.__name__.lower()
            if self.medhistory_compatible_with_aid_object(mh, related_object):
                if not getattr(mh, related_object_attr, None):
                    setattr(mh, related_object_attr, related_object)
                    self.add_mh_to_medhistorys_qs(mh, related_object)
                    self.add_mh_to_mhs_2_save(mh)
                else:
                    self.add_mh_to_medhistorys_qs(mh, related_object)

    @classmethod
    def add_mh_to_medhistorys_qs(cls, mh: "MedHistory", object: "Aids") -> None:
        cls.add_mh_to_qs(mh, getattr(object, "medhistorys_qs"))

    def add_mh_to_object_medhistorys_qs(self, mh: "MedHistory") -> None:
        self.add_mh_to_qs(mh, getattr(self.object, "medhistorys_qs"))

    def add_mh_to_related_object_medhistorys_qs(self, mh: "MedHistory") -> None:
        self.add_mh_to_qs(mh, getattr(self.related_object, "medhistorys_qs"))

    def add_mh_to_mhs_2_save(self, mh: "MedHistory") -> None:
        self.add_mh_to_qs(mh, self.mhs_2_save)

    @classmethod
    def medhistory_compatible_with_aid_object(cls, mh: "MedHistory", object: "Aids") -> bool:
        return (
            mh.medhistorytype in object.aid_medhistorys()
            or mh._state.adding
            and medhistorys_get_default_medhistorytype(mh) in object.aid_medhistorys()
        )

    @classmethod
    def medhistory_needs_object_attr_update(cls, mh: "MedHistory", object: "Aids", object_attr: str) -> bool:
        if not object_attr:
            object_attr = object.__class__.__name__.lower()
        return cls.medhistory_compatible_with_aid_object(mh, object) and not getattr(mh, object_attr, None)

    def form_valid_save_medhistory_details(self) -> None:
        if self.mhdets_2_save:
            for mh_det in self.mhdets_2_save:
                mh_det.save()
                self.form_valid_update_mh_det_mh(
                    mh_det.instance.medhistory if isinstance(mh_det, ModelForm) else mh_det.medhistory,
                )

    def form_valid_delete_medhistorys(self) -> None:
        if self.mhs_2_remove:
            for mh in self.mhs_2_remove:
                mh.update_set_date_and_save(commit=False)
                mh.delete()
                self.form_valid_remove_medhistory_from_related_objects(mh)

    def form_valid_remove_medhistory_from_related_objects(self, mh: "MedHistory") -> None:
        for related_object in self.related_objects:
            if mh.medhistorytype in related_object.aid_medhistorys():
                related_object_medhistory = next(
                    iter(
                        related_mh
                        for related_mh in related_object.medhistorys_qs
                        if related_mh.medhistorytype == mh.medhistorytype
                    ),
                    None,
                )
                if related_object_medhistory:
                    related_object.medhistorys_qs.remove(related_object_medhistory)

    def form_valid_delete_medhistory_details(self) -> None:
        if self.mhdets_2_remove:
            for mh_det in self.mhdets_2_remove:
                mh_det.instance.delete()
                self.form_valid_update_mh_det_mh(
                    mh_det.instance.medhistory if isinstance(mh_det, ModelForm) else mh_det.medhistory,
                )
                self.form_valid_remove_medhistorydetails_from_related_objects(mh_det.instance)

    def form_valid_remove_medhistorydetails_from_related_objects(
        self, mh_detail: Union["CkdDetail", "GoutDetail"]
    ) -> None:
        for related_object in self.related_objects:
            medhistorydetail_attr = f"{mh_detail.__class__.__name__.lower()}"
            if hasattr(related_object, medhistorydetail_attr):
                medhistory_attr = f"{mh_detail.medhistory.medhistorytype.lower()}"
                related_object_medhistory = getattr(related_object, medhistory_attr, None)
                # These are 100% necessary because of the cached_property decorator-the related medhistory (CKD, Gout)
                # references the now deleted medhistorydetail object (CKDDetail, GoutDetail)
                setattr(related_object_medhistory, medhistorydetail_attr, None)
                setattr(related_object, medhistorydetail_attr, None)


class OneToOneFormMixin(GoutHelperEditMixin):
    request: "HttpRequest"

    def get_context_data(self, **kwargs):
        """Overwritten to add OneToOne forms to the context."""

        context = super().get_context_data(**kwargs)

        for onetoone, oto_form in self.oto_forms.items():
            self.update_oto_form_context(context=context, onetoone=onetoone, oto_form=oto_form, query_obj=self.object)

        for onetoone, oto_form in self.patient_oto_forms.items():
            self.update_oto_form_context(
                context=context, onetoone=onetoone, oto_form=oto_form, query_obj=self.patient if self.patient else None
            )

        return context

    def get_errors_context(self) -> dict[str, Any]:
        """Overwritten to add the OneToOne forms to the errors context."""
        context = super().get_errors_context()
        context.update(
            {
                **self.oto_forms,
                **self.patient_oto_forms,
            }
        )
        return context

    def update_oto_form_context(
        self,
        context: dict[str, Any],
        onetoone: str,
        oto_form: ModelForm | type[ModelForm],
        query_obj: Model | None,
    ) -> None:
        """Method to update the context with a OneToOne form."""
        # When rendering errors, the ModelForm will already be an instance
        # and should be rendereda as such, containing errors.
        form_str = f"{onetoone}_form"
        if form_str not in context:
            if isinstance(oto_form, ModelForm):
                context[form_str] = oto_form
            # Otherwise, an instance needs to be created
            else:
                oto_obj = getattr(query_obj, onetoone, None) if query_obj else None
                context[form_str] = oto_form(
                    **{
                        "instance": oto_obj if oto_obj else oto_form._meta.model(),
                        "patient": self.patient,
                        "request_user": self.request.user,
                        "str_attrs": self.str_attrs,
                        "initial": (
                            getattr(query_obj, onetoone, None) if query_obj and not query_obj._state.adding else None
                        ),
                    }
                )

    def dispatch_user_missing_requirements(self, request: "HttpRequest") -> bool:
        return not self.user_has_required_otos or super().dispatch_user_missing_requirements(request)

    def form_valid_init(self) -> None:
        super().form_valid_init()
        self.form_valid_save_otos()
        self.form_valid_delete_otos()
        if self.req_otos and self.related_object:
            self.form_valid_related_object_otos()

    def form_valid_save_otos(self) -> None:
        if self.oto_2_save:
            for oto in self.oto_2_save:
                oto_attr = f"{oto.__class__.__name__.lower()}"
                if self.user and oto.user is None:
                    oto.user = self.user
                oto.save()
                if getattr(self.form.instance, oto_attr, None) is None:
                    if not self.user or oto_attr == "urate" or oto_attr == "aki":
                        setattr(self.form.instance, oto_attr, oto)

    def form_valid_delete_otos(self) -> None:
        if self.oto_2_rem:
            for oto in self.oto_2_rem:
                oto_class = oto.__class__.__name__.lower()
                if not self.user or oto_class == "urate" or oto_class == "aki":
                    setattr(self.form.instance, f"{oto.__class__.__name__.lower()}", None)
                oto.delete()

    def form_valid_related_object_otos(self):
        def check_if_oto_attr_in_related_object_fields(oto_attr: str) -> bool:
            return attr_is_in_model_fields(oto_attr, self.related_object)

        for oto_attr in self.req_otos:
            related_object_oto = getattr(self.related_object, oto_attr, None)
            if (
                related_object_oto
                and check_if_oto_attr_in_related_object_fields(oto_attr)
                and getattr(self.form.instance, oto_attr, None) is None
            ):
                setattr(self.form.instance, oto_attr, related_object_oto)

    @cached_property
    def aki(self) -> Union["Aki", None]:
        return self.get_aki()

    def get_aki(self):
        aki = getattr(self.query_object, "aki", None)
        return aki if aki else (getattr(self.object, "aki", None) if self.object else None)

    def get_aki_value(self):
        return "True" if self.aki else "False"

    def get_aki_status(self):
        return self.aki.Statuses(self.aki.status) if self.aki else None

    def get_aki_initial(self) -> dict[str, Any]:
        return {"value": self.get_aki_value(), "status": self.get_aki_status()}

    def get_urate(self) -> Union["Lab", None]:
        urate = getattr(self.query_object, "urate", None)
        return urate if urate else (getattr(self.object, "urate", None) if self.object else None)

    def get_urate_value(self):
        urate = self.get_urate()
        return urate.value if urate else None

    def post_populate_oto_forms(self) -> None:
        for onetoone, oto_form in self.oto_forms.items():
            if self.onetoone_not_attr_of_related_object(onetoone):
                oto_obj = self.get_oto_obj(onetoone) if self.query_object else None
                oto_form_kwargs = {
                    "instance": oto_obj if oto_obj else oto_form._meta.model(),
                    "patient": self.user,
                    "request_user": self.request.user,
                    "str_attrs": self.str_attrs,
                }
                oto_form_kwargs.update({"initial": self.get_onetoone_initial(onetoone=onetoone)})
                self.oto_forms.update({onetoone: oto_form(self.request.POST, **oto_form_kwargs)})

    def get_oto_obj(
        self,
        onetoone: str,
    ) -> Model:
        """Method that looks looks for a 1to1 related object on the query_object and returns it if found.
        If it's not, if the oto str is "urate", it looks for the 1to1 on the alt_obj and returns it if found."""
        oto_obj = getattr(self.query_object, onetoone, None) if self.query_object else None
        if not oto_obj and (onetoone == "urate" or onetoone == "aki"):
            oto_obj = getattr(self.object, onetoone, None) if self.object else None
        return oto_obj

    def onetoone_not_attr_of_related_object(self, onetoone: str) -> bool:
        return not self.related_object or (self.related_object and not getattr(self.related_object, onetoone, None))

    def post_init(self) -> None:
        super().post_init()
        self.post_populate_oto_forms()

    def post_forms_valid(self) -> bool:
        other_forms_valid = super().post_forms_valid()
        oto_forms_valid = self.validate_form_list(form_list=self.oto_forms.values()) if self.oto_forms else True
        return other_forms_valid and oto_forms_valid

    def post_get_dateofbirth_value(self) -> Union["date", None]:
        return self.oto_forms["dateofbirth"].cleaned_data["value"]

    def post_get_age_value(self) -> int | None:
        return age_calc(self.post_get_dateofbirth_value())

    def post_get_gender_value(self) -> Union["Gender", None]:
        return self.oto_forms["gender"].cleaned_data["value"]

    def post_process_forms(self) -> None:
        super().post_process_forms()
        self.post_process_oto_forms()

    def post_process_oto_forms(
        self,
    ) -> tuple[list[Model], list[Model]]:
        self.oto_2_save: list[Model] = []
        self.oto_2_rem: list[Model] = []
        for onetoone, oto_form in self.oto_forms.items():
            try:
                oto_form.check_for_value()
                # Check if the onetoone changed
                if oto_form.has_changed():
                    onetoone = oto_form.save(commit=False)
                    self.oto_2_save.append(onetoone)
                else:
                    onetoone = oto_form.instance
            # If EmptyRelatedModel exception is raised by the related model's form save() method,
            # Check if the related model exists and delete it if it does
            except EmptyRelatedModel:
                # Check if the related model has already been saved to the DB and mark for deletion if so
                if oto_form.instance and not oto_form.instance._state.adding:
                    # Set the related model's fields to their initial values to prevent
                    # IntegrityError from Django-Simple-History historical model on delete().
                    if hasattr(oto_form, "required_fields"):
                        for field in oto_form.required_fields:
                            setattr(oto_form.instance, field, oto_form.initial[field])
                    self.oto_2_rem.append(oto_form.instance)


class GoutHelperCreateView(
    GoutHelperEditMixin,
    CreateView,
):
    def dispatch(self, request, *args, **kwargs):
        """Overwritten to redirect if the user is attempting to create an instance of a model that the intended
        Pseudopatient already has an instance of and their relationship is a 1to1."""

        if self.patient_has_model_to_be_created:
            return self.dispatch_redirect_to_update_view()

        return super().dispatch(request, *args, **kwargs)

    @property
    def patient_has_model_to_be_created(self) -> bool:
        """Checks if the patient has an instance of the model to be created.
        It will have been fetched and set by the get_patient_qs() method."""

        return hasattr(self.patient, self.model.__name__.lower())

    def dispatch_redirect_to_update_view(self, request: "HttpRequest") -> HttpResponseRedirect:
        messages.error(request, f"{self.patient} already has a {self.model.__name__}. Please update it instead.")
        return HttpResponseRedirect(
            reverse(
                f"{self.model._meta.app_label}:update",
                kwargs={"pk": self.object.pk},
            )
        )


class GoutHelperUserEditMixin(
    PatientSessionMixin,
    OneToOneFormMixin,
    MedHistoryFormMixin,
    MedAllergyFormMixin,
):
    """Overwritten to modify related models around a User, rather than
    a GoutHelper DecisionAid or TreatmentAid object. Also to create a user."""

    def get_dateofbirth_form(self) -> "DateOfBirthForm":
        """Overwritten to avoid returning None if there is a User as is the case for the non-User edit view."""
        return self.oto_forms["dateofbirth"]

    def get_gender_form(self) -> "GenderForm":
        """Overwritten to avoid returning None if there is a User as is the case for the non-User edit view."""
        return self.oto_forms["gender"]

    def gout_form_is_in_mhs_2_save(self) -> bool:
        return any([isinstance(mh, Gout) for mh in self.mhs_2_save])

    def form_valid(self, **kwargs) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Overwritten to facilitate creating Users."""

        def create_pseudopatient() -> Patient:
            self.form.instance.username = uuid.uuid4().hex[:30]
            self.form.instance.role = Roles.PSEUDOPATIENT
            new_goutpatient = self.form.save()
            return new_goutpatient

        def create_pseudopatientprofile() -> None:
            with transaction.atomic():
                PseudopatientProfile.objects.create(
                    user=self.object,
                    provider=self.request.user if self.provider else None,
                    provider_alias=(
                        get_provider_alias(
                            provider=self.provider,
                            age=self.post_get_age_value(),
                            gender=self.post_get_gender_value(),
                        )
                        if self.provider
                        else None
                    ),
                )

        if self.create_view:  # pylint: disable=W0125
            self.object = create_pseudopatient()
        self.user = self.object
        self.form_valid_process_related_objects()
        # Save the OneToOne related models
        if self.oto_forms:
            self.form_valid_save_otos()
            self.form_valid_delete_otos()
        if self.req_otos and self.related_object:
            self.form_valid_related_object_otos()
        if self.medhistory_forms:
            self.form_valid_save_medhistorys()
            self.form_valid_save_medhistory_details()
            self.form_valid_delete_medhistorys()
            self.form_valid_delete_medhistory_details()
        if self.medallergy_forms:
            self.form_valid_save_medallergys()
            self.form_valid_delete_medallergys()
        if self.create_view:  # pylint: disable=W0125
            create_pseudopatientprofile()
        return HttpResponseRedirect(self.get_success_url())

    def form_valid_process_related_objects(self) -> None:
        if self.related_object:
            related_objects_related_objects = list_of_objects_related_objects(self.related_object)
            for related_object in related_objects_related_objects:
                related_object_attr = self.get_related_object_attr(related_object)
                setattr(self.related_object, related_object_attr, None)
                self.update_related_object_and_otos(related_object)
                self.update_related_object_medhistorys_qs(related_object, related_object_attr)
                if hasattr(related_object, "medallergys_qs"):
                    self.update_related_object_medallergys_qs(related_object, related_object_attr)
            self.update_related_object_and_otos(self.related_object)
            self.update_related_object_medhistorys_qs(self.related_object, self.related_object_attr)

    def form_valid_update_related_object_oto_user_foreign_keys(
        self,
        related_object_oto: Any,
    ) -> None:
        if hasattr(related_object_oto, "user_foreign_key_fields"):
            for fk_field in related_object_oto.user_foreign_key_fields:
                for fk in getattr(related_object_oto, f"{fk_field}s_qs"):
                    if fk.user is None:
                        fk.user = self.user
                        fk.full_clean()
                        fk.save()

    def update_related_obj_medhistory(
        self, mh: "MedHistory", mh_related_obj: Any | None, related_object_attr: str
    ) -> None:
        if mh_related_obj is not None:
            setattr(mh, related_object_attr, None)
        if mh.user is None:
            mh.user = self.user
        if mh not in self.mhs_2_save:
            self.mhs_2_save.append(mh)

    def update_related_object_medhistorys_qs(self, related_object: Any, related_object_attr: str) -> None:
        if not hasattr(related_object, "medhistorys_qs"):
            raise AttributeError("Related object must have a medhistorys_qs attribute.")
        for mh in related_object.medhistorys_qs:
            mh_related_obj = getattr(mh, related_object_attr, None)
            if mh_related_obj is not None or mh.user is None:
                # For some reason this is needed to prevent IntegrityError when saving the MedHistory
                # TODO: learn more about editing object references between separate lists
                mh_in_mhs_2_save = next((m for m in self.mhs_2_save if m == mh), None)
                self.update_related_obj_medhistory(
                    mh_in_mhs_2_save if mh_in_mhs_2_save else mh, mh_related_obj, related_object_attr
                )

    def update_related_object_medallergys_qs(self, related_object: Any, related_object_attr: str) -> None:
        if not hasattr(related_object, "medallergys_qs"):
            raise AttributeError("Related object must have a medallergys_qs attribute.")
        if self.form_valid_need_to_set_ma_save_rem_forms():
            self.medallergy_forms = True
            self.ma_2_save = []
            self.ma_2_rem = []
        for ma in related_object.medallergys_qs:
            ma_related_obj = getattr(ma, related_object_attr, None)
            if ma_related_obj is not None or ma.user is None:
                ma_in_ma_2_save = next((m for m in self.ma_2_save if m == ma), None)
                self.update_related_obj_medallergy(
                    ma_in_ma_2_save if ma_in_ma_2_save else ma, ma_related_obj, related_object_attr
                )

    def form_valid_need_to_set_ma_save_rem_forms(self) -> bool:
        return (
            not hasattr(self, "ma_2_save")
            or not hasattr(self, "ma_2_rem")
            or not hasattr(self, "medallergy_forms")
            or hasattr(self, "medallergy_forms")
            and not self.medallergy_forms
        )

    def update_related_obj_medallergy(
        self, ma: "MedAllergy", ma_related_obj: Any | None, related_object_attr: str
    ) -> None:
        if ma_related_obj is not None:
            setattr(ma, related_object_attr, None)
        if ma.user is None:
            ma.user = self.user
        if ma not in self.ma_2_save:
            self.ma_2_save.append(ma)

    def update_related_object_and_otos(self, related_object: Any) -> None:
        if self.update_related_object_oto_fields(related_object):
            related_object.full_clean()
            related_object.save()

    def update_related_object_oto(self, related_object: Any, oto: str, related_obj_oto: Any) -> None:
        setattr(related_object, oto, None)
        self.update_related_object_oto_user(related_obj_oto)

    def update_related_object_oto_user(self, related_obj_oto: Any) -> bool:
        if related_obj_oto.user is None:
            related_obj_oto.user = self.user
            self.oto_2_save.append(related_obj_oto)
            return True
        return False

    def update_related_object_oto_fields(self, related_object: Any) -> bool:
        save_related_obj = False
        for oto in get_model_onetoone_field_names(related_object):
            related_obj_oto = getattr(related_object, oto, None)
            if related_obj_oto:
                if oto in self.req_otos:
                    if related_obj_oto:
                        self.update_related_object_oto(related_object, oto, related_obj_oto)
                        if not save_related_obj:
                            save_related_obj = True
                    if related_object.user is None:
                        related_object.user = self.user
                        if not save_related_obj:
                            save_related_obj = True
                elif self.update_related_object_oto_user(related_obj_oto):
                    if not save_related_obj:
                        save_related_obj = True
            self.form_valid_update_related_object_oto_user_foreign_keys(related_obj_oto)
        return save_related_obj

    def form_valid_save_medhistory_details(self) -> None:
        if self.mhdets_2_save:
            for mh_det in self.mhdets_2_save:
                # Call self.gout_form_is_in_mhs_2_save() at the end of the conditional to prevent
                # IntegrityError when creating a Pseudopatient from a Flare that already has a Gout MedHistory
                if self.create_view and isinstance(mh_det, GoutDetail) and not self.gout_form_is_in_mhs_2_save():
                    mh_det.medhistory = Gout.objects.create(user=self.object)
                mh_det.save()
                self.form_valid_update_mh_det_mh(
                    mh_det.instance.medhistory if isinstance(mh_det, ModelForm) else mh_det.medhistory,
                )

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Provider the view is trying to create
        a Pseudopatient for."""
        if self.create_view:  # pylint: disable=W0125
            return self.provider_username
        else:
            return self.object

    def goutdetail_mh_context(
        self,
        kwargs: dict[str, Any],
        mh_obj: Union["MedHistory", User, None] = None,
    ) -> None:
        """Overwritten to always raise Continue, which will skip adding the GoutForm to the context."""
        if "goutdetail_form" not in kwargs:
            goutdetail_i = getattr(mh_obj, "goutdetail", None) if mh_obj else None
            goutdetail_form = self.medhistory_detail_forms["goutdetail"]
            kwargs["goutdetail_form"] = (
                goutdetail_form
                if isinstance(goutdetail_form, ModelForm)
                else goutdetail_form(
                    instance=goutdetail_i,
                    patient=self.user,
                    request_user=self.request.user,
                    str_attrs=self.str_attrs,
                )
            )
            raise Continue

    def goutdetail_mh_post_pop(
        self,
        gout: Union["MedHistory", None],
    ) -> None:
        """Overwritten to always raise Continue, which will skip adding the GoutForm to the context."""
        if gout:
            gd = getattr(gout, "goutdetail", None)
        else:
            gd = GoutDetail()
        self.medhistory_detail_forms.update(
            {
                "goutdetail": self.medhistory_detail_forms["goutdetail"](
                    self.request.POST,
                    instance=gd,
                    str_attrs=self.str_attrs,
                    patient=self.user,
                    request_user=self.request.user,
                )
            }
        )
        raise Continue

    @cached_property
    def provider_username(self) -> str | None:
        """Method that returns the username kwarg from the url."""
        return self.kwargs.get("username", None)

    @cached_property
    def provider(self) -> User | None:
        return (
            self.request.user
            if self.provider_username and self.request.user.username == self.provider_username
            else None
        )

    @cached_property
    def user(self) -> User | None:
        return None

    @cached_property
    def related_objects(self) -> list[Model]:
        return []
