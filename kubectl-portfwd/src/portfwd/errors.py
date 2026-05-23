class PortForwardError(Exception):
    """Base error for portfwd. Failed to set up or run port-forwards."""


class ConfigLoadError(PortForwardError):
    """Config file could not be loaded or parsed."""


class InvalidServiceSpecError(PortForwardError):
    """A --service argument did not match the expected format."""


class UnknownGroupError(PortForwardError):
    """The requested --group is not defined in the config."""


class NoGroupsDefinedError(PortForwardError):
    """The config file has no groups, but a group was requested."""


class MissingNamespaceError(PortForwardError):
    """No namespace was provided and none could be resolved from kubeconfig."""


class ServiceNotFoundError(PortForwardError):
    """A Kubernetes Service was not found in the given namespace."""


class NoServicePortsError(PortForwardError):
    """A Kubernetes Service has no ports declared."""


class AmbiguousServicePortError(PortForwardError):
    """A Kubernetes Service has multiple ports and none was selected."""


class NoServicesFoundError(PortForwardError):
    """Service discovery returned no services for the selected namespaces."""


class NoSelectionError(PortForwardError):
    """The user exited an interactive prompt without selecting anything."""


class PortForwardStartError(PortForwardError):
    """kubectl port-forward subprocess failed to start."""
