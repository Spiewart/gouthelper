from typing import TYPE_CHECKING

from rest_framework.serializers import ModelSerializer

from ....dateofbirths.api.serializers import DateOfBirthSerializer
from ....dateofbirths.helpers import age_calc
from ....ethnicitys.api.serializers import EthnicitySerializer
from ....genders.api.serializers import GenderSerializer
from ....medhistorys.api.serializers.nested_serializers import GoutSerializer
from ....profiles.helpers import get_provider_alias
from ....profiles.models import PseudopatientProfile
from ...models import Pseudopatient

if TYPE_CHECKING:
    from django.contribu.auth import get_user_model

    from ...types import PseudopatientEditData

    User = get_user_model()


class PseudopatientSerializer(ModelSerializer):
    class Meta:
        model = Pseudopatient
        fields = ["dateofbirth", "ethnicity", "gender", "gout", "id"]

    dateofbirth = DateOfBirthSerializer(optional=False, patient_edit=True)
    ethnicity = EthnicitySerializer(optional=False, patient_edit=True)
    gender = GenderSerializer(optional=False, patient_edit=True)
    gout = GoutSerializer(implicit=True)

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        self.provider = kwargs.pop("provider", None)
        super().__init__(*args, **kwargs)

    def create(self, validated_data: "PseudopatientEditData") -> Pseudopatient:
        patient = Pseudopatient.objects.create()
        PseudopatientProfile.objects.create(
            user=patient,
            provider=self.provider,
            provider_alias=get_provider_alias(
                provider=self.provider,
                age=age_calc(validated_data["dateofbirth"]["value"]),
                gender=validated_data["gender"]["value"],
            )
            if self.provider
            else None,
        )
        self.update_validated_data_user(validated_data, patient)
        DateOfBirthSerializer.create_dateofbirth(validated_data["dateofbirth"])
        EthnicitySerializer.create_ethnicity(validated_data["ethnicity"])
        GenderSerializer.create_gender(validated_data["gender"])
        GoutSerializer.create_gout(validated_data["gout"])
        return patient

    @staticmethod
    def update_validated_data_user(
        validated_data: "PseudopatientEditData", patient: Pseudopatient
    ) -> "PseudopatientEditData":
        validated_data["dateofbirth"]["user"] = patient
        validated_data["gender"]["user"] = patient
        validated_data["ethnicity"]["user"] = patient
        validated_data["gout"]["user"] = patient

    def update(self, instance: Pseudopatient, validated_data: "PseudopatientEditData") -> Pseudopatient:
        DateOfBirthSerializer.update_dateofbirth(instance.dateofbirth, validated_data["dateofbirth"])
        EthnicitySerializer.update_ethnicity(instance.ethnicity, validated_data["ethnicity"])
        GenderSerializer.update_gender(instance.gender, validated_data["gender"])
        GoutSerializer.update_gout(instance=instance.gout, validated_data=validated_data["gout"])
        return instance
