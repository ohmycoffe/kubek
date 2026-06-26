import asyncio
import json
import os
import shutil
from datetime import datetime

from kubek.kube._infrastructure.client import KubernetesClient, KubeSession

NS = "ns-kubek-shared"
DIRECTORY = "tmp_api-responses"


def serialize(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def write_to_file(name: str, data: dict):
    with open(f"{DIRECTORY}/{name}.json", "w") as f:
        f.write(json.dumps(data["items"], indent=2, default=serialize))


async def _fetch_all() -> dict[str, dict]:
    async with await KubeSession.from_config() as session:
        client = KubernetesClient(session)
        return {
            "Deployment": await client.get_deployments(namespace=NS),
            "StatefulSet": await client.get_statefulsets(namespace=NS),
            "DaemonSet": await client.get_daemonsets(namespace=NS),
            "Job": await client.get_jobs(namespace=NS),
            "CronJob": await client.get_cronjobs(namespace=NS),
            "ReplicaSet": await client.get_replica_sets(namespace=NS),
            "Service": await client.get_services(namespace=NS),
            "Secret": await client.get_secrets(namespace=NS),
            "ConfigMap": await client.get_configmaps(namespace=NS),
            "WorkflowTemplate": await client.get_workflowtemplates(namespace=NS),
            "Namespace": await client.get_namespaces(),
        }


def main() -> None:
    responses = asyncio.run(_fetch_all())
    shutil.rmtree(DIRECTORY, ignore_errors=True)
    os.makedirs(DIRECTORY, exist_ok=True)
    for name, data in responses.items():
        write_to_file(name, data)


if __name__ == "__main__":
    main()
