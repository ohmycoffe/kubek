# kubectl portfwd

## Usage

```bash
kubectl port-forward                                      # interactive: pick namespace → pick services
kubectl port-forward -n my-namespace                      # skip namespace prompt
kubectl port-forward -s auth-service -s cache-api         # skip interactive selection, forward specific services
kubectl port-forward -n my-namespace -s auth-service      # non-interactive: namespace + services fully specified
kubectl port-forward --config ~/.config/kpf/config.toml   # use a config file
kubectl port-forward -v / -vv                             # INFO / DEBUG logging
kubectl port-forward --help                               # full option reference
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


## License

MIT — see [LICENSE](LICENSE).
