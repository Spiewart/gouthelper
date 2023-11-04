from typing import TYPE_CHECKING

from .choices import Ethnicitys

if TYPE_CHECKING:
    from ..ethnicitys.models import Ethnicity


def ethnicitys_hlab5801_risk(ethnicity: "Ethnicity") -> bool:
    """Method that determines whether an object object has an ethnicity and whether
    it is an ethnicity that has a high prevalence of HLA-B*58:01 genotype."""
    return (
        ethnicity.value == Ethnicitys.AFRICANAMERICAN
        or ethnicity.value == Ethnicitys.HANCHINESE
        or ethnicity.value == Ethnicitys.KOREAN
        or ethnicity.value == Ethnicitys.THAI
    )
