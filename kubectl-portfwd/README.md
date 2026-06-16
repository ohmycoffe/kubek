# kubectl portfwd

## Usage

```bash
kubectl portfwd                                            # interactive: pick services
kubectl portfwd -f .portfwd-plan                           # forward services from a spec file
kubectl portfwd -s kube-public/auth-service                # forward a single service
kubectl portfwd -s kube-public/auth-service:8080           # specify remote port explicitly
kubectl portfwd -s kube-public/auth-service:8080::50000    # specify remote and local ports
kubectl portfwd -s kube-public/auth-service -s kube-public/user-service  # forward multiple services
kubectl portfwd -v / -vv                                   # INFO / DEBUG logging
kubectl portfwd --context my-cluster                       # use a specific kube context
kubectl portfwd --kubeconfig ~/.kube/other-config          # use a specific kubeconfig file
kubectl portfwd --help                                     # full option reference
```

`--file` and `--service` are mutually exclusive.

### Context

Use the plugin’s `--context` flag (after `portfwd`):

```bash
kubectl portfwd --context my-cluster
kubectl portfwd -f .portfwd-plan --context staging
```

That flag is passed to every `kubectl` call the plugin makes (list/get and each `port-forward` subprocess).


### Kubeconfig

Pass `--kubeconfig` to use a non-default config file (single path only):

```bash
kubectl portfwd --kubeconfig ~/.kube/staging-config
kubectl portfwd --kubeconfig ~/.kube/staging-config --context staging
```

The path is forwarded to every `kubectl` call, including each `port-forward` subprocess.

## Spec file

List services to forward, one per line. Blank lines and `#` comments are ignored.
The filename is arbitrary; `.portfwd-plan` is a common convention in this repo.

```
# backend
ns-kubectl-portfwd/httpd:8080::50000
ns-kubectl-portfwd/nginx:80::50001
```

Each line uses the same format as `--service`: `[namespace/]name[:remote_port][::local_port]`.

When ports are omitted, remote port is read from the Kubernetes Service (single-port services only) and local port is chosen automatically.

Interactive mode (no `--file` or `--service`) prompts for namespaces, then services to forward.
