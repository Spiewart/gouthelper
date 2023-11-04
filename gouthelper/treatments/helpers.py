from datetime import timedelta

from .choices import Freqs, Treatments


def treatments_stringify_trt_tuple(trt: Treatments, dosing: dict) -> tuple[str, dict]:
    """Returns a tuple of treatment str and dict of strings for a trt_dict."""
    for key, val in dosing.items():
        if isinstance(val, timedelta):
            dosing.update({key: f"{val.days} days"})
        elif val in Freqs.values:
            dosing.update({key: Freqs(val).label})
        elif not val:
            dosing.update({key: None})
        else:
            dosing.update({key: str(val)})
    return Treatments(trt).label, dosing
