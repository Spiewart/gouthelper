class EmptyRelatedModel(Exception):
    """Exception raised by GoutHelper views when a related model
    has an empty value but is still a valid form. Used to indicate
    not to save or potentially to delete the related model."""

    pass


class Continue(Exception):
    """Exception raised by GoutHelper when some element of the program wants
    the for loop that called the function raising the exception to continue."""

    pass


class GoutHelperValidationError(Exception):
    def __init__(self, message, errors):
        super().__init__(message)

        self.errors = errors
