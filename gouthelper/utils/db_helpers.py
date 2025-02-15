# Separate file for methods that interact with the database
# Avoids circular import errors
from typing import TYPE_CHECKING, Any, Union

from django.db import IntegrityError, transaction  # pylint: disable=e0401 # type: ignore

from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.tests.factories import MedHistoryFactory

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # type: ignore

    from ..medhistorys.models import MedHistory

    User = get_user_model()


def create_onetoone_factory_atomic(factory, **kwargs):
    with transaction.atomic():
        try:
            return factory(**kwargs)
        except IntegrityError as exc:
            integrityerror = exc
    if integrityerror:
        # Check if duplicate key error is due to the onetoone object already existing
        if "already exists" in str(integrityerror):
            return factory._meta.model.objects.get(**kwargs)  # pylint: disable=W0212
        raise integrityerror


def get_or_create_attr(obj: Any, attr: str, attr_obj: Any, commit: bool = False) -> Any:
    """Method that takes any object, a string, and an object and creates an
    attr on the object if it doesn't already exist. If the attr is already
    set, it returns the attr. If commit is True, it saves the object.

    Args:
        obj: Any
        attr: str
        attr_obj: Any
        commit: bool

    Returns:
        Any: attr on obj

    Raises:
        ValueError: If the attr already exists on the object and is not equal to attr_obj.
    """

    if not getattr(obj, attr, None):
        setattr(obj, attr, attr_obj)
        if commit:
            obj.save()
        return getattr(obj, attr)
    else:
        obj_attr = getattr(obj, attr)
        if obj_attr and obj_attr != attr_obj:
            raise ValueError(f"{attr} already exists ({obj_attr}) on {obj} and is not equal to {attr_obj}.")
        return obj_attr


def get_or_create_medhistory_atomic(
    medhistorytype: MedHistoryTypes,
    patient: "User",
) -> Union["MedHistory", None]:
    return MedHistoryFactory(
        medhistorytype=medhistorytype,
        patient=patient,
    )
