from typing import TYPE_CHECKING

from rest_framework import fields, serializers

from ...akis.api.serializers.base_serializers import AkiSerializer
from ...dateofbirths.api.serializers import DateOfBirthSerializer
from ...genders.api.serializers import GenderSerializer
from ...genders.choices import Genders
from ...labs.api.serializers import UrateSerializer
from ...medhistorys.api.serializers.nested_serializers import (
    AnginaSerializer,
    CadSerializer,
    ChfSerializer,
    CkdSerializer,
    GoutSerializer,
    HeartattackSerializer,
    HypertensionSerializer,
    MenopauseSerializer,
    PvdSerializer,
    StrokeSerializer,
)
from ...users.api.serializers.nested_serializers import PseudopatientAidSerializer
from ...utils.api.serializers import GoutHelperModelSerializer
from ..models import Flare

if TYPE_CHECKING:
    from ...medhistorys.models import MedHistory
    from ..types import FlareData


class FlareSerializer(GoutHelperModelSerializer):
    class Meta:
        model = Flare
        fields = [
            "id",
            "aki",
            "angina",
            "cad",
            "chf",
            "ckd",
            "crystal_analysis",
            "dateofbirth",
            "date_ended",
            "date_started",
            "diagnosed",
            "flareaid",
            "gender",
            "gout",
            "heartattack",
            "hypertension",
            "joints",
            "likelihood",
            "menopause",
            "onset",
            "prevalence",
            "pvd",
            "redness",
            "stroke",
            "urate",
            "user",
        ]
        extra_kwargs = {
            "aki": {"required": False, "allow_null": True},
            "crystal_analysis": {"required": False, "allow_null": True},
            "date_ended": {"required": False, "allow_null": True},
            "diagnosed": {"required": False, "allow_null": True},
            "flareaid": {"required": False, "allow_null": True},
            "likelihood": {"read_only": True, "allow_null": True},
            "prevalence": {"read_only": True, "allow_null": True},
            "urate": {"required": False, "allow_null": True},
            "user": {"required": False, "allow_null": True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if (
            hasattr(self, "initial_data")
            and self.initial_data.get("user", False)
            or self.instance
            and self.instance.user
        ):
            self.fields.pop("dateofbirth")
            self.fields.pop("gender")

    aki = AkiSerializer(required=False, allow_null=True)
    angina = AnginaSerializer(required=False)
    cad = CadSerializer(required=False)
    chf = ChfSerializer(required=False)
    ckd = CkdSerializer(required=False, ckddetail_optional=True)
    dateofbirth = serializers.DateField()
    gender = serializers.ChoiceField(choices=Genders.choices, read_only=True)
    gout = GoutSerializer(implicit=False)
    heartattack = HeartattackSerializer(required=False)
    hypertension = HypertensionSerializer(required=False)
    joints = fields.MultipleChoiceField(choices=Flare.LimitedJointChoices.choices)
    menopause = MenopauseSerializer(required=False)
    pvd = PvdSerializer(required=False)
    stroke = StrokeSerializer(required=False)
    urate = UrateSerializer(required=False, allow_null=True)
    user = PseudopatientAidSerializer(required=False, allow_null=True)

    def create(self, validated_data: "FlareData") -> Flare:
        aki = validated_data.get("aki", None)
        angina = validated_data.get("angina", None)
        cad = validated_data.get("cad", None)
        chf = validated_data.get("chf", None)
        ckd = validated_data.get("ckd", None)
        dateofbirth = validated_data.get("dateofbirth", None)
        gender = validated_data.get("gender", None)
        gout = validated_data.get("gout", None)
        heartattack = validated_data.get("heartattack", None)
        hypertension = validated_data.get("hypertension", None)
        menopause = validated_data.get("menopause", None)
        pvd = validated_data.get("pvd", None)
        stroke = validated_data.get("stroke", None)
        urate = validated_data.get("urate", None)

        if aki:
            aki.update({"user": self.patient})
            aki = AkiSerializer.create_aki(validated_data_data=aki)
        if dateofbirth:
            dateofbirth = {"value": dateofbirth, "user": self.patient}
            dateofbirth = DateOfBirthSerializer.create_dateofbirth(validated_data=dateofbirth)
        if gender:
            gender = {"value": gender, "user": self.patient}
            gender = GenderSerializer.create_gender(validated_data=gender)
        if urate:
            urate.update({"date_drawn": validated_data["date_started"], "user": self.patient})
            urate = UrateSerializer.create_urate(validated_data=validated_data)
        flare = Flare.objects.create(
            aki=aki,
            dateofbirth=dateofbirth,
            gender=gender,
            urate=urate,
            crystal_analysis=validated_data.get("crystal_analysis"),
            date_ended=validated_data.get("date_ended"),
            date_started=validated_data.get("date_started"),
            diagnosed=validated_data.get("diagnosed"),
            flareaid=validated_data.get("flareaid"),
            joints=validated_data.get("joints"),
            onset=validated_data.get("onset"),
            redness=validated_data.get("redness"),
            user__id=validated_data.get("user"),
        )
        self.instance = flare
        if angina:
            if angina.get("value", False):
                angina["flare"] = flare
                angina = AnginaSerializer.create_medhistory(validated_data=angina)
                if angina:
                    self.add_medhistory_to_medhistorys_qs(angina)
        if cad:
            cad["flare"] = flare
            cad = CadSerializer(data=cad).is_valid(raise_exception=True)
            cad.save()
            if cad:
                self.add_medhistory_to_medhistorys_qs(cad)
        if chf:
            chf["flare"] = flare
            chf = ChfSerializer(data=chf).is_valid(raise_exception=True)
            chf.save()
            if chf:
                self.add_medhistory_to_medhistorys_qs(chf)
        if ckd:
            ckd["flare"] = flare
            ckd = CkdSerializer(data=ckd).is_valid(raise_exception=True)
            ckd.save()
            if ckd:
                self.add_medhistory_to_medhistorys_qs(ckd)
        if gout:
            gout["flare"] = flare
            gout = GoutSerializer(data=gout).is_valid(raise_exception=True)
            gout.save()
            if gout:
                self.add_medhistory_to_medhistorys_qs(gout)
        if heartattack:
            heartattack["flare"] = flare
            heartattack = HeartattackSerializer(data=heartattack).is_valid(raise_exception=True)
            heartattack.save()
            if heartattack:
                self.add_medhistory_to_medhistorys_qs(heartattack)
        if hypertension:
            hypertension["flare"] = flare
            hypertension = HypertensionSerializer(data=hypertension).is_valid(raise_exception=True)
            hypertension.save()
            if hypertension:
                self.add_medhistory_to_medhistorys_qs(hypertension)
        if menopause:
            menopause["flare"] = flare
            menopause = MenopauseSerializer(data=menopause).is_valid(raise_exception=True)
            menopause.save()
            if menopause:
                self.add_medhistory_to_medhistorys_qs(menopause)
        if pvd:
            pvd["flare"] = flare
            pvd = PvdSerializer(data=pvd).is_valid(raise_exception=True)
            pvd.save()
            if pvd:
                self.add_medhistory_to_medhistorys_qs(pvd)
        if stroke:
            stroke["flare"] = flare
            stroke = StrokeSerializer(data=stroke).is_valid(raise_exception=True)
            stroke.save()
            if stroke:
                self.add_medhistory_to_medhistorys_qs(stroke)
        return flare

    def add_medhistory_to_medhistorys_qs(self, medhistory: "MedHistory") -> None:
        if not hasattr(self.instance, "medhistorys_qs"):
            self.instance.medhistorys_qs = []
        self.instance.medhistorys_qs.append(medhistory)
