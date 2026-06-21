<div align="center">

# kubek

> `kubectl` plugins for friendlier Kubernetes interactions.

**kubek** (**kub**ernetes **e**xtension **k**it) is a collection of CLI tools that plug into `kubectl` and add interactive, developer-friendly shortcuts on top of it.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![CI](https://github.com/ohmycoffe/kubek/actions/workflows/ci.yml/badge.svg?branch=main)
[![coverage](https://img.shields.io/endpoint?url=https%3A%2F%2Fgist.githubusercontent.com%2Fohmycoffe%2Fdde6edd698fb5f25063c01f49ba251d7%2Fraw%2Fcoverage.json)](https://gist.github.com/ohmycoffe/dde6edd698fb5f25063c01f49ba251d7)
</div>

---

## Plugins

### 🔌 portfwd — Interactive port forwarding

**portfwd** (**port** **f**or**w**ar**d**) manages many `kubectl port-forward` sessions as one. You choose what to forward — Services, Pods, Deployments, StatefulSets, DaemonSets, or Jobs — and it runs and supervises every session under a single live dashboard.

At its core it does three things:

- **Select** targets — interactively, via `-t`, or from a spec file ([example](./kubectl-portfwd/docs/.portfwd-spec))
- **Forward** them all at once — the same target always gets the same local port across new runs
- **Supervise** them — a live status view with automatic reconnection

```bash
kubectl portfwd # interactive mode
kubectl portfwd -t ns1/svc/auth-service -t ns2/pod/worker-xyz # via CLI options (no prompts)
kubectl portfwd -f .portfwd-plan # via spec file (no prompts)
```

![portfwd demo](https://github.com/user-attachments/assets/a4686a82-b1d6-46ef-99bc-88fbbfe31c79)
| Resource | Status |
|---|:---|
| CronJob | ❌ |
| DaemonSet | ✅ |
| Deployment | ✅ |
| Job | ✅ |
| Pod | ✅ |
| ReplicaSet | ❌ |
| StatefulSet | ✅ |

→ [Full documentation](kubectl-portfwd/README.md)

---

### 📦 export-dotenv — Export env vars from cluster resources

**export-dotenv** reads the environment of a running Kubernetes resource and hands it back ready to use — no manual YAML digging or copy-paste.

At its core it does three things:

- **Pick** a resource — a Deployment, StatefulSet, DaemonSet, Job, or Argo WorkflowTemplate, interactively or by flag
- **Resolve** its full environment — including values referenced from ConfigMaps and Secrets
- **Emit** it as `.env` or JSON — to stdout for piping

```bash
kubectl export-dotenv
kubectl export-dotenv --kind deployment --name my-service --namespace prod > .env
kubectl export-dotenv --kind workflowtemplate --name my-workflow --output json
```

![export-dotenv demo](https://github.com/user-attachments/assets/420e1004-71f0-457e-aa83-44dbf828011e)

#### Supported Resources

| Resource | Status |
|---|:---|
| ConfigMap | ✅ |
| CronJob | ❌ |
| DaemonSet | ✅ |
| Deployment | ✅ |
| Job | ✅ |
| Pod | ✅ |
| ReplicaSet | ❌ |
| Secret | ✅ |
| StatefulSet | ✅ |

→ [Full documentation](kubectl-export-dotenv/README.md)

---

## Installation

### Prerequisites

- Python 3.11+
- `kubectl` installed and configured with cluster access

### Install

The recommended way to install kubek is with [pipx](https://pipx.pypa.io/) or [uv](https://docs.astral.sh/uv/), which installs it in an isolated environment and automatically makes the plugin executables available on your PATH:

#### pipx
```bash
pipx install kubek
```

#### uv
```bash
uv tool install kubek
```

### Verify

After installing, confirm both plugins are available:

```bash
kubectl portfwd --help
kubectl export-dotenv --help
```

See each plugin's README for full usage details.

---

## License

MIT — see [LICENSE](LICENSE).
