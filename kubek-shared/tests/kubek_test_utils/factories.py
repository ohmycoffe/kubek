def make_deployment(name: str, namespace: str) -> dict:
    return {
        "metadata": {"name": name, "namespace": namespace},
        "spec": {"template": {"spec": {"containers": []}}},
        "kind": "Deployment",
    }


def make_statefulset(name: str, namespace: str) -> dict:
    return {
        "metadata": {"name": name, "namespace": namespace},
        "spec": {"template": {"spec": {"containers": []}}},
        "kind": "StatefulSet",
    }


def make_daemonset(name: str, namespace: str) -> dict:
    return {
        "metadata": {"name": name, "namespace": namespace},
        "spec": {"template": {"spec": {"containers": []}}},
        "kind": "DaemonSet",
    }


def make_job(name: str, namespace: str) -> dict:
    return {
        "metadata": {"name": name, "namespace": namespace},
        "spec": {"template": {"spec": {"containers": []}}},
        "kind": "Job",
    }


def make_secret(name: str, namespace: str) -> dict:
    return {
        "metadata": {"name": name, "namespace": namespace},
        "data": {"key": "cGFzc3dvcmQ="},
        "kind": "Secret",
    }


def make_configmap(name: str, namespace: str) -> dict:
    return {
        "metadata": {"name": name, "namespace": namespace},
        "data": {"key": "value"},
        "kind": "ConfigMap",
    }


def make_workflowtemplate(name: str, namespace: str) -> dict:
    return {
        "metadata": {"name": name, "namespace": namespace},
        "spec": {"template": {"spec": {"containers": []}}},
        "kind": "WorkflowTemplate",
    }


def make_namespace(name: str) -> dict:
    return {
        "metadata": {"name": name, "namespace": name},
        "kind": "Namespace",
    }


def make_service(name: str, namespace: str) -> dict:
    return {
        "metadata": {"name": name, "namespace": namespace},
        "spec": {"ports": []},
        "kind": "Service",
    }
