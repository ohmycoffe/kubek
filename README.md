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

Interactive `kubectl port-forward` — fuzzy-search namespaces and services,
forward multiple ports at once, watch a live status table.

- Fuzzy-search namespaces and services interactively
- Forward multiple services simultaneously in one command
- Live status table with real-time updates when a process dies
- Pin preferred local ports per service in a TOML config
- Fallback to a random free port if the preferred port is taken
- Inform user which services are currently forwarded and on which ports


![portfwd demo](https://github.com/user-attachments/assets/18e1b913-b1f4-420a-8d76-2a717d604b3e)

→ [Full documentation](kubext-portfwd/README.md)

---

### 📦 envx — Export env vars from Kubernetes manifests

Pull environment variables out of Kubernetes Deployments and Argo WorkflowTemplates and pipe them straight to a dotenv file.

- Fully interactive (fuzzy-search, arrow key navigation, multi-select)
- Output as `.env` or JSON
- Pipe directly: `kubectl envx ... > .env` to produce a dotenv file

![envx demo](https://github.com/user-attachments/assets/232d778b-77db-4de6-9b79-929a525419d4)

→ [Full documentation](kubext-envx/README.md)

---

## Installation

Both plugins require **Python 3.12+** and `kubectl` configured with cluster access. Install with [pipx](https://pipx.pypa.io/) or your preferred Python package manager:

```bash
pipx install git+https://github.com/ohmycoffe/kubext.git

```

Note: to register the plugins with `kubectl`, you need to add the installation directory to your PATH. Installing with pipx handles this for you, but if you use another method, make sure plugin executables are discoverable in your PATH.

See each plugin's README for full install and usage details.

---

## License

MIT
