from ..dateofbirths.forms import DateOfBirthForm
from ..ethnicitys.forms import EthnicityForm
from ..genders.forms import GenderForm
from ..medhistorydetails.forms import GoutDetailForm
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import GoutForm, MenopauseForm

MEDHISTORY_FORMS = {
    MedHistoryTypes.GOUT: GoutForm,
    MedHistoryTypes.MENOPAUSE: MenopauseForm,
}

OTO_FORMS = {
    "dateofbirth": DateOfBirthForm,
    "ethnicity": EthnicityForm,
    "gender": GenderForm,
}

MEDHISTORY_DETAIL_FORMS = {MedHistoryTypes.GOUT: GoutDetailForm}
