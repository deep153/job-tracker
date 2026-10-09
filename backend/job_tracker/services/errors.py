"""Errors services raise for requests that can't be done, each with a message meant for the user."""


class ServiceError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(ServiceError):
    pass


class InvalidRequestError(ServiceError):
    """The request is well formed but its content can't be accepted."""


class ConflictError(ServiceError):
    """The request can't be done in the current state."""


class TooLargeError(ServiceError):
    pass


class SetupIncompleteError(ServiceError):
    """A run can't start until these setup steps are done."""

    def __init__(self, missing: list[str]) -> None:
        first = missing[0]
        super().__init__(f"Finish setting up first: {first[0].lower()}{first[1:]}")
        self.missing = missing


class RunAlreadyActiveError(ConflictError):
    def __init__(self) -> None:
        super().__init__("A run is already in progress.")
