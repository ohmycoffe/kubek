# kube-envx

kube-envx is a CLI tool for extracting and exporting environment variables from Kubernetes deployments and Argo WorkflowTemplates.
It provides a simplified facade over kubectl commands.

## Features

- Extract environment variables from Kubernetes deployments and Argo WorkflowTemplates
- Export environment variables in `.env` or JSON format
- Interactive namespace and service selection when not specified
- Simple, scriptable CLI interface

## Installation


### Install with pipx (recommended)

You can install kube-envx globally using [pipx](https://pipx.pypa.io/):

```bash
pipx install git+https://github.com/ohmycoffe/kube-envx.git
```

### Install with Poetry (development)

This project uses [Poetry](https://python-poetry.org/) for dependency management.

```bash
poetry install
```

## Usage

You can run the CLI using Poetry:

```bash
poetry run envx --help
```

### Service

Run without arguments to select namespace and service interactively:

```bash
envx service
```

Or pass them directly:

```bash
envx service <service_name> --namespace <namespace> --output env|json
```

### Worker

Run without arguments to select namespace and worker interactively:

```bash
envx worker
```

Or pass them directly:

```bash
envx worker <worker_name> --namespace <namespace> --output env|json
```

## Example

Export environment variables for a service as a dotenv file:

```bash
envx service my-service --namespace kube-public --output env > .env
```

Export worker environment variables as JSON:

```bash
envx worker my-worker --namespace kube-public --output json > worker-env.json
```

## Environment Variables

| Variable | Applies to | Description |
|---|---|---|---|
| `ENVX_NAMESPACE_SERVICE` | `envx service` | Default Kubernetes namespace for service commands |
| `ENVX_NAMESPACE_WORKER` | `envx worker` | Default Kubernetes namespace for worker commands |

Note: the `--namespace` flag always takes precedence over the environment variable.

## Requirements

- Python 3.10+
- [kubectl](https://kubernetes.io/docs/tasks/tools/) installed and configured
- Access to the target Kubernetes cluster


## License

MIT License. See [LICENSE](LICENSE) for details.
