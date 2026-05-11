<div align="center">

# kubext

> `kubectl` plugins for friendlier Kubernetes interactions.

A collection of CLI tools that plug into `kubectl` and add interactive, developer-friendly shortcuts on top of it.

![CI](https://github.com/ohmycoffe/kubext/actions/workflows/ci.yml/badge.svg?branch=main)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

## Plugins

### 🔌 portfwd — Interactive port forwarding

Interactively forward multiple ports at once and watch a live status table.

- Fuzzy-search namespaces and services interactively
- Forward multiple services simultaneously
- Live status table with real-time updates
- Pin preferred local ports per service in a TOML config

![portfwd demo](demo_kubext_pfwd.gif)

→ [Full documentation](kubext-portfwd/README.md)

---

### 📦 envx — Export env vars from Kubernetes manifests

Pull environment variables out of Kubernetes Deployments and Argo WorkflowTemplates and pipe them straight to a dotenv file.

- Fully interactive (fuzzy-search, arrow key navigation, multi-select)
- Output as `.env` or JSON
- Pipe directly: `kenvx ... > .env` to produce a dotenv file

![envx demo](demo_kubext_envx.gif)

→ [Full documentation](kubext-envx/README.md)

---

## Installation

Both plugins require **Python 3.10+** and `kubectl` configured with cluster access. Install with [pipx](https://pipx.pypa.io/) (recommended):

```bash
# portfwd
pipx install kubectl-portfwd

# envx
pipx install git+https://github.com/ohmycoffe/kube-envx.git
```

See each plugin's README for full install and usage details.

---

## License

MIT
