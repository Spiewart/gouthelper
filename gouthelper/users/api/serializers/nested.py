from typing import TYPE_CHECKING

from rest_framework import serializers

from ....dateofbirths.api.serializers import DateOfBirthSerializer
from ....ethnicitys.api.serializers import EthnicitySerializer
from ....genders.api.serializers import GenderSerializer
from ....medhistorydetails.schema import GoutDetailSchema
from ...models import Pseudopatient
from ...schema import PseudopatientEditSchema
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
    goutdetail = GoutDetailSchema.drf_serializer()
    provider = UserSerializer(required=False, read_only=True)

    class Meta:
        model = Pseudopatient
        fields = ["dateofbirth", "ethnicity", "gender", "goutdetail", "provider", "id"]

    def create(self, validated_data: PseudopatientEditSchema) -> Pseudopatient:
        return Pseudopatient.profile_objects.api_create(
            dateofbirth=validated_data["dateofbirth"]["value"],
            ethnicity=validated_data["ethnicity"]["value"],
            gender=validated_data["gender"]["value"],
            provider=self.provider,
            at_goal=validated_data["goutdetail"]["at_goal"],
            at_goal_long_term=validated_data["goutdetail"]["at_goal_long_term"],
            flaring=validated_data["goutdetail"]["flaring"],
            on_ppx=validated_data["goutdetail"]["on_ppx"],
            on_ult=validated_data["goutdetail"]["on_ult"],
            starting_ult=validated_data["goutdetail"]["starting_ult"],
        )

    def update(self, instance, validated_data: PseudopatientEditSchema) -> Pseudopatient:
        return Pseudopatient.profile_objects.api_update(
            patient=instance.pk,
            dateofbirth=validated_data["dateofbirth"]["value"],
            ethnicity=validated_data["ethnicity"]["value"],
            gender=validated_data["gender"]["value"],
            at_goal=validated_data["goutdetail"]["at_goal"],
            at_goal_long_term=validated_data["goutdetail"]["at_goal_long_term"],
            flaring=validated_data["goutdetail"]["flaring"],
            on_ppx=validated_data["goutdetail"]["on_ppx"],
            on_ult=validated_data["goutdetail"]["on_ult"],
            starting_ult=validated_data["goutdetail"]["starting_ult"],
        )