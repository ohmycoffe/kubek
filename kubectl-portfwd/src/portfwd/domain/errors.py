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


class StatefulSetNotFoundError(PortForwardError):
    """A Kubernetes StatefulSet was not found in the given namespace."""


class NoStatefulSetPortsError(PortForwardError):
    """A Kubernetes StatefulSet declares no container ports and none was specified."""


class AmbiguousStatefulSetPortError(PortForwardError):
    """A Kubernetes StatefulSet declares multiple container ports and none was selected."""


class DaemonSetNotFoundError(PortForwardError):
    """A Kubernetes DaemonSet was not found in the given namespace."""


class NoDaemonSetPortsError(PortForwardError):
    """A Kubernetes DaemonSet declares no container ports and none was specified."""


class AmbiguousDaemonSetPortError(PortForwardError):
    """A Kubernetes DaemonSet declares multiple container ports and none was selected."""


class ReplicaSetNotFoundError(PortForwardError):
    """A Kubernetes ReplicaSet was not found in the given namespace."""


class NoReplicaSetPortsError(PortForwardError):
    """A Kubernetes ReplicaSet declares no container ports and none was specified."""


class AmbiguousReplicaSetPortError(PortForwardError):
    """A Kubernetes ReplicaSet declares multiple container ports and none was selected."""


class JobNotFoundError(PortForwardError):
    """A Kubernetes Job was not found in the given namespace."""


class NoJobPortsError(PortForwardError):
    """A Kubernetes Job declares no container ports and none was specified."""


class AmbiguousJobPortError(PortForwardError):
    """A Kubernetes Job declares multiple container ports and none was selected."""


class CronJobNotFoundError(PortForwardError):
    """A Kubernetes CronJob was not found in the given namespace."""


class NoCronJobPortsError(PortForwardError):
    """A Kubernetes CronJob declares no container ports and none was specified."""


class AmbiguousCronJobPortError(PortForwardError):
    """A Kubernetes CronJob declares multiple container ports and none was selected."""


class NoTargetsFoundError(PortForwardError):
    """Target discovery returned no services, pods, deployments, statefulsets, daemonsets, replicasets, jobs, or cronjobs for the selected namespaces."""


class NoSelectionError(PortForwardError):
    """The user exited an interactive prompt without selecting anything."""


class PortForwardStartError(PortForwardError):
    """kubectl port-forward subprocess failed to start."""


class DuplicateLocalPortError(PortForwardError):
    """Two or more plans resolve to the same local port."""
