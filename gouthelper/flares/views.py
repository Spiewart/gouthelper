from typing import TYPE_CHECKING, Any

from django.apps import apps  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # type: ignore
from django.core.exceptions import ValidationError  # type: ignore
from django.views.generic import DetailView, TemplateView, View  # type: ignore

from ..contents.choices import Contexts
from ..dateofbirths.forms import DateOfBirthForm
from ..dateofbirths.helpers import age_calc
from ..dateofbirths.models import DateOfBirth
from ..genders.choices import Genders
from ..genders.forms import GenderForm
from ..genders.models import Gender
from ..labs.forms import UrateFlareForm
from ..labs.models import Urate
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import (
    AnginaForm,
    CadForm,
    ChfForm,
    CkdForm,
    GoutForm,
    HeartattackForm,
    HypertensionForm,
    MenopauseForm,
    PvdForm,
    StrokeForm,
)
from ..medhistorys.models import Angina, Cad, Chf, Ckd, Gout, Heartattack, Hypertension, Menopause, Pvd, Stroke
from ..utils.views import MedHistorysModelCreateView, MedHistorysModelUpdateView
from .forms import FlareForm
from .models import Flare
from .selectors import flare_userless_qs

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore
    from django.forms import ModelForm  # type: ignore

    from ..utils.types import MedAllergyAidHistoryModel


class FlareAbout(TemplateView):
    """About Flares"""

    template_name = "flares/about.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"content": self.content})
        return context

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="about", context=Contexts.FLARE, tag=None)


class FlareBase(View):
    class Meta:
        abstract = True

    form_class = FlareForm
    model = Flare

    onetoones = {
        "dateofbirth": {"form": DateOfBirthForm, "model": DateOfBirth},
        "gender": {"form": GenderForm, "model": Gender},
        "urate": {"form": UrateFlareForm, "model": Urate},
    }
    medhistorys = {
        MedHistoryTypes.ANGINA: {"form": AnginaForm, "model": Angina},
        MedHistoryTypes.CAD: {"form": CadForm, "model": Cad},
        MedHistoryTypes.CHF: {"form": ChfForm, "model": Chf},
        MedHistoryTypes.CKD: {"form": CkdForm, "model": Ckd},
        MedHistoryTypes.GOUT: {"form": GoutForm, "model": Gout},
        MedHistoryTypes.HEARTATTACK: {"form": HeartattackForm, "model": Heartattack},
        MedHistoryTypes.HYPERTENSION: {"form": HypertensionForm, "model": Hypertension},
        MedHistoryTypes.MENOPAUSE: {"form": MenopauseForm, "model": Menopause},
        MedHistoryTypes.PVD: {"form": PvdForm, "model": Pvd},
        MedHistoryTypes.STROKE: {"form": StrokeForm, "model": Stroke},
    }

    def post_process_menopause(
        self,
        medhistorys_forms: dict[str, "ModelForm"],
        object: "MedAllergyAidHistoryModel",
        errors: bool,
    ) -> tuple[dict[str, "ModelForm"], bool]:
        if object.gender and object.gender.value == Genders.FEMALE and object.dateofbirth:
            age = age_calc(object.dateofbirth.value)
            if (
                age >= 40
                and age < 60
                and (
                    medhistorys_forms[f"{MedHistoryTypes.MENOPAUSE}_form"].cleaned_data.get(
                        f"{MedHistoryTypes.MENOPAUSE}-value"
                    )
                    is None
                )
            ):
                menopause_error = ValidationError(
                    message="For females between ages 40 and 60, we need to know the patient's \
menopause status to evaluate their flare."
                )
                medhistorys_forms[f"{MedHistoryTypes.MENOPAUSE}_form"].add_error(
                    f"{MedHistoryTypes.MENOPAUSE}-value", menopause_error
                )
                errors = True
        return medhistorys_forms, errors

    def post_process_urate_check(
        self,
        form: "ModelForm",
        object: "MedAllergyAidHistoryModel",
        onetoone_forms: dict[str, "ModelForm"],
        errors: bool,
    ) -> tuple["ModelForm", dict[str, "ModelForm"], bool]:
        if form.cleaned_data.get("urate_check", None) and (
            not getattr(object, "urate") or not getattr(object.urate, "value")
        ):
            urate_error = ValidationError(message="If urate was checked, we should know it!")
            form.add_error("urate_check", urate_error)
            onetoone_forms["urate_form"].add_error("value", urate_error)
            errors = True
        return form, onetoone_forms, errors


class FlareCreate(FlareBase, MedHistorysModelCreateView, SuccessMessageMixin):
    """Creates a new Flare"""

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            object_data,
            onetoone_forms,
            medallergys_forms,
            medhistorys_forms,
            medhistorydetails_forms,
            lab_formset,
            onetoones_to_save,
            medallergys_to_add,
            medhistorys_to_add,
            medhistorydetails_to_add,
            labs_to_add,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        medhistorys_forms, errors = self.post_process_menopause(
            medhistorys_forms=medhistorys_forms, object=object_data, errors=errors
        )
        form, onetoone_forms, errors = self.post_process_urate_check(
            form=form, object=object_data, onetoone_forms=onetoone_forms, errors=errors
        )
        if errors:
            return super().post.render_errors()
        else:
            return self.form_valid(
                form=form,  # type: ignore
                medallergys_to_add=medallergys_to_add,
                onetoones_to_save=onetoones_to_save,
                medhistorydetails_to_add=medhistorydetails_to_add,
                medhistorys_to_add=medhistorys_to_add,
                labs_to_add=labs_to_add,
            )


class FlareDetail(DetailView):
    model = Flare
    object: Flare

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        for content in self.contents:
            context.update({content.slug: {content.tag: content}})  # type: ignore
        return context

    def get_queryset(self) -> "QuerySet[Any]":
        return flare_userless_qs(self.kwargs["pk"])

    def get_object(self, *args, **kwargs) -> Flare:
        flare: Flare = super().get_object(*args, **kwargs)  # type: ignore
        flare.update()
        return flare

    @property
    def contents(self):
        return apps.get_model("contents.Content").objects.filter(context=Contexts.FLARE)


class FlareUpdate(FlareBase, MedHistorysModelUpdateView, SuccessMessageMixin):
    """Updates a Flare"""

    def get_initial(self) -> dict[str, Any]:
        """Overwrite get_initial() to populate form non-field field inputs"""
        initial = super().get_initial()
        if getattr(self.object, "crystal_analysis") is not None:
            initial["aspiration"] = True
        elif getattr(self.object, "diagnosed"):
            initial["aspiration"] = False
        else:
            initial["aspiration"] = None
        if getattr(self.object, "urate", None):
            initial["urate_check"] = True
        else:
            initial["urate_check"] = False
        return initial

    def get_queryset(self):
        return flare_userless_qs(self.kwargs["pk"])

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            object_data,
            onetoone_forms,
            medhistorys_forms,
            medhistorydetails_forms,
            medallergys_forms,
            lab_formset,
            medallergys_to_add,
            medallergys_to_remove,
            onetoones_to_delete,
            onetoones_to_save,
            medhistorydetails_to_add,
            medhistorys_to_add,
            medhistorys_to_remove,
            labs_to_add,
            labs_to_remove,
            labs_to_update,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        medhistorys_forms, errors = self.post_process_menopause(
            medhistorys_forms=medhistorys_forms, object=object_data, errors=errors
        )
        form, onetoone_forms, errors = self.post_process_urate_check(
            form=form, object=object_data, onetoone_forms=onetoone_forms, errors=errors
        )
        if errors:
            return super().post.render_errors()
        return self.form_valid(
            form=form,  # type: ignore
            medallergys_to_add=medallergys_to_add,
            medallergys_to_remove=medallergys_to_remove,
            onetoones_to_delete=onetoones_to_delete,
            onetoones_to_save=onetoones_to_save,
            medhistorydetails_to_add=medhistorydetails_to_add,
            medhistorys_to_add=medhistorys_to_add,
            medhistorys_to_remove=medhistorys_to_remove,
            labs_to_add=labs_to_add,
            labs_to_remove=labs_to_remove,
            labs_to_update=labs_to_update,
        )
