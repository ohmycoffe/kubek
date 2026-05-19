<div align="center">

# kubek

> `kubectl` plugins for friendlier Kubernetes interactions.

**kubek** (**kub**ernetes **e**xtension **k**it) is a collection of CLI tools that plug into `kubectl` and add interactive, developer-friendly shortcuts on top of it.

![CI](https://github.com/ohmycoffe/kubek/actions/workflows/ci.yml/badge.svg?branch=main)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

## Plugins

### 🔌 portfwd — Interactive port forwarding

Forwarding ports to Kubernetes services usually means running a separate `kubectl port-forward` command for each service, keeping track of which local port maps to what, and restarting them when they die. **portfwd** (**port** **f**or**w**ar**d**) replaces all of that with a single interactive command — pick your services, and it handles the rest.

- Fuzzy-search namespaces and services interactively
- Forward multiple services simultaneously in one command
- Live status table with real-time updates when a process dies
- Pin preferred local ports per service in a TOML config
- Fallback to a random free port if the preferred port is taken
- Inform user which services are currently forwarded and on which ports

![portfwd demo](https://github.com/user-attachments/assets/98e91737-8bed-4b2d-a760-4d685ecdb1a9)

→ [Full documentation](kubectl-portfwd/README.md)

---

### 📦 export-dotenv — Export env vars from Kubernetes manifests

Getting credentials out of a running deployment usually means digging through `kubectl get deployment -o yaml`, copying values by hand, and reformatting them into a `.env` file. **export-dotenv** (**env**ironment e**x**porter) does it in one command — pick any Deployment or Argo WorkflowTemplate you have access to and get its env vars exported instantly.

- Fully interactive (fuzzy-search, arrow key navigation)
- Output as `.env` or JSON
- Pipe directly: `kubectl export-dotenv ... > .env` to produce a dotenv file

![export-dotenv demo](https://github.com/user-attachments/assets/05ed2fad-6a51-4816-a1b3-24ddc9520dec)

→ [Full documentation](kubectl-export-dotenv/README.md)

---

## Installation

### Prerequisites

- Python 3.11+
- `kubectl` installed and configured with cluster access (recommended version 1.36+)

### Install

The recommended way to install kubek is with [pipx](https://pipx.pypa.io/), which installs it in an isolated environment and automatically makes the plugin executables available on your PATH:

```bash
# Latest stable release (recommended)
pipx install kubek

# Newest development version
pipx install git+https://github.com/ohmycoffe/kubek.git
```

If you use pip or another package manager, make sure the installation's `bin/` directory is on your PATH — `kubectl` discovers plugins by scanning PATH for executables prefixed with `kubectl-`.

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
