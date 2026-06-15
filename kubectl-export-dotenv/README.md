# kubectl export-dotenv

Export environment variables from Kubernetes Deployments and Argo WorkflowTemplates into a `.env` file or JSON format. Values from ConfigMap and Secret references are resolved from the cluster.

## Usage

Run without arguments for interactive mode (pick kind and resource name):

```bash
kubectl export-dotenv
```

Or pass options directly to skip prompts:

```bash
kubectl export-dotenv --kind deployment --namespace my-namespace --name my-service
```

Namespace defaults to the current kubectl context namespace (or `default`). Set it with `kubectl config set-context --current --namespace=my-namespace` if you omit `--namespace`.

### Context

```bash
kubectl export-dotenv --context my-cluster
kubectl export-dotenv --kind deployment --name my-service --context staging
```

### Kubeconfig

```bash
kubectl export-dotenv --kubeconfig ~/.kube/staging-config
kubectl export-dotenv --kubeconfig ~/.kube/staging-config --context staging
```

### Options

| Option | Default | Description |
|---|---|---|
| `--kind` | — | `deployment` or `workflowtemplate`. Prompted if omitted. |
| `--namespace` | context namespace | Kubernetes namespace (`default` if unset in kubeconfig). |
| `--context` | current | Kubernetes context from kubeconfig. |
| `--kubeconfig` | — | Path to kubeconfig file (optional). |
| `--name` | — | Resource name. Prompted if omitted. |
| `--output` | `env` | Output format: `env` or `json`. |
| `-v` / `-vv` | — | Verbosity: info / debug. |

### Limitations

- Deployments must have exactly one container.
- WorkflowTemplates: env vars are merged from all container templates.

## Examples

Export env vars for a deployment to a dotenv file:

```bash
kubectl export-dotenv --kind deployment --name my-service --namespace prod > .env
```

Extract WorkflowTemplate env vars as JSON:

```bash
kubectl export-dotenv --kind workflowtemplate --name my-workflow --namespace argo --output json
```
