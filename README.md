# kube-kenvx

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Extract and export environment variables from Kubernetes Deployments and Argo WorkflowTemplates — interactively or scripted.

![demo](https://github.com/user-attachments/assets/4c492cd0-87ab-4c97-90b5-fa5e3a43db82)

## Installation

**pipx**:

```bash
pipx install git+https://github.com/ohmycoffe/kube-envx.git
```

**Poetry** (development):

```bash
poetry install
```

## Usage

Run without arguments for fully interactive mode:

```bash
kenvx
```

Or pass options directly to skip individual prompts:

```bash
kenvx --kind deployment --namespace my-namespace --name my-service
```

### Options

| Option | Default | Description |
|---|---|---|
| `--kind` | — | `deployment` or `workflowtemplate`. Prompted if omitted. |
| `--namespace` | — | Kubernetes namespace. Prompted if omitted. |
| `--name` | — | Resource name. Prompted if omitted. |
| `--output` | `env` | Output format: `env` or `json`. |
| `-v` / `-vv` | — | Verbosity: info / debug. |

### Environment variables

| Variable | Description |
|---|---|
| `ENVX_NAMESPACE` | Default namespace, overridden by `--namespace`. |

## Examples

Export env vars for a deployment to a dotenv file:

```bash
kenvx --kind deployment --name my-service --namespace prod > .env
```

Extract WorkflowTemplate env vars as JSON:

```bash
kenvx --kind workflowtemplate --name my-workflow --namespace argo --output json
```

## Requirements

- Python 3.10+
- [`kubectl`](https://kubernetes.io/docs/tasks/tools/) configured with cluster access

## License

MIT — see [LICENSE](LICENSE).
