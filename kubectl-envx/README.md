# kubectl envx

## Usage

Run without arguments for fully interactive mode:

```bash
kubectl envx
```

Or pass options directly to skip individual prompts:

```bash
kubectl envx --kind deployment --namespace my-namespace --name my-service
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
kubectl envx --kind deployment --name my-service --namespace prod > .env
```

Extract WorkflowTemplate env vars as JSON:

```bash
kubectl envx --kind workflowtemplate --name my-workflow --namespace argo --output json
```
