from typing import TYPE_CHECKING

from ....medhistorydetails.api.serializers import GoutDetailSerializer
from ....medhistorydetails.models import GoutDetail
from ...models import Gout
from .base_serializers import MedHistorySerializer

if TYPE_CHECKING:
    from ....medhistorydetails.types import GoutDetailData
    from ...types import GoutData


class GoutSerializer(MedHistorySerializer):
    goutdetail = GoutDetailSerializer(required=True)

    class Meta:
        model = Gout
        fields = ["id", "value", "user", "goutdetail"]

    def __init__(self, *args, **kwargs):
        # implicit is the kwarg indicating the API is handling data for a
        # GoutPatient, who are all assumed to have gout
        self.implicit: bool = kwargs.pop("implicit", False)
        if self.implicit:
            self.fields["value"].read_only = True
            self.fields["value"].default = True
        else:
            self.fields["value"].required = True
        self.goutdetail_optional: bool = kwargs.pop("goutdetail_optional", False)
        if self.goutdetail_optional:
            self.fields["goutdetail"].required = False

        super().__init__(*args, **kwargs)

    @property
    def should_create_or_update(self) -> bool:
        return super().should_create_or_update or "value" not in self.validated_data and self.implicit

    @classmethod
    def create_gout(cls, validated_data: "GoutData") -> Gout:
        gout = Gout.objects.create(user=validated_data["user"])
        goutdetail_data = validated_data.get("goutdetail", None)
        if goutdetail_data:
            cls.create_goutdetail(gout, goutdetail_data)

        return gout

    @classmethod
    def create_goutdetail(cls, gout: Gout, goutdetail_data: "GoutDetailData") -> GoutDetail:
        goutdetail_data.update({"medhistory": gout})
        return GoutDetail.objects.create(**goutdetail_data)

    def create(self, validated_data: "GoutData") -> Gout:
        return self.create_gout(validated_data)

    @classmethod
    def update_gout(cls, instance: Gout, validated_data: "GoutDetailData") -> Gout:
        goutdetail_data = validated_data.get("goutdetail", None)

        if goutdetail_data:
            if hasattr(instance, "goutdetail"):
                instance.goutdetail.update(validated_data=goutdetail_data)
            else:
                cls.create_goutdetail(instance, goutdetail_data)

        return instance

    def update(self, instance: Gout, validated_data: "GoutData") -> Gout:
        return self.update_gout(instance, validated_data)
