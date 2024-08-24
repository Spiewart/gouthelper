from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import ErosionsForm, TophiForm

MEDHISTORY_FORMS = {
    MedHistoryTypes.EROSIONS: ErosionsForm,
    MedHistoryTypes.TOPHI: TophiForm,
}
