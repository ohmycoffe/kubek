# kubectl export-dotenv

Export environment variables from Kubernetes Deployments and Argo WorkflowTemplates into a `.env` file or JSON format.

## Usage

Run without arguments for fully interactive mode:

```bash
kubectl export-dotenv
```

Or pass options directly to skip individual prompts:

```bash
kubectl export-dotenv --kind deployment --namespace my-namespace --name my-service
```

### Options

| Option | Default | Description |
|---|---|---|
| `--kind` | — | `deployment` or `workflowtemplate`. Prompted if omitted. |
| `--namespace` | — | Kubernetes namespace. Prompted if omitted. |
| `--context` | current | Kubernetes context from kubeconfig. |
| `--kubeconfig` | — | Path to kubeconfig file (optional). |
| `--name` | — | Resource name. Prompted if omitted. |
| `--output` | `env` | Output format: `env` or `json`. |
| `-v` / `-vv` | — | Verbosity: info / debug. |

## Examples

Export env vars for a deployment to a dotenv file:

```bash
kubectl export-dotenv --kind deployment --name my-service --namespace prod > .env
```

Extract WorkflowTemplate env vars as JSON:

```bash
kubectl export-dotenv --kind workflowtemplate --name my-workflow --namespace argo --output json
```
