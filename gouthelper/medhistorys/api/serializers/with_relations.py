from ....medhistorydetails.api.serializers import GoutDetailSerializer
from ...models import Gout
from .base import MedHistorySerializer


class GoutSerializer(MedHistorySerializer):
    goutdetail = GoutDetailSerializer(required=False)

    class Meta:
        model = Gout
        fields = ["id", "medhistorytype", "value", "user", "goutdetail"]
