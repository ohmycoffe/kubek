import json
import os
import shutil
from datetime import datetime

from kubek.kube._infrastructure.client import KubernetesClient

client = KubernetesClient.from_config()


ns = "ns-kubek-shared"
deployments = client.get_deployments(namespace=ns)
services = client.get_services(namespace=ns)
secrets = client.get_secrets(namespace=ns)
configmaps = client.get_configmaps(namespace=ns)
workflows = client.get_workflowtemplates(namespace=ns)
namespaces = client.get_namespaces()


def serialize(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


DIRECTORY = "tmp_api-responses"


def write_to_file(name: str, data: dict):
    with open(f"{DIRECTORY}/{name}.json", "w") as f:
        f.write(json.dumps(data["items"], indent=2, default=serialize))


shutil.rmtree(DIRECTORY, ignore_errors=True)
os.makedirs(DIRECTORY, exist_ok=True)

write_to_file("Deployment", deployments)
write_to_file("Service", services)
write_to_file("Secret", secrets)
write_to_file("ConfigMap", configmaps)
write_to_file("WorkflowTemplate", workflows)
write_to_file("Namespace", namespaces)
