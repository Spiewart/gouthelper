from typing import TYPE_CHECKING

from crispy_forms.layout import HTML, Div, MultiField  # type: ignore
from django.db.models import DateTimeField  # type: ignore
from django.forms import BooleanField, ModelForm  # type: ignore

from ..medhistorys.dicts import CVD_CONTRAS
from ..utils.exceptions import EmptyRelatedModel  # type: ignore

if TYPE_CHECKING:
    from ..medhistorys.choices import MedHistoryTypes


def make_custom_datetimefield(f, **kwargs):
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


class OneToOneForm(ModelForm):
    class Meta:
        abstract = True

    def check_for_value(self):
        if self.cleaned_data["value"] is not None:
            pass
        else:
            raise EmptyRelatedModel


class CardiovascularDiseasesModelFormMixin:
    def __init__(self, form: ModelForm):
        self.form = form

    def _add_cv_medhistorytype_field(self, medhistorytype: "MedHistoryTypes"):
        self.form.fields.update({medhistorytype: BooleanField(required=False)})

    def _add_cv_medhistorytype_layout(
        self, medhistorytype: "MedHistoryTypes", layout_position: int, sublayout_position: int
    ):
        self.form.helper.layout[0][layout_position - 1][sublayout_position - 1][0][0][1].insert(
            0,
            Div(
                MultiField(
                    "Cardiovascular Disease(s)",
                    *CVD_CONTRAS,
                    type="checkbox",
                    css_class="form-check-input",
                ),
                css_class="form-check form-check-inline",
            ),
        )

    def _add_cv_medhistorytype_legend(self):
        self.form.helper.layout[0].append(
            Div(
                HTML("""<hr size="3" color="dark">"""),
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
                                HTML("""Does the patient have any cardiovascular diseases?"""),
                                css_id="hint_id_cardiovascular_diseases",
                                css_class="form-text",
                            ),
                            css_class="mb-3",
                            css_id="div_id_cardiovascular_diseases",
                        ),
                        css_class="col inline-cb",
                    ),
                    css_class="row",
                ),
            ),
        )

    def add_cv_medhistorys(self):
        self._add_cv_medhistorytype_legend()
        layout_len = len(self.form.helper.layout[0])
        sublayout_len = len(self.form.helper.layout[0][layout_len - 1])
        for medhistorytype in CVD_CONTRAS:
            self._add_cv_medhistorytype_field(medhistorytype)
            self._add_cv_medhistorytype_layout(
                medhistorytype=medhistorytype, layout_position=layout_len, sublayout_position=sublayout_len
            )
        return self.form
