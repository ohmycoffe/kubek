class ExportDotenvError(Exception):
    """Base error for export-dotenv. Failed to export environment variables."""


class ResourceNotFoundError(ExportDotenvError):
    """Requested Kubernetes resource was not found."""


class NoResourcesFoundError(ExportDotenvError):
    """No Kubernetes resources found."""


class UnsupportedKindError(ExportDotenvError):
    """Resource kind is not supported."""


class UnsupportedFormatError(ExportDotenvError):
    """Resource format is not supported."""


class UnsupportedResourceError(ExportDotenvError):
    """Resource is not supported by the tool."""
