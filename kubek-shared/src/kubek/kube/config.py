import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ResolvedKubeConfig:
    context: str
    namespace: str
    kubeconfig: str | os.PathLike | None = None


@dataclass(frozen=True)
class KubeConfig:
    context: str | None = None
    namespace: str | None = None
    kubeconfig: str | os.PathLike[str] | None = None
