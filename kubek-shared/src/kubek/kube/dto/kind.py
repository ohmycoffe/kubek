import enum


class Kind(enum.StrEnum):
    DEPLOYMENT = "Deployment"
    STATEFULSET = "StatefulSet"
    DAEMONSET = "DaemonSet"
    WORKFLOWTEMPLATE = "WorkflowTemplate"
    CONFIG = "Config"
    NAMESPACE = "Namespace"
    POD = "Pod"
    SERVICE = "Service"
    SECRET = "Secret"
    CONFIGMAP = "ConfigMap"
