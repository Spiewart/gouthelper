from typing import TYPE_CHECKING

from ....medhistorydetails.api.serializers import CkdDetailSerializer, GoutDetailSerializer
from ....medhistorydetails.models import GoutDetail
from ...models import Angina, Cad, Chf, Ckd, Gout, Heartattack, Hypertension, Menopause, Pvd, Stroke
from .base_serializers import MedHistorySerializer

if TYPE_CHECKING:
    from ....medhistorydetails.types import GoutDetailData
    from ...types import GoutData


class AnginaSerializer(MedHistorySerializer):
    class Meta(MedHistorySerializer.Meta):
        model = Angina
        fields = ["id", "value", "user"]


class CadSerializer(MedHistorySerializer):
    class Meta(MedHistorySerializer.Meta):
        model = Cad
        fields = ["id", "value", "user"]


class ChfSerializer(MedHistorySerializer):
    class Meta(MedHistorySerializer.Meta):
        model = Chf
        fields = ["id", "value", "user"]


class CkdSerializer(MedHistorySerializer):
    class Meta(MedHistorySerializer.Meta):
        model = Ckd
        fields = ["id", "value", "user", "ckddetail"]

    ckddetail = CkdDetailSerializer(required=True)

    def __init__(self, *args, **kwargs):
        self.ckddetail_optional: bool = kwargs.pop("ckddetail_optional", False)
        if self.ckddetail_optional:
            self.fields["ckddetail"].required = False

        super().__init__(*args, **kwargs)


class GoutSerializer(MedHistorySerializer):
    class Meta:
        model = Gout
        fields = ["id", "value", "user", "goutdetail"]

    goutdetail = GoutDetailSerializer(required=True)

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

    def should_create_or_update(self, validated_data: "GoutData") -> bool:
        return (
            super().should_create_or_update(validated_data=validated_data)
            or "value" not in self.validated_data
            and self.implicit
        )

    @classmethod
    def create_medhistory(cls, validated_data: "GoutData") -> Gout:
        goutdetail_data = validated_data.pop("goutdetail", None)
        gout = super().create_medhistory(validated_data)
        if goutdetail_data:
            cls.create_goutdetail(gout, goutdetail_data)

        return gout

    @classmethod
    def create_goutdetail(cls, gout: Gout, goutdetail_data: "GoutDetailData") -> GoutDetail:
        goutdetail_data.update({"medhistory": gout})
        return GoutDetail.objects.create(**goutdetail_data)

    @classmethod
    def update_medhistory(cls, instance: Gout, validated_data: "GoutData") -> Gout:
        goutdetail_data = validated_data.pop("goutdetail", None)

        super().update_medhistory(instance, validated_data)
        print(instance)
        if goutdetail_data:
            if hasattr(instance, "goutdetail"):
                instance.goutdetail.update(validated_data=goutdetail_data)
            else:
                cls.create_goutdetail(instance, goutdetail_data)

        return instance


class HeartattackSerializer(MedHistorySerializer):
    class Meta(MedHistorySerializer.Meta):
        model = Heartattack
        fields = ["id", "value", "user"]


class HypertensionSerializer(MedHistorySerializer):
    class Meta(MedHistorySerializer.Meta):
        model = Hypertension
        fields = ["id", "value", "user"]


class MenopauseSerializer(MedHistorySerializer):
    class Meta(MedHistorySerializer.Meta):
        model = Menopause
        fields = ["id", "value", "user"]


class PvdSerializer(MedHistorySerializer):
    class Meta(MedHistorySerializer.Meta):
        model = Pvd
        fields = ["id", "value", "user"]


class StrokeSerializer(MedHistorySerializer):
    class Meta(MedHistorySerializer.Meta):
        model = Stroke
        fields = ["id", "value", "user"]
