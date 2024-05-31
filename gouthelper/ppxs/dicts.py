from ..labs.forms import PpxUrateFormSet, UrateFormHelper
from ..medhistorydetails.forms import GoutDetailPpxForm
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import GoutForm

LAB_FORMSETS = {"urate": (PpxUrateFormSet, UrateFormHelper)}

MEDHISTORY_FORMS = {
    MedHistoryTypes.GOUT: GoutForm,
}

MEDHISTORY_DETAIL_FORMS = {"goutdetail": GoutDetailPpxForm}
