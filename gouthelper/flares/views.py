from typing import TYPE_CHECKING, Any, Union

from django.apps import apps  # type: ignore
from django.contrib import messages  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from django.contrib.auth.mixins import LoginRequiredMixin  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # type: ignore
from django.core.exceptions import ValidationError  # type: ignore
from django.http import Http404, HttpResponseRedirect  # type: ignore
from django.urls import reverse  # type: ignore
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView  # type: ignore
from rules.contrib.views import AutoPermissionRequiredMixin, PermissionRequiredMixin  # type: ignore

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
from ..users.models import Pseudopatient
from ..utils.exceptions import EmptyRelatedModel
from ..utils.views import (
    MedHistorysModelCreateView,
    MedHistorysModelUpdateView,
    PatientAidCreateView,
    PatientAidUpdateView,
)
from .forms import FlareForm
from .models import Flare
from .selectors import flare_user_qs, flare_userless_qs, user_flares

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet  # type: ignore
    from django.forms import ModelForm  # type: ignore
    from django.http import HttpRequest, HttpResponse  # type: ignore

    from ..labs.models import BaselineCreatinine, Lab
    from ..medallergys.models import MedAllergy
    from ..medhistorydetails.forms import CkdDetailForm, GoutDetailForm
    from ..medhistorys.models import MedHistory
    from ..utils.types import FormModelDict, MedAllergyAidHistoryModel

User = get_user_model()


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


class FlareBase:
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
        post_object: "MedAllergyAidHistoryModel",
        errors_bool: bool = False,
    ) -> tuple[dict[str, "ModelForm"], bool]:
        if post_object.gender and post_object.gender.value == Genders.FEMALE and post_object.dateofbirth:
            age = age_calc(post_object.dateofbirth.value)
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
                errors_bool = True
        return medhistorys_forms, errors_bool

    def post_process_urate_check(
        self,
        form: "ModelForm",
        onetoone_forms: dict[str, "ModelForm"],
        errors_bool: bool = False,
    ) -> tuple["ModelForm", dict[str, "ModelForm"], bool]:
        urate_val = onetoone_forms["urate_form"].cleaned_data.get("value", None)
        urate_check = form.cleaned_data.get("urate_check", None)
        if urate_check and not urate_val:
            urate_error = ValidationError(message="If urate was checked, we should know it!")
            form.add_error("urate_check", urate_error)
            onetoone_forms["urate_form"].add_error("value", urate_error)
            errors_bool = True
        return form, onetoone_forms, errors_bool


class FlareCreate(FlareBase, MedHistorysModelCreateView, SuccessMessageMixin):
    """Creates a new Flare"""

    success_message = "Flare created successfully!"

    def form_valid(
        self,
        form: FlareForm,
        onetoones_to_save: list["Model"] | None,
        medhistorydetails_to_save: list["CkdDetailForm", "BaselineCreatinine", "GoutDetailForm"] | None,
        medallergys_to_save: list["MedAllergy"] | None,
        medhistorys_to_save: list["MedHistory"] | None,
        labs_to_save: list["Lab"] | None,
        **kwargs,
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Overwritten to redirect appropriately, as parent method doesn't redirect at all."""
        # Object will be returned by the super().form_valid() call
        self.object = super().form_valid(
            form=form,
            onetoones_to_save=onetoones_to_save,
            medhistorydetails_to_save=medhistorydetails_to_save,
            medallergys_to_save=medallergys_to_save,
            medhistorys_to_save=medhistorys_to_save,
            labs_to_save=labs_to_save,
            **kwargs,
        )
        # Update object / form instance
        self.object.update_aid(qs=self.object)
        return HttpResponseRedirect(self.get_success_url())

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            onetoone_forms,
            medallergys_forms,
            medhistorys_forms,
            medhistorydetails_forms,
            lab_formset,
            onetoones_to_save,
            medallergys_to_save,
            medhistorys_to_save,
            medhistorydetails_to_save,
            labs_to_save,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        medhistorys_forms, errors_bool = self.post_process_menopause(
            medhistorys_forms=medhistorys_forms, post_object=form.instance
        )
        form, onetoone_forms, errors_bool = self.post_process_urate_check(
            form=form, onetoone_forms=onetoone_forms, errors_bool=errors_bool
        )
        if errors_bool:
            return super().render_errors(
                form=form,
                onetoone_forms=onetoone_forms,
                medhistorys_forms=medhistorys_forms,
                medhistorydetails_forms=medhistorydetails_forms,
                medallergys_forms=medallergys_forms,
                lab_formset=lab_formset,
                labs=self.labs if hasattr(self, "labs") else None,
            )
        else:
            return self.form_valid(
                form=form,  # type: ignore
                medallergys_to_save=medallergys_to_save,
                onetoones_to_save=onetoones_to_save,
                medhistorydetails_to_save=medhistorydetails_to_save,
                medhistorys_to_save=medhistorys_to_save,
                labs_to_save=labs_to_save,
            )


class FlareDetailBase(DetailView):
    class Meta:
        abstract = True

    model = Flare
    object: Flare

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        for content in self.contents:
            context.update({content.slug: {content.tag: content}})  # type: ignore
        return context

    @property
    def contents(self):
        return apps.get_model("contents.Content").objects.filter(context=Contexts.FLARE, tag__isnull=False)


class FlareDetail(FlareDetailBase):
    """View for viewing a Flare"""

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Check if the object has a User and if there is no username in the kwargs,
        # redirect to the username url
        if self.object.user:
            return HttpResponseRedirect(self.object.get_absolute_url())
        else:
            # Check if Flare is up to date and update if not update
            if not request.GET.get("updated", None):
                self.object.update_aid(qs=self.object)
            return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not hasattr(self, "object"):
            self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_queryset(self) -> "QuerySet[Any]":
        return flare_userless_qs(self.kwargs["pk"])


class FlarePatientBase(FlareBase):
    medhistorys = {
        MedHistoryTypes.ANGINA: {"form": AnginaForm, "model": Angina},
        MedHistoryTypes.CAD: {"form": CadForm, "model": Cad},
        MedHistoryTypes.CHF: {"form": ChfForm, "model": Chf},
        MedHistoryTypes.CKD: {"form": CkdForm, "model": Ckd},
        MedHistoryTypes.HEARTATTACK: {"form": HeartattackForm, "model": Heartattack},
        MedHistoryTypes.HYPERTENSION: {"form": HypertensionForm, "model": Hypertension},
        MedHistoryTypes.PVD: {"form": PvdForm, "model": Pvd},
        MedHistoryTypes.STROKE: {"form": StrokeForm, "model": Stroke},
    }
    onetoones = {"urate": {"form": UrateFlareForm, "model": Urate}}
    req_onetoones = ["dateofbirth", "gender"]

    def get_user_queryset(self, username: str) -> "QuerySet[Any]":
        """Used to set the user attribute on the view, with associated related models
        select_related and prefetch_related."""
        return flare_user_qs(username=username, flare_pk=self.kwargs.get("pk"))


class FlarePseudopatientList(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    context_object_name = "flares"
    model = Flare
    permission_required = "flares.can_view_pseudopatient_flare_list"
    template_name = "flares/flare_list.html"

    def dispatch(self, request, *args, **kwargs):
        self.user = self.get_queryset().get()
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.object_list = self.user.flares_qs
        context = self.get_context_data()
        return self.render_to_response(context)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["patient"] = Pseudopatient.objects.get(username=self.kwargs["username"])
        return context

    def get_permission_object(self):
        return self.user

    def get_queryset(self):
        return user_flares(username=self.kwargs["username"])


class FlarePseudopatientCreate(
    PermissionRequiredMixin, FlarePatientBase, PatientAidCreateView, CreateView, SuccessMessageMixin
):
    """View for creating a Flare for a patient."""

    permission_required = "flares.can_add_pseudopatient_flare"
    success_message = "FlareAid successfully created."

    def context_onetoones(
        self,
        onetoones: dict[str, "FormModelDict"],
        req_onetoones: list[str],
        kwargs: dict,
        user: "User",
    ) -> None:
        """Method to populate the kwargs dict with forms for the user's related models. For
        required one to one objects, the value is set as a kwarg for the context."""
        # Iterate over the OneToOne related models and add the form to the context
        for onetoone, onetoone_dict in onetoones.items():
            form_str = f"{onetoone}_form"
            if form_str not in kwargs:
                # Add the form to the context with a new instance of the related model
                kwargs[form_str] = onetoone_dict["form"](instance=onetoone_dict["model"]())
        # Add the required one to one objects to the context
        for onetoone in req_onetoones:
            if onetoone not in kwargs:
                # If the one to one is a dateofbirth, calculate the age and add it to the context
                if onetoone == "dateofbirth":
                    kwargs["age"] = age_calc(getattr(user, onetoone).value)
                else:
                    kwargs[onetoone] = getattr(user, onetoone).value

    def dispatch(self, request, *args, **kwargs):
        """Overwritten to avoid redirecting if the user already has a Flare."""
        # Will also set self.user
        self.get_object()
        try:
            self.check_user_onetoones(user=self.user)
        except AttributeError as exc:
            messages.error(request, exc)
            return HttpResponseRedirect(reverse("users:pseudopatient-update", kwargs={"username": self.user.username}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(
        self,
        form,
        onetoones_to_save: list["Model"] | None,
        onetoones_to_delete: list["Model"] | None,
        medhistorydetails_to_save: list["CkdDetailForm", "BaselineCreatinine", "GoutDetailForm"] | None,
        medhistorydetails_to_remove: list["CkdDetailForm", "BaselineCreatinine", "GoutDetailForm"] | None,
        medallergys_to_save: list["MedAllergy"] | None,
        medallergys_to_remove: list["MedAllergy"] | None,
        medhistorys_to_save: list["MedHistory"] | None,
        medhistorys_to_remove: list["MedHistory"] | None,
        labs_to_save: list["Lab"] | None,
        labs_to_remove: list["Lab"] | None,
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Overwritten to redirect appropriately and update the form instance."""
        form = super().form_valid(
            form=form,
            onetoones_to_save=onetoones_to_save,
            onetoones_to_delete=onetoones_to_delete,
            medhistorys_to_save=medhistorys_to_save,
            medhistorys_to_remove=medhistorys_to_remove,
            medhistorydetails_to_save=medhistorydetails_to_save,
            medhistorydetails_to_remove=medhistorydetails_to_remove,
            medallergys_to_save=medallergys_to_save,
            medallergys_to_remove=medallergys_to_remove,
            labs_to_save=labs_to_save,
            labs_to_remove=labs_to_remove,
        )
        flare = form.save()
        self.user.flare_qs = flare
        # Update object / form instance
        flare.update_aid(qs=self.user)
        # Add a querystring to the success_url to trigger the DetailView to NOT re-update the object
        return HttpResponseRedirect(flare.get_absolute_url() + "?updated=True")

    def get_permission_object(self):
        """Returns the User / Pseudopatietn object the view is trying to create
        a FlareAid for."""
        return self.user

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            onetoone_forms,
            medhistorys_forms,
            medhistorydetails_forms,
            medallergys_forms,
            lab_formset,
            _,  # medallergys_to_save
            _,  # medallergys_to_remove
            onetoones_to_save,
            onetoones_to_delete,
            medhistorydetails_to_save,
            medhistorydetails_to_remove,
            medhistorys_to_save,
            medhistorys_to_remove,
            _,  # labs_to_save
            _,  # labs_to_remove
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        form, onetoone_forms, errors_bool = self.post_process_urate_check(form=form, onetoone_forms=onetoone_forms)
        if errors_bool:
            return super().render_errors(
                form=form,
                onetoone_forms=onetoone_forms,
                medhistorys_forms=medhistorys_forms,
                medhistorydetails_forms=medhistorydetails_forms,
                medallergys_forms=medallergys_forms,
                lab_formset=lab_formset,
                labs=self.labs if hasattr(self, "labs") else None,
            )
        return self.form_valid(
            form=form,  # type: ignore
            medallergys_to_save=None,
            medallergys_to_remove=None,
            onetoones_to_save=onetoones_to_save,
            onetoones_to_delete=onetoones_to_delete,
            medhistorydetails_to_save=medhistorydetails_to_save,
            medhistorydetails_to_remove=medhistorydetails_to_remove,
            medhistorys_to_save=medhistorys_to_save,
            medhistorys_to_remove=medhistorys_to_remove,
            labs_to_save=None,
            labs_to_remove=None,
        )

    def post_populate_onetoone_forms(
        self,
        onetoones: dict[str, "FormModelDict"],
        request: "HttpRequest",
        user: "User",
    ) -> dict[str, "ModelForm"]:
        """Method that populates a dict of OneToOne related model forms with POST data
        in the post() method."""
        onetoone_forms: dict[str, "ModelForm"] = {}
        if onetoones:
            for onetoone in onetoones:
                if onetoone == "urate":
                    onetoone_forms.update(
                        {
                            f"{onetoone}_form": onetoones[onetoone]["form"](
                                request.POST,
                                # Urate will be queried on the Flare (not the User) so we need to check
                                # if the object is a Flare to avoid raising an AttributeError when
                                # this method is called on a the CreateView when the object is None
                                instance=Urate(),
                            )
                        }
                    )
                else:
                    user_i = getattr(user, onetoone, None)
                    onetoone_forms.update(
                        {
                            f"{onetoone}_form": onetoones[onetoone]["form"](
                                request.POST,
                                instance=user_i,
                                # TODO: see if this is required
                                # initial={f"{onetoone}-value": user_i.value} if user_i else None,
                            )
                        }
                    )
        return onetoone_forms

    def post_process_onetoone_forms(
        self,
        onetoone_forms: dict[str, "ModelForm"],
        req_onetoones: list[str],
        user: "User",
    ) -> tuple[list["Model"], list["Model"]]:
        """Method to process the forms for the OneToOne objects for
        the post() method."""
        onetoones_to_save: list["Model"] = []
        onetoones_to_delete: list["Model"] = []
        # Set related models for saving and set as attrs of the UpdateView model instance
        for onetoone_form_str, onetoone_form in onetoone_forms.items():
            object_attr = onetoone_form_str.split("_")[0]
            if object_attr not in req_onetoones:
                if object_attr == "urate":
                    try:
                        onetoone_form.check_for_value()
                        onetoone = onetoone_form.save(commit=False)
                        onetoones_to_save.append(onetoone)
                        # Still need to set the urate attr on the User so that
                        # it can be correctly processed by the post_process_urate_check() method
                        setattr(user, object_attr, onetoone)
                    # If EmptyRelatedModel exception is raised by the related model's form save() method,
                    # Check if the related model exists and delete it if it does
                    except EmptyRelatedModel:
                        # For CreateView, if the UrateForm is empty, can just pass because
                        # there will be no pre-existing object to delete
                        pass
                else:
                    try:
                        onetoone_form.check_for_value()
                        onetoone = onetoone_form.save(commit=False)
                        onetoones_to_save.append(onetoone)
                        setattr(user, object_attr, onetoone)
                    # If EmptyRelatedModel exception is raised by the related model's form save() method,
                    # Check if the related model exists and delete it if it does
                    except EmptyRelatedModel:
                        # Check if the related model has already been saved to the DB and mark for deletion if so
                        if onetoone_form.instance and not onetoone_form.instance._state.adding:
                            to_delete = getattr(user, object_attr)
                            # Iterate over the forms required_fields property and set the related model's
                            # fields to their initial values to prevent IntegrityError from Django-Simple-History
                            # historical model on delete().
                            if hasattr(onetoone_form, "required_fields"):
                                for field in onetoone_form.required_fields:
                                    setattr(to_delete, field, onetoone_form.initial[field])
                            # Set the object attr to None so it is reflected
                            # in the QuerySet fed to update in form_valid()
                            setattr(user, object_attr, None)
                            onetoones_to_delete.append(to_delete)
        return onetoones_to_save, onetoones_to_delete


class FlarePseudopatientDelete(AutoPermissionRequiredMixin, DeleteView):
    """View for deleting a Flare for a patient."""

    model = Flare
    success_message = "Flare successfully deleted."

    def dispatch(self, request, *args, **kwargs):
        # Set the user and object with get_object()
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, *args, **kwargs) -> Flare:
        """Overwritten to set the user attr on the view."""
        try:
            self.user: User = self.get_queryset().get()
        except User.DoesNotExist as exc:
            raise Http404(f"User with username {self.kwargs['username']} does not exist.") from exc
        try:
            flare: Flare = self.user.flare_qs[0]
        except IndexError as exc:
            raise Http404(f"Flare for {self.user} does not exist.") from exc
        return flare

    def get_permission_object(self):
        return self.object

    def get_success_url(self) -> str:
        return reverse("flares:pseudopatient-list", kwargs={"username": self.object.user.username})

    def get_queryset(self) -> "QuerySet[Any]":
        return flare_user_qs(
            username=self.kwargs["username"],
            flare_pk=self.kwargs["pk"],
        )


class FlarePseudopatientDetail(AutoPermissionRequiredMixin, FlareDetailBase):
    """Overwritten for different url routing, object fetching, and
    building the content data."""

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["patient"] = self.user
        return context

    def dispatch(self, request, *args, **kwargs):
        """Overwritten to check for a User on the object and redirect to the
        correct FlarePseudopatientCreate url instead. Also checks if the user has
        the correct OneToOne models and redirects to the view to add them if not."""
        try:
            self.object = self.get_object()
        except (DateOfBirth.DoesNotExist, Gender.DoesNotExist):
            messages.error(request, "Baseline information is needed to use GoutHelper Decision and Treatment Aids.")
            return HttpResponseRedirect(reverse("users:pseudopatient-update", kwargs={"username": self.user.username}))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Check if Flare is up to date and update if not update
        if not request.GET.get("updated", None):
            self.object.update_aid(qs=self.object)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_permission_object(self):
        return self.object

    def assign_flare_attrs_from_user(self, flare: Flare, user: "User") -> Flare:
        flare.dateofbirth = user.dateofbirth
        flare.gender = user.gender
        flare.medhistorys_qs = user.medhistorys_qs
        return flare

    def get_queryset(self) -> "QuerySet[Any]":
        return flare_user_qs(
            username=self.kwargs["username"],
            flare_pk=self.kwargs["pk"],
        )

    def get_object(self, *args, **kwargs) -> Flare:
        try:
            self.user: User = self.get_queryset().get()
        except User.DoesNotExist as exc:
            raise Http404(f"User with username {self.kwargs['username']} does not exist.") from exc
        try:
            flare: Flare = self.user.flare_qs[0]
        except IndexError as exc:
            raise Http404(f"Flare for {self.user} does not exist.") from exc
        flare = self.assign_flare_attrs_from_user(flare=flare, user=self.user)
        return flare


class FlarePseudopatientUpdate(
    AutoPermissionRequiredMixin, FlarePatientBase, PatientAidUpdateView, UpdateView, SuccessMessageMixin
):
    success_message = "FlareAid successfully updated."

    def context_onetoones(
        self,
        onetoones: dict[str, "FormModelDict"],
        req_onetoones: list[str],
        kwargs: dict,
        user: "User",
    ) -> None:
        """Method to populate the kwargs dict with forms for the user's related models. For
        required one to one objects, the value is set as a kwarg for the context."""
        # Iterate over the OneToOne related models and add the form to the context
        for onetoone, onetoone_dict in onetoones.items():
            form_str = f"{onetoone}_form"
            if form_str not in kwargs:
                # Check if the onetoone is "urate"
                if onetoone == "urate":
                    # If so, the urate_form instance needs to be set from the Flare's urate
                    # because that's how the QuerySet fetches it
                    user_i = getattr(self.object, onetoone, None)
                # Otherwise process the oneotone as normal
                else:
                    # Check if the user has the related model and add the form to the context
                    # with the instance set to the related model if it exists, otherwise
                    # set the instance to a new instance of the related model
                    user_i = getattr(user, onetoone, None)
                kwargs[form_str] = onetoone_dict["form"](instance=user_i if user_i else onetoone_dict["model"]())
        # Add the required one to one objects to the context
        for onetoone in req_onetoones:
            if onetoone not in kwargs:
                # If the one to one is a dateofbirth, calculate the age and add it to the context
                if onetoone == "dateofbirth":
                    kwargs["age"] = age_calc(getattr(user, onetoone).value)
                else:
                    kwargs[onetoone] = getattr(user, onetoone).value

    def dispatch(self, request, *args, **kwargs):
        """Overwritten to avoid redirecting if the user already has a Flare."""
        # Set the object attr and the get_object() method will also set the user attr
        self.object = self.get_object()
        try:
            self.check_user_onetoones(user=self.user)
        except AttributeError as exc:
            messages.error(request, exc)
            return HttpResponseRedirect(reverse("users:pseudopatient-update", kwargs={"username": self.user.username}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(
        self,
        form,
        onetoones_to_save: list["Model"] | None,
        onetoones_to_delete: list["Model"] | None,
        medhistorydetails_to_save: list["CkdDetailForm", "BaselineCreatinine", "GoutDetailForm"] | None,
        medhistorydetails_to_remove: list["CkdDetailForm", "BaselineCreatinine", "GoutDetailForm"] | None,
        medallergys_to_save: list["MedAllergy"] | None,
        medallergys_to_remove: list["MedAllergy"] | None,
        medhistorys_to_save: list["MedHistory"] | None,
        medhistorys_to_remove: list["MedHistory"] | None,
        labs_to_save: list["Lab"] | None,
        labs_to_remove: list["Lab"] | None,
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Overwritten to redirect appropriately and update the form instance."""
        form = super().form_valid(
            form=form,
            onetoones_to_save=onetoones_to_save,
            onetoones_to_delete=onetoones_to_delete,
            medhistorys_to_save=medhistorys_to_save,
            medhistorys_to_remove=medhistorys_to_remove,
            medhistorydetails_to_save=medhistorydetails_to_save,
            medhistorydetails_to_remove=medhistorydetails_to_remove,
            medallergys_to_save=medallergys_to_save,
            medallergys_to_remove=medallergys_to_remove,
            labs_to_save=labs_to_save,
            labs_to_remove=labs_to_remove,
        )
        if form.changed_data or onetoones_to_save:
            flare = form.save()
        else:
            flare = form.instance
        self.user.flare_qs = flare
        # Update object / form instance
        flare.update_aid(qs=self.user)
        # Add a querystring to the success_url to trigger the DetailView to NOT re-update the object
        return HttpResponseRedirect(flare.get_absolute_url() + "?updated=True")

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

    def get_object(self, *args, **kwargs) -> Flare:
        self.user: User = self.get_user_queryset(username=self.kwargs["username"]).get()
        if self.user.flare_qs:
            flare: Flare = self.user.flare_qs[0]
        else:
            raise Flare.DoesNotExist(f"Flare for {self.user} does not exist. Create it.")
        return flare

    def get_permission_object(self):
        """Returns the view's object, which will have already been set by dispatch()."""
        return self.object

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            onetoone_forms,
            medhistorys_forms,
            medhistorydetails_forms,
            medallergys_forms,
            lab_formset,
            _,  # medallergys_to_save
            _,  # medallergys_to_remove
            onetoones_to_save,
            onetoones_to_delete,
            medhistorydetails_to_save,
            medhistorydetails_to_remove,
            medhistorys_to_save,
            medhistorys_to_remove,
            _,  # labs_to_save
            _,  # labs_to_remove
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        form, onetoone_forms, errors_bool = self.post_process_urate_check(form=form, onetoone_forms=onetoone_forms)
        if errors_bool:
            return super().render_errors(
                form=form,
                onetoone_forms=onetoone_forms,
                medhistorys_forms=medhistorys_forms,
                medhistorydetails_forms=medhistorydetails_forms,
                medallergys_forms=medallergys_forms,
                lab_formset=lab_formset,
                labs=self.labs if hasattr(self, "labs") else None,
            )
        return self.form_valid(
            form=form,  # type: ignore
            medallergys_to_save=None,
            medallergys_to_remove=None,
            onetoones_to_save=onetoones_to_save,
            onetoones_to_delete=onetoones_to_delete,
            medhistorydetails_to_save=medhistorydetails_to_save,
            medhistorydetails_to_remove=medhistorydetails_to_remove,
            medhistorys_to_save=medhistorys_to_save,
            medhistorys_to_remove=medhistorys_to_remove,
            labs_to_save=None,
            labs_to_remove=None,
        )

    def post_populate_onetoone_forms(
        self,
        onetoones: dict[str, "FormModelDict"],
        request: "HttpRequest",
        user: "User",
    ) -> dict[str, "ModelForm"]:
        """Method that populates a dict of OneToOne related model forms with POST data
        in the post() method."""
        onetoone_forms: dict[str, "ModelForm"] = {}
        if onetoones:
            for onetoone in onetoones:
                if onetoone == "urate":
                    onetoone_forms.update(
                        {
                            f"{onetoone}_form": onetoones[onetoone]["form"](
                                request.POST,
                                instance=self.object.urate,
                            )
                        }
                    )
                else:
                    user_i = getattr(user, onetoone, None)
                    onetoone_forms.update(
                        {
                            f"{onetoone}_form": onetoones[onetoone]["form"](
                                request.POST,
                                instance=user_i,
                            )
                        }
                    )
        return onetoone_forms

    def post_process_onetoone_forms(
        self,
        onetoone_forms: dict[str, "ModelForm"],
        req_onetoones: list[str],
        user: "User",
    ) -> tuple[list["Model"], list["Model"]]:
        """Method to process the forms for the OneToOne objects for the post() method."""
        onetoones_to_save: list["Model"] = []
        onetoones_to_delete: list["Model"] = []
        # Set related models for saving and set as attrs of the UpdateView model instance
        for onetoone_form_str, onetoone_form in onetoone_forms.items():
            object_attr = onetoone_form_str.split("_")[0]
            if object_attr not in req_onetoones:
                if object_attr == "urate":
                    try:
                        onetoone_form.check_for_value()
                        # Check if the value has changed or is a new object being created
                        # and mark the urate for saving if so
                        if onetoone_form.has_changed() or onetoone_form.instance._state.adding:
                            # Declare onetoone var to assign to the user later
                            onetoone = onetoone_form.save(commit=False)
                            onetoones_to_save.append(onetoone)
                        else:
                            # Still need to assign the onetoone var to assign to the user later
                            onetoone = onetoone_form.instance
                        # Still need to set the urate attr on the User so that
                        # it can be correctly processed by the post_process_urate_check() method
                        setattr(user, object_attr, onetoone)
                    # If EmptyRelatedModel exception is raised by the related model's form save() method,
                    # Check if the related model exists and delete it if it does
                    except EmptyRelatedModel:
                        # Check if the related model has already been saved to the DB and mark for deletion if so
                        if onetoone_form.instance and not onetoone_form.instance._state.adding:
                            to_delete = getattr(self.object, object_attr)
                            # Iterate over the forms required_fields property and set the related model's
                            # fields to their initial values to prevent IntegrityError from Django-Simple-History
                            # historical model on delete().
                            if hasattr(onetoone_form, "required_fields"):
                                for field in onetoone_form.required_fields:
                                    setattr(to_delete, field, onetoone_form.initial[field])
                            # Set the object attr to None so it is reflected
                            # in the QuerySet fed to update in form_valid()
                            setattr(self.object, object_attr, None)
                            onetoones_to_delete.append(to_delete)
                else:
                    try:
                        onetoone_form.check_for_value()
                        # Check if the value has changed and mark the related model for saving if so
                        if onetoone_form.has_changed:
                            onetoone = onetoone_form.save(commit=False)
                            onetoones_to_save.append(onetoone)
                        else:
                            onetoone = onetoone_form.instance
                        setattr(user, object_attr, onetoone)
                    # If EmptyRelatedModel exception is raised by the related model's form save() method,
                    # Check if the related model exists and delete it if it does
                    except EmptyRelatedModel:
                        # Check if the related model has already been saved to the DB and mark for deletion if so
                        if onetoone_form.instance and not onetoone_form.instance._state.adding:
                            to_delete = getattr(user, object_attr)
                            # Iterate over the forms required_fields property and set the related model's
                            # fields to their initial values to prevent IntegrityError from Django-Simple-History
                            # historical model on delete().
                            if hasattr(onetoone_form, "required_fields"):
                                for field in onetoone_form.required_fields:
                                    setattr(to_delete, field, onetoone_form.initial[field])
                            # Set the object attr to None so it is reflected in
                            # the QuerySet fed to update in form_valid()
                            setattr(user, object_attr, None)
                            onetoones_to_delete.append(to_delete)
        return onetoones_to_save, onetoones_to_delete


class FlareUpdate(FlareBase, MedHistorysModelUpdateView, SuccessMessageMixin):
    """Updates a Flare"""

    def form_valid(
        self,
        form,
        onetoones_to_save: list["Model"] | None,
        onetoones_to_delete: list["Model"] | None,
        medhistorydetails_to_save: list["CkdDetailForm", "BaselineCreatinine", "GoutDetailForm"] | None,
        medhistorydetails_to_remove: list["CkdDetailForm", "BaselineCreatinine", "GoutDetailForm"] | None,
        medallergys_to_save: list["MedAllergy"] | None,
        medallergys_to_remove: list["MedAllergy"] | None,
        medhistorys_to_save: list["MedHistory"] | None,
        medhistorys_to_remove: list["MedHistory"] | None,
        labs_to_save: list["Lab"] | None,
        labs_to_remove: list["Lab"] | None,
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Overwritten to redirect appropriately and update the form instance."""

        self.object = super().form_valid(
            form=form,
            onetoones_to_save=onetoones_to_save,
            onetoones_to_delete=onetoones_to_delete,
            medhistorys_to_save=medhistorys_to_save,
            medhistorys_to_remove=medhistorys_to_remove,
            medhistorydetails_to_save=medhistorydetails_to_save,
            medhistorydetails_to_remove=medhistorydetails_to_remove,
            medallergys_to_save=medallergys_to_save,
            medallergys_to_remove=medallergys_to_remove,
            labs_to_save=labs_to_save,
            labs_to_remove=labs_to_remove,
        )
        # Update object / form instance
        self.object.update_aid(qs=self.object)
        # Add a querystring to the success_url to trigger the DetailView to NOT re-update the object
        return HttpResponseRedirect(self.get_success_url() + "?updated=True")

    def get_initial(self) -> dict[str, Any]:
        """Overwrite get_initial() to populate form non-field form inputs"""
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
            onetoone_forms,
            medallergys_forms,
            medhistorys_forms,
            medhistorydetails_forms,
            lab_formset,
            onetoones_to_save,
            onetoones_to_delete,
            _,  # medallergys_to_save
            _,  # medallergys_to_remove
            medhistorys_to_save,
            medhistorys_to_remove,
            medhistorydetails_to_save,
            medhistorydetails_to_remove,
            _,  # labs_to_save
            _,  # labs_to_remove
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        medhistorys_forms, errors_bool = self.post_process_menopause(
            medhistorys_forms=medhistorys_forms, post_object=form.instance
        )
        form, onetoone_forms, errors_bool = self.post_process_urate_check(
            form=form, onetoone_forms=onetoone_forms, errors_bool=errors_bool
        )
        if errors_bool:
            return super().render_errors(
                form=form,
                onetoone_forms=onetoone_forms,
                medhistorys_forms=medhistorys_forms,
                medhistorydetails_forms=medhistorydetails_forms,
                medallergys_forms=medallergys_forms,
                lab_formset=lab_formset,
                labs=self.labs if hasattr(self, "labs") else None,
            )
        return self.form_valid(
            form=form,  # type: ignore
            medallergys_to_save=None,
            medallergys_to_remove=None,
            onetoones_to_delete=onetoones_to_delete,
            onetoones_to_save=onetoones_to_save,
            medhistorydetails_to_save=medhistorydetails_to_save,
            medhistorydetails_to_remove=medhistorydetails_to_remove,
            medhistorys_to_save=medhistorys_to_save,
            medhistorys_to_remove=medhistorys_to_remove,
            labs_to_save=None,
            labs_to_remove=None,
        )
