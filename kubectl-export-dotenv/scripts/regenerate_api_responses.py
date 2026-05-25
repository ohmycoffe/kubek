import json
import os
import shutil

from kubek.kube import KubeFacade

kf = KubeFacade.from_config()

DIRECTORY = "tmp_api-responses"


resources = [
    "Deployment",
    "Service",
    "Secret",
    "ConfigMap",
    "WorkflowTemplate",
    "Namespace",
]
shutil.rmtree(DIRECTORY, ignore_errors=True)
os.makedirs(DIRECTORY, exist_ok=True)

for resource in resources:
    func = getattr(kf, resource.lower()).list
    print(f"Exporting {resource}s...")
    vals_dict = [
        el.model_dump(
            exclude_none=True, exclude_unset=True, exclude_computed_fields=True
        )
        for el in func()
    ]
    with open(f"{DIRECTORY}/{resource}.json", "w") as f:
        f.write(json.dumps(vals_dict, indent=2, sort_keys=True))
