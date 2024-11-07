from ...utils.services import APIMixin
from ..types import PseudopatientData
from .mixins import PseudopatientAPIMixin


class PseudopatientAPI(PseudopatientAPIMixin, APIMixin):
    def __init__(
        self,
        patient_data: PseudopatientData,
    ):
        super().__init__()
        self.patient_data = patient_data
