# kubectl portfwd

## Usage

```bash
kubectl portfwd                                             # interactive: pick group or services
kubectl portfwd -g ddr                                     # run a predefined service group
kubectl portfwd -s kube-public/auth-service                # forward a single service
kubectl portfwd --include-namespace my-namespace           # filter services to a namespace (interactive mode)
kubectl portfwd --config ~/.kube/portfwd.yaml              # use a specific config file
kubectl portfwd -v / -vv                                   # INFO / DEBUG logging
kubectl portfwd --help                                     # full option reference
```

## Configuration

Default path: `~/.kube/portfwd.yaml` (or override with `KPF_CONFIG`).

```yaml
port_forwards:
  kube-public:
    auth-service: "50000:80"    # local:remote
    user-service: "50001:8080"
    ddr-service:  "50002:8080"

groups:
  backend:
    - kube-public/auth-service
    - kube-public/user-service
  ddr:
    - kube-public/auth-service
    - kube-public/ddr-service
```

When a config is present the CLI shows a group picker in interactive mode:

```
? Select group:
  ◉ backend
  ◉ ddr
  ◉ all services
  ◉ custom selection
```

If no config file exists, the tool falls back to kubectl service discovery (namespace prompt → service checkbox).

Option precedence: CLI flag → `KPF_CONFIG` env var → default path.

---

## Breaking changes (v0.5)

| What | Before | After |
|------|--------|-------|
| Config format | TOML (`~/.config/kpf/config.toml`) | YAML (`~/.kube/portfwd.yaml`) |
| Config schema | `[[ports]]` list | `port_forwards` + `groups` sections |
| `--namespace / -n` | Filter by namespace | **Removed** — use `--include-namespace` |
| `--service / -s` | Bare service name(s), multi-value | `namespace/service`, single value |

No automatic migration is provided. To migrate, create `~/.kube/portfwd.yaml` with the new schema and remove the old `~/.config/kpf/config.toml`.
