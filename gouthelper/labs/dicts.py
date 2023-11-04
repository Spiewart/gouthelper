from .choices import LabTypes, LowerLimits, Units, UpperLimits

LABS_LABTYPES_LOWER_LIMITS: dict[LabTypes, dict[Units, LowerLimits]] = {
    # First key/val in dict is default
    LabTypes.CREATININE: {Units.MGDL: LowerLimits.CREATININEMGDL},
    LabTypes.URATE: {Units.MGDL: LowerLimits.URATEMGDL},
}

LABS_LABTYPES_UPPER_LIMITS: dict[LabTypes, dict[Units, UpperLimits]] = {
    # First key/val in dict is default
    LabTypes.CREATININE: {Units.MGDL: UpperLimits.CREATININEMGDL},
    LabTypes.URATE: {Units.MGDL: UpperLimits.URATEMGDL},
}

LABS_LABTYPES_UNITS: dict[LabTypes, list[Units]] = {
    # First item in list is default
    LabTypes.CREATININE: [Units.MGDL],
    LabTypes.URATE: [Units.MGDL],
}
