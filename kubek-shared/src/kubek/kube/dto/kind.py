import enum


class Kind(enum.StrEnum):
    DEPLOYMENT = "Deployment"
    WORKFLOWTEMPLATE = "WorkflowTemplate"
    CONFIG = "Config"
    NAMESPACE = "Namespace"
    SERVICE = "Service"
    SECRET = "Secret"
    CONFIGMAP = "ConfigMap"
