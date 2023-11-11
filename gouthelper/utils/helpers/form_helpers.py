from typing import TYPE_CHECKING, Union

from crispy_forms.layout import HTML, Div  # type: ignore

from ...medhistorys.choices import CVDiseases, MedHistoryTypes
from ...medhistorys.lists import OTHER_NSAID_CONTRAS

if TYPE_CHECKING:
    from crispy_forms.layout import Layout  # type: ignore

    from ...choices import FlarePpxChoices, UltChoices  # type: ignore


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
                        <legend>About the Patient</legend>
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


def forms_helper_insert_cvdiseases(layout: "Layout", hypertension: bool = False) -> "Layout":
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
                            """What cardiovascular diseases does the patient have?
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


def forms_helper_insert_medallergys(layout: "Layout", treatments: Union["FlarePpxChoices", "UltChoices"]) -> "Layout":
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
                    Div(),
                    Div(
                        HTML(
                            """Does the patient have an allergy to any of these medications?
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
                HTML(
                    f"""
                    {{% load crispy_forms_tags %}}
                    {{% crispy medallergy_{treatment}_form %}}
                    """
                ),
                css_class="form-check form-check-inline medhistory_form-check",
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


def forms_helper_insert_other_nsaid_contras(layout: "Layout") -> "Layout":
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
                            """What other contraindications to NSAIDs (non-steroidal anti-inflammatory drugs) \
does the patient have?
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
                        f"""
                        <hr size="3" color="dark">
                        <legend>Urates</legend>
                        <div class="form-text">Has the patient had his or her uric acid level checked \
in the past 12-24 months? Enter as many as you like, in any order.</div>
                        {{% load crispy_forms_tags %}}
                        {{% crispy lab_formset lab_formset_helper %}}
                        """,  # noqa: F541
                    ),
                    css_class="col",
                ),
            ),
            css_class="row",
            css_id="labs",
        ),
    )
