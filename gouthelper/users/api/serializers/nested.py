from rest_framework import serializers

from ....dateofbirths.api.serializers import DateOfBirthSerializer
from ....ethnicitys.api.serializers import EthnicitySerializer
from ....genders.api.serializers import GenderSerializer
from ....medhistorydetails.api.serializers import GoutDetailSerializer
from ...models import Pseudopatient
from .base import UserSerializer


class PseudopatientSerializer(serializers.ModelSerializer[Pseudopatient]):
    dateofbirth = DateOfBirthSerializer()
    ethnicity = EthnicitySerializer()
    gender = GenderSerializer()
    goutdetail = GoutDetailSerializer()
    provider = UserSerializer(required=False, read_only=True)
    provider_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = Pseudopatient
        fields = ["dateofbirth", "ethnicity", "gender", "goutdetail", "provider", "provider_id"]

    def create(self, validated_data) -> Pseudopatient:
        provider_id = validated_data.pop("provider_id", None)
        return Pseudopatient.profile_objects.api_create(
            dateofbirth=validated_data["dateofbirth"]["value"],
            ethnicity=validated_data["ethnicity"]["value"],
            gender=validated_data["gender"]["value"],
            provider_id=provider_id,
            at_goal=validated_data["goutdetail"]["at_goal"],
            at_goal_long_term=validated_data["goutdetail"]["at_goal_long_term"],
            flaring=validated_data["goutdetail"]["flaring"],
            on_ppx=validated_data["goutdetail"]["on_ppx"],
            on_ult=validated_data["goutdetail"]["on_ult"],
            starting_ult=validated_data["goutdetail"]["starting_ult"],
        )

    def update(self, instance, validated_data) -> Pseudopatient:
        return Pseudopatient.profile_objects.api_update(
            pk=instance.pk,
            dateofbirth=validated_data["dateofbirth"],
            ethnicity=validated_data["ethnicity"],
            gender=validated_data["gender"],
            at_goal=validated_data["at_goal"],
            at_goal_long_term=validated_data["at_goal_long_term"],
            flaring=validated_data["flaring"],
            on_ppx=validated_data["on_ppx"],
            on_ult=validated_data["on_ult"],
            starting_ult=validated_data["starting_ult"],
        )
