# kubectl portfwd

## Usage

```bash
kubectl portfwd                                            # interactive: pick group or services
kubectl portfwd -g backend                                 # run a predefined service group
kubectl portfwd -s kube-public/auth-service                # forward a single service
kubectl portfwd -s kube-public/auth-service:8080           # specify remote port explicitly
kubectl portfwd -s kube-public/auth-service:8080::50000    # specify remote and local ports
kubectl portfwd -s kube-public/auth-service -s kube-public/user-service  # forward multiple services
kubectl portfwd -c ~/.kube/portfwd                         # use a specific config file
kubectl portfwd -v / -vv                                   # INFO / DEBUG logging
kubectl portfwd --context my-cluster                       # use a specific kube context
kubectl portfwd --kubeconfig ~/.kube/other-config          # use a specific kubeconfig file
kubectl portfwd --help                                     # full option reference
```

### Context

Use the plugin’s `--context` flag (after `portfwd`):

```bash
kubectl portfwd --context my-cluster
kubectl portfwd -g backend --context staging
```

That flag is passed to every `kubectl` call the plugin makes (list/get and each `port-forward` subprocess).

`kubectl --context my-cluster portfwd` is kubectl’s global flag. Depending on your kubectl version it may or may not reach the plugin executable; prefer `kubectl portfwd --context …` for predictable behavior.

### Kubeconfig

Pass `--kubeconfig` to use a non-default config file (single path only):

```bash
kubectl portfwd --kubeconfig ~/.kube/staging-config
kubectl portfwd --kubeconfig ~/.kube/staging-config --context staging
```

The path is forwarded to every `kubectl` call, including each `port-forward` subprocess.

## Configuration

Default path: `~/.kube/portfwd` (or override with `KUBEK_PORTFWD_CONFIG`).

```yaml
defaults:
  - name: auth-service
    namespace: kube-public
    local_port: 50000
    remote_port: 80
  - name: user-service
    namespace: kube-public
    local_port: 50001
    remote_port: 8080

groups:
  - name: backend
    services:
      - name: auth-service-2
        namespace: kube-public
        remote_port: 80
        local_port: 50010


```

When a config is present the CLI shows a group picker in interactive mode:

```
? Select a group to run:
  ◉ backend
  ◉ backend-2
  ◉ custom   (interactive: select services to forward)
```

If no config file exists, the tool falls back to kubectl service discovery (namespace prompt → service checkbox).

The `--service` / `-s` flag accepts the format `[namespace/]name[:remote_port][::local_port]`. Remote and local ports are optional — if omitted, the config defaults are used, or a free port is chosen automatically.

Option precedence: CLI flag → `KUBEK_PORTFWD_CONFIG` env var → default path.

---

## Breaking changes (v0.5)

| What | Before | After |
|------|--------|-------|
| Config format | TOML (`~/.config/kpf/config.toml`) | YAML (`~/.kube/portfwd`) |
| Config schema | `[[ports]]` list | `defaults` + `groups` sections |
| `--namespace / -n` | Filter by namespace | **Removed** — pick namespaces in the interactive UI |
| `--service / -s` | Bare service name(s), multi-value | `namespace/service`, can be repeated |

No automatic migration is provided. To migrate, create `~/.kube/portfwd` with the new schema and remove the old `~/.config/kpf/config.toml`.
