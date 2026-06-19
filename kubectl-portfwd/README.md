# kubectl portfwd

## Usage

```bash
kubectl portfwd                                              # interactive: pick types, then targets
kubectl portfwd -f .portfwd-plan                             # forward targets from a spec file
kubectl portfwd -t kube-public/svc/auth-service              # forward a single service
kubectl portfwd -t kube-public/pod/worker-xyz                # forward a single pod
kubectl portfwd -t kube-public/svc/auth-service:8080         # specify remote port explicitly
kubectl portfwd -t kube-public/svc/auth-service:8080::50000  # specify remote and local ports
kubectl portfwd -t kube-public/svc/auth -t kube-public/pod/worker-xyz  # forward multiple targets
kubectl portfwd -v / -vv                                     # INFO / DEBUG logging
kubectl portfwd --context my-cluster                         # use a specific kube context
kubectl portfwd --kubeconfig ~/.kube/other-config            # use a specific kubeconfig file
kubectl portfwd --help                                       # full option reference
```

`--file` and `--target` are mutually exclusive. Every target names its type
explicitly with a `svc/` or `pod/` segment (aliases: `service`/`services`,
`po`/`pods`); there is no implicit default.

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

List targets to forward, one per line. Blank lines and `#` comments are ignored.
The filename is arbitrary; `.portfwd-plan` is a common convention in this repo.

```
# backend
ns-kubectl-portfwd/svc/httpd:8080::50000
ns-kubectl-portfwd/pod/nginx:80::50001
```

Each line uses the same format as `--target`: `[namespace/]type/name[:remote_port][::local_port]`, where `type` is `svc` or `pod`.

When ports are omitted, the remote port is read from the target (single-port services/pods only) and the local port is chosen automatically.

Interactive mode (no `--file` or `--target`) prompts for the types to forward, then namespaces, then the targets.
