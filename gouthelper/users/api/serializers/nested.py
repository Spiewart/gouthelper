from typing import TYPE_CHECKING

from rest_framework import serializers

from ....dateofbirths.api.serializers import DateOfBirthSerializer
from ....ethnicitys.api.serializers import EthnicitySerializer
from ....genders.api.serializers import GenderSerializer
from ....medhistorys.api.serializers.with_relations import GoutSerializer
from ...models import Pseudopatient
from ...schema.with_related_schema import PseudopatientEditSchema
from ...tests.factories import get_pseudopatient_api_data
from .base import UserSerializer

if TYPE_CHECKING:
    from django.contribu.auth import get_user_model

    User = get_user_model()


class PseudopatientSerializer(serializers.ModelSerializer[Pseudopatient]):
    def __init__(
        self,
        *args,
        **kwargs,
    ):
        self.provider = kwargs.pop("provider", None)
        super().__init__(*args, **kwargs)

    dateofbirth = DateOfBirthSerializer()
    ethnicity = EthnicitySerializer()
    gender = GenderSerializer()
    gout = GoutSerializer()
    provider = UserSerializer(required=False, read_only=True)

    class Meta:
        model = Pseudopatient
        fields = ["dateofbirth", "ethnicity", "gender", "gout", "provider", "id"]

    def create(self, validated_data: PseudopatientEditSchema) -> Pseudopatient:
        return Pseudopatient.profile_objects.api_create(
            patient_data=get_pseudopatient_api_data(),
            dateofbirth_data=validated_data["dateofbirth"],
            ethnicity_data=validated_data["ethnicity"],
            gender_data=validated_data["gender"],
            gout_data=validated_data["gout"],
        )

    def update(self, instance, validated_data: PseudopatientEditSchema) -> Pseudopatient:
        return Pseudopatient.profile_objects.api_update(
            patient_data=get_pseudopatient_api_data(patient=instance),
            dateofbirth_data=validated_data["dateofbirth"],
            ethnicity_data=validated_data["ethnicity"],
            gender_data=validated_data["gender"],
            gout_data=validated_data["gout"],
        )
