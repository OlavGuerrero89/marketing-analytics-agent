"""Application-specific exceptions."""


class CubeClientError(Exception):
    """Base error for Cube communication failures."""


class CubeConnectionError(CubeClientError):
    """Cube could not be reached."""


class CubeTimeoutError(CubeClientError):
    """Cube did not respond within the configured timeout."""


class CubeResponseError(CubeClientError):
    """Cube returned an error or an invalid response."""


class LanguageModelConfigurationError(Exception):
    """The language model cannot start with the supplied configuration."""


class LanguageModelResponseError(Exception):
    """The language model returned an invalid structured response."""


class ResultValidationError(Exception):
    """Cube data violates the expected analytical contract."""