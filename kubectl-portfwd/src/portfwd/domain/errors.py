class PortForwardError(Exception):
    """Base error for portfwd. Failed to set up or run port-forwards."""


class SpecFileLoadError(PortForwardError):
    """Spec file could not be loaded or parsed."""


class EmptySpecFileError(PortForwardError):
    """Spec file has no target entries."""


class InvalidTargetSpecError(PortForwardError):
    """A target spec did not match the expected format."""


class MissingNamespaceError(PortForwardError):
    """No namespace was provided and none could be resolved from kubeconfig."""


class ServiceNotFoundError(PortForwardError):
    """A Kubernetes Service was not found in the given namespace."""


class NoServicePortsError(PortForwardError):
    """A Kubernetes Service has no ports declared."""


class AmbiguousServicePortError(PortForwardError):
    """A Kubernetes Service has multiple ports and none was selected."""


class PodNotFoundError(PortForwardError):
    """A Kubernetes Pod was not found in the given namespace."""


class NoPodPortsError(PortForwardError):
    """A Kubernetes Pod declares no container ports and none was specified."""


class AmbiguousPodPortError(PortForwardError):
    """A Kubernetes Pod declares multiple container ports and none was selected."""


class DeploymentNotFoundError(PortForwardError):
    """A Kubernetes Deployment was not found in the given namespace."""


class NoDeploymentPortsError(PortForwardError):
    """A Kubernetes Deployment declares no container ports and none was specified."""


class AmbiguousDeploymentPortError(PortForwardError):
    """A Kubernetes Deployment declares multiple container ports and none was selected."""


class NoTargetsFoundError(PortForwardError):
    """Target discovery returned no services, pods, or deployments for the selected namespaces."""


class NoSelectionError(PortForwardError):
    """The user exited an interactive prompt without selecting anything."""


class PortForwardStartError(PortForwardError):
    """kubectl port-forward subprocess failed to start."""
