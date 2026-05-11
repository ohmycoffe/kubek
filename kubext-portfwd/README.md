# kubectl portfwd

> Interactive `kubectl port-forward` — fuzzy-search namespaces and services,
> forward multiple ports at once, watch a live status table.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

![demo](docs/assets/demo.gif)

---

## Features

- Fuzzy-search namespaces and services interactively
- Forward multiple services simultaneously in one command
- Live status table with real-time updates when a process dies
- Pin preferred local ports per service in a TOML config
- Fallback to a random free port if the preferred port is taken
- Inform user which services are currently forwarded and on which ports

## Quick start

**Install with [pipx](https://pipx.pypa.io/) (recommended)**

```bash
pipx install kubectl portfwd
```

Or install from source:

```bash
pipx install git+https://github.com/ohmycoffe/kubectl portfwd.git
```

**Requirements:** Python 3.11+, `kubectl` installed and pointing at a cluster.

## Usage

```bash
kubepf                                      # interactive: pick namespace → pick services
kubepf -n my-namespace                      # skip namespace prompt
kubepf -s auth-service -s cache-api        # skip interactive selection, forward specific services
kubepf -n my-namespace -s auth-service     # non-interactive: namespace + services fully specified
kubepf --config ~/.config/kpf/config.toml  # use a config file
kubepf -v / -vv                             # INFO / DEBUG logging
kubepf --help                               # full option reference
```

## Configuration

Default path: `~/.config/kpf/config.toml` (or set `KPF_CONFIG`).

```toml
default_namespace = "kube-public"

[[ports]]
name        = "auth-service"
namespace   = "kube-public"
remote_port = 80
local_port  = 50000

[[ports]]
name        = "user-service"
namespace   = "kube-public"
remote_port = 8080
local_port  = 50001
```

Option precedence: CLI flag → `KPF_CONFIG` env var → config file → built-in default.

## Development

```bash
poetry install           # install deps
poetry run kubepf --help
poetry run pytest        # run unit tests
```

**Local test cluster with [kind](https://kind.sigs.k8s.io/):**

```bash
scripts/run-local-cluster.sh  # creates cluster + applies test manifests
```

**Regenerate demo GIF** (requires [VHS](https://github.com/charmbracelet/vhs)):

```bash
vhs docs/tapes/demo.tape     # outputs to docs/assets/demo.gif
```

## License

MIT — see [LICENSE](LICENSE).
