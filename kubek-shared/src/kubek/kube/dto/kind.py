import enum


class Kind(enum.StrEnum):
    DEPLOYMENT = "Deployment"
    STATEFULSET = "StatefulSet"
    DAEMONSET = "DaemonSet"
    REPLICASET = "ReplicaSet"
    JOB = "Job"
    CRONJOB = "CronJob"
    WORKFLOWTEMPLATE = "WorkflowTemplate"
    CONFIG = "Config"
    NAMESPACE = "Namespace"
    POD = "Pod"
    SERVICE = "Service"
    SECRET = "Secret"
    CONFIGMAP = "ConfigMap"
