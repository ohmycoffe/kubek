# kube-envx

kube-envx is a CLI tool for extracting and exporting environment variables from Kubernetes deployments and Argo WorkflowTemplates.
It provides a simplified facade over kubectl commands.

## Features

- List available Kubernetes services and Argo workers
- Extract environment variables from deployments and workflow templates
- Export environment variables in `.env` or JSON format
- Supports both services (deployments) and workers (workflow templates)
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

### Service Commands

List all available services in a namespace:

```bash
envx service list --namespace <namespace>
```

Get environment variables for a service:

```bash
envx service get <service_name> --namespace <namespace> --output env|json
```

### Worker Commands

List all available workers in a namespace:

```bash
envx worker list --namespace <namespace>
```

Get environment variables for a worker:

```bash
envx worker get <worker_name> --namespace <namespace> --output env|json
```

## Example

Export environment variables for a service as a dotenv file:

```bash
envx service get my-service --namespace kube-public --output env > .env
```

Export worker environment variables as JSON:

```bash
envx worker get my-worker --namespace kube-public --output json > worker-env.json
```

## Environment Variables

| Variable | Applies to | Description | Default |
|---|---|---|---|
| `ENVX_NAMESPACE_SERVICE` | `envx service` commands | Default Kubernetes namespace for service commands | `kube-public` |
| `ENVX_NAMESPACE_WORKER` | `envx worker` commands | Default Kubernetes namespace for worker commands | `kube-public` |

Note: the `--namespace` flag always takes precedence over the environment variable.

## Requirements

- Python 3.9+
- [kubectl](https://kubernetes.io/docs/tasks/tools/) installed and configured
- Access to the target Kubernetes cluster


## License

MIT License. See [LICENSE](LICENSE) for details.