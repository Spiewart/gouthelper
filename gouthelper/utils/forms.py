from typing import TYPE_CHECKING, Union

from crispy_forms.layout import HTML, Div  # type: ignore
from django.db.models import DateTimeField  # type: ignore
from django.forms import BaseModelFormSet, ModelForm  # type: ignore

from ..medhistorys.choices import CVDiseases, MedHistoryTypes
from ..medhistorys.lists import OTHER_NSAID_CONTRAS
from .exceptions import EmptyRelatedModel  # type: ignore

if TYPE_CHECKING:
    from crispy_forms.layout import Layout  # type: ignore
    from django.http import HttpResponse  # type: ignore

    from ..choices import FlarePpxChoices, UltChoices  # type: ignore


class OneToOneForm(ModelForm):
    class Meta:
        abstract = True

    def check_for_value(self):
        if self.cleaned_data["value"] is not None:
            pass
        else:
            raise EmptyRelatedModel


def forms_helper_insert_about_the_patient(layout: "Layout", htmx: bool = False) -> "Layout":
    """Method that inserts a Div with an id="about-the-patient" and a legend
    into a crispy_forms.layout.Layout object"""
    layout_len = len(layout)
    if not htmx:
        layout[layout_len - 1].append(
            Div(
                HTML(
                    """
                        <hr size="3" color="dark">
                        <legend>About {% if patient %}{{ patient }} \
({{ patient.gender }}, age {{ age }}) {% else %} {{ str_attrs.subject_the }} {% endif %} \
{% if view.related_object %}({{ view.related_object.gender }}, age {{ view.related_object.age }}) {% endif %}</legend>
                    """
                ),
                css_id="about-the-patient",
            ),
        )
    else:
        layout[layout_len - 1].append(
            Div(),
        )
    return layout


def forms_helper_insert_cvdiseases(
    layout: "Layout",
    hypertension: bool = False,
    subject_the: str = "the patient",
) -> "Layout":
    layout_len = len(layout)
    sub_len = len(layout[layout_len - 1])
    layout[layout_len - 1][sub_len - 1].append(
        Div(
            Div(
                Div(
                    HTML(
                        """
                        <label class="form-label">Cardiovascular Diseases</label>
                        """
                    ),
                    Div(),
                    Div(
                        HTML(
                            f"""What cardiovascular diseases does {subject_the} have?
                            """
                        ),
                        css_id="hint_id_cardiovascular_diseases",
                        css_class="form-text",
                    ),
                    css_class="mb-3",
                    css_id="div_id_cardiovascular_diseases",
                ),
                css_class="col",
            ),
            css_class="row",
            css_id="cardiovascular_diseases",
        ),
    )
    sub_sub_len = len(layout[layout_len - 1][sub_len - 1])
    for cv_disease in CVDiseases:
        layout[layout_len - 1][sub_len - 1][sub_sub_len - 1][0][0][1].append(
            Div(
                HTML(
                    f"""
                    {{% load crispy_forms_tags %}}
                    {{% crispy {cv_disease.name}_form %}}
                    """
                ),
                css_class="form-check form-check-inline medhistory_form-check",
            ),
        )
    if hypertension:
        layout[layout_len - 1][sub_len - 1][sub_sub_len - 1][0][0][1].append(
            Div(
                HTML(
                    f"""
                    {{% load crispy_forms_tags %}}
                    {{% crispy {MedHistoryTypes.HYPERTENSION}_form %}}
                    """
                ),
                css_class="form-check form-check-inline medhistory_form-check",
            ),
        )


def forms_helper_insert_dateofbirth(layout: "Layout") -> "Layout":
    layout_len = len(layout)
    sub_len = len(layout[layout_len - 1])
    layout[layout_len - 1][sub_len - 1].append(
        Div(
            Div(
                HTML(
                    """
                    {% load crispy_forms_tags %}
                    {% crispy dateofbirth_form %}
                    """
                ),
                css_class="col",
            ),
            css_class="row",
            css_id="dateofbirth",
        ),
    )


def forms_helper_insert_demographics(layout: "Layout", htmx: bool = False) -> "Layout":
    """Method that inserts a Div with an id="about-the-patient" and a legend
    into a crispy_forms.layout.Layout object"""
    layout_len = len(layout)
    if not htmx:
        layout[layout_len - 1].append(
            Div(
                HTML(
                    """
                        <hr size="3" color="dark">
                        <legend>{% if patient %}{{ patient }}'s{% endif %} Demographic Information</legend>
                    """
                ),
                css_id="about-the-patient",
            ),
        )
    else:
        layout[layout_len - 1].append(
            Div(),
        )
    return layout


def forms_helper_insert_gender(layout: "Layout") -> "Layout":
    layout_len = len(layout)
    sub_len = len(layout[layout_len - 1])
    layout[layout_len - 1][sub_len - 1].append(
        Div(
            Div(
                HTML(
                    """
                    {% load crispy_forms_tags %}
                    {% crispy gender_form %}
                    """
                ),
                css_class="col",
            ),
            css_id="gender",
            css_class="row",
        ),
    )


def forms_helper_insert_goutdetail(layout: "Layout") -> "Layout":
    """Generic form_helper method to insert a GoutDetailForm into a
    crispy_forms.layout.Layout object

    Args:
        layout (Layout): crispy_forms.layout.Layout object

    Returns:
        Layout: crispy_forms.layout.Layout object
    """
    layout_len = len(layout)
    sub_len = len(layout[layout_len - 1])
    layout[layout_len - 1][sub_len - 1].append(
        Div(
            Div(
                HTML(
                    f"""{{% load crispy_forms_tags %}}{{% crispy goutdetail_form %}}"""  # noqa: E501, F541 # pylint: disable=W1309
                ),
                css_class="col",
            ),
            css_class="row",
            css_id="goutdetail",
        ),
    )


def forms_helper_insert_medallergys(
    layout: "Layout", treatments: Union["FlarePpxChoices", "UltChoices"], subject_the: str = "the patient"
) -> "Layout":
    layout_len = len(layout)
    sub_len = len(layout[layout_len - 1])
    layout[layout_len - 1][sub_len - 1].append(
        Div(
            Div(
                Div(
                    HTML(
                        """
                        <label class="form-label">
                        Medication Allergies </label>
                        """
                    ),
                    Div(css_class="row"),
                    Div(
                        HTML(
                            f"""Does {subject_the} have an allergy to any of these medications?
                            """
                        ),
                        css_id="hint_id_medallergys",
                        css_class="form-text",
                    ),
                    css_class="mb-3",
                    css_id="div_id_medallergys",
                ),
                css_class="col",
            ),
            css_class="row",
            css_id="medallergys",
        ),
    )
    sub_sub_len = len(layout[layout_len - 1][sub_len - 1])
    for treatment in treatments:
        layout[layout_len - 1][sub_len - 1][sub_sub_len - 1][0][0][1].append(
            Div(
                Div(
                    HTML(
                        f"""
                        {{% load crispy_forms_tags %}}
                        {{% crispy medallergy_{treatment}_form %}}
                        """
                    ),
                    css_class="form-check form-check-inline medhistory_form-check",
                ),
                css_class="col",
            ),
        )


def forms_helper_insert_medhistory(medhistorytype: MedHistoryTypes, layout: "Layout") -> "Layout":
    """Generic form_helper method to insert a MedHistory form into a
    crispy_forms.layout.Layout object

    Args:
        medhistorytype (MedHistoryTypes): MedHistoryTypes enum
        layout (Layout): crispy_forms.layout.Layout object

    Returns:
        Layout: crispy_forms.layout.Layout object
    """
    layout_len = len(layout)
    sub_len = len(layout[layout_len - 1])
    layout[layout_len - 1][sub_len - 1].append(
        Div(
            Div(
                HTML(
                    f"""
                    {{% load crispy_forms_tags %}}
                    {{% crispy {medhistorytype}_form %}}
                    """
                ),
                css_class="col",
            ),
            css_class="row",
            css_id=f"{medhistorytype.name.lower()}",
        ),
    )


def forms_helper_insert_other_nsaid_contras(layout: "Layout", subject_the: str = "the patient") -> "Layout":
    layout_len = len(layout)
    sub_len = len(layout[layout_len - 1])
    layout[layout_len - 1][sub_len - 1].append(
        Div(
            Div(
                Div(
                    HTML(
                        """
                        <label for="" class=" form-label">
                        Other Contraindications to NSAIDs </label>
                        """
                    ),
                    Div(),
                    Div(
                        HTML(
                            f"""What other contraindications to NSAIDs (non-steroidal anti-inflammatory drugs) \
does {subject_the} have?
                            """
                        ),
                        css_id="hint_id_other_nsaid_contras",
                        css_class="form-text",
                    ),
                    css_class="mb-3",
                    css_id="div_id_other_nsaid_contras",
                ),
                css_class="col",
            ),
            css_class="row",
            css_id="other_nsaid_contras",
        ),
    )
    sub_sub_len = len(layout[layout_len - 1][sub_len - 1])
    for contra in OTHER_NSAID_CONTRAS:
        layout[layout_len - 1][sub_len - 1][sub_sub_len - 1][0][0][1].append(
            Div(
                HTML(
                    f"""
                    {{% load crispy_forms_tags %}}
                    {{% crispy {contra.name}_form %}}
                    """
                ),
                css_class="form-check form-check-inline medhistory_form-check",
            ),
        )


def forms_helper_insert_ethnicity(layout: "Layout") -> "Layout":
    """Helper method that inserts the Ethnicity form into a crispy_forms.layout.Layout object
    as part of a multi-model form."""
    layout_len = len(layout)
    sub_len = len(layout[layout_len - 1])
    layout[layout_len - 1][sub_len - 1].append(
        Div(
            Div(
                HTML(
                    """
                    {% load crispy_forms_tags %}
                    {% crispy ethnicity_form %}
                    """
                ),
                css_class="col",
            ),
            css_class="row",
            css_id="ethnicity",
        ),
    )


def forms_helper_insert_hlab5801(layout: "Layout") -> "Layout":
    """Helper method that inserts the Hlab5801 form into a crispy_forms.layout.Layout object
    as part of a multi-model form."""
    layout_len = len(layout)
    sub_len = len(layout[layout_len - 1])
    layout[layout_len - 1][sub_len - 1].append(
        Div(
            Div(
                HTML(
                    """
                    {% load crispy_forms_tags %}
                    {% crispy hlab5801_form %}
                    """
                ),
                css_class="col",
            ),
            css_class="row",
            css_id="hlab5801",
        ),
    )


def forms_helper_insert_urates_formset(layout: "Layout") -> "Layout":
    """Helper method that inserts a Urate Labs formset into a crispy_forms.layout.Layout object
    as part of a multi-model form."""
    layout_len = len(layout)
    sub_len = len(layout[layout_len - 1])
    layout[layout_len - 1][sub_len - 1].append(
        Div(
            Div(
                Div(
                    HTML(
                        f"""<hr size="3" color="dark"><legend>Urates</legend><div class="form-text">Has the patient had his or her uric acid level checked in the past 12-24 months? Enter as many as you like, in any order.</div>{{% load crispy_forms_tags %}}{{% crispy urate_formset urate_formset_helper %}}""",  # noqa: E501, F541 # pylint: disable=W1309
                    ),
                    css_class="col",
                ),
            ),
            css_class="row",
            css_id="labs",
        ),
    )


def forms_make_custom_datetimefield(f, **kwargs):
    """Method to use to override the default DateTimeField widget
    and truncate the datetime to just the date."""
    # Need to call with **kwargs
    # https://stackoverflow.com/questions/14328381/django-error-unexpected-keyword-argument-widget
    if isinstance(f, DateTimeField):
        # return form field with your custom widget here...
        formfield = f.formfield(**kwargs)
        formfield.widget.format = "%m/%d/%Y"
        return formfield
    return f.formfield(**kwargs)


def forms_print_response_errors(response: Union["HttpResponse", None] = None) -> None:
    """Will print errors for all forms and formsets in the context_data."""

    if response and hasattr(response, "context_data"):
        for key, val in response.context_data.items():
            if key.endswith("_form") or key == "form":
                if getattr(val, "errors", None):
                    print("printing form errors")
                    print(key, val.errors)
            elif val and isinstance(val, BaseModelFormSet):
                non_form_errors = val.non_form_errors()
                if non_form_errors:
                    print("printing non form errors")
                    print(key, non_form_errors)
                # Check if the formset has forms and iterate over them if so
                if val.forms:
                    for form in val.forms:
                        if getattr(form, "errors", None):
                            print("printing formset form errors")
                            print(form.instance.pk)
                            print(form.instance.date_drawn)
                            print(form.instance.value)
                            print(key, form.errors)
