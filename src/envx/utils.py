from __future__ import annotations

import base64


def decode(val: str) -> str:
    decoded_bytes = base64.b64decode(val)
    return decoded_bytes.decode("utf-8")


def export_as_dotenv(vals: dict[str, str], service_name: str | None = None) -> str:
    sorted_list = sorted(vals.items(), key=lambda x: x[0])
    res = []
    if service_name:
        res.append(f"# {service_name}")
    for key, value in sorted_list:
        res.append(f"{key}={value}")
    return "\n".join(res)
