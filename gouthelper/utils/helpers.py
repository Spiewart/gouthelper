import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Union

from django.utils import timezone  # type: ignore

from ..treatments.choices import Freqs, Treatments, TrtTypes
from ..treatments.helpers import stringify_dosing_dict

if TYPE_CHECKING:
    from datetime import date

    from django.contrib.auth import get_user_model
    from django.db.models import QuerySet

    from ..utils.models import GoutHelperAidModel, GoutHelperPatientModel

    User = get_user_model()


def calculate_duration(
    date_started: "date",
    date_ended: Union["date", None],
) -> timedelta:
    """Method that calculates the duration a from a date started and date ended
    or if date ended is None, calculates the duration from date started to today.

    Args:
        date_started: date the flare started
        date_ended [optional]: date the flare ended

    Returns:
        timedelta: duration of flare
    """
    if date_ended:
        duration = date_ended - date_started
    else:
        duration = timezone.now().date() - date_started
    return duration


class TrtDictStr:
    def __init__(self, dosing_dict: dict, trttype: TrtTypes, treatment: Treatments = None):
        self.freq2_val = dosing_dict.get("freq2")
        self.freq3_val = dosing_dict.get("freq3")
        self.dosing_dict = stringify_dosing_dict(dosing_dict)
        self.trttype = trttype
        self.treatment = treatment
        for key, val in self.dosing_dict.items():
            setattr(self, key, val)

    dose: Decimal
    dose2: Decimal | None
    dose3: Decimal | None
    freq: Freqs | None
    freq2: Freqs | None
    freq3: Freqs | None
    duration: timedelta | None
    duration2: timedelta | None
    duration3: timedelta | None

    def trt_dict_to_str(self):
        trt_str = ""
        if self.dose3:
            trt_str += f"{self.dose2} mg"
            if (
                self.trttype == TrtTypes.FLARE
                and self.treatment == Treatments.COLCHICINE
                and self.freq2_val == Freqs.ONCE
            ):
                trt_str += " (2 tabs)"
            else:
                trt_str += f"{self.trttype} {self.treatment} {self.freq2.lower()} for {self.duration2}"
            trt_str += f", then {self.dose3} mg"
            if (
                self.trttype == TrtTypes.FLARE
                and self.treatment == Treatments.COLCHICINE
                and self.freq3_val == Freqs.ONCE
            ):
                trt_str += " (1 tab) an hour after the first dose"
            else:
                trt_str += f" {self.freq3.lower()} for {self.duration3}"
            trt_str += ", then "
        trt_str += f"{self.dose} mg {self.freq.lower()} for {self.duration}"
        if not self.dose3 and self.dose2 and self.duration2:
            trt_str += f", then {self.dose2} mg {self.freq2.lower()} for {self.duration2}"
        return trt_str

    def __str__(self):
        return self.trt_dict_to_str()


def duration_decimal_parser(json_dict):
    """Method that takes a json dict and parses it for strings compatible
    with duration (timedelta) and Decimal objects and converts them to their python
    data type."""
    duration_regex = re.compile("P*[1-9]?[0-7]DT00H00M00S")
    decimal_regex = re.compile("[1-9]?[1-9]?[0-9]?[0-9].?[0-9]?")
    for key, value in json_dict.items():
        if isinstance(value, str) and duration_regex.fullmatch(value):
            duration = datetime.strptime(value, "P%dDT%HH%MM%SS")
            json_dict[key] = timedelta(
                days=duration.day,
                hours=duration.hour,
                minutes=duration.minute,
                seconds=duration.second,
            )
        elif isinstance(value, str) and decimal_regex.fullmatch(value):
            json_dict[key] = normalize_fraction(Decimal(value))
    return json_dict


def get_or_create_qs_attr(obj: Any, name: str) -> list:
    """Method that takes any object and a string and creates an empty list
    attr on the object if it doesn't already exist. Adds an "s" to the end
    of the name str if it doesn't end with one already. Returns the list attr,
    whether or not it is new or empty.

    Args:
        obj: Any
        name: str

    Returns:
        list: list attr on obj
    """

    qs_name = f"{name}s_qs" if not name.endswith("s") else f"{name}_qs"
    if not hasattr(obj, qs_name):
        setattr(obj, qs_name, [])
    return getattr(obj, qs_name)


def get_qs_or_set(obj: Any, name: str) -> Union[list, "QuerySet"]:
    """Method that attempts to get a prefetched QuerySet or list from an object
    based on a str. If the str doesn't end in "s", "s" will be added to the str
    to create the QuerySet's attr. If the attr doesn't exist, will attempt to fetch
    the str's _set object manager."""
    qs_name = f"{name}s_qs" if not name.endswith("s") else f"{name}_qs"
    return getattr(obj, qs_name) if hasattr(obj, qs_name) else getattr(obj, f"{name}_set").all()


def normalize_fraction(d):
    # https://stackoverflow.com/questions/11227620/drop-trailing-zeros-from-decimal
    normalized = d.normalize()
    _, _, exponent = normalized.as_tuple()  # sign, digit, exponent
    return normalized if exponent <= 0 else normalized.quantize(1)


def now_date() -> "date":
    return timezone.now().date()


def now_datetime() -> "datetime":
    return timezone.now()


def get_str_attrs(
    obj: Union["GoutHelperPatientModel", "GoutHelperAidModel", None] = None,
    patient: Union["GoutHelperPatientModel", None] = None,
    request_user: Union["User", None] = None,
) -> dict[str, str]:
    str_attrs = {}
    if patient:
        if request_user and request_user == patient:
            str_attrs.update(
                {
                    "query": "do",
                    "tobe": "are",
                    "tobe_past": "were",
                    "tobe_neg": "aren't",
                    "pos": "have",
                    "pos_past": "had",
                    "pos_neg": "don't have",
                    "pos_neg_past": "haven't had",
                    "subject": "you",
                    "subject_the": "you",
                    "subject_pos": "your",
                    "subject_the_pos": "your",
                    "gender_pos": "hers" if patient.gender.value else "his",
                    "gender_subject": "she" if patient.gender.value else "he",
                    "gender_ref": "her" if patient.gender.value else "him",
                }
            )
            str_attrs.update({key.capitalize(): val.capitalize() for key, val in str_attrs.items()})
        else:
            str_attrs.update(
                {
                    "query": "does",
                    "tobe": "is",
                    "tobe_past": "was",
                    "tobe_neg": "isn't",
                    "pos": "has",
                    "pos_past": "had",
                    "pos_neg": "doesn't have",
                    "pos_neg_past": "hasn't had",
                    "gender_pos": "her" if patient.gender.value else "his",
                    "gender_subject": "she" if patient.gender.value else "he",
                    "gender_ref": "her" if patient.gender.value else "him",
                }
            )
            str_attrs.update({key.capitalize(): val.capitalize() for key, val in str_attrs.items()})
            subject_dict = {
                "subject": str(patient),
                "subject_the": str(patient),
                "subject_pos": f"{str(patient)}'s",
                "subject_the_pos": f"{str(patient)}'s",
            }
            subject_dict.update({key.capitalize(): val for key, val in subject_dict.items()})
            str_attrs.update(subject_dict)
    else:
        str_attrs.update(
            {
                "query": "does",
                "tobe": "is",
                "tobe_past": "was",
                "tobe_neg": "isn't",
                "pos": "has",
                "pos_past": "had",
                "pos_neg": "doesn't have",
                "pos_neg_past": "hasn't had",
                "subject": "patient",
                "subject_the": "the patient",
                "subject_pos": "patient's",
                "subject_the_pos": "the patient's",
                "gender_pos": (
                    "hers"
                    if obj and obj.gender and obj.gender.value
                    else "his"
                    if obj and obj.gender
                    else "his or hers"
                ),
                "gender_subject": (
                    "she" if obj and obj.gender and obj.gender.value else "he" if obj and obj.gender else "he or she"
                ),
                "gender_ref": (
                    "her" if obj and obj.gender and obj.gender.value else "him" if obj and obj.gender else "him or her"
                ),
            }
        )
        str_attrs.update({key.capitalize(): val.capitalize() for key, val in str_attrs.items()})
    return str_attrs
