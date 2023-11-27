class EmptyRelatedModel(Exception):
    """Exception raised by Gouthelper views when a related model
    has an empty value but is still a valid form. Used to indicate
    not to save or potentially to delete the related model."""

    pass
