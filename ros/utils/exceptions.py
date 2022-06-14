# Sources Exceptions:
class SourcesAPIException(Exception):
    """Raise when Insights Sources API behaves unexpectedly."""


class SourcesAPINotOkStatus(SourcesAPIException):
    """Raise when Sources API returns a not-200 status."""


class SourcesAPINotJsonContent(SourcesAPIException):
    """Raise when Sources API returns not-JSON content."""
