from typing import TYPE_CHECKING, Any

from django.apps import apps  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # type: ignore
from django.db.models import Q  # type: ignore
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView  # type: ignore

from ..contents.choices import Contexts
from ..dateofbirths.forms import DateOfBirthFormOptional
from ..dateofbirths.models import DateOfBirth
from ..genders.forms import GenderFormOptional
from ..genders.models import Gender
from ..medhistorydetails.forms import CkdDetailForm
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import CkdForm, ErosionsForm, HyperuricemiaForm, TophiForm, UratestonesForm
from ..medhistorys.models import Ckd, Erosions, Hyperuricemia, Tophi, Uratestones
from ..utils.views import GoutHelperAidMixin
from .forms import UltForm
from .models import Ult
from .selectors import ult_userless_qs

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


class UltAbout(TemplateView):
    """About page for ULTs."""

    template_name = "ults/about.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"content": self.content})
        return context

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="about", context=Contexts.ULT, tag=None)


class UltBase:
    class Meta:
        abstract = True

    model = Ult
    form_class = UltForm

    # Assign onetoones dict with key as the name of the model and value as a
    # dict of the model's form and model.
    onetoones = {
        "dateofbirth": {"form": DateOfBirthFormOptional, "model": DateOfBirth},
        "gender": {"form": GenderFormOptional, "model": Gender},
    }
    # Assign medhistory manytomanys to a dict of ULT_MEDHISTORYS
    medhistorys = {
        MedHistoryTypes.CKD: {
            "form": CkdForm,
            "model": Ckd,
        },
        MedHistoryTypes.EROSIONS: {
            "form": ErosionsForm,
            "model": Erosions,
        },
        MedHistoryTypes.HYPERURICEMIA: {
            "form": HyperuricemiaForm,
            "model": Hyperuricemia,
        },
        MedHistoryTypes.TOPHI: {
            "form": TophiForm,
            "model": Tophi,
        },
        MedHistoryTypes.URATESTONES: {
            "form": UratestonesForm,
            "model": Uratestones,
        },
    }
    medhistory_details = {MedHistoryTypes.CKD: CkdDetailForm}


class UltCreate(UltBase, GoutHelperAidMixin, CreateView, SuccessMessageMixin):
    """View to create a new Ult instance."""

    success_message = "ULT created successfully."

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            _,  # oto_forms,
            _,  # mh_forms,
            _,  # mh_det_forms,
            _,  # ma_forms,
            _,  # lab_formsets,
            oto_2_save,
            oto_2_rem,
            mh_2_save,
            mh_2_rem,
            mh_det_2_save,
            mh_det_2_rem,
            ma_2_save,
            ma_2_rem,
            _,  # labs_2_save,
            _,  # labs_2_rem,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        else:
            return self.form_valid(
                form=form,
                oto_2_save=oto_2_save,
                oto_2_rem=oto_2_rem,
                mh_2_save=mh_2_save,
                mh_2_rem=mh_2_rem,
                mh_det_2_save=mh_det_2_save,
                mh_det_2_rem=mh_det_2_rem,
                ma_2_save=ma_2_save,
                ma_2_rem=ma_2_rem,
                labs_2_save=None,
                labs_2_rem=None,
            )


class UltDetail(DetailView):
    """DetailView for Ult model."""

    model = Ult
    object: Ult

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        for content in self.contents:
            context.update({content.slug: {content.tag: content}})  # type: ignore
        return context

    def get_queryset(self) -> "QuerySet[Any]":
        return ult_userless_qs(self.kwargs["pk"])

    def get_object(self, *args, **kwargs) -> Ult:
        ult: Ult = super().get_object(*args, **kwargs)  # type: ignore
        # Check if Ult is up to date and update if not update
        if not self.request.GET.get("updated", None):
            ult.update_aid(qs=ult)
        return ult

    @property
    def contents(self):
        return apps.get_model("contents.Content").objects.filter(Q(tag__isnull=False), context=Contexts.ULT)


class UltUpdate(UltBase, GoutHelperAidMixin, UpdateView, SuccessMessageMixin):
    """Updates a Ult"""

    success_message = "ULT updated successfully."

    def get_queryset(self):
        return ult_userless_qs(self.kwargs["pk"])

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            _,  # oto_forms,
            _,  # mh_forms,
            _,  # mh_det_forms,
            _,  # ma_forms,
            _,  # lab_formsets,
            oto_2_save,
            oto_2_rem,
            mh_2_save,
            mh_2_rem,
            mh_det_2_save,
            mh_det_2_rem,
            ma_2_save,
            ma_2_rem,
            _,  # labs_2_save,
            _,  # labs_2_rem,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        else:
            return self.form_valid(
                form=form,
                oto_2_rem=oto_2_rem,
                oto_2_save=oto_2_save,
                mh_2_save=mh_2_save,
                mh_2_rem=mh_2_rem,
                mh_det_2_save=mh_det_2_save,
                mh_det_2_rem=mh_det_2_rem,
                ma_2_save=ma_2_save,
                ma_2_rem=ma_2_rem,
                labs_2_save=None,
                labs_2_rem=None,
            )
